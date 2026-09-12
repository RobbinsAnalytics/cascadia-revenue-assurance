"""build_entitlement.py -- PATH 1: a record-at-a-time state machine, pure Python.

Written from governance/entitlement-rules.md. Section numbers in comments
refer to that document. This file imports nothing from src/validate_measures.py
(Path 2) and shares no helper with it (D12).

How it works
    Transactions are sorted by (received_date, transaction_id) and fed one at
    a time to a per-subscription state object. Before each transaction the
    subscription is rolled forward through any term boundaries that fall
    before that day (rule 2.2: boundary first), manufacturing renewals or
    ending the subscription as the rules say. The state object mutates and
    emits term instances and daily quantity SEGMENTS (start, end, quantity,
    term_seq). Months are then cut from the segments.

Outputs (main)
    data/conformed/fact_order_event.csv        observed; every transaction, with accepted/reason
    data/conformed/fact_entitlement_term.csv   observed+derived, flagged per row
    data/conformed/fact_billable_month.csv     derived
    data/conformed/fact_deferral.csv           derived; M-05's lineage
    data/conformed/fact_invoice_line.csv       derived roll-up
    data/conformed/measures_manifest.json      every M- value at as-of
    data/conformed/manifest.json               what was written, grain, disclosure
    governance/reconciliation.md               D10 tie-out, per invoice line

Entry points
    derive(events, subs_meta, customers_meta, as_of) -> dict of row lists
    derive_from_files(events_csv, subscriptions_csv, as_of, customers_csv=None)
        the signature src/test_golden.py calls on both paths

    python src/build_entitlement.py
"""

from __future__ import annotations

import calendar
import csv
import json
import math
import sys
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = Path(__file__).resolve().parent.parent
RAW = REPO / "data" / "raw"
CONF = REPO / "data" / "conformed"
RECON_PATH = REPO / "governance" / "reconciliation.md"

# Rules section 0, restated deliberately. No shared constants module (D12).
RATE_CENTS = {"annual": 1000, "monthly": 1200}

VALID_TYPES = ("NEW", "ADD", "REDUCE", "CANCEL")
VALID_TERMS = ("annual", "monthly")


# ---------------------------------------------------------------------------
# date arithmetic -- rules 3.2, 3.3, 3.4
# ---------------------------------------------------------------------------

def _clamp(y: int, m: int, d: int) -> date:
    return date(y, m, min(d, calendar.monthrange(y, m)[1]))


def add_months_clamped(d: date, n: int) -> date:
    y = d.year + (d.month - 1 + n) // 12
    m = (d.month - 1 + n) % 12 + 1
    return _clamp(y, m, d.day)


def add_years_clamped(d: date, n: int) -> date:
    return _clamp(d.year + n, d.month, d.day)


def term_end_for(start: date, term_type: str) -> date:
    """The last day of a term opened on `start`, computed from ITS OWN start (3.4)."""
    nxt = add_years_clamped(start, 1) if term_type == "annual" else add_months_clamped(start, 1)
    return nxt - timedelta(days=1)


def month_end(d: date) -> date:
    return date(d.year, d.month, calendar.monthrange(d.year, d.month)[1])


def next_month_start(d: date) -> date:
    return date(d.year + (d.month == 12), d.month % 12 + 1, 1)


def cents(licence_days: int, rate_cents: int, days_in_month: int) -> int:
    """Rule 6.3: round half-up, once, in integer arithmetic."""
    return (licence_days * rate_cents * 2 + days_in_month) // (2 * days_in_month)


# ---------------------------------------------------------------------------
# state
# ---------------------------------------------------------------------------

@dataclass
class Term:
    seq: int
    start: date
    end: date
    opening: int
    derived: bool
    opened_by: int | None
    closing: int | None = None
    pending_target: int | None = None
    cancel_pending: bool = False
    last_accepted_tid: int | None = None   # last accepted ADD/REDUCE/CANCEL in this term (8.1)


@dataclass
class Segment:
    start: date
    end: date | None
    qty: int
    term_seq: int


@dataclass
class Sub:
    key: str
    term_type: str
    terms: list[Term] = field(default_factory=list)
    effective: int = 0
    register: int = 0
    pending: int | None = None          # the quantity the next term opens at, if below effective
    cancel_pending: bool = False
    ended_on: date | None = None        # last effective day, once a cancelled term has ended
    segments: list[Segment] = field(default_factory=list)
    register_history: list[tuple[date, int]] = field(default_factory=list)
    deferrals: list[dict] = field(default_factory=list)

    @property
    def cur(self) -> Term:
        return self.terms[-1]

    # -- segments ----------------------------------------------------------------
    def _open_segment(self, start: date, qty: int, seq: int) -> None:
        if self.segments and self.segments[-1].end is None:
            last = self.segments[-1]
            if last.start == start:
                # same-day change (NEW then ADD, or a boundary-day ADD, G10): overwrite
                last.qty, last.term_seq = qty, seq
                return
            last.end = start - timedelta(days=1)
        self.segments.append(Segment(start, None, qty, seq))

    def _close_segment(self, end: date) -> None:
        if self.segments and self.segments[-1].end is None:
            self.segments[-1].end = end

    # -- boundaries: rules 2.2, 3.5, 3.6, 3.8, 4.4 ---------------------------------
    def roll_forward(self, upto: date) -> None:
        """Process every term boundary that falls strictly before `upto`."""
        while self.ended_on is None and self.cur.end < upto:
            t = self.cur
            t.closing = self.effective
            t.pending_target = self.pending if (self.pending is not None and self.pending != self.effective) else None
            t.cancel_pending = self.cancel_pending
            if self.cancel_pending:
                self.ended_on = t.end
                self._close_segment(t.end)
                return
            start = t.end + timedelta(days=1)
            opening = self.pending if self.pending is not None else self.effective
            nt = Term(seq=t.seq + 1, start=start, end=term_end_for(start, self.term_type),
                      opening=opening, derived=True, opened_by=None)
            self.terms.append(nt)
            self._open_segment(start, opening, nt.seq)
            self.effective = opening
            self.pending = None

    def finish(self, as_of: date) -> None:
        self.roll_forward(as_of)
        if self.ended_on is None:
            t = self.cur
            t.closing = self.effective
            t.pending_target = self.pending if (self.pending is not None and self.pending != self.effective) else None
            t.cancel_pending = self.cancel_pending
            self._close_segment(min(t.end, as_of))

    def register_at(self, d: date) -> int:
        q = 0
        for when, val in self.register_history:
            if when <= d:
                q = val
            else:
                break
        return q


# ---------------------------------------------------------------------------
# the state machine -- rules 1.2, 1.3, 2.1, 4.x
# ---------------------------------------------------------------------------

def _validate(ev: dict, as_of: date) -> None:
    if ev["transaction_type"] not in VALID_TYPES:
        raise ValueError(f"transaction {ev['transaction_id']}: unknown type {ev['transaction_type']!r}")
    if ev["requested_quantity"] < 0:
        raise ValueError(f"transaction {ev['transaction_id']}: negative quantity")
    if ev["transaction_type"] == "NEW":
        if ev["requested_quantity"] < 1:
            raise ValueError(f"transaction {ev['transaction_id']}: NEW with quantity < 1")
        if ev["term_type"] not in VALID_TERMS:
            raise ValueError(f"transaction {ev['transaction_id']}: NEW without a valid term_type")
    if ev["transaction_type"] == "CANCEL" and ev["requested_quantity"] != 0:
        raise ValueError(f"transaction {ev['transaction_id']}: CANCEL must carry quantity 0")
    if ev["received_date"] > as_of:
        raise ValueError(f"transaction {ev['transaction_id']}: received after the as-of date")


def run_state_machine(events: list[dict], as_of: date) -> tuple[list[dict], dict[str, Sub]]:
    seen_ids: set[int] = set()
    subs: dict[str, Sub] = {}
    order_events: list[dict] = []

    for ev in sorted(events, key=lambda e: (e["received_date"], e["transaction_id"])):  # 2.1
        _validate(ev, as_of)
        if ev["transaction_id"] in seen_ids:
            raise ValueError(f"duplicate transaction_id {ev['transaction_id']}")
        seen_ids.add(ev["transaction_id"])

        tid, d, key = ev["transaction_id"], ev["received_date"], ev["subscription_key"]
        ttype, q = ev["transaction_type"], ev["requested_quantity"]
        out = dict(ev)
        out["accepted"], out["rejection_reason"] = True, None
        order_events.append(out)

        def reject(reason: str) -> None:
            out["accepted"], out["rejection_reason"] = False, reason

        st = subs.get(key)

        if ttype == "NEW":
            if st is not None:
                reject("DUPLICATE_NEW")
                continue
            st = Sub(key=key, term_type=ev["term_type"])
            st.terms.append(Term(seq=1, start=d, end=term_end_for(d, st.term_type),
                                 opening=q, derived=False, opened_by=tid))
            st.effective = st.register = q
            st.register_history.append((d, q))
            st._open_segment(d, q, 1)
            subs[key] = st
            continue

        if st is None:
            reject("UNKNOWN_SUBSCRIPTION")
            continue

        st.roll_forward(d)                                  # 2.2 boundary first

        if st.cancel_pending:                               # after-cancel reasons
            reject({"ADD": "ADD_AFTER_CANCEL", "REDUCE": "REDUCE_AFTER_CANCEL",
                    "CANCEL": "DUPLICATE_CANCEL"}[ttype])
            continue

        if ttype == "CANCEL":                               # 4.3
            st.cancel_pending = True
            st.register = 0
            st.register_history.append((d, 0))
            st.cur.last_accepted_tid = tid
            st.deferrals.append({"transaction_id": tid, "transaction_type": "CANCEL",
                                 "received_date": d, "term_seq": st.cur.seq,
                                 "landing_date": st.cur.end + timedelta(days=1)})
            continue

        if q == 0:
            reject("REDUCE_TO_ZERO")
            continue
        if q == st.register:                                # 4.5
            reject("NOOP_QUANTITY")
            continue

        # accepted quantity order -- 4.2
        st.register = q
        st.register_history.append((d, q))
        st.cur.last_accepted_tid = tid
        if q > st.effective:
            st.effective = q
            st.pending = None
            st._open_segment(d, q, st.cur.seq)
        elif q < st.effective:
            st.pending = q
            st.deferrals.append({"transaction_id": tid, "transaction_type": ttype,
                                 "received_date": d, "term_seq": st.cur.seq,
                                 "landing_date": st.cur.end + timedelta(days=1)})
        else:
            st.pending = None

    for st in subs.values():
        st.finish(as_of)
    return order_events, subs


# ---------------------------------------------------------------------------
# facts from state -- rules 5, 6, 7, 8
# ---------------------------------------------------------------------------

def cut_months(st: Sub, meta: dict, as_of: date) -> list[dict]:
    rate = RATE_CENTS[st.term_type]
    acc: dict[str, dict] = {}
    for seg in st.segments:
        s, e = seg.start, seg.end
        if e is None or e < s:
            continue
        m = date(s.year, s.month, 1)
        while m <= e:
            me = month_end(m)
            lo, hi = max(s, m), min(e, me)
            if lo <= hi:
                mk = f"{m.year:04d}-{m.month:02d}"
                a = acc.setdefault(mk, {"licence_days": 0, "effective_days": 0, "seqs": set(),
                                        "qty_at_end": 0, "month_end": me,
                                        "dim": calendar.monthrange(m.year, m.month)[1]})
                days = (hi - lo).days + 1
                a["licence_days"] += seg.qty * days
                a["effective_days"] += days
                a["seqs"].add(seg.term_seq)
                if hi == me:
                    a["qty_at_end"] = seg.qty
            m = next_month_start(m)

    rows = []
    for mk in sorted(acc):
        a = acc[mk]
        eff_end = a["qty_at_end"]
        reg_end = st.register_at(a["month_end"])
        gap = eff_end - reg_end
        rows.append({
            "subscription_key": st.key, "month_key": mk,
            "customer_key": meta["customer_key"], "partner_id": meta["partner_id"],
            "channel": meta["channel"], "term_type": st.term_type,
            "days_in_month": a["dim"], "effective_days": a["effective_days"],
            "licence_days": a["licence_days"],
            "licence_months": f"{a['licence_days'] / a['dim']:.6f}",
            "rate_cents": rate,
            "billable_amount_cents": cents(a["licence_days"], rate, a["dim"]),
            "register_quantity_at_month_end": reg_end,
            "effective_quantity_at_month_end": eff_end,
            "gap_quantity": gap,
            "gap_amount_cents": gap * rate,
            "derived": 1 not in a["seqs"],                          # 5.2
            "straddles_boundary": len(a["seqs"]) > 1,               # 5.3
            "is_partial_month": a["licence_days"] != a["dim"] * eff_end,  # 6.5
        })
    return rows


def derive(events: list[dict], subs_meta: dict[str, dict], customers_meta: dict[str, dict],
           as_of: date) -> dict[str, list[dict]]:
    order_events, subs = run_state_machine(events, as_of)

    terms, months, deferrals = [], [], []
    for key in sorted(subs):
        st = subs[key]
        meta = subs_meta.get(key)
        if meta is None:
            raise KeyError(f"subscription {key} has events but no dimension row")
        for t in st.terms:
            terms.append({
                "subscription_key": key, "term_seq": t.seq, "term_start": t.start, "term_end": t.end,
                "opening_quantity": t.opening, "closing_quantity": t.closing,
                "pending_reduction_target": t.pending_target, "cancel_pending": t.cancel_pending,
                "derived": t.derived, "opened_by_transaction_id": t.opened_by,
            })
        months.extend(cut_months(st, meta, as_of))
        term_by_seq = {t.seq: t for t in st.terms}
        for dfr in st.deferrals:
            t = term_by_seq[dfr["term_seq"]]
            landed = dfr["landing_date"] <= as_of
            if dfr["transaction_type"] == "CANCEL":
                took = landed
            else:
                took = landed and t.last_accepted_tid == dfr["transaction_id"] and not t.cancel_pending
            deferrals.append({
                "transaction_id": dfr["transaction_id"], "subscription_key": key,
                "term_type": st.term_type, "transaction_type": dfr["transaction_type"],
                "received_date": dfr["received_date"], "term_seq": dfr["term_seq"],
                "landing_date": dfr["landing_date"],
                "days_pending": (dfr["landing_date"] - dfr["received_date"]).days,
                "landed_by_as_of": landed, "took_effect_as_scheduled": took,
            })

    # invoice roll-up -- rule 7. Amount from the row's own (dim_subscription) attributes;
    # constituents re-derived through dim_customer. The tie-out proves that join.
    lines: dict[tuple, dict] = {}
    for r in months:
        k = (r["month_key"], r["channel"], r["partner_id"] if r["channel"] == "partner" else "DIRECT",
             r["customer_key"] if r["channel"] == "direct" else "")
        line = lines.setdefault(k, {"month_key": k[0], "channel": k[1], "partner_id": k[2],
                                    "customer_key": k[3], "invoice_amount_cents": 0,
                                    "constituent_count": 0, "constituent_sum_cents": 0})
        line["invoice_amount_cents"] += r["billable_amount_cents"]
    for r in months:
        c = customers_meta[r["customer_key"]]
        k = (r["month_key"], c["channel"], c["partner_id"] if c["channel"] == "partner" else "DIRECT",
             r["customer_key"] if c["channel"] == "direct" else "")
        line = lines.setdefault(k, {"month_key": k[0], "channel": k[1], "partner_id": k[2],
                                    "customer_key": k[3], "invoice_amount_cents": 0,
                                    "constituent_count": 0, "constituent_sum_cents": 0})
        line["constituent_count"] += 1
        line["constituent_sum_cents"] += r["billable_amount_cents"]
    invoice_lines = []
    for k in sorted(lines):
        line = lines[k]
        line["tie_out_difference_cents"] = line["invoice_amount_cents"] - line["constituent_sum_cents"]
        line["invoice_line_key"] = f"{line['month_key']}|{line['partner_id']}|{line['customer_key']}"
        invoice_lines.append(line)

    return {"order_events": order_events, "terms": terms, "billable_months": months,
            "deferrals": deferrals, "invoice_lines": invoice_lines}


# ---------------------------------------------------------------------------
# measures -- governance/metric_register.md
# ---------------------------------------------------------------------------

def nearest_rank(values: list[int], p: float) -> int | None:
    if not values:
        return None
    s = sorted(values)
    return s[max(1, math.ceil(p * len(s))) - 1]


def compute_measures(out: dict, as_of: date) -> dict:
    months, ev, dfr, inv = out["billable_months"], out["order_events"], out["deferrals"], out["invoice_lines"]
    mk = f"{as_of.year:04d}-{as_of.month:02d}"
    at = [r for r in months if r["month_key"] == mk]
    by_tt = lambda rows, tt: [r for r in rows if r["term_type"] == tt]  # noqa: E731

    m01 = sum(r["effective_quantity_at_month_end"] for r in at)
    m02 = sum(r["register_quantity_at_month_end"] for r in at)
    gap_lic = sum(r["gap_quantity"] for r in at)
    gap_cents = sum(r["gap_amount_cents"] for r in at)
    bill_at = sum(r["billable_amount_cents"] for r in at)
    total_cents = sum(r["billable_amount_cents"] for r in months)
    partial_cents = sum(r["billable_amount_cents"] for r in months if r["is_partial_month"])
    rejected = [e for e in ev if not e["accepted"]]
    reasons: dict[str, int] = {}
    for e in rejected:
        reasons[e["rejection_reason"]] = reasons.get(e["rejection_reason"], 0) + 1

    def m05(tt: str) -> dict:
        rows = by_tt(dfr, tt)
        days = [r["days_pending"] for r in rows]
        return {"n": len(rows),
                "median_days": nearest_rank(days, 0.5), "p90_days": nearest_rank(days, 0.9),
                "max_days": max(days) if days else None,
                "landed_by_as_of": sum(1 for r in rows if r["landed_by_as_of"]),
                "took_effect_as_scheduled": sum(1 for r in rows if r["took_effect_as_scheduled"]),
                "backlog_cents_at_as_of": sum(r["gap_amount_cents"] for r in by_tt(at, tt))}

    return {
        "as_of_date": as_of.isoformat(),
        "M-01_effective_licences_at_as_of": m01,
        "M-02_register_licences_at_as_of": m02,
        "M-03_entitlement_gap": {
            "licences_at_as_of": gap_lic,
            "cents_at_as_of": gap_cents,
            "backlog_share_of_as_of_month_billable": (gap_cents / bill_at) if bill_at else None,
            "subscription_months_total": len(months),
            "subscription_months_with_gap": sum(1 for r in months if r["gap_quantity"] > 0),
            "subscription_months_with_gap_share": (sum(1 for r in months if r["gap_quantity"] > 0) / len(months)) if months else None,
            "cents_at_as_of_by_term_type": {tt: sum(r["gap_amount_cents"] for r in by_tt(at, tt)) for tt in ("annual", "monthly")},
            "annual_share_of_backlog_cents": (sum(r["gap_amount_cents"] for r in by_tt(at, "annual")) / gap_cents) if gap_cents else None,
            "gap_cents_all_months": sum(r["gap_amount_cents"] for r in months),
        },
        "M-04_prorated_revenue": {
            "billable_cents_all_months": total_cents,
            "billable_cents_at_as_of_month": bill_at,
            "partial_month_cents": partial_cents,
            "partial_month_share": (partial_cents / total_cents) if total_cents else None,
            "by_term_type_cents": {tt: sum(r["billable_amount_cents"] for r in by_tt(months, tt)) for tt in ("annual", "monthly")},
            "by_channel_cents": {ch: sum(r["billable_amount_cents"] for r in months if r["channel"] == ch) for ch in ("partner", "direct")},
        },
        "M-05_deferral_exposure": {tt: m05(tt) for tt in ("annual", "monthly")},
        "M-06_derived_share": {
            "rows_total": len(months),
            "rows_derived": sum(1 for r in months if r["derived"]),
            "rows_derived_share": (sum(1 for r in months if r["derived"]) / len(months)) if months else None,
            "cents_derived": sum(r["billable_amount_cents"] for r in months if r["derived"]),
            "cents_derived_share": (sum(r["billable_amount_cents"] for r in months if r["derived"]) / total_cents) if total_cents else None,
            "terms_total": len(out["terms"]),
            "terms_derived": sum(1 for t in out["terms"] if t["derived"]),
        },
        "M-07_rejected_transaction_rate": {
            "received": len(ev), "rejected": len(rejected),
            "rate": (len(rejected) / len(ev)) if ev else None,
            "by_reason": dict(sorted(reasons.items())),
        },
        "M-08_invoice_tie_out": {
            "invoice_lines": len(inv),
            "lines_with_nonzero_tie_out": sum(1 for l in inv if l["tie_out_difference_cents"] != 0),
            "partner_lines": sum(1 for l in inv if l["channel"] == "partner"),
            "direct_lines": sum(1 for l in inv if l["channel"] == "direct"),
            "invoice_cents_total": sum(l["invoice_amount_cents"] for l in inv),
        },
    }


# ---------------------------------------------------------------------------
# io
# ---------------------------------------------------------------------------

def read_events(path: Path) -> list[dict]:
    rows = []
    with open(path, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            rows.append({
                "transaction_id": int(r["transaction_id"]),
                "received_date": date.fromisoformat(r["received_date"]),
                "subscription_key": r["subscription_key"],
                "transaction_type": r["transaction_type"],
                "requested_quantity": int(r["requested_quantity"]),
                "term_type": r.get("term_type") or None,
                "source": r.get("source") or None,
            })
    return rows


def read_meta(subscriptions_csv: Path, customers_csv: Path | None) -> tuple[dict, dict]:
    subs_meta, customers_meta = {}, {}
    with open(subscriptions_csv, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            subs_meta[r["subscription_key"]] = {"customer_key": r["customer_key"],
                                                "partner_id": r["partner_id"], "channel": r["channel"]}
            if customers_csv is None:
                customers_meta[r["customer_key"]] = {"partner_id": r["partner_id"], "channel": r["channel"]}
    if customers_csv is not None:
        with open(customers_csv, newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                customers_meta[r["customer_key"]] = {"partner_id": r["partner_id"], "channel": r["channel"]}
    return subs_meta, customers_meta


def derive_from_files(events_csv: Path, subscriptions_csv: Path, as_of: date,
                      customers_csv: Path | None = None) -> dict[str, list[dict]]:
    subs_meta, customers_meta = read_meta(subscriptions_csv, customers_csv)
    return derive(read_events(events_csv), subs_meta, customers_meta, as_of)


def _fmt(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, date):
        return v.isoformat()
    return "" if v is None else v


def write_csv(path: Path, rows: list[dict], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(columns)
        for r in rows:
            w.writerow([_fmt(r.get(c)) for c in columns])


def dollars(c: int) -> str:
    sign = "-" if c < 0 else ""
    return f"{sign}${abs(c) // 100:,}.{abs(c) % 100:02d}"


def render_reconciliation(out: dict, measures: dict, as_of: date, disclosure: str) -> str:
    inv = out["invoice_lines"]
    m08 = measures["M-08_invoice_tie_out"]
    partner = [l for l in inv if l["channel"] == "partner"]
    direct = [l for l in inv if l["channel"] == "direct"]
    lines = [
        "# Reconciliation — invoice lines against their constituent subscription-months (D10)",
        "",
        f"*Generated by `src/build_entitlement.py`. As-of **{as_of.isoformat()}**. Do not hand-edit; rebuild.*",
        "",
        f"> **{disclosure}**",
        "",
        "Every invoice line is a roll-up of subscription-month lines (Partner: one line per "
        "partner × month; Direct: one line per customer × month). `invoice_amount` is summed "
        "from each subscription-month's own channel attributes; `constituent_sum` is re-derived "
        "by joining each subscription-month to its line through `dim_customer`. The difference "
        "must be zero on every line. **It is published even where it is zero** (PRINCIPLES rule 9): "
        "the value is the discipline of checking, not the size of the gap found.",
        "",
        "| | |",
        "|---|---|",
        f"| Invoice lines | **{m08['invoice_lines']:,}** ({m08['partner_lines']:,} partner × month, {m08['direct_lines']:,} customer × month) |",
        f"| Lines with non-zero tie-out | **{m08['lines_with_nonzero_tie_out']:,}** |",
        f"| Invoice total, all lines | {dollars(m08['invoice_cents_total'])} |",
        f"| Subscription-month total (M-04) | {dollars(measures['M-04_prorated_revenue']['billable_cents_all_months'])} |",
        "",
        "## Partner lines (partner × month)",
        "",
        "| Month | Partner | Invoice amount | Constituents | Constituent sum | Difference |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for l in partner:
        lines.append(f"| {l['month_key']} | `{l['partner_id']}` | {dollars(l['invoice_amount_cents'])} | "
                     f"{l['constituent_count']:,} | {dollars(l['constituent_sum_cents'])} | "
                     f"{dollars(l['tie_out_difference_cents'])} |")
    lines += [
        "",
        "## Direct lines (customer × month)",
        "",
        "| Month | Customer | Invoice amount | Constituents | Constituent sum | Difference |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for l in direct:
        lines.append(f"| {l['month_key']} | `{l['customer_key']}` | {dollars(l['invoice_amount_cents'])} | "
                     f"{l['constituent_count']:,} | {dollars(l['constituent_sum_cents'])} | "
                     f"{dollars(l['tie_out_difference_cents'])} |")
    lines += ["", f"*{disclosure} Revenue share, settlement and currency are out of scope (D10).*", ""]
    return "\n".join(lines)


def main() -> int:
    raw_manifest = json.loads((RAW / "manifest.json").read_text(encoding="utf-8"))
    as_of = date.fromisoformat(raw_manifest["as_of_date"])
    disclosure = raw_manifest["disclosure"]

    out = derive_from_files(RAW / "order_events.csv", CONF / "dim_subscription.csv", as_of,
                            customers_csv=CONF / "dim_customer.csv")
    measures = compute_measures(out, as_of)

    write_csv(CONF / "fact_order_event.csv", out["order_events"],
              ["transaction_id", "received_date", "subscription_key", "transaction_type",
               "requested_quantity", "term_type", "source", "accepted", "rejection_reason"])
    write_csv(CONF / "fact_entitlement_term.csv", out["terms"],
              ["subscription_key", "term_seq", "term_start", "term_end", "opening_quantity",
               "closing_quantity", "pending_reduction_target", "cancel_pending", "derived",
               "opened_by_transaction_id"])
    write_csv(CONF / "fact_billable_month.csv", out["billable_months"],
              ["subscription_key", "month_key", "customer_key", "partner_id", "channel", "term_type",
               "days_in_month", "effective_days", "licence_days", "licence_months", "rate_cents",
               "billable_amount_cents", "register_quantity_at_month_end",
               "effective_quantity_at_month_end", "gap_quantity", "gap_amount_cents", "derived",
               "straddles_boundary", "is_partial_month"])
    write_csv(CONF / "fact_deferral.csv", out["deferrals"],
              ["transaction_id", "subscription_key", "term_type", "transaction_type", "received_date",
               "term_seq", "landing_date", "days_pending", "landed_by_as_of", "took_effect_as_scheduled"])
    write_csv(CONF / "fact_invoice_line.csv", out["invoice_lines"],
              ["invoice_line_key", "month_key", "channel", "partner_id", "customer_key",
               "invoice_amount_cents", "constituent_count", "constituent_sum_cents",
               "tie_out_difference_cents"])

    measures_doc = {"module": "cascadia-revenue-assurance", "disclosure": disclosure,
                    "built_by": "src/build_entitlement.py (Path 1)", "seed": raw_manifest["seed"],
                    "measures": measures}
    (CONF / "measures_manifest.json").write_text(json.dumps(measures_doc, indent=2) + "\n",
                                                 encoding="utf-8", newline="\n")

    conf_manifest = {
        "module": "cascadia-revenue-assurance", "as_of_date": as_of.isoformat(),
        "disclosure": disclosure, "seed": raw_manifest["seed"],
        "tables": {
            "dim_date.csv": {"status": "derived", "grain": "one row per day in the window"},
            "dim_term_type.csv": {"status": "observed", "grain": "one row per term type"},
            "dim_partner.csv": {"status": "observed", "grain": "one row per partner, plus DIRECT"},
            "dim_customer.csv": {"status": "observed", "grain": "one row per customer"},
            "dim_subscription.csv": {"status": "observed", "grain": "one row per subscription; register attributes as of the as-of date"},
            "fact_order_event.csv": {"status": "observed", "grain": "one row per transaction received", "rows": len(out["order_events"])},
            "fact_entitlement_term.csv": {"status": "observed and derived, flagged per row", "grain": "one row per subscription x term instance", "rows": len(out["terms"])},
            "fact_billable_month.csv": {"status": "derived", "grain": "one row per subscription x calendar month with >= 1 effective day", "rows": len(out["billable_months"])},
            "fact_deferral.csv": {"status": "derived", "grain": "one row per accepted REDUCE or CANCEL", "rows": len(out["deferrals"])},
            "fact_invoice_line.csv": {"status": "derived roll-up", "grain": "partner x month (Partner) or customer x month (Direct)", "rows": len(out["invoice_lines"])},
            "measures_manifest.json": {"status": "derived", "grain": "every M- value at as-of"},
        },
    }
    (CONF / "manifest.json").write_text(json.dumps(conf_manifest, indent=2) + "\n",
                                        encoding="utf-8", newline="\n")
    RECON_PATH.write_text(render_reconciliation(out, measures, as_of, disclosure),
                          encoding="utf-8", newline="\n")

    m = measures
    print(f"build_entitlement.py (Path 1), as-of {as_of}: "
          f"{len(out['order_events']):,} events, {len(out['terms']):,} terms, "
          f"{len(out['billable_months']):,} subscription-months, {len(out['deferrals']):,} deferrals, "
          f"{len(out['invoice_lines']):,} invoice lines")
    print(f"  M-01 effective {m['M-01_effective_licences_at_as_of']:,}  M-02 register {m['M-02_register_licences_at_as_of']:,}  "
          f"M-03 gap {m['M-03_entitlement_gap']['licences_at_as_of']:,} licences / {dollars(m['M-03_entitlement_gap']['cents_at_as_of'])}")
    print(f"  M-06 derived share {m['M-06_derived_share']['rows_derived_share']:.1%}  "
          f"M-07 rejected {m['M-07_rejected_transaction_rate']['rate']:.2%}  "
          f"M-08 nonzero tie-outs {m['M-08_invoice_tie_out']['lines_with_nonzero_tie_out']}")
    print(f"  {disclosure}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
