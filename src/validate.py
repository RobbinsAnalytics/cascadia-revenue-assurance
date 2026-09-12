"""validate.py -- the domain gate. Exits non-zero on any failure (PRINCIPLES rule 8).

Checks the things the rules say must be true of the published tables, plus the
things the generator and the engine must agree on. It does NOT compare Path 1
with Path 2 -- that is src/validate_measures.py -- and it does NOT check the
freeze -- that is src/validate_freeze.py. Run all three, plus src/test_golden.py.

    1. gap_quantity >= 0 on every subscription-month (rule 4.2 makes it so by construction)
    2. no subscription-month after a cancelled term's end (rule 6.1)
    3. every derived term has opened_by_transaction_id null; every observed term has it
       set to that subscription's accepted NEW; exactly one observed term per subscription
    4. invoice tie-out zero on every line; invoice total equals subscription-month total
    5. dim_subscription's register attributes equal what the accepted events imply
    6. the engine refused exactly the transactions the generator intended to be refused
    7. no transaction after the as-of date; ids unique and monotonic in date
    8. the as-of date agrees across freeze.toml, the raw manifest and the measures manifest
    9. every output document carries the synthetic disclosure
   10. reproducibility: regenerating from SEED into a temporary folder reproduces every raw
       file and governance/generator_assumptions.md byte for byte

    python src/validate.py
"""

from __future__ import annotations

import csv
import filecmp
import json
import sys
import tempfile
import tomllib
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = Path(__file__).resolve().parent.parent
RAW = REPO / "data" / "raw"
CONF = REPO / "data" / "conformed"
GOV = REPO / "governance"

sys.path.insert(0, str(REPO / "src"))
import generate  # noqa: E402  -- for SEED and the regenerate-and-diff check


def read_csv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def main() -> int:
    results: list[tuple[str, bool, str]] = []

    def record(name: str, ok: bool, detail: str) -> None:
        results.append((name, ok, detail))

    ev = read_csv(CONF / "fact_order_event.csv")
    terms = read_csv(CONF / "fact_entitlement_term.csv")
    bm = read_csv(CONF / "fact_billable_month.csv")
    inv = read_csv(CONF / "fact_invoice_line.csv")
    dsub = read_csv(CONF / "dim_subscription.csv")
    raw_manifest = json.loads((RAW / "manifest.json").read_text(encoding="utf-8"))
    measures_doc = json.loads((CONF / "measures_manifest.json").read_text(encoding="utf-8"))
    conf_manifest = json.loads((CONF / "manifest.json").read_text(encoding="utf-8"))
    freeze = tomllib.loads((GOV / "freeze.toml").read_text(encoding="utf-8"))["freeze"]
    as_of = raw_manifest["as_of_date"]

    # 1 -----------------------------------------------------------------------------
    neg = [r for r in bm if int(r["gap_quantity"]) < 0]
    record("gap_quantity >= 0 on every subscription-month", not neg,
           f"{len(bm):,} rows, {len(neg)} negative")

    # 2 -----------------------------------------------------------------------------
    cancelled_end = {t["subscription_key"]: t["term_end"] for t in terms if t["cancel_pending"] == "true"}
    late = [r for r in bm if r["subscription_key"] in cancelled_end
            and r["month_key"] > cancelled_end[r["subscription_key"]][:7]]
    record("no subscription-month after a cancelled term's end", not late,
           f"{len(cancelled_end):,} cancelled subscriptions, {len(late)} rows after term end")

    # 3 -----------------------------------------------------------------------------
    accepted_new = {e["subscription_key"]: e["transaction_id"] for e in ev
                    if e["transaction_type"] == "NEW" and e["accepted"] == "true"}
    bad_derived = [t for t in terms if t["derived"] == "true" and t["opened_by_transaction_id"] != ""]
    bad_observed = [t for t in terms if t["derived"] == "false"
                    and t["opened_by_transaction_id"] != accepted_new.get(t["subscription_key"])]
    observed_per_sub: dict[str, int] = {}
    for t in terms:
        if t["derived"] == "false":
            observed_per_sub[t["subscription_key"]] = observed_per_sub.get(t["subscription_key"], 0) + 1
    not_one = [k for k, n in observed_per_sub.items() if n != 1]
    missing_obs = [k for k in accepted_new if k not in observed_per_sub]
    record("derived terms carry no opener; observed terms carry their NEW; one observed term per subscription",
           not (bad_derived or bad_observed or not_one or missing_obs),
           f"{len(terms):,} terms; {len(bad_derived)} derived with opener, {len(bad_observed)} observed "
           f"with wrong opener, {len(not_one)} subscriptions with != 1 observed term, {len(missing_obs)} without one")

    # 4 -----------------------------------------------------------------------------
    nonzero = [l for l in inv if int(l["tie_out_difference_cents"]) != 0]
    inv_total = sum(int(l["invoice_amount_cents"]) for l in inv)
    bm_total = sum(int(r["billable_amount_cents"]) for r in bm)
    record("invoice tie-out zero on every line, and invoices sum to the subscription-months",
           not nonzero and inv_total == bm_total,
           f"{len(inv):,} lines, {len(nonzero)} non-zero; invoices {inv_total:,} vs subscription-months {bm_total:,} cents")

    # 5 -----------------------------------------------------------------------------
    last_q: dict[str, int] = {}
    cancel_date: dict[str, str] = {}
    for e in sorted(ev, key=lambda e: (e["received_date"], int(e["transaction_id"]))):
        if e["accepted"] != "true":
            continue
        last_q[e["subscription_key"]] = int(e["requested_quantity"])
        if e["transaction_type"] == "CANCEL":
            cancel_date[e["subscription_key"]] = e["received_date"]
    reg_bad = []
    for s in dsub:
        k = s["subscription_key"]
        want_q = last_q.get(k)
        want_status = "cancelled" if k in cancel_date else "active"
        want_date = cancel_date.get(k, s["opened_date"])
        if (int(s["register_quantity"]) != want_q or s["register_status"] != want_status
                or s["register_status_date"] != want_date):
            reg_bad.append(k)
    keys_dim, keys_new = {s["subscription_key"] for s in dsub}, set(accepted_new)
    record("dim_subscription register quantity, status and status date equal the last accepted order",
           not reg_bad and keys_dim == keys_new,
           f"{len(dsub):,} subscriptions, {len(reg_bad)} disagree; "
           f"{len(keys_dim ^ keys_new)} key(s) in one side only")

    # 6 -----------------------------------------------------------------------------
    intended = raw_manifest["counts"]["transactions_intended_to_be_refused_by_reason"]
    got: dict[str, int] = {}
    for e in ev:
        if e["accepted"] == "false":
            got[e["rejection_reason"]] = got.get(e["rejection_reason"], 0) + 1
    record("the engine refused exactly the transactions the generator intended, by reason",
           got == intended, f"engine {got} vs generator {intended}")

    # 7 -----------------------------------------------------------------------------
    ids = [int(e["transaction_id"]) for e in ev]
    dates = [e["received_date"] for e in ev]
    order = sorted(range(len(ev)), key=lambda i: ids[i])
    monotonic = all(dates[order[i]] <= dates[order[i + 1]] for i in range(len(order) - 1))
    record("no transaction after as-of; ids unique and monotonic in received_date",
           max(dates) <= as_of and len(set(ids)) == len(ids) and monotonic,
           f"{len(ev):,} transactions, last {max(dates)}, as-of {as_of}")

    # 8 -----------------------------------------------------------------------------
    record("as-of agrees across freeze.toml, raw manifest, measures manifest and conformed manifest",
           freeze["as_of_date"] == as_of == measures_doc["measures"]["as_of_date"] == conf_manifest["as_of_date"],
           f"{freeze['as_of_date']} / {as_of} / {measures_doc['measures']['as_of_date']} / {conf_manifest['as_of_date']}")

    # 9 -----------------------------------------------------------------------------
    disclosure = raw_manifest["disclosure"]
    docs = [GOV / "generator_assumptions.md", GOV / "reconciliation.md",
            CONF / "measures_manifest.json", CONF / "manifest.json"]
    missing = [d.name for d in docs if disclosure not in d.read_text(encoding="utf-8")]
    record("every output document carries the synthetic disclosure", not missing,
           f"{len(docs)} documents checked; missing from {missing or 'none'}")

    # 10 ----------------------------------------------------------------------------
    with tempfile.TemporaryDirectory() as tmp:
        tmp_raw = Path(tmp) / "raw"
        tmp_asm = Path(tmp) / "generator_assumptions.md"
        generate.generate(tmp_raw, tmp_asm)
        pairs = [(RAW / f, tmp_raw / f) for f in raw_manifest["files"]] + [(GOV / "generator_assumptions.md", tmp_asm)]
        differing = [a.name for a, b in pairs if not (b.exists() and filecmp.cmp(a, b, shallow=False))]
    record(f"reproducible from seed {generate.SEED}: regenerated and diffed byte for byte", not differing,
           f"{len(pairs)} files compared; differing: {differing or 'none'}")

    # report ---------------------------------------------------------------------------
    print(f"validate.py -- domain gate, as-of {as_of}")
    print(f"  {disclosure}")
    ok_all = True
    for name, ok, detail in results:
        ok_all &= ok
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
        print(f"        {detail}")
    print("\nPUBLISH GATE: " + ("PASSED -- every domain check holds." if ok_all
                                else "FAILED -- publish nothing, commit nothing under data/conformed/."))
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
