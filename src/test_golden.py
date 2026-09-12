"""test_golden.py -- the hand-specified acceptance fixture, run against both paths.

Written 2026-09-11 BEFORE any engine code existed, and committed failing. The
expected values in tests/golden/*.csv were computed by hand from
governance/entitlement-rules.md; this script only compares.

Both derivation paths must expose the same entry point:

    derive_from_files(events_csv: Path, subscriptions_csv: Path, as_of: date)
        -> dict with keys
           "order_events"    rows: transaction_id, accepted, rejection_reason
           "terms"           rows: subscription_key, term_seq, term_start,
                                   term_end, opening_quantity, derived,
                                   pending_reduction_target, cancel_pending
           "billable_months" rows: subscription_key, month_key, licence_days,
                                   days_in_month, billable_amount_cents,
                                   gap_quantity, gap_amount_cents, derived,
                                   straddles_boundary, is_partial_month
           "deferrals"       rows: transaction_id, days_pending,
                                   landed_by_as_of, took_effect_as_scheduled
           "invoice_lines"   rows: month_key, channel, partner_id,
                                   customer_key, invoice_amount_cents,
                                   constituent_count

Path 1 is src/build_entitlement.py; Path 2 is src/validate_measures.py. This
harness imports both. Neither imports the other (D12).

Exit 0 only if every expected cell matches on BOTH paths. A path that cannot
be imported is a failure, not a skip -- that is what "committed failing" means.

    python src/test_golden.py
"""

from __future__ import annotations

import csv
import importlib
import sys
from datetime import date
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = Path(__file__).resolve().parent.parent
GOLDEN = REPO / "tests" / "golden"
AS_OF = date(2026, 6, 30)

PATHS = {
    "Path 1 (build_entitlement)": "build_entitlement",
    "Path 2 (validate_measures)": "validate_measures",
}


def read_csv(name: str) -> list[dict]:
    with open(GOLDEN / name, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def norm(v) -> str:
    """Normalise a cell for comparison: bools, ints, None, dates, floats."""
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, float):
        if v != v:  # NaN
            return ""
        if v.is_integer():
            return str(int(v))
        return repr(v)
    s = str(v).strip()
    if s.lower() in ("true", "false"):
        return s.lower()
    if s.lower() in ("nan", "none", "<na>"):
        return ""
    return s


def check(label: str, expected: str, actual, failures: list[str]) -> None:
    if norm(expected) != norm(actual):
        failures.append(f"{label}: expected {expected!r}, got {norm(actual)!r}")


def run_path(name: str, module_name: str) -> list[str]:
    failures: list[str] = []
    sys.path.insert(0, str(REPO / "src"))
    try:
        mod = importlib.import_module(module_name)
    except Exception as exc:  # noqa: BLE001 -- a missing engine is a failure
        return [f"{name}: cannot import src/{module_name}.py -- {type(exc).__name__}: {exc}"]
    try:
        out = mod.derive_from_files(
            GOLDEN / "golden_events.csv",
            GOLDEN / "golden_subscriptions.csv",
            AS_OF,
        )
    except Exception as exc:  # noqa: BLE001
        return [f"{name}: derive_from_files raised {type(exc).__name__}: {exc}"]

    # -- events -------------------------------------------------------------
    ev = {norm(r["transaction_id"]): r for r in out["order_events"]}
    for exp in read_csv("golden_expected_events.csv"):
        tid = exp["transaction_id"]
        row = ev.get(tid)
        if row is None:
            failures.append(f"event {tid}: missing from output")
            continue
        check(f"event {tid} accepted", exp["accepted"], row["accepted"], failures)
        check(f"event {tid} rejection_reason", exp["rejection_reason"],
              row.get("rejection_reason"), failures)

    # -- billable months ----------------------------------------------------
    bm = {(norm(r["subscription_key"]), norm(r["month_key"])): r
          for r in out["billable_months"]}
    for exp in read_csv("golden_expected.csv"):
        key = (exp["subscription_key"], exp["month_key"])
        label = f"{exp['case']} {key[0]} {key[1]}"
        row = bm.get(key)
        if exp["expect_absent"] == "1":
            if row is not None:
                failures.append(f"{label}: expected NO row, got one "
                                f"(licence_days={row.get('licence_days')})")
            continue
        if row is None:
            failures.append(f"{label}: expected a row, got none")
            continue
        lm = int(row["licence_days"]) / int(row["days_in_month"])
        if abs(lm - float(exp["licence_months"])) > 0.00005:
            failures.append(f"{label} licence_months: expected {exp['licence_months']}, "
                            f"got {lm:.4f}")
        check(f"{label} amount_cents", exp["amount_cents"],
              row["billable_amount_cents"], failures)
        for col in ("gap_quantity", "gap_amount_cents", "derived",
                    "straddles_boundary", "is_partial_month"):
            if exp[col] != "":
                check(f"{label} {col}", exp[col], row[col], failures)

    # -- terms --------------------------------------------------------------
    terms = {(norm(r["subscription_key"]), norm(r["term_seq"])): r for r in out["terms"]}
    for exp in read_csv("golden_expected_terms.csv"):
        key = (exp["subscription_key"], exp["term_seq"])
        label = f"term {key[0]}#{key[1]}"
        row = terms.get(key)
        if exp["expect_absent"] == "1":
            if row is not None:
                failures.append(f"{label}: expected NO term, got one "
                                f"({row.get('term_start')}..{row.get('term_end')})")
            continue
        if row is None:
            failures.append(f"{label}: expected a term, got none")
            continue
        for col in ("term_start", "term_end", "opening_quantity", "derived",
                    "pending_reduction_target", "cancel_pending"):
            check(f"{label} {col}", exp[col], row[col], failures)

    # -- deferrals ----------------------------------------------------------
    de = {norm(r["transaction_id"]): r for r in out["deferrals"]}
    for exp in read_csv("golden_expected_deferrals.csv"):
        tid = exp["transaction_id"]
        row = de.get(tid)
        if row is None:
            failures.append(f"deferral {tid}: missing from output")
            continue
        for col in ("days_pending", "landed_by_as_of", "took_effect_as_scheduled"):
            check(f"deferral {tid} {col}", exp[col], row[col], failures)

    # -- invoice lines ------------------------------------------------------
    inv = {(norm(r["month_key"]), norm(r["channel"]), norm(r["partner_id"]),
            norm(r.get("customer_key"))): r for r in out["invoice_lines"]}
    for exp in read_csv("golden_expected_invoice.csv"):
        key = (exp["month_key"], exp["channel"], exp["partner_id"], exp["customer_key"])
        label = f"invoice {key}"
        row = inv.get(key)
        if row is None:
            failures.append(f"{label}: missing from output")
            continue
        check(f"{label} invoice_amount_cents", exp["invoice_amount_cents"],
              row["invoice_amount_cents"], failures)
        check(f"{label} constituent_count", exp["constituent_count"],
              row["constituent_count"], failures)

    return failures


def main() -> int:
    n_expected = (len(read_csv("golden_expected.csv"))
                  + len(read_csv("golden_expected_events.csv"))
                  + len(read_csv("golden_expected_terms.csv"))
                  + len(read_csv("golden_expected_deferrals.csv"))
                  + len(read_csv("golden_expected_invoice.csv")))
    print(f"Golden fixture: {n_expected} expected rows, as-of {AS_OF.isoformat()}")
    all_ok = True
    for name, module_name in PATHS.items():
        failures = run_path(name, module_name)
        if failures:
            all_ok = False
            print(f"  FAIL  {name}: {len(failures)} mismatch(es)")
            for f in failures[:40]:
                print(f"        - {f}")
            if len(failures) > 40:
                print(f"        ... and {len(failures) - 40} more")
        else:
            print(f"  PASS  {name}: every expected row matches")
    print("\nGOLDEN: " + ("PASSED" if all_ok else "FAILED"))
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
