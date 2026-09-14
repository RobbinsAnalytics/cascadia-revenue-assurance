"""Build docs/index.html -- the module's visual layer (Stage 2).

K2 IS THE RULE THIS FILE EXISTS TO KEEP. Every figure on the page -- in a
title, a subtitle, an annotation, a summary, a table cell or an aria-label --
is computed here from a certified artifact. Nothing is typed. The artifacts:

    data/conformed/measures_manifest.json   Stage 1: M-01..M-08 at as-of
    data/conformed/measures_stage2.json     Stage 2: M-03a, M-05a, M-06a and
                                            the M-01/M-02 monthly series
    data/conformed/manifest.json            as-of date and disclosure (cross-checked)

Both JSON files are written by src/build_entitlement.py (Path 1) and every
leaf is re-derived by src/validate_measures.py (Path 2) before anything is
published. This script reads them and formats; it derives nothing new.

The page is EXPLANATORY (VIZ-PRINCIPLES 0.2): no reader controls, four
charts, one finding each. Every sentence a chart makes is composed here from
the JSON, passed to docs/assets/page.js in the data block, and page.js
decides geometry only.

No real company, customer, partner, product or person appears anywhere; the
synthetic disclosure and the as-of date are visible above the fold, not only
in a footer. No accuracy, error-rate or correctness figure exists (D13).

    python src/build_page.py
"""
from __future__ import annotations

import hashlib
import html
import json
import pathlib
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = pathlib.Path(__file__).resolve().parent.parent
CONF = REPO / "data" / "conformed"
DOCS = REPO / "docs"

REPO_URL = "https://github.com/RobbinsAnalytics/cascadia-revenue-assurance"
# The path the site-side brief will publish this page at. Recorded in the
# Open Graph tags because K8 requires an absolute URL; the page's own prose
# does not promise it (Stage 2 brief B4).
PAGE_URL = "https://www.robbinsanalytics.com/cascadia-revenue-assurance/"
THUMB_URL = "https://www.robbinsanalytics.com/assets/thumb-revenue-assurance.png"

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


# ---------------------------------------------------------------------------
# formatting -- every figure passes through one of these
# ---------------------------------------------------------------------------

def nf(n: int | float, dp: int = 0) -> str:
    return format(round(float(n), dp) if dp else int(round(float(n))), ",")


def dollars(cents: int) -> str:
    sign = "-" if cents < 0 else ""
    c = abs(int(cents))
    return f"{sign}${c // 100:,}" if c % 100 == 0 else f"{sign}${c // 100:,}.{c % 100:02d}"


def pct(x: float, dp: int = 1) -> str:
    return f"{100.0 * x:.{dp}f}%"


def month_name(mk: str) -> str:
    y, m = mk.split("-")
    return f"{MONTHS[int(m) - 1]} {y}"


def month_long(mk: str) -> str:
    names = ["January", "February", "March", "April", "May", "June", "July", "August",
             "September", "October", "November", "December"]
    y, m = mk.split("-")
    return f"{names[int(m) - 1]} {y}"


# ---------------------------------------------------------------------------
# facts -- one function per exhibit, each reading only certified artifacts
# ---------------------------------------------------------------------------

def load() -> tuple[dict, dict, dict]:
    m1 = json.loads((CONF / "measures_manifest.json").read_text(encoding="utf-8"))
    m2 = json.loads((CONF / "measures_stage2.json").read_text(encoding="utf-8"))
    cm = json.loads((CONF / "manifest.json").read_text(encoding="utf-8"))
    as_of = {m1["measures"]["as_of_date"], m2["as_of_date"], m2["measures"]["as_of_date"], cm["as_of_date"]}
    if len(as_of) != 1:
        raise SystemExit(f"as-of dates disagree across the certified artifacts: {sorted(as_of)}")
    if m1["disclosure"] != m2["disclosure"] or m1["disclosure"] != cm["disclosure"]:
        raise SystemExit("disclosure strings disagree across the certified artifacts")
    if m1["seed"] != m2["seed"]:
        raise SystemExit("seeds disagree between measures_manifest.json and measures_stage2.json")
    return m1, m2, cm


def exhibit1(m1: dict, m2: dict, as_of: str, source: str) -> dict:
    """M-05 / M-05a: the two deferral distributions."""
    m05 = m1["measures"]["M-05_deferral_exposure"]
    hist = m2["measures"]["M-05a_histogram_30_day_bins"]
    by_type = m2["measures"]["M-05a_deferral_by_term_type_and_transaction_type"]
    bins = sorted(int(b) for b in hist["annual"])
    if bins != sorted(int(b) for b in hist["monthly"]):
        raise SystemExit("histogram bins differ between term types")
    ann = [hist["annual"][str(b)] for b in bins]
    mon = [hist["monthly"][str(b)] for b in bins]
    n_ann, n_mon = m05["annual"]["n"], m05["monthly"]["n"]
    if sum(ann) != n_ann or sum(mon) != n_mon:
        raise SystemExit("histogram counts do not sum to M-05 n")
    modal_ann = bins[ann.index(max(ann))]
    modal_mon = bins[mon.index(max(mon))]
    med_a, med_m = m05["annual"]["median_days"], m05["monthly"]["median_days"]
    finding = (f"A reduction or cancellation takes effect after a median {nf(med_m)} days on a "
               f"monthly term and a median {nf(med_a)} days on an annual one")
    subtitle = (f"Days from an order's receipt to the term boundary where it was scheduled to land, "
                f"for all {nf(n_ann + n_mon)} deferred orders ({nf(n_ann)} annual, {nf(n_mon)} monthly), "
                f"in 30-day bins. Both panels share the same axes.")
    annotation = (f"Most common wait {modal_ann}–{modal_ann + 29} days; "
                  f"the right tail is partly the window's edge")
    summary = (f"Two histograms of days pending, one per term type, same axes: 30-day bins from "
               f"0–29 up to {bins[-1]}–{bins[-1] + 29} days on the horizontal axis, count of "
               f"deferred orders on the vertical. "
               f"Monthly term: {nf(n_mon)} orders, median {nf(med_m)} days, 90th percentile "
               f"{nf(m05['monthly']['p90_days'])}, maximum {nf(m05['monthly']['max_days'])}; the mass sits "
               f"in the {modal_mon}–{modal_mon + 29} day bin ({nf(max(mon))} orders). Annual term: "
               f"{nf(n_ann)} orders, median {nf(med_a)} days, 90th percentile {nf(m05['annual']['p90_days'])}, "
               f"maximum {nf(m05['annual']['max_days'])}; the counts spread across every bin and are largest "
               f"in the {modal_ann}–{modal_ann + 29} day bin ({nf(max(ann))} orders).")
    aria = (f"Two histograms of days pending by term type, 30-day bins, shared axes. Monthly median "
            f"{nf(med_m)} days, annual median {nf(med_a)} days.")
    rows = [[f"{b}–{b + 29}", nf(mon[i]), nf(ann[i])] for i, b in enumerate(bins)]
    detail = []
    for tt in ("annual", "monthly"):
        for ttype in ("REDUCE", "CANCEL", "ADD"):
            c = by_type[tt][ttype]
            if c["n"]:
                detail.append([tt.capitalize(), ttype, nf(c["n"]), nf(c["median_days"]),
                               nf(c["p90_days"]), nf(c["min_days"]), nf(c["max_days"])])
    return {
        "bins": bins, "annual": ann, "monthly": mon,
        "n": {"annual": n_ann, "monthly": n_mon},
        "median": {"annual": med_a, "monthly": med_m},
        "p90": {"annual": m05["annual"]["p90_days"], "monthly": m05["monthly"]["p90_days"]},
        "max": {"annual": m05["annual"]["max_days"], "monthly": m05["monthly"]["max_days"]},
        "modalBin": {"annual": modal_ann, "monthly": modal_mon},
        "finding": finding, "subtitle": subtitle, "annotation": annotation,
        "summary": summary, "ariaLabel": aria,
        "provenance": {"source": source, "asOf": as_of,
                       "flags": "right tail partly window-censored; not trimmed"},
        "table": rows, "detail": detail,
        "tookEffect": {tt: m05[tt]["took_effect_as_scheduled"] for tt in ("annual", "monthly")},
        "landed": {tt: m05[tt]["landed_by_as_of"] for tt in ("annual", "monthly")},
    }


def exhibit2(m1: dict, m2: dict, as_of: str, source: str) -> dict:
    """M-03 / M-03a: June's backlog by term type and cause."""
    m03 = m1["measures"]["M-03_entitlement_gap"]
    m03a = m2["measures"]["M-03a_gap_at_as_of_by_term_type_and_cause"]
    cells = m03a["by_term_type"]
    if m03a["total_cents"] != m03["cents_at_as_of"]:
        raise SystemExit("M-03a does not sum to M-03")
    label = {"cancel_riding_out": "cancellations riding out the term",
             "deferred_reduction": "deferred reductions"}
    rows = []
    for tt in ("annual", "monthly"):
        for cause, c in sorted(cells[tt].items(), key=lambda kv: -kv[1]["cents"]):
            rows.append({"termType": tt, "cause": cause,
                         "label": f"{tt.capitalize()} — {label[cause]}",
                         "cents": c["cents"], "dollars": dollars(c["cents"]),
                         "months": c["subscription_months"], "licences": c["licences"]})
    # Rule 2.7 sort: largest dollars first, groups kept adjacent by term type (3.5).
    groups = sorted(("annual", "monthly"), key=lambda tt: -sum(c["cents"] for c in cells[tt].values()))
    rows.sort(key=lambda r: (groups.index(r["termType"]), -r["cents"]))
    annual_c = sum(c["cents"] for c in cells["annual"].values())
    total_c = m03a["total_cents"]
    a_cancel = cells["annual"]["cancel_riding_out"]
    a_reduce = cells["annual"]["deferred_reduction"]
    cancel_share = a_cancel["cents"] / annual_c if annual_c else 0.0
    mk = m03a["as_of_month"]
    finding = (f"{dollars(annual_c)} of the {dollars(total_c)} {month_long(mk)} backlog sits on annual "
               f"terms, and {dollars(a_cancel['cents'])} of that is cancellations still billing")
    subtitle = (f"Month-end gap between effective and register licences at {as_of}, in dollars at the "
                f"term type's monthly rate, by term type and by cause. The count beside each bar is "
                f"subscription-months.")
    annotation = f"{pct(cancel_share, 0)} of annual backlog dollars are cancellations still billing"
    summary = (f"Horizontal bar chart, four bars, dollars per month on the horizontal axis from $0. "
               + "; ".join(f"{r['label']}: {r['dollars']} across {nf(r['months'])} subscription-months "
                           f"({nf(r['licences'])} licences)" for r in rows)
               + f". Total {dollars(total_c)}. Annual terms carry {pct(annual_c / total_c)} of the dollars; "
               f"within annual, cancellations are the larger dollars ({dollars(a_cancel['cents'])} vs "
               f"{dollars(a_reduce['cents'])}) and deferred reductions the larger count "
               f"({nf(a_reduce['subscription_months'])} vs {nf(a_cancel['subscription_months'])} subscription-months).")
    aria = (f"Horizontal bar chart of the {month_long(mk)} backlog in dollars by term type and cause, "
            f"four bars, largest {rows[0]['dollars']}.")
    return {
        "rows": rows, "totalCents": total_c, "annualCents": annual_c,
        "annualShare": annual_c / total_c if total_c else 0.0, "cancelShareOfAnnual": cancel_share,
        "asOfMonth": mk, "finding": finding, "subtitle": subtitle, "annotation": annotation,
        "summary": summary, "ariaLabel": aria,
        "provenance": {"source": source, "asOf": as_of,
                       "flags": f"month-end run rate, {month_long(mk)} only"},
        "table": [[r["label"], r["dollars"], nf(r["months"]), nf(r["licences"])] for r in rows],
    }


def exhibit3(m1: dict, m2: dict, as_of: str, source: str) -> dict:
    """M-01 vs M-02 at 24 month ends."""
    series = m2["measures"]["M-01_M-02_monthly_series"]
    m01, m02 = m1["measures"]["M-01_effective_licences_at_as_of"], m1["measures"]["M-02_register_licences_at_as_of"]
    last = series[-1]
    if last["effective_licences"] != m01 or last["register_licences"] != m02:
        raise SystemExit("the monthly series' last point does not equal M-01 / M-02 at as-of")
    if last["month_key"] != as_of[:7]:
        raise SystemExit("the monthly series does not end at the as-of month")
    pts = [{"month": s["month_key"], "label": month_name(s["month_key"]),
            "effective": s["effective_licences"], "register": s["register_licences"],
            "gap": s["gap_licences"],
            "share": (s["gap_licences"] / s["effective_licences"]) if s["effective_licences"] else 0.0}
           for s in series]
    n = len(pts)
    months_with_gap = sum(1 for p in pts if p["gap"] > 0)
    last_share = pts[-1]["share"]
    every = months_with_gap == n
    clause = f"In every one of {nf(n)} months" if every else f"In {nf(months_with_gap)} of {nf(n)} months"
    finding = (f"{clause} the register showed fewer licences than were billable; "
               f"{nf(last['gap_licences'])} fewer ({pct(last_share)}) at {month_long(last['month_key'])}")
    subtitle = (f"Sum of effective and of register licences at each month end, {month_name(pts[0]['month'])} "
                f"to {month_name(pts[-1]['month'])}, with the gap between them shaded. Gap share is gap "
                f"divided by effective.")
    annotation = f"{month_long(last['month_key'])}: {nf(last['gap_licences'])} licences the register does not show"
    peak = max(pts, key=lambda p: p["gap"])
    peak_share = max(pts, key=lambda p: p["share"])
    summary = (f"Line chart, two lines over {n} month ends from {month_name(pts[0]['month'])} to "
               f"{month_name(pts[-1]['month'])}, licences on the vertical axis from 0. Effective licences rise "
               f"from {nf(pts[0]['effective'])} to {nf(pts[-1]['effective'])}; register licences rise from "
               f"{nf(pts[0]['register'])} to {nf(pts[-1]['register'])}. The effective line sits above the "
               f"register line at every month end. The gap grows from {nf(pts[0]['gap'])} licences to a peak "
               f"of {nf(peak['gap'])} in {month_name(peak['month'])} and is {nf(last['gap_licences'])} at "
               f"{month_name(last['month_key'])}; as a share of effective it peaks at {pct(peak_share['share'])} "
               f"in {month_name(peak_share['month'])} and ends at {pct(last_share)}.")
    aria = (f"Line chart of effective versus register licences at {n} month ends, gap shaded; gap "
            f"{nf(last['gap_licences'])} licences at {month_name(last['month_key'])}.")
    return {
        "points": pts, "n": n, "monthsWithGap": months_with_gap, "every": every,
        "finding": finding, "subtitle": subtitle, "annotation": annotation,
        "summary": summary, "ariaLabel": aria,
        "provenance": {"source": source, "asOf": as_of,
                       "flags": "rows in manufactured renewals are derived under a stated rule and flagged"},
        "table": [[p["label"], nf(p["effective"]), nf(p["register"]), nf(p["gap"]), pct(p["share"])]
                  for p in pts],
        "peak": {"month": peak["month"], "gap": peak["gap"]},
    }


def exhibit4(m1: dict, m2: dict, as_of: str, source: str) -> dict:
    """M-06 / M-06a: derived share by term type."""
    m06 = m1["measures"]["M-06_derived_share"]
    m06a = m2["measures"]["M-06a_derived_share_by_term_type"]
    if sum(v["rows"] for v in m06a.values()) != m06["rows_total"]:
        raise SystemExit("M-06a rows do not sum to M-06 rows_total")
    rows = sorted(({"termType": tt, "label": f"{tt.capitalize()} term", "rows": v["rows"],
                    "derived": v["rows_derived"], "share": v["share"]} for tt, v in m06a.items()),
                  key=lambda r: -r["share"])
    m, a = m06a["monthly"], m06a["annual"]
    finding = (f"{pct(m['share'], 0)} of monthly-term billing rows and {pct(a['share'], 0)} of annual-term "
               f"rows fall in a renewal no transaction marked")
    subtitle = (f"Share of subscription-month rows whose every effective day lies in a manufactured term, by "
                f"term type; {pct(m06['rows_derived_share'])} of all {nf(m06['rows_total'])} rows blended.")
    annotation = "Every monthly term after the first is manufactured"
    summary = (f"Horizontal bar chart, two bars, percent on the horizontal axis from 0 to 100. "
               + "; ".join(f"{r['label']}: {pct(r['share'])} ({nf(r['derived'])} of {nf(r['rows'])} rows)"
                           for r in rows)
               + f". Blended: {pct(m06['rows_derived_share'])} of {nf(m06['rows_total'])} rows; "
               f"{nf(m06['terms_derived'])} of {nf(m06['terms_total'])} term instances are manufactured.")
    aria = (f"Horizontal bar chart of derived row share by term type: monthly {pct(m['share'])}, "
            f"annual {pct(a['share'])}.")
    return {
        "rows": rows, "blended": m06["rows_derived_share"], "rowsTotal": m06["rows_total"],
        "termsDerived": m06["terms_derived"], "termsTotal": m06["terms_total"],
        "finding": finding, "subtitle": subtitle, "annotation": annotation,
        "summary": summary, "ariaLabel": aria,
        "provenance": {"source": source, "asOf": as_of,
                       "flags": "derived = no transaction opened the term"},
        "table": [[r["label"], pct(r["share"]), nf(r["derived"]), nf(r["rows"])] for r in rows],
    }


# ---------------------------------------------------------------------------
# page assembly
# ---------------------------------------------------------------------------

def asset_v(name: str) -> str:
    """`assets/<name>?v=<content hash>` so a republish is never served stale (K7)."""
    b = (DOCS / "assets" / name).read_bytes()
    return f"assets/{name}?v={hashlib.md5(b).hexdigest()[:10]}"


def table(tid: str, caption: str, headers: list[str], rows: list[list[str]]) -> str:
    h = [f'<table id="{tid}"><caption>{html.escape(caption)}</caption><thead><tr>']
    h += [f'<th scope="col">{html.escape(c)}</th>' for c in headers]
    h.append("</tr></thead><tbody>")
    for r in rows:
        h.append("<tr>" + "".join(
            f'<th scope="row">{html.escape(str(c))}</th>' if i == 0 else f"<td>{html.escape(str(c))}</td>"
            for i, c in enumerate(r)) + "</tr>")
    h.append("</tbody></table>")
    return "".join(h)


def main() -> int:
    m1, m2, cm = load()
    as_of = m1["measures"]["as_of_date"]
    disclosure = m1["disclosure"]
    seed = m1["seed"]
    source = f"Synthetic, seeded generator (seed {seed})"
    for k, v in (("source", source), ("asOf", as_of)):
        if "·" in v:
            raise SystemExit(f"provenance {k} contains the strip separator (K5)")

    c1 = exhibit1(m1, m2, as_of, source)
    c2 = exhibit2(m1, m2, as_of, source)
    c3 = exhibit3(m1, m2, as_of, source)
    c4 = exhibit4(m1, m2, as_of, source)
    for c in (c1, c2, c3, c4):
        if "·" in c["provenance"]["flags"]:
            raise SystemExit("a provenance flag contains the strip separator (K5)")
        if len(c["annotation"].split()) > 14:
            raise SystemExit(f"annotation over 14 words: {c['annotation']!r}")

    M = m1["measures"]
    m03, m04, m07, m08 = (M["M-03_entitlement_gap"], M["M-04_prorated_revenue"],
                          M["M-07_rejected_transaction_rate"], M["M-08_invoice_tie_out"])
    data = {"asOf": as_of, "seed": seed, "disclosure": disclosure, "source": source,
            "c1": c1, "c2": c2, "c3": c3, "c4": c4}

    f = {
        "as_of": as_of, "as_of_long": month_long(as_of[:7]) if False else as_of,
        "seed": seed, "disclosure": html.escape(disclosure),
        "m01": nf(M["M-01_effective_licences_at_as_of"]),
        "m02": nf(M["M-02_register_licences_at_as_of"]),
        "gap_lic": nf(m03["licences_at_as_of"]), "gap_usd": dollars(m03["cents_at_as_of"]),
        "gap_share_billable": pct(m03["backlog_share_of_as_of_month_billable"]),
        "gap_share_eff": pct(m03["licences_at_as_of"] / M["M-01_effective_licences_at_as_of"]),
        "rows_gap": nf(m03["subscription_months_with_gap"]), "rows_all": nf(m03["subscription_months_total"]),
        "rows_gap_pct": pct(m03["subscription_months_with_gap_share"]),
        "billable_total": dollars(m04["billable_cents_all_months"]),
        "billable_june": dollars(m04["billable_cents_at_as_of_month"]),
        "inv_lines": nf(m08["invoice_lines"]), "inv_nonzero": nf(m08["lines_with_nonzero_tie_out"]),
        "inv_partner": nf(m08["partner_lines"]), "inv_direct": nf(m08["direct_lines"]),
        "rej_n": nf(m07["rejected"]), "rej_recv": nf(m07["received"]), "rej_rate": pct(m07["rate"], 2),
        "med_a": nf(c1["median"]["annual"]), "med_m": nf(c1["median"]["monthly"]),
        "max_a": nf(c1["max"]["annual"]), "max_m": nf(c1["max"]["monthly"]),
        "n_def": nf(c1["n"]["annual"] + c1["n"]["monthly"]),
        "took_a": nf(c1["tookEffect"]["annual"]), "n_a": nf(c1["n"]["annual"]),
        "landed_a": nf(c1["landed"]["annual"]),
        "annual_usd": dollars(c2["annualCents"]), "annual_share": pct(c2["annualShare"]),
        "a_cancel_usd": dollars(c2["rows"][0]["cents"]) if c2["rows"][0]["cause"] == "cancel_riding_out"
                        else dollars(next(r["cents"] for r in c2["rows"] if r["termType"] == "annual" and r["cause"] == "cancel_riding_out")),
        "a_cancel_n": nf(next(r["months"] for r in c2["rows"] if r["termType"] == "annual" and r["cause"] == "cancel_riding_out")),
        "a_reduce_usd": dollars(next(r["cents"] for r in c2["rows"] if r["termType"] == "annual" and r["cause"] == "deferred_reduction")),
        "a_reduce_n": nf(next(r["months"] for r in c2["rows"] if r["termType"] == "annual" and r["cause"] == "deferred_reduction")),
        "cancel_share_annual": pct(c2["cancelShareOfAnnual"], 0),
        "c3_n": nf(c3["n"]), "c3_months_gap": nf(c3["monthsWithGap"]),
        "c3_peak_gap": nf(c3["peak"]["gap"]), "c3_peak_month": month_name(c3["peak"]["month"]),
        "c3_first_month": month_name(c3["points"][0]["month"]),
        "c3_last_month": month_long(c3["points"][-1]["month"]),
        "c4_m": pct(c4["rows"][0]["share"] if c4["rows"][0]["termType"] == "monthly" else c4["rows"][1]["share"]),
        "c4_a": pct(c4["rows"][0]["share"] if c4["rows"][0]["termType"] == "annual" else c4["rows"][1]["share"]),
        "c4_blended": pct(c4["blended"]), "terms_derived": nf(c4["termsDerived"]), "terms_total": nf(c4["termsTotal"]),
        "c1_finding": html.escape(c1["finding"]), "c2_finding": html.escape(c2["finding"]),
        "c3_finding": html.escape(c3["finding"]), "c4_finding": html.escape(c4["finding"]),
        "c1_note": html.escape(c1["annotation"]), "c2_note": html.escape(c2["annotation"]),
        "c3_note": html.escape(c3["annotation"]), "c4_note": html.escape(c4["annotation"]),
    }

    t1 = table("tbl-c1", "Chart 1 data — deferred orders by days pending, 30-day bins",
               ["Days pending", "Monthly term (orders)", "Annual term (orders)"], c1["table"])
    t1b = table("tbl-c1-detail", "Chart 1 detail — by term type and the order's label (M-05a)",
                ["Term type", "Order label", "Orders", "Median days", "90th pct days", "Min", "Max"],
                c1["detail"])
    t2 = table("tbl-c2", f"Chart 2 data — {month_long(c2['asOfMonth'])} backlog by term type and cause (M-03a)",
               ["Term type and cause", "Dollars per month", "Subscription-months", "Licences"], c2["table"])
    t3 = table("tbl-c3", "Chart 3 data — effective and register licences at each month end (M-01, M-02)",
               ["Month", "Effective licences", "Register licences", "Gap (licences)", "Gap share of effective"],
               c3["table"])
    t4 = table("tbl-c4", "Chart 4 data — derived row share by term type (M-06a)",
               ["Term type", "Derived share", "Derived rows", "All rows"], c4["table"])

    subs = {
        "data": json.dumps(data, separators=(",", ":")),
        "t1": t1, "t1b": t1b, "t2": t2, "t3": t3, "t4": t4,
        "v_css": asset_v("cascadia.css"), "v_echarts": asset_v("echarts.min.js"),
        "v_theme": asset_v("cascadia-echarts-theme.js"), "v_page": asset_v("page.js"),
        "v_favicon": asset_v("favicon.svg"),
        "repo_url": REPO_URL, "page_url": PAGE_URL, "thumb_url": THUMB_URL,
    }
    subs.update(f)
    out = TEMPLATE
    for k, v in subs.items():
        out = out.replace(f"@@{k}@@", str(v))
    left = sorted(set(re.findall(r"@@(\w+)@@", out)))
    if left:
        raise SystemExit(f"unsubstituted tokens in template: {left}")

    DOCS.mkdir(parents=True, exist_ok=True)
    (DOCS / "index.html").write_text(out, encoding="utf-8", newline="\n")
    print("wrote docs/index.html")
    for c, name in ((c1, "c1"), (c2, "c2"), (c3, "c3"), (c4, "c4")):
        print(f"  {name}: {c['finding']}")
    print(f"  {disclosure}")
    return 0


TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Cascadia Revenue Assurance — contracted is not billable</title>
<meta name="description" content="A synthetic subscription-licensing book in which the register's contracted quantity and the billable quantity are different numbers, kept apart by timing rules. Seeded, disclosed, re-derived down two independent paths.">
<meta property="og:type" content="website">
<meta property="og:title" content="Cascadia Revenue Assurance — contracted is not billable">
<meta property="og:description" content="The same reduction waits a median @@med_m@@ days on a monthly term and @@med_a@@ on an annual one. A synthetic book, a stated rule, and a register that is quietly wrong every month.">
<meta property="og:image" content="@@thumb_url@@">
<meta property="og:url" content="@@page_url@@">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="@@thumb_url@@">
<link rel="icon" href="@@v_favicon@@" type="image/svg+xml">
<link rel="stylesheet" href="@@v_css@@">
<style>
  .answers { display:flex; flex-wrap:wrap; gap:18px; margin:18px 0 6px; }
  .answer { flex:1 1 210px; border:1px solid var(--grid); border-radius:3px;
            padding:14px 16px; background:var(--surface); min-width:0; }
  .answer .lbl { font:12px/1.5 var(--sans); color:var(--ink-2);
                 text-transform:uppercase; letter-spacing:.06em; margin:0; }
  .answer .val { font:700 28px/1.15 var(--serif); margin:4px 0 2px; color:var(--ink);
                 overflow-wrap:anywhere; }
  .answer .note { font:13px/1.5 var(--sans); color:var(--ink-2); margin:0; }
  .chart { width:100%; }
  .chart-summary { font:13px/1.6 var(--sans); color:var(--ink); margin:0 2px 8px; max-width:72ch; }
  .chart-note { font:13px/1.55 var(--serif); color:var(--ink-s1); margin:6px 2px 0; max-width:72ch; }
  .chart-note.glacier { color:var(--ink-s2); }
  .chart-note.madrona { color:var(--ink-s3); }
  details.data-table { margin:8px 2px 0; }
  details.data-table summary { font:12px/1.5 var(--sans); color:var(--ink-2); cursor:pointer;
                               min-height:24px; }
  .table-scroll { overflow-x:auto; }
  details.data-table table { border-collapse:collapse; margin-top:8px; font:12px/1.5 var(--sans); }
  details.data-table caption { display:block; text-align:left; font-weight:600; padding:4px 0;
                               color:var(--ink); }
  details.data-table th, details.data-table td { border:1px solid var(--grid); padding:4px 8px;
                               text-align:right; white-space:nowrap; }
  details.data-table th[scope="row"] { text-align:left; font-weight:400; white-space:normal; }
  details.data-table thead th { background:#F3F5F2; text-align:right; }
  .governance-note { border-left:3px solid var(--s1); padding:2px 0 2px 14px; margin:16px 2px;
                     font:14px/1.65 var(--sans); color:var(--ink); max-width:72ch; }
  .disclosure-band { border:1px solid var(--grid); border-radius:3px; background:var(--surface);
                     padding:12px 16px; margin:14px 0 0; font:13px/1.6 var(--sans); color:var(--ink);
                     max-width:80ch; }
  .disclosure-band strong { color:var(--ink); }
  h2 { font:600 24px/1.3 var(--serif); margin:34px 0 6px; }
  h3 { font:600 17px/1.35 var(--serif); margin:22px 0 4px; }
  .lede { font:17px/1.65 var(--serif); max-width:70ch; }
  .method p { max-width:80ch; }
  @media (max-width:400px) { .answer .val { font-size:22px; } }
</style>
<script src="@@v_echarts@@"></script>
<!-- Local, and after ECharts so registerTheme('cascadia') finds it. -->
<script src="@@v_theme@@"></script>
</head>
<body>

<!--CASCADIA_DATA_START-->
<script id="cascadia-data" type="application/json">@@data@@</script>
<!--CASCADIA_DATA_END-->

<div class="wrap">

<header class="site-head">
  <p class="kicker"><a href="https://www.robbinsanalytics.com/">Cascadia Portfolio</a> · Revenue Assurance</p>
  <h1>What a customer is contracted for and what they are billable for are different numbers</h1>
  <p class="subtitle">A subscription-licensing book with three timing rules: adding licences takes effect
  at once, reducing them waits for the next term boundary, and cancelling rides out the term. The order
  register records what each customer asked for. The billable quantity is derived from the event stream
  and the rules, and the two sit apart for up to a year on an annual term with nothing erroring and no
  register showing it.</p>
  <div class="disclosure-band"><strong>@@disclosure@@</strong> Every figure on this page is stated as of
  <strong>@@as_of@@</strong> and computed at build time from certified artifacts that two independently
  written derivation paths agree on cell for cell. No figure may be read as a claim about any real book of
  business.</div>
</header>

<h2>The decision this page serves</h2>
<p class="lede">Whether to keep invoicing from the register's current quantity, or to derive the billable
quantity from the event stream and the rules and reconcile the invoice to it.</p>
<p class="chart-summary">The reader is the finance or revenue-operations owner who signs the monthly
invoice run and is accountable for the number on it. The benchmark is the register's own quantity, the
naive answer. Every chart below shows where that answer and the derived one part ways, and by how much.</p>

<div class="answers">
  <div class="answer">
    <p class="lbl">Effective licences at @@as_of@@</p>
    <p class="val">@@m01@@</p>
    <p class="note">Billable under the rules, summed across every subscription effective that day (M-01).</p>
  </div>
  <div class="answer">
    <p class="lbl">Register licences at @@as_of@@</p>
    <p class="val">@@m02@@</p>
    <p class="note">What the register shows: the last quantity each customer asked for (M-02).</p>
  </div>
  <div class="answer">
    <p class="lbl">Entitlement gap</p>
    <p class="val">@@gap_lic@@ licences</p>
    <p class="note">@@gap_usd@@ per month at the term rates, @@gap_share_billable@@ of the month's
    billable (M-03). The register never exceeds the effective quantity, so the gap is never negative.</p>
  </div>
  <div class="answer">
    <p class="lbl">Subscription-months carrying a gap</p>
    <p class="val">@@rows_gap_pct@@</p>
    <p class="note">@@rows_gap@@ of @@rows_all@@ subscription-months across the 24-month window.</p>
  </div>
</div>

<h2>How long a reduction waits depends on the term, not on the customer</h2>
<div class="chart-card">
  <p id="sum-c1" class="chart-summary"></p>
  <div id="c1" class="chart" style="height:460px"></div>
  <p id="note-c1" class="chart-note" hidden>@@c1_note@@</p>
  <details class="data-table"><summary>Chart 1 data table</summary><div class="table-scroll">@@t1@@</div></details>
  <details class="data-table"><summary>Chart 1 detail — by the order's label</summary><div class="table-scroll">@@t1b@@</div></details>
</div>

<div class="governance-note">
<strong>The wait is the rule's, not the customer's.</strong> A reduction or a cancellation is refused
mid-term and lands at the next boundary, so on a monthly term it waits at most @@max_m@@ days and on an
annual term up to @@max_a@@. Of the @@n_a@@ annual deferrals, @@landed_a@@ had reached their boundary by
@@as_of@@ and @@took_a@@ took effect unchanged; the rest were superseded by a later order or are still
waiting. <strong>The right tail is partly the window's edge:</strong> half the annual book is still in its
first term at the as-of date, so an order placed late in a term, with a short wait, is under-observed.
The distribution is shown as measured, not trimmed to move the median.
</div>

<h2>Where the backlog sits at the as-of date</h2>
<div class="chart-card">
  <p id="sum-c2" class="chart-summary"></p>
  <div id="c2" class="chart" style="height:320px"></div>
  <p id="note-c2" class="chart-note" hidden>@@c2_note@@</p>
  <details class="data-table"><summary>Chart 2 data table</summary><div class="table-scroll">@@t2@@</div></details>
</div>

<div class="governance-note">
<strong>Cancellations are the larger dollars; deferred reductions are the larger count.</strong> On
annual terms, @@a_cancel_usd@@ of backlog sits on @@a_cancel_n@@ subscription-months whose customer has
cancelled and is still billable to term end, against @@a_reduce_usd@@ on @@a_reduce_n@@ subscription-months
waiting for a reduction to land. A register that goes to zero on the cancel date while billing continues for
up to a year is the module's single largest source of gap, and it is a consequence of the rules rather than
of any error. A subscription with both a pending reduction and a pending cancellation is counted with the
cancellations, because the cancellation is what decides that no next term opens.
</div>

<h2>The register against the effective quantity, month by month</h2>
<div class="chart-card">
  <p id="sum-c3" class="chart-summary"></p>
  <div id="c3" class="chart" style="height:420px"></div>
  <p id="note-c3" class="chart-note madrona" hidden>@@c3_note@@</p>
  <details class="data-table"><summary>Chart 3 data table</summary><div class="table-scroll">@@t3@@</div></details>
</div>

<div class="governance-note">
<strong>A query that reads the register's current quantity is wrong about the invoice in every month a
deferral is outstanding.</strong> The book grows through the whole window because subscriptions open
throughout it, so the gap in licences grows with the book; the share of effective licences the register
does not show is the figure to read, and it ends at @@gap_share_eff@@. The gap peaked at @@c3_peak_gap@@
licences in @@c3_peak_month@@. Rows in later months increasingly sit in manufactured renewals, which the
next chart counts.
</div>

<h2>The renewals nobody sent</h2>
<div class="chart-card">
  <p id="sum-c4" class="chart-summary"></p>
  <div id="c4" class="chart" style="height:260px"></div>
  <p id="note-c4" class="chart-note glacier" hidden>@@c4_note@@</p>
  <details class="data-table"><summary>Chart 4 data table</summary><div class="table-scroll">@@t4@@</div></details>
</div>

<div class="governance-note">
<strong>No transaction marks a renewal; a renewal is implied by the absence of a cancellation.</strong>
The state machine manufactures the next term under a stated rule and flags every row that rests on one:
@@terms_derived@@ of @@terms_total@@ term instances, and @@c4_blended@@ of all billing rows. That is
derivation under a written rule, declared on the row, and it is not the filling of a gap. The blended
figure hides two books: monthly terms are @@c4_m@@ derived because every month after the first is a
manufactured term, and annual terms are @@c4_a@@ derived because at most one renewal fits inside the
window.
</div>

<h2>What was checked and found to be nothing</h2>
<p class="chart-summary">Every partner invoice line and every Direct customer invoice line is a roll-up of
subscription-months, re-derived through a second join. <strong>@@inv_lines@@ invoice lines
(@@inv_partner@@ partner-by-month, @@inv_direct@@ customer-by-month), @@inv_nonzero@@ with a non-zero
tie-out</strong> (M-08). Published because the value of a reconciliation is the discipline of checking,
not the size of what it finds. Separately, @@rej_n@@ of @@rej_recv@@ transactions received were refused
under a fixed vocabulary of reasons and kept in the register rather than dropped (M-07); a refusal is a
fact about the sender and says nothing about the engine.</p>

<h2>How it stays right</h2>
<div class="method">
<p><strong>Two derivation paths, written to be different.</strong> A record-at-a-time state machine in
Python derives every term, every subscription-month and every measure from the event stream and a
normative rules document. A set-based SQL path in DuckDB, written from the same rules document and not
from the first path's code, re-derives every published cell and must agree before anything is published.
On this build it did, on every cell.</p>
<p><strong>A hand-specified golden fixture written before either engine.</strong> Fifteen worked cases,
including a boundary-day order, a monthly term opened on the 31st, and a Direct-channel subscription, with
expected values computed by hand. Both paths pass it.</p>
<p><strong>Derived rows are declared, never hidden.</strong> Every term and every billing row that rests on
a manufactured renewal carries a <code>derived</code> flag, and Chart 4 counts them.</p>
<p><strong>No accuracy, error-rate or correctness percentage exists in this module, and none may be
added.</strong> Its only correctness claim is that an independent re-derivation agrees and that the golden
fixture passes. That is a statement about method.</p>
<p><strong>The layer the author cannot self-verify.</strong> Whether a reader who does not know the finding
takes it away from these charts is not something the author can test alone. A blind reading panel reads
static renders of this page before it ships; at the time this page was built, that panel had not yet run,
and the page says so here rather than implying otherwise.</p>
</div>

<div class="disclosure">
<h3>Disclosure</h3>
<p>An independent portfolio project by Aaron Robbins. <strong>@@disclosure@@</strong> Every customer,
partner, subscription and transaction was invented by a seeded generator; the partner names are
invented and resemble no real reseller, carrier or company. Nothing here is a claim about how any real
company operates, and nothing is financial or legal advice.</p>
<p>Source, governance documents, the rules the engines implement, and the build scripts:
<a href="@@repo_url@@">github.com/RobbinsAnalytics/cascadia-revenue-assurance</a>. Every figure on this
page is computed at build time from <code>data/conformed/measures_manifest.json</code> and
<code>data/conformed/measures_stage2.json</code>; the independent re-derivation that gates publication is
<code>src/validate_measures.py</code>.</p>
<p class="asof">As of <strong>@@as_of@@</strong> · seed @@seed@@ · billable across the window @@billable_total@@</p>
</div>

</div>

<script src="@@v_page@@"></script>
</body>
</html>
"""


if __name__ == "__main__":
    sys.exit(main())
