"""validate_measures.py -- PATH 2: set-based SQL in DuckDB, written from the rules.

Written from governance/entitlement-rules.md and from nothing else. Section
numbers in comments refer to that document. This file imports nothing from
src/build_entitlement.py (Path 1) and shares no helper with it (D12). Its only
inputs are the raw order transactions (the register's source) and the dim_*
tables; it re-derives every published fact and every M- value and compares
them, cell by cell, with what Path 1 published.

How it is different from Path 1, on purpose
    No per-row iteration and no state object. Acceptance is decided without
    recursion: a subscription's first NEW and first CANCEL are found with
    MIN() over an ordering, and NOOP_QUANTITY is a LAG() over the quantity
    chain -- which works because a no-op is transparent to the register (a
    refused no-op asks for what the register already says). Term chains are
    closed-form date arithmetic over a generated series (rule 3.4's second
    reading). Daily quantities come from a generated calendar joined to each
    term's running maximum (rule 4.2: the effective quantity never falls
    inside a term, so E(t) = max(opening, max q received in the term by t)).
    Months are GROUP BYs over that calendar.

Entry points
    derive_from_files(events_csv, subscriptions_csv, as_of, customers_csv=None)
        the signature src/test_golden.py calls on both paths
    main()  re-derive from data/raw/order_events.csv + data/conformed/dim_*,
            compare with data/conformed/fact_* and measures_manifest.json,
            print the first 20 mismatching keys, exit 1 on any mismatch.

    python src/validate_measures.py
"""

from __future__ import annotations

import json
import math
import sys
from datetime import date, datetime
from pathlib import Path

import duckdb
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = Path(__file__).resolve().parent.parent
RAW = REPO / "data" / "raw"
CONF = REPO / "data" / "conformed"

# Rules section 0, restated deliberately. No shared constants module (D12).
RATE_CENTS = {"annual": 1000, "monthly": 1200}
MAX_TERMS_PER_SUBSCRIPTION = 40   # generous: 24 monthly terms fit the window

EVENT_TYPES = {"transaction_id": "BIGINT", "received_date": "DATE", "subscription_key": "VARCHAR",
               "transaction_type": "VARCHAR", "requested_quantity": "BIGINT",
               "term_type": "VARCHAR", "source": "VARCHAR"}


# ---------------------------------------------------------------------------
# the derivation
# ---------------------------------------------------------------------------

def load_inputs(con: duckdb.DuckDBPyConnection, events_csv: Path, subscriptions_csv: Path,
                customers_csv: Path | None) -> None:
    con.execute("CREATE TABLE ev AS SELECT transaction_id, received_date, subscription_key, "
                "transaction_type, requested_quantity, term_type, source "
                "FROM read_csv(?, header=true, types=?, nullstr='')",
                [events_csv.as_posix(), EVENT_TYPES])
    con.execute("CREATE TABLE subs AS SELECT subscription_key, customer_key, partner_id, channel "
                "FROM read_csv(?, header=true, all_varchar=true)", [subscriptions_csv.as_posix()])
    if customers_csv is None:
        con.execute("CREATE TABLE cust AS SELECT DISTINCT customer_key, partner_id, channel FROM subs")
    else:
        con.execute("CREATE TABLE cust AS SELECT customer_key, partner_id, channel "
                    "FROM read_csv(?, header=true, all_varchar=true)", [customers_csv.as_posix()])


def derive_sql(con: duckdb.DuckDBPyConnection, as_of: date) -> None:
    """Build every derived table inside `con`. Rule numbers refer to entitlement-rules.md."""
    con.execute("SET TimeZone = 'UTC'")
    as_of_s = as_of.isoformat()

    # -- input contract (1.3): malformed input raises; it is not a rejection row -------
    bad = con.execute(f"""
        SELECT count(*) FROM ev
        WHERE transaction_type NOT IN ('NEW','ADD','REDUCE','CANCEL')
           OR requested_quantity < 0
           OR (transaction_type = 'NEW' AND (requested_quantity < 1 OR term_type NOT IN ('annual','monthly') OR term_type IS NULL))
           OR (transaction_type = 'CANCEL' AND requested_quantity <> 0)
           OR received_date > DATE '{as_of_s}'
    """).fetchone()[0]
    dup = con.execute("SELECT count(*) - count(DISTINCT transaction_id) FROM ev").fetchone()[0]
    if bad or dup:
        raise ValueError(f"input contract violated: {bad} malformed row(s), {dup} duplicate id(s)")

    # -- 2.1 processing order ------------------------------------------------------------
    con.execute("""
        CREATE TABLE e AS
        SELECT *, row_number() OVER (ORDER BY received_date, transaction_id) AS ord FROM ev
    """)
    # -- 1.2 the facts acceptance depends on: first NEW, first CANCEL after it ------------
    con.execute("""
        CREATE TABLE first_new AS
        SELECT subscription_key, min(ord) AS new_ord FROM e WHERE transaction_type = 'NEW' GROUP BY 1
    """)
    con.execute("""
        CREATE TABLE first_cancel AS
        SELECT e.subscription_key, min(e.ord) AS cancel_ord
        FROM e JOIN first_new f USING (subscription_key)
        WHERE e.transaction_type = 'CANCEL' AND e.ord > f.new_ord
        GROUP BY 1
    """)
    # The quantity chain: the first NEW and every ADD/REDUCE with a positive quantity
    # received after it and before the first CANCEL. A NOOP is transparent to the
    # register, so LAG over this chain is the register quantity before each order (4.5).
    con.execute("""
        CREATE TABLE chain AS
        SELECT e.transaction_id,
               lag(e.requested_quantity) OVER (PARTITION BY e.subscription_key ORDER BY e.ord) AS prev_q
        FROM e
        JOIN first_new f USING (subscription_key)
        LEFT JOIN first_cancel c USING (subscription_key)
        WHERE (e.transaction_type = 'NEW' AND e.ord = f.new_ord)
           OR (e.transaction_type IN ('ADD','REDUCE') AND e.requested_quantity > 0
               AND e.ord > f.new_ord AND (c.cancel_ord IS NULL OR e.ord < c.cancel_ord))
    """)
    # -- 1.2 precedence: UNKNOWN, DUPLICATE_NEW, after-cancel, REDUCE_TO_ZERO, NOOP -------
    con.execute("""
        CREATE TABLE classified AS
        SELECT e.transaction_id, e.received_date, e.subscription_key, e.transaction_type,
               e.requested_quantity, e.term_type, e.source, e.ord,
               CASE
                 WHEN e.transaction_type = 'NEW' AND e.ord = f.new_ord THEN NULL
                 WHEN e.transaction_type = 'NEW' THEN 'DUPLICATE_NEW'
                 WHEN f.new_ord IS NULL OR e.ord < f.new_ord THEN 'UNKNOWN_SUBSCRIPTION'
                 WHEN c.cancel_ord IS NOT NULL AND e.ord > c.cancel_ord THEN
                      CASE e.transaction_type WHEN 'ADD' THEN 'ADD_AFTER_CANCEL'
                                              WHEN 'REDUCE' THEN 'REDUCE_AFTER_CANCEL'
                                              ELSE 'DUPLICATE_CANCEL' END
                 WHEN e.transaction_type = 'CANCEL' THEN NULL
                 WHEN e.requested_quantity = 0 THEN 'REDUCE_TO_ZERO'
                 WHEN ch.prev_q = e.requested_quantity THEN 'NOOP_QUANTITY'
                 ELSE NULL
               END AS rejection_reason
        FROM e
        LEFT JOIN first_new f USING (subscription_key)
        LEFT JOIN first_cancel c USING (subscription_key)
        LEFT JOIN chain ch USING (transaction_id)
    """)
    con.execute("CREATE TABLE acc AS SELECT * FROM classified WHERE rejection_reason IS NULL")

    # -- 3.1 subscriptions: opened by the accepted NEW; cancel date if any --------------
    con.execute("""
        CREATE TABLE sub AS
        SELECT n.subscription_key, n.received_date AS opened, n.term_type,
               n.requested_quantity AS opening_qty, n.transaction_id AS new_tid,
               (SELECT min(received_date) FROM acc c
                 WHERE c.subscription_key = n.subscription_key AND c.transaction_type = 'CANCEL') AS cancel_date
        FROM acc n WHERE n.transaction_type = 'NEW'
    """)

    # -- 3.2-3.4 term chain, closed form: term k opens in month0 + k months (or years),
    #    on the smaller of the opening day and every month length passed so far ------------
    con.execute(f"""
        CREATE TABLE term_raw AS
        WITH ks AS (
          SELECT s.*, g.k FROM sub s, generate_series(0, {MAX_TERMS_PER_SUBSCRIPTION}) AS g(k)
        ), m AS (
          SELECT *, CASE WHEN term_type = 'monthly'
                         THEN (date_trunc('month', opened) + to_months(k))::DATE
                         ELSE (date_trunc('month', opened) + to_years(k))::DATE END AS mstart
          FROM ks
        ), d AS (
          SELECT *, day(last_day(mstart)) AS dim FROM m
        ), a AS (
          SELECT *, least(day(opened),
                          coalesce(min(CASE WHEN k > 0 THEN dim END)
                                   OVER (PARTITION BY subscription_key ORDER BY k
                                         ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW), 31)) AS anchor
          FROM d
        ), t AS (
          SELECT subscription_key, term_type, opened, cancel_date, opening_qty, new_tid, k,
                 (mstart + to_days(anchor - 1))::DATE AS term_start
          FROM a
        )
        SELECT *, (lead(term_start) OVER (PARTITION BY subscription_key ORDER BY k) - INTERVAL 1 DAY)::DATE AS term_end
        FROM t
    """)
    # -- 3.5-3.7: emit while term_start <= as-of and not after the term holding the CANCEL
    con.execute(f"""
        CREATE TABLE term0 AS
        SELECT subscription_key, term_type, k + 1 AS term_seq, term_start, term_end,
               k > 0 AS derived, CASE WHEN k = 0 THEN new_tid END AS opened_by_transaction_id,
               cancel_date, opening_qty
        FROM term_raw
        WHERE term_start <= DATE '{as_of_s}' AND (cancel_date IS NULL OR term_start <= cancel_date)
          AND term_end IS NOT NULL
    """)

    # -- 4.4 opening quantity: the last accepted NEW/ADD/REDUCE received before term_start
    con.execute("""
        CREATE TABLE q_daily AS
        SELECT subscription_key, received_date,
               arg_max(requested_quantity, transaction_id) AS q,
               lead(received_date) OVER (PARTITION BY subscription_key ORDER BY received_date) AS next_date
        FROM acc WHERE transaction_type IN ('NEW','ADD','REDUCE')
        GROUP BY subscription_key, received_date
    """)
    con.execute("""
        CREATE TABLE term AS
        SELECT t.subscription_key, t.term_type, t.term_seq, t.term_start, t.term_end, t.derived,
               t.opened_by_transaction_id, t.cancel_date,
               CASE WHEN t.term_seq = 1 THEN t.opening_qty ELSE q.q END AS opening_quantity
        FROM term0 t
        LEFT JOIN q_daily q
          ON q.subscription_key = t.subscription_key
         AND t.term_seq > 1
         AND q.received_date < t.term_start
         AND (q.next_date IS NULL OR q.next_date >= t.term_start)
    """)

    # -- every accepted order placed in its term (2.2: a boundary-day order is in the new term)
    con.execute("""
        CREATE TABLE acc_term AS
        SELECT a.transaction_id, a.received_date, a.subscription_key, a.transaction_type,
               a.requested_quantity, a.ord,
               t.term_type, t.term_seq, t.term_start, t.term_end, t.opening_quantity
        FROM acc a JOIN term t
          ON t.subscription_key = a.subscription_key
         AND a.received_date BETWEEN t.term_start AND t.term_end
        WHERE a.transaction_type IN ('ADD','REDUCE','CANCEL')
    """)

    # -- 4.2 daily effective quantity over a generated calendar ---------------------------
    con.execute(f"""
        CREATE TABLE cal AS
        SELECT d::DATE AS d
        FROM generate_series((SELECT min(opened) FROM sub), DATE '{as_of_s}', INTERVAL 1 DAY) AS g(d)
    """)
    con.execute(f"""
        CREATE TABLE day_q AS
        SELECT t.subscription_key, t.term_type, t.term_seq, c.d,
               greatest(t.opening_quantity, coalesce(max(o.requested_quantity), 0)) AS eff
        FROM term t
        JOIN cal c ON c.d BETWEEN t.term_start AND least(t.term_end, DATE '{as_of_s}')
        LEFT JOIN acc_term o
          ON o.subscription_key = t.subscription_key AND o.term_seq = t.term_seq
         AND o.transaction_type IN ('ADD','REDUCE') AND o.received_date <= c.d
        GROUP BY t.subscription_key, t.term_type, t.term_seq, c.d, t.opening_quantity
    """)

    # -- 8.3 register quantity at a date: last accepted order of any kind (CANCEL carries 0)
    con.execute("""
        CREATE TABLE reg_daily AS
        SELECT subscription_key, received_date,
               arg_max(requested_quantity, transaction_id) AS q,
               lead(received_date) OVER (PARTITION BY subscription_key ORDER BY received_date) AS next_date
        FROM acc GROUP BY subscription_key, received_date
    """)

    # -- 5.2, 5.3, 6.x subscription-months ------------------------------------------------
    con.execute(f"""
        CREATE TABLE bm AS
        WITH g AS (
          SELECT subscription_key, term_type, strftime(d, '%Y-%m') AS month_key,
                 last_day(min(d)) AS month_end_date,
                 day(last_day(min(d))) AS days_in_month,
                 count(*) AS effective_days,
                 sum(eff)::BIGINT AS licence_days,
                 count(DISTINCT term_seq) AS n_terms,
                 min(term_seq) AS min_seq,
                 coalesce(max(CASE WHEN d = last_day(d) THEN eff END), 0)::BIGINT AS effective_quantity_at_month_end
          FROM day_q GROUP BY 1, 2, 3
        )
        SELECT g.subscription_key, g.month_key, s.customer_key, s.partner_id, s.channel, g.term_type,
               g.days_in_month, g.effective_days, g.licence_days,
               CASE g.term_type WHEN 'annual' THEN {RATE_CENTS['annual']} ELSE {RATE_CENTS['monthly']} END AS rate_cents,
               (g.licence_days * (CASE g.term_type WHEN 'annual' THEN {RATE_CENTS['annual']} ELSE {RATE_CENTS['monthly']} END) * 2
                 + g.days_in_month) // (2 * g.days_in_month) AS billable_amount_cents,
               coalesce(r.q, 0)::BIGINT AS register_quantity_at_month_end,
               g.effective_quantity_at_month_end,
               g.effective_quantity_at_month_end - coalesce(r.q, 0) AS gap_quantity,
               (g.effective_quantity_at_month_end - coalesce(r.q, 0))
                 * (CASE g.term_type WHEN 'annual' THEN {RATE_CENTS['annual']} ELSE {RATE_CENTS['monthly']} END) AS gap_amount_cents,
               g.min_seq > 1 AS derived,
               g.n_terms > 1 AS straddles_boundary,
               g.licence_days <> g.days_in_month * g.effective_quantity_at_month_end AS is_partial_month
        FROM g
        JOIN subs s USING (subscription_key)
        LEFT JOIN reg_daily r
          ON r.subscription_key = g.subscription_key
         AND r.received_date <= g.month_end_date
         AND (r.next_date IS NULL OR r.next_date > g.month_end_date)
    """)

    # -- 3.8 term attributes -----------------------------------------------------------------
    con.execute(f"""
        CREATE TABLE term_out AS
        WITH closing AS (
          SELECT subscription_key, term_seq, arg_max(eff, d) AS closing_quantity FROM day_q GROUP BY 1, 2
        ), last_order AS (
          SELECT subscription_key, term_seq,
                 arg_max(requested_quantity, ord) FILTER (WHERE transaction_type IN ('ADD','REDUCE')) AS last_q,
                 bool_or(transaction_type = 'CANCEL') AS cancel_pending
          FROM acc_term
          WHERE received_date <= DATE '{as_of_s}'
          GROUP BY 1, 2
        )
        SELECT t.subscription_key, t.term_seq, t.term_start, t.term_end, t.opening_quantity,
               c.closing_quantity,
               CASE WHEN l.last_q IS NOT NULL AND l.last_q < c.closing_quantity THEN l.last_q END AS pending_reduction_target,
               coalesce(l.cancel_pending, FALSE) AS cancel_pending,
               t.derived, t.opened_by_transaction_id
        FROM term t
        JOIN closing c USING (subscription_key, term_seq)
        LEFT JOIN last_order l USING (subscription_key, term_seq)
    """)

    # -- 8.1 deferrals: every accepted order that created a pending reduction, and every
    #    accepted CANCEL. Pending iff q < E just before it (max of opening and earlier orders
    #    in the same term).
    con.execute(f"""
        CREATE TABLE dfr AS
        WITH o AS (
          SELECT *, greatest(opening_quantity,
                             coalesce(max(CASE WHEN transaction_type IN ('ADD','REDUCE') THEN requested_quantity END)
                                      OVER (PARTITION BY subscription_key, term_seq ORDER BY ord
                                            ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING), 0)) AS e_before,
                 max(ord) OVER (PARTITION BY subscription_key, term_seq) AS last_ord_in_term,
                 bool_or(transaction_type = 'CANCEL') OVER (PARTITION BY subscription_key, term_seq) AS term_cancelled
          FROM acc_term
        )
        SELECT transaction_id, subscription_key, term_type, transaction_type, received_date, term_seq,
               (term_end + INTERVAL 1 DAY)::DATE AS landing_date,
               date_diff('day', received_date, (term_end + INTERVAL 1 DAY)::DATE) AS days_pending,
               (term_end + INTERVAL 1 DAY)::DATE <= DATE '{as_of_s}' AS landed_by_as_of,
               CASE WHEN transaction_type = 'CANCEL'
                    THEN (term_end + INTERVAL 1 DAY)::DATE <= DATE '{as_of_s}'
                    ELSE (term_end + INTERVAL 1 DAY)::DATE <= DATE '{as_of_s}'
                         AND ord = last_ord_in_term AND NOT term_cancelled END AS took_effect_as_scheduled
        FROM o
        WHERE transaction_type = 'CANCEL' OR requested_quantity < e_before
    """)

    # -- 7 invoice roll-up: amount by the row's own attributes; constituents through cust --
    con.execute("""
        CREATE TABLE inv AS
        WITH amount AS (
          SELECT month_key, channel,
                 CASE WHEN channel = 'partner' THEN partner_id ELSE 'DIRECT' END AS partner_id,
                 CASE WHEN channel = 'direct' THEN customer_key ELSE '' END AS customer_key,
                 sum(billable_amount_cents)::BIGINT AS invoice_amount_cents
          FROM bm GROUP BY 1, 2, 3, 4
        ), constituents AS (
          SELECT b.month_key, c.channel,
                 CASE WHEN c.channel = 'partner' THEN c.partner_id ELSE 'DIRECT' END AS partner_id,
                 CASE WHEN c.channel = 'direct' THEN b.customer_key ELSE '' END AS customer_key,
                 count(*) AS constituent_count,
                 sum(b.billable_amount_cents)::BIGINT AS constituent_sum_cents
          FROM bm b JOIN cust c USING (customer_key)
          GROUP BY 1, 2, 3, 4
        )
        SELECT coalesce(a.month_key, k.month_key) AS month_key,
               coalesce(a.channel, k.channel) AS channel,
               coalesce(a.partner_id, k.partner_id) AS partner_id,
               coalesce(a.customer_key, k.customer_key) AS customer_key,
               coalesce(a.invoice_amount_cents, 0) AS invoice_amount_cents,
               coalesce(k.constituent_count, 0) AS constituent_count,
               coalesce(k.constituent_sum_cents, 0) AS constituent_sum_cents,
               coalesce(a.invoice_amount_cents, 0) - coalesce(k.constituent_sum_cents, 0) AS tie_out_difference_cents
        FROM amount a FULL OUTER JOIN constituents k
          ON a.month_key = k.month_key AND a.channel = k.channel
         AND a.partner_id = k.partner_id AND a.customer_key = k.customer_key
    """)


def measures_sql(con: duckdb.DuckDBPyConnection, as_of: date) -> dict:
    """Every M- value, as SQL aggregates, in the same shape Path 1 publishes."""
    mk = f"{as_of.year:04d}-{as_of.month:02d}"
    one = lambda sql, *p: con.execute(sql, list(p)).fetchone()  # noqa: E731

    m01, m02, gap_lic, gap_c, bill_at = one(
        "SELECT sum(effective_quantity_at_month_end), sum(register_quantity_at_month_end), "
        "sum(gap_quantity), sum(gap_amount_cents), sum(billable_amount_cents) FROM bm WHERE month_key = ?", mk)
    n_rows, n_gap, total_c, partial_c, gap_all = one(
        "SELECT count(*), count(*) FILTER (WHERE gap_quantity > 0), sum(billable_amount_cents), "
        "sum(billable_amount_cents) FILTER (WHERE is_partial_month), sum(gap_amount_cents) FROM bm")
    gap_tt = dict(con.execute("SELECT term_type, sum(gap_amount_cents) FROM bm WHERE month_key = ? GROUP BY 1", [mk]).fetchall())
    bill_tt = dict(con.execute("SELECT term_type, sum(billable_amount_cents) FROM bm GROUP BY 1").fetchall())
    bill_ch = dict(con.execute("SELECT channel, sum(billable_amount_cents) FROM bm GROUP BY 1").fetchall())
    n_der, der_c = one("SELECT count(*) FILTER (WHERE derived), sum(billable_amount_cents) FILTER (WHERE derived) FROM bm")
    t_tot, t_der = one("SELECT count(*), count(*) FILTER (WHERE derived) FROM term_out")
    recv, rej = one("SELECT count(*), count(*) FILTER (WHERE rejection_reason IS NOT NULL) FROM classified")
    reasons = dict(con.execute("SELECT rejection_reason, count(*) FROM classified WHERE rejection_reason IS NOT NULL GROUP BY 1 ORDER BY 1").fetchall())
    lines, nonzero, p_lines, d_lines, inv_total = one(
        "SELECT count(*), count(*) FILTER (WHERE tie_out_difference_cents <> 0), "
        "count(*) FILTER (WHERE channel = 'partner'), count(*) FILTER (WHERE channel = 'direct'), "
        "sum(invoice_amount_cents) FROM inv")

    def m05(tt: str) -> dict:
        n, landed, took, mx = one(
            "SELECT count(*), count(*) FILTER (WHERE landed_by_as_of), "
            "count(*) FILTER (WHERE took_effect_as_scheduled), max(days_pending) FROM dfr WHERE term_type = ?", tt)
        # 8.2 nearest rank
        med, p90 = one("""
            WITH s AS (SELECT days_pending, row_number() OVER (ORDER BY days_pending) AS rn,
                              count(*) OVER () AS n FROM dfr WHERE term_type = ?)
            SELECT max(CASE WHEN rn = greatest(1, ceil(0.5 * n)) THEN days_pending END),
                   max(CASE WHEN rn = greatest(1, ceil(0.9 * n)) THEN days_pending END) FROM s""", tt)
        return {"n": int(n), "median_days": _i(med), "p90_days": _i(p90), "max_days": _i(mx),
                "landed_by_as_of": int(landed), "took_effect_as_scheduled": int(took),
                "backlog_cents_at_as_of": int(gap_tt.get(tt, 0) or 0)}

    total_c, gap_c, bill_at, partial_c = _i(total_c) or 0, _i(gap_c) or 0, _i(bill_at) or 0, _i(partial_c) or 0
    return {
        "as_of_date": as_of.isoformat(),
        "M-01_effective_licences_at_as_of": _i(m01) or 0,
        "M-02_register_licences_at_as_of": _i(m02) or 0,
        "M-03_entitlement_gap": {
            "licences_at_as_of": _i(gap_lic) or 0,
            "cents_at_as_of": gap_c,
            "backlog_share_of_as_of_month_billable": (gap_c / bill_at) if bill_at else None,
            "subscription_months_total": int(n_rows),
            "subscription_months_with_gap": int(n_gap),
            "subscription_months_with_gap_share": (n_gap / n_rows) if n_rows else None,
            "cents_at_as_of_by_term_type": {tt: int(gap_tt.get(tt, 0) or 0) for tt in ("annual", "monthly")},
            "annual_share_of_backlog_cents": (int(gap_tt.get("annual", 0) or 0) / gap_c) if gap_c else None,
            "gap_cents_all_months": _i(gap_all) or 0,
        },
        "M-04_prorated_revenue": {
            "billable_cents_all_months": total_c,
            "billable_cents_at_as_of_month": bill_at,
            "partial_month_cents": partial_c,
            "partial_month_share": (partial_c / total_c) if total_c else None,
            "by_term_type_cents": {tt: int(bill_tt.get(tt, 0) or 0) for tt in ("annual", "monthly")},
            "by_channel_cents": {ch: int(bill_ch.get(ch, 0) or 0) for ch in ("partner", "direct")},
        },
        "M-05_deferral_exposure": {tt: m05(tt) for tt in ("annual", "monthly")},
        "M-06_derived_share": {
            "rows_total": int(n_rows), "rows_derived": int(n_der),
            "rows_derived_share": (n_der / n_rows) if n_rows else None,
            "cents_derived": _i(der_c) or 0,
            "cents_derived_share": ((_i(der_c) or 0) / total_c) if total_c else None,
            "terms_total": int(t_tot), "terms_derived": int(t_der),
        },
        "M-07_rejected_transaction_rate": {
            "received": int(recv), "rejected": int(rej),
            "rate": (rej / recv) if recv else None,
            "by_reason": {k: int(v) for k, v in reasons.items()},
        },
        "M-08_invoice_tie_out": {
            "invoice_lines": int(lines), "lines_with_nonzero_tie_out": int(nonzero),
            "partner_lines": int(p_lines), "direct_lines": int(d_lines),
            "invoice_cents_total": _i(inv_total) or 0,
        },
    }


def _i(v):
    if v is None:
        return None
    if isinstance(v, float) and math.isnan(v):
        return None
    return int(v)


def stage2_sql(con: duckdb.DuckDBPyConnection, as_of: date) -> dict:
    """Stage 2 cuts, re-derived as SQL aggregates from this path's own tables.

    Definitions from governance/metric_register.md M-03a, M-05a, M-06a and the
    Stage 2 lineage notes under M-01 and M-02. Same shape as Path 1 publishes.
    """
    mk = f"{as_of.year:04d}-{as_of.month:02d}"
    tts, causes = ("annual", "monthly"), ("cancel_riding_out", "deferred_reduction")

    # M-03a: cause = cancel_pending on the term instance containing the as-of date
    rows = con.execute(f"""
        WITH cur AS (
          SELECT subscription_key, cancel_pending FROM term_out
          WHERE DATE '{as_of.isoformat()}' BETWEEN term_start AND term_end
        )
        SELECT b.term_type,
               CASE WHEN coalesce(c.cancel_pending, FALSE) THEN 'cancel_riding_out'
                    ELSE 'deferred_reduction' END AS cause,
               sum(b.gap_amount_cents), count(*), sum(b.gap_quantity)
        FROM bm b LEFT JOIN cur c USING (subscription_key)
        WHERE b.month_key = ? AND b.gap_amount_cents > 0
        GROUP BY 1, 2
    """, [mk]).fetchall()
    cells = {tt: {c: {"cents": 0, "subscription_months": 0, "licences": 0} for c in causes} for tt in tts}
    for tt, cause, cents, n, lic in rows:
        cells[tt][cause] = {"cents": int(cents), "subscription_months": int(n), "licences": int(lic)}
    total = sum(cells[tt][c]["cents"] for tt in tts for c in causes)

    # M-05a: by term type x transaction type; nearest-rank percentiles (rule 8.2)
    m05a = {tt: {} for tt in tts}
    for tt in tts:
        for ttype in ("ADD", "CANCEL", "REDUCE"):
            n, mn, mx = con.execute(
                "SELECT count(*), min(days_pending), max(days_pending) FROM dfr "
                "WHERE term_type = ? AND transaction_type = ?", [tt, ttype]).fetchone()
            med, p90 = con.execute("""
                WITH s AS (SELECT days_pending, row_number() OVER (ORDER BY days_pending) AS rn,
                                  count(*) OVER () AS n FROM dfr
                           WHERE term_type = ? AND transaction_type = ?)
                SELECT max(CASE WHEN rn = greatest(1, ceil(0.5 * n)) THEN days_pending END),
                       max(CASE WHEN rn = greatest(1, ceil(0.9 * n)) THEN days_pending END) FROM s""",
                [tt, ttype]).fetchone()
            m05a[tt][ttype] = {"n": int(n), "median_days": _i(med), "p90_days": _i(p90),
                               "min_days": _i(mn), "max_days": _i(mx)}
    hist = {tt: {str(b): 0 for b in range(0, 361, 30)} for tt in tts}
    for tt, b, n in con.execute(
            "SELECT term_type, least(360, (days_pending // 30) * 30), count(*) FROM dfr GROUP BY 1, 2").fetchall():
        hist[tt][str(int(b))] = int(n)

    # M-06a
    m06a = {}
    for tt, n, nd in con.execute(
            "SELECT term_type, count(*), count(*) FILTER (WHERE derived) FROM bm GROUP BY 1").fetchall():
        m06a[tt] = {"rows": int(n), "rows_derived": int(nd), "share": (nd / n) if n else None}

    # M-01 / M-02 at each month end
    series = [
        {"month_key": k, "effective_licences": int(e), "register_licences": int(r),
         "gap_licences": int(g), "gap_cents": int(gc), "billable_cents": int(bc), "rows": int(n)}
        for k, e, r, g, gc, bc, n in con.execute("""
            SELECT month_key, sum(effective_quantity_at_month_end), sum(register_quantity_at_month_end),
                   sum(gap_quantity), sum(gap_amount_cents), sum(billable_amount_cents), count(*)
            FROM bm GROUP BY 1 ORDER BY 1""").fetchall()
    ]
    return {
        "as_of_date": as_of.isoformat(),
        "M-03a_gap_at_as_of_by_term_type_and_cause": {"as_of_month": mk, "by_term_type": cells,
                                                      "total_cents": total},
        "M-05a_deferral_by_term_type_and_transaction_type": m05a,
        "M-05a_histogram_30_day_bins": hist,
        "M-06a_derived_share_by_term_type": m06a,
        "M-01_M-02_monthly_series": series,
    }


# ---------------------------------------------------------------------------
# entry points
# ---------------------------------------------------------------------------

OUT_QUERIES = {
    "order_events": "SELECT transaction_id, received_date, subscription_key, transaction_type, "
                    "requested_quantity, term_type, source, rejection_reason IS NULL AS accepted, "
                    "rejection_reason FROM classified ORDER BY transaction_id",
    "terms": "SELECT subscription_key, term_seq, term_start, term_end, opening_quantity, closing_quantity, "
             "pending_reduction_target, cancel_pending, derived, opened_by_transaction_id "
             "FROM term_out ORDER BY subscription_key, term_seq",
    "billable_months": "SELECT * FROM bm ORDER BY subscription_key, month_key",
    "deferrals": "SELECT * FROM dfr ORDER BY transaction_id",
    "invoice_lines": "SELECT * FROM inv ORDER BY month_key, channel, partner_id, customer_key",
}


def _records(df: pd.DataFrame) -> list[dict]:
    out = []
    for rec in df.to_dict("records"):
        clean = {}
        for k, v in rec.items():
            if v is None or (isinstance(v, float) and math.isnan(v)) or v is pd.NaT:
                clean[k] = None
            elif isinstance(v, datetime):        # pandas Timestamp is a datetime is a date
                clean[k] = v.date()
            elif hasattr(v, "item"):
                clean[k] = v.item()
            else:
                clean[k] = v
        out.append(clean)
    return out


def derive_from_files(events_csv: Path, subscriptions_csv: Path, as_of: date,
                      customers_csv: Path | None = None) -> dict[str, list[dict]]:
    con = duckdb.connect()
    load_inputs(con, Path(events_csv), Path(subscriptions_csv),
                Path(customers_csv) if customers_csv else None)
    derive_sql(con, as_of)
    out = {name: _records(con.execute(sql).df()) for name, sql in OUT_QUERIES.items()}
    out["measures"] = measures_sql(con, as_of)
    out["stage2"] = stage2_sql(con, as_of)
    con.close()
    return out


# ---------------------------------------------------------------------------
# comparison against what Path 1 published
# ---------------------------------------------------------------------------

def _norm(v) -> str:
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, float):
        if math.isnan(v):
            return ""
        return str(int(v)) if v.is_integer() else repr(v)
    if isinstance(v, datetime):
        return v.date().isoformat()
    if isinstance(v, date):
        return v.isoformat()
    if hasattr(v, "item"):
        return _norm(v.item())
    s = str(v).strip()
    if s.lower() in ("true", "false"):
        return s.lower()
    if s.lower() in ("nan", "none", "<na>", "nat"):
        return ""
    return s


def compare(name: str, published: pd.DataFrame, rederived: list[dict], keys: list[str],
            cols: list[str], mismatches: list[str]) -> int:
    """Compare column by column on the key; return the number of cells compared."""
    pub = {tuple(_norm(r[k]) for k in keys): r for r in published.to_dict("records")}
    red = {tuple(_norm(r[k]) for k in keys): r for r in rederived}
    for k in sorted(set(pub) - set(red)):
        mismatches.append(f"{name} {k}: published by Path 1, not re-derived by Path 2")
    for k in sorted(set(red) - set(pub)):
        mismatches.append(f"{name} {k}: re-derived by Path 2, not published by Path 1")
    cells = 0
    for k in sorted(set(pub) & set(red)):
        p, r = pub[k], red[k]
        for c in cols:
            cells += 1
            if _norm(p.get(c)) != _norm(r.get(c)):
                mismatches.append(f"{name} {k} .{c}: Path 1 {_norm(p.get(c))!r} vs Path 2 {_norm(r.get(c))!r}")
    return cells


def flatten(d, prefix: str = "") -> dict:
    out = {}
    items = d.items() if isinstance(d, dict) else enumerate(d)
    for k, v in items:
        p = f"{prefix}.{k}" if prefix else str(k)
        if isinstance(v, (dict, list)):
            out.update(flatten(v, p))
        else:
            out[p] = v
    return out


def main() -> int:
    raw_manifest = json.loads((RAW / "manifest.json").read_text(encoding="utf-8"))
    as_of = date.fromisoformat(raw_manifest["as_of_date"])
    print(f"validate_measures.py (Path 2, DuckDB {duckdb.__version__}), as-of {as_of}")
    print(f"  {raw_manifest['disclosure']}")

    out = derive_from_files(RAW / "order_events.csv", CONF / "dim_subscription.csv", as_of,
                            customers_csv=CONF / "dim_customer.csv")

    read = lambda n: pd.read_csv(CONF / n, dtype=str, keep_default_na=False)  # noqa: E731
    mismatches: list[str] = []
    cells = 0
    cells += compare("fact_order_event", read("fact_order_event.csv"), out["order_events"],
                     ["transaction_id"], ["accepted", "rejection_reason"], mismatches)
    cells += compare("fact_entitlement_term", read("fact_entitlement_term.csv"), out["terms"],
                     ["subscription_key", "term_seq"],
                     ["term_start", "term_end", "opening_quantity", "closing_quantity",
                      "pending_reduction_target", "cancel_pending", "derived", "opened_by_transaction_id"],
                     mismatches)
    cells += compare("fact_billable_month", read("fact_billable_month.csv"), out["billable_months"],
                     ["subscription_key", "month_key"],
                     ["customer_key", "partner_id", "channel", "term_type", "days_in_month", "effective_days",
                      "licence_days", "rate_cents", "billable_amount_cents", "register_quantity_at_month_end",
                      "effective_quantity_at_month_end", "gap_quantity", "gap_amount_cents", "derived",
                      "straddles_boundary", "is_partial_month"], mismatches)
    cells += compare("fact_deferral", read("fact_deferral.csv"), out["deferrals"],
                     ["transaction_id"],
                     ["subscription_key", "term_type", "transaction_type", "received_date", "term_seq",
                      "landing_date", "days_pending", "landed_by_as_of", "took_effect_as_scheduled"], mismatches)
    cells += compare("fact_invoice_line", read("fact_invoice_line.csv"), out["invoice_lines"],
                     ["month_key", "channel", "partner_id", "customer_key"],
                     ["invoice_amount_cents", "constituent_count", "constituent_sum_cents",
                      "tie_out_difference_cents"], mismatches)

    def compare_measures(label: str, published: dict, rederived: dict) -> int:
        n = 0
        p1, p2 = flatten(published), flatten(rederived)
        for k in sorted(set(p1) | set(p2)):
            n += 1
            a, b = p1.get(k), p2.get(k)
            if isinstance(a, float) or isinstance(b, float):
                same = (a is not None and b is not None and abs(float(a) - float(b)) <= 1e-9)
            else:
                same = _norm(a) == _norm(b)
            if not same:
                mismatches.append(f"{label} {k}: Path 1 {a!r} vs Path 2 {b!r}")
        return n

    published = json.loads((CONF / "measures_manifest.json").read_text(encoding="utf-8"))["measures"]
    cells += compare_measures("measures", published, out["measures"])

    # Stage 2 (2026-09-14): the page's cuts, published by Path 1 in a separate file.
    # The monthly series is a list; flatten() keys it by index, which is what we want.
    stage2_path = CONF / "measures_stage2.json"
    stage2_cells = 0
    if stage2_path.exists():
        published2 = json.loads(stage2_path.read_text(encoding="utf-8"))["measures"]
        stage2_cells = compare_measures("stage2", published2, out["stage2"])
        cells += stage2_cells
    else:
        mismatches.append("stage2: data/conformed/measures_stage2.json is not published")

    print(f"  cells compared: {cells:,}  (events, terms, subscription-months, deferrals, invoice lines, "
          f"M- values; of which {stage2_cells:,} in measures_stage2.json)")
    if mismatches:
        summary: dict[str, int] = {}
        for m in mismatches:
            head = m.split(":")[0]
            tag = head.split(" ")[0] + (" ." + head.rsplit(".", 1)[1] if " ." in head else " (key)")
            summary[tag] = summary.get(tag, 0) + 1
        print(f"  MISMATCHES: {len(mismatches):,} -- by table and column:")
        for tag, n in sorted(summary.items(), key=lambda kv: -kv[1]):
            print(f"    {n:>8,}  {tag}")
        print("  first 20:")
        for m in mismatches[:20]:
            print(f"    - {m}")
        print("\nPUBLISH GATE: FAILED -- Path 2 does not agree with Path 1. Publish nothing.")
        return 1
    print("  every published cell re-derives identically down the set-based path")
    print("\nPUBLISH GATE: PASSED -- the two paths agree.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
