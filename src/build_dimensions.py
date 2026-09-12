"""build_dimensions.py -- the dim_* tables, from the frozen raw layer.

Reads   data/raw/customers.csv, data/raw/subscriptions_register.csv,
        data/raw/manifest.json
Writes  data/conformed/dim_date.csv          one row per day in the window
        data/conformed/dim_term_type.csv     two rows: annual, monthly
        data/conformed/dim_partner.csv       three synthetic partners + DIRECT
        data/conformed/dim_customer.csv      one row per customer
        data/conformed/dim_subscription.csv  one row per subscription, with the
                                             REGISTER attributes as of the as-of
                                             date -- what a naive query reads

Grain and observed/derived status of every table are in governance/codebook.md.
Both derivation paths may read these tables (D12 allows dim_* and
fact_order_event as the only shared inputs). Neither path may read anything
this script does not write.

    python src/build_dimensions.py
"""

from __future__ import annotations

import calendar
import csv
import json
import sys
from datetime import date, timedelta
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = Path(__file__).resolve().parent.parent
RAW = REPO / "data" / "raw"
CONF = REPO / "data" / "conformed"

# Restated deliberately from governance/entitlement-rules.md section 0. Each
# derivation path restates them too; there is no shared constants module (D12).
TERM_TYPES = [
    # term_type, months_per_term, rate_cents_per_licence_month, description
    ("annual", 12, 1000, "Twelve-month term, billed one-twelfth per calendar month in arrears"),
    ("monthly", 1, 1200, "One-month term, billed per calendar month in arrears"),
]


def read_csv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def write_csv(path: Path, rows: list[dict], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(columns)
        for r in rows:
            w.writerow([r[c] for c in columns])


def build_dim_date(start: date, end: date) -> list[dict]:
    rows, d = [], start
    while d <= end:
        dim = calendar.monthrange(d.year, d.month)[1]
        rows.append({
            "date_key": d.isoformat(),
            "year": d.year,
            "month": d.month,
            "month_key": f"{d.year:04d}-{d.month:02d}",
            "day_of_month": d.day,
            "days_in_month": dim,
            "is_month_start": "true" if d.day == 1 else "false",
            "is_month_end": "true" if d.day == dim else "false",
        })
        d += timedelta(days=1)
    return rows


def main() -> int:
    manifest = json.loads((RAW / "manifest.json").read_text(encoding="utf-8"))
    window = manifest["window"]
    start, end = date.fromisoformat(window["start"]), date.fromisoformat(window["end"])
    as_of = manifest["as_of_date"]

    dim_date = build_dim_date(start, end)
    write_csv(CONF / "dim_date.csv", dim_date,
              ["date_key", "year", "month", "month_key", "day_of_month",
               "days_in_month", "is_month_start", "is_month_end"])

    write_csv(CONF / "dim_term_type.csv",
              [{"term_type": t, "months_per_term": m, "rate_cents_per_licence_month": r,
                "description": d} for t, m, r, d in TERM_TYPES],
              ["term_type", "months_per_term", "rate_cents_per_licence_month", "description"])

    partners = [{"partner_id": p["partner_id"], "partner_name": p["partner_name"],
                 "channel": "partner", "designed_share_of_partner_customers": p["share"]}
                for p in manifest["parameters"]["PARTNERS"]]
    partners.append({"partner_id": "DIRECT", "partner_name": "Direct (no partner)",
                     "channel": "direct", "designed_share_of_partner_customers": ""})
    write_csv(CONF / "dim_partner.csv", partners,
              ["partner_id", "partner_name", "channel", "designed_share_of_partner_customers"])

    customers = read_csv(RAW / "customers.csv")
    write_csv(CONF / "dim_customer.csv", customers,
              ["customer_key", "partner_id", "customer_ref", "channel"])

    cust_by_key = {c["customer_key"]: c for c in customers}
    subs = []
    for r in read_csv(RAW / "subscriptions_register.csv"):
        c = cust_by_key[r["customer_key"]]
        subs.append({
            "subscription_key": r["subscription_key"],
            "customer_key": r["customer_key"],
            "partner_id": c["partner_id"],
            "channel": c["channel"],
            "term_type": r["term_type"],
            "opened_date": r["opened_date"],
            "register_quantity": r["register_quantity"],
            "register_status": r["register_status"],
            "register_status_date": r["register_status_date"],
            "register_as_of_date": as_of,
        })
    subs.sort(key=lambda s: s["subscription_key"])
    write_csv(CONF / "dim_subscription.csv", subs,
              ["subscription_key", "customer_key", "partner_id", "channel", "term_type",
               "opened_date", "register_quantity", "register_status",
               "register_status_date", "register_as_of_date"])

    print(f"build_dimensions.py: dim_date {len(dim_date):,} rows, dim_term_type {len(TERM_TYPES)}, "
          f"dim_partner {len(partners)}, dim_customer {len(customers):,}, dim_subscription {len(subs):,} "
          f"-> data/conformed/  (as-of {as_of}; {manifest['disclosure']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
