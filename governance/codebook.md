# Codebook — grain, status and vocabulary of every table

*Stage 1 artifact. Owner: Aaron Robbins. As-of 2026-06-30. Everything here
is synthetic, generated from seed 20260911; see
`governance/generator_assumptions.md`. Row counts are in
`data/conformed/manifest.json` and are not restated here.*

Every table states its **grain** and whether it is **observed** (it came from
the register's source or the generator's population), **derived** (the engine
produced it under `governance/entitlement-rules.md`), or both, flagged per
row. The rules document is normative; this describes the shape.

---

## Dimensions

### `dim_date` — derived. Grain: one row per day, 2024-07-01 to 2026-06-30

| Column | Meaning |
|---|---|
| `date_key` | ISO date |
| `year`, `month`, `day_of_month` | Calendar parts |
| `month_key` | `YYYY-MM`; the key every subscription-month uses |
| `days_in_month` | Actual days; the proration denominator (rule 6.2) |
| `is_month_start`, `is_month_end` | Booleans |

### `dim_term_type` — observed. Grain: one row per term type

| `term_type` | `months_per_term` | `rate_cents_per_licence_month` |
|---|---:|---:|
| `annual` | 12 | 1,000 |
| `monthly` | 1 | 1,200 |

The two rates are rule 0. Each derivation path restates them with a comment;
this table is where a reader looks them up, not where either path reads them.

### `dim_partner` — observed. Grain: one row per partner, plus `DIRECT`

| Column | Meaning |
|---|---|
| `partner_id` | `P1`, `P2`, `P3`, `DIRECT` |
| `partner_name` | Invented. Nothing here resembles a real reseller, carrier or company |
| `channel` | `partner` or `direct` |
| `designed_share_of_partner_customers` | The generator's parameter; blank for `DIRECT` |

### `dim_customer` — observed. Grain: one row per customer

| Column | Meaning |
|---|---|
| `customer_key` | Surrogate, `C` + 5 digits. **The** key. Does not encode the partner |
| `partner_id` | Foreign key to `dim_partner` |
| `customer_ref` | **Partner-scoped. Not unique across partners** — see hazards |
| `channel` | `partner` or `direct` |

### `dim_subscription` — observed. Grain: one row per subscription, register attributes as of the as-of date

| Column | Meaning |
|---|---|
| `subscription_key` | Surrogate, `S` + 5 digits; **persists across renewals** — see hazards |
| `customer_key`, `partner_id`, `channel` | Denormalised from `dim_customer` at build time |
| `term_type` | `annual` or `monthly`; fixed for the life of the subscription |
| `opened_date` | The accepted `NEW`'s `received_date` |
| `register_quantity` | **What the register shows**: the last accepted `requested_quantity`; 0 after a `CANCEL`. M-02 at as-of |
| `register_status` | `active` or `cancelled` |
| `register_status_date` | The `CANCEL`'s date if cancelled, else `opened_date` |
| `register_as_of_date` | The as-of date, stamped on every row |

**This is what a naive query reads.** It is published so the naive answer is
visible beside the derived one. `src/validate.py` checks that it equals what
the accepted events imply.

## Facts

### `fact_order_event` — observed. Grain: one row per transaction received

The register's source and the only event input to both derivation paths.
Rejected transactions are kept (D8).

| Column | Meaning |
|---|---|
| `transaction_id` | Monotonic integer; the tie-break within a day (rule 2.1) |
| `received_date` | ISO date |
| `subscription_key` | May name a key that was never issued (`UNKNOWN_SUBSCRIPTION`) |
| `transaction_type` | `NEW`, `ADD`, `REDUCE`, `CANCEL` — the sender's label (rule 1.1) |
| `requested_quantity` | **Absolute**, never a delta. 0 on every `CANCEL` |
| `term_type` | On `NEW` only |
| `source` | `contract_record` (Direct) or `partner_api_order` (Partner) — D2's difference in source |
| `accepted` | Engine output under rule 1.2 |
| `rejection_reason` | One of the vocabulary below, or blank |

**Rejection vocabulary** (rule 1.2, precedence in this order):
`UNKNOWN_SUBSCRIPTION`, `DUPLICATE_NEW`, `ADD_AFTER_CANCEL`,
`REDUCE_AFTER_CANCEL`, `DUPLICATE_CANCEL`, `REDUCE_TO_ZERO`, `NOOP_QUANTITY`.
`DUPLICATE_CANCEL` was added by the build session; the brief's six could not
classify a second `CANCEL`.

### `fact_entitlement_term` — observed and derived, flagged per row. Grain: one row per subscription × term instance

| Column | Meaning |
|---|---|
| `subscription_key`, `term_seq` | The key. `term_seq` 1 is the observed term; 2 and up are manufactured |
| `term_start`, `term_end` | Rules 3.1–3.4; `term_end` may be after the as-of date |
| `opening_quantity` | Effective quantity on `term_start` before that day's orders (rule 4.4) |
| `closing_quantity` | Effective quantity on the earlier of `term_end` and as-of |
| `pending_reduction_target` | What the next term opens at if below `closing_quantity`, else blank. On a cancelled term it is recorded and never lands |
| `cancel_pending` | An accepted `CANCEL` was received in this term; no term follows |
| `derived` | `true` iff no `NEW` opened it (rule 5.1) |
| `opened_by_transaction_id` | The `NEW`'s id on term 1; blank on every derived term |

### `fact_billable_month` — derived. Grain: one row per subscription × calendar month with ≥ 1 effective day

No row exists for a month with no effective day (rule 6.1, PRINCIPLES rule 3).

| Column | Meaning |
|---|---|
| `subscription_key`, `month_key` | The key |
| `customer_key`, `partner_id`, `channel`, `term_type` | Denormalised for the roll-up and the exhibits |
| `days_in_month` | Actual days |
| `effective_days` | Days in the month the subscription was effective |
| `licence_days` | Σ effective quantity over those days — the exact quantity (rule 6.2) |
| `licence_months` | `licence_days / days_in_month`, six decimals, for reading; paths compare `licence_days` |
| `rate_cents` | From the term type |
| `billable_amount_cents` | Rule 6.3, rounded half-up once |
| `register_quantity_at_month_end` | M-02 on the month's last day |
| `effective_quantity_at_month_end` | M-01 on the month's last day; 0 if the subscription had ended |
| `gap_quantity`, `gap_amount_cents` | M-03; ≥ 0 by construction |
| `derived` | `true` iff no effective day in the month lies in term 1 (rule 5.2) |
| `straddles_boundary` | `true` iff the month's effective days span more than one term (rule 5.3) |
| `is_partial_month` | Opened, ended or changed quantity inside the month (rule 6.5) |

### `fact_deferral` — derived. Grain: one row per deferred order

M-05's lineage. One row per accepted `CANCEL` and per accepted order whose
effect was a pending reduction (rule 8.1).

| Column | Meaning |
|---|---|
| `transaction_id` | The order |
| `subscription_key`, `term_type`, `transaction_type`, `received_date`, `term_seq` | Where it landed in the state |
| `landing_date` | The day after the term's end |
| `days_pending` | `landing_date − received_date` |
| `landed_by_as_of` | The landing date is on or before the as-of date |
| `took_effect_as_scheduled` | Landed, and (for a reduction) no later accepted order in the same term |

### `fact_invoice_line` — derived roll-up. Grain: partner × month (Partner) or customer × month (Direct)

| Column | Meaning |
|---|---|
| `invoice_line_key` | `month|partner|customer` |
| `month_key`, `channel`, `partner_id`, `customer_key` | `partner_id` is `DIRECT` and `customer_key` is set on Direct lines; `customer_key` is blank on Partner lines |
| `invoice_amount_cents` | Σ constituent `billable_amount_cents`, by the rows' own channel attributes |
| `constituent_count`, `constituent_sum_cents` | Re-derived through `dim_customer` |
| `tie_out_difference_cents` | Must be 0; published anyway (M-08) |

### `measures_manifest.json` — derived. Every M- value at as-of

Written by Path 1; every leaf is re-derived and compared by Path 2. Carries
the disclosure and the seed.

---

## Natural-key hazards, documented rather than merely avoided

1. **`customer_ref` is partner-scoped.** Every partner and the Direct channel
   issue `00001` upward, so a `customer_ref` alone identifies nothing. Join on
   `customer_key`, always. The generator reports how many refs collide.
2. **`subscription_key` persists across renewals.** A term instance needs its
   own key, `(subscription_key, term_seq)`. Anything grouped by
   `subscription_key` alone mixes observed and manufactured terms.
3. **An order on a boundary day belongs to the new term** (rule 2.2). A join
   of orders to terms on `received_date BETWEEN term_start AND term_end` gets
   this right; a join that treats `term_end` as exclusive does not.
4. **A monthly term opened on the 29th–31st drifts** (rule 3.4). After the
   first short month it opens on the 28th, 29th or 30th and never returns to
   its original day. Do not reconstruct term boundaries from `opened_date`
   and a month count; read `fact_entitlement_term`.
5. **`register_quantity` is 0 after a `CANCEL`** while the subscription is still
   billable to term end. That is the gap, by design; it is not a missing value.

## Vocabularies

| Field | Values |
|---|---|
| `transaction_type` | `NEW`, `ADD`, `REDUCE`, `CANCEL` |
| `rejection_reason` | `UNKNOWN_SUBSCRIPTION`, `DUPLICATE_NEW`, `ADD_AFTER_CANCEL`, `REDUCE_AFTER_CANCEL`, `DUPLICATE_CANCEL`, `REDUCE_TO_ZERO`, `NOOP_QUANTITY` |
| `term_type` | `annual`, `monthly` |
| `channel` | `partner`, `direct` |
| `source` | `partner_api_order`, `contract_record` |
| `register_status` | `active`, `cancelled` |
| Booleans in CSV | `true`, `false` |
| Money | Integer cents, everywhere; dollars appear only in rendered prose |
