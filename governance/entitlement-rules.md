# Entitlement rules — the normative statement

*Owner: Aaron Robbins. Written 2026-09-11, before any engine code. This is the
document both derivation paths are written from. `src/build_entitlement.py`
(Path 1) and `src/validate_measures.py` (Path 2) each implement every rule
below from this text and from nothing else. If the two paths disagree and each
is a faithful reading of this document, the defect is here: fix this document,
then both paths.*

Everything in this repository is synthetic. These rules describe a model of a
problem shape. They are not a description of any real company's systems.

---

## 0 · Constants

| Constant | Value | Where it may appear |
|---|---|---|
| Annual term rate | **$10.00 per licence per month**, i.e. 1,000 cents | Restated in each path, with a comment saying it is restated deliberately |
| Monthly term rate | **$12.00 per licence per month**, i.e. 1,200 cents | Same |
| As-of date | **2026-06-30** | `governance/freeze.toml`; passed to each path as a parameter |
| Window | 2024-07-01 to 2026-06-30 | The generator's parameter block |

Prices are fixed for the whole window. There is no price list to effective-date.

## 1 · Vocabulary

### 1.1 Transaction types

Every transaction carries a `transaction_type`, an absolute `requested_quantity`
(never a delta), a `received_date`, a `subscription_key`, and a monotonic
integer `transaction_id`. A `NEW` also carries a `term_type`.

| Type | What the sender is saying |
|---|---|
| `NEW` | Open this subscription at `requested_quantity` on `term_type`. |
| `ADD` | I now want `requested_quantity`, which is more than I last asked for. |
| `REDUCE` | I now want `requested_quantity`, which is less than I last asked for. |
| `CANCEL` | Do not renew. `requested_quantity` is **0** on a `CANCEL` row, always. |

**The type label on an `ADD` or a `REDUCE` is the sender's declaration. It
does not alter the effect** (rule 4.2). The effect of an accepted quantity
order is determined by comparing its `requested_quantity` to the subscription's
current *effective* quantity, and the label is recorded as sent. The generator
always labels by direction against the register, so in the synthetic data every
`ADD` is above the register and every `REDUCE` is below it; the rule is stated
so that it is total, not because the data exercises the mislabelled case.

### 1.2 Rejection reasons

A rejected transaction is kept in `fact_order_event` with `accepted = false`
and exactly one `rejection_reason`. **A rejected transaction changes no
state** — not the register, not the effective quantity, not any pending order.

| Reason | Fires when |
|---|---|
| `UNKNOWN_SUBSCRIPTION` | A non-`NEW` transaction names a key for which no accepted `NEW` precedes it in processing order. |
| `DUPLICATE_NEW` | A `NEW` names a key for which an accepted `NEW` already precedes it. A key is never re-opened; a returning customer gets a new key. |
| `ADD_AFTER_CANCEL` | An `ADD` on a subscription with an accepted `CANCEL` preceding it — whether or not the cancelled term has ended yet. |
| `REDUCE_AFTER_CANCEL` | A `REDUCE`, likewise. |
| `DUPLICATE_CANCEL` | A `CANCEL` on a subscription with an accepted `CANCEL` preceding it. |
| `REDUCE_TO_ZERO` | An `ADD` or `REDUCE` with `requested_quantity = 0`. Use `CANCEL`. |
| `NOOP_QUANTITY` | An `ADD` or `REDUCE` whose `requested_quantity` equals the current register quantity (rule 4.5). |

**Precedence, when more than one could fire:** `UNKNOWN_SUBSCRIPTION`, then
`DUPLICATE_NEW`, then the three after-cancel reasons, then `REDUCE_TO_ZERO`,
then `NOOP_QUANTITY`. Both paths apply the checks in this order and stop at
the first that fires.

*The brief's vocabulary had six reasons. `DUPLICATE_CANCEL` is added here
because the six could not classify a second `CANCEL`, and without it the rule
is not total. Recorded as a correction to the brief.*

### 1.3 Input contract — what raises, as distinct from what rejects

A rejection is a business outcome and is a row. The following are malformed
input, and both paths **raise** rather than classify: an unknown
`transaction_type`; a negative `requested_quantity`; a `NEW` with
`requested_quantity < 1`, or without a `term_type` in {`annual`, `monthly`}; a
`CANCEL` with `requested_quantity ≠ 0`; a `received_date` after the as-of date;
two rows sharing a `transaction_id`. The generator emits none of these.

## 2 · Processing order

**2.1** Transactions are processed in ascending `(received_date,
transaction_id)` order. Never by row order in any file.

**2.2 Within one calendar day, the term boundary comes first.** If a
subscription's current term ends on the day before `d`, the renewal (or the
end of the subscription, if a cancellation is pending) is processed before any
transaction received on `d`. Consequently **a transaction received on a
boundary day belongs to the new term** (worked example G10).

**2.3** Transactions received after the as-of date are outside the model and
are rejected by the input contract (1.3). Every rule below is evaluated as of
the as-of date: nothing after it is derived, and no term that would open after
it is emitted.

## 3 · Terms

**3.1 Opening.** An accepted `NEW` opens term 1 on its `received_date`. Term 1
is *observed*: `derived = false`, `opened_by_transaction_id` = the `NEW`'s id.

**3.2 Annual boundary.** `term_end = term_start + 1 year − 1 day`, where "+ 1
year" keeps the month and day and clamps the day to the last day of that month
if it does not exist in the target year (a term opened 2024-02-29 ends
2025-02-27 and the next opens 2025-02-28). A term opened 2025-01-16 ends
2026-01-15 (G12). No opening date in the generation window is a 29 February,
so the clamp is stated for totality and is not exercised by the data.

**3.3 Monthly boundary.** `term_end` is the day before the same day-of-month in
the following month, with that day clamped to the following month's last day
if it does not exist there. A term opened 2025-01-31 ends 2025-02-27 and the
next term opens **2025-02-28** (G14). A term opened on the 1st ends on the last
day of the same month.

**3.4 Each term is computed from its own start; the original anchor is not
remembered.** After the clamp in 3.3, the next term opens 2025-02-28 and ends
2025-03-27, and every later term opens on the 28th. Equivalently, term *k*'s
start day-of-month is the smaller of the opening day and the length of every
month the chain has passed through. Both readings are the same rule; the two
paths may use either.

**3.5 Renewal.** At a term end with no pending cancellation, a new term
instance is **manufactured**: `term_start` = prior `term_end + 1 day`, same
term type, `term_seq` incremented, `opening_quantity` per rule 4.4. It is
*derived*: `derived = true`, `opened_by_transaction_id` null. No transaction
marks a renewal, ever.

**3.6 End.** At a term end with a pending cancellation, the subscription ends.
Its last effective day is that `term_end`. No further term is manufactured.

**3.7 Last term emitted.** Terms are emitted only while `term_start ≤ as-of`.
A term whose `term_end` is after the as-of date is emitted with its full
`term_end`; its `closing_quantity`, `pending_reduction_target` and
`cancel_pending` are recorded as they stand on the as-of date.

**3.8 Term attributes.** `opening_quantity` is the effective quantity on
`term_start`, before any transaction received that day. `closing_quantity` is
the effective quantity on the earlier of `term_end` and the as-of date.
`pending_reduction_target` is the quantity the next term will open at if it
differs from `closing_quantity`, else null. `cancel_pending` is true if an
accepted `CANCEL` was received in this term.

## 4 · Quantities

Two quantities exist per subscription at every instant, and the module's
subject is the difference between them.

- **Register quantity** — what the customer last asked for. Changes on the
  `received_date` of every accepted `NEW`, `ADD`, `REDUCE` or `CANCEL`, to that
  transaction's `requested_quantity` (so a `CANCEL` sets it to 0).
- **Effective quantity** — what they are billable for. Changes only per rules
  4.1–4.4.

**4.1 `NEW`.** Effective quantity = `requested_quantity` from `received_date`.

**4.2 Accepted `ADD` or `REDUCE`, with requested quantity *q* and current
effective quantity *E*:**

| Case | Effect on effective quantity | Effect on any pending reduction |
|---|---|---|
| *q* > *E* | Rises to *q* from `received_date`. Term boundary unchanged. | **Voided** — the latest order wins (G7). |
| *q* < *E* | Unchanged until the next term boundary, where the term opens at *q*. | **Replaced** by *q* — the latest order wins (G9). |
| *q* = *E* | Unchanged. | **Voided.** (This is a customer restoring a quantity they had asked to reduce; it is accepted because it differs from the register.) |

The register quantity becomes *q* immediately in every accepted case. Because
*q* > *E* is the only case that changes the effective quantity mid-term, the
effective quantity never decreases inside a term. Because the register follows
every accepted order immediately, **the register never exceeds the effective
quantity**, so the gap in rule 6.4 is non-negative by construction.

**4.3 Accepted `CANCEL`.** Register quantity becomes 0 and register status
becomes `cancelled` with `register_status_date = received_date`. The effective
quantity is unchanged; the subscription ends at the current `term_end` (3.6).
Any pending reduction is moot, since no next term opens; it is left recorded
on the term as `pending_reduction_target` and does not take effect.

**4.4 Opening quantity of a manufactured term.** The `requested_quantity` of
the last accepted `NEW`, `ADD` or `REDUCE` received before the new term's
`term_start` (that is, received on or before the prior `term_end`). This single
statement covers all three cases of 4.2: a pending reduction (last order was
below *E*), a voided one (last order was at or above *E*), and no order at all
(the last order is whatever opened the prior term or raised it).

**4.5 `NOOP_QUANTITY`.** Compared against the register quantity, never the
effective quantity. On G1 after the March `ADD` to 20 the register is 20; an
`ADD` to 20 is a no-op and is rejected (G8). A `REDUCE` to 15 when a reduction
to 15 is already pending is likewise rejected.

## 5 · Derived flags

**5.1 Term.** `derived = true` iff no `NEW` opened it (3.5). Term 1 is the only
observed term a subscription ever has.

**5.2 Subscription-month.** `derived = true` iff **no effective day of the
subscription in that month lies in term 1.** A month with days in term 1 and
days in term 2 is not derived (G12b). A month lying wholly across two
manufactured monthly terms is derived.

**5.3 `straddles_boundary`.** True iff the subscription's effective days in
the month belong to **more than one term instance.** A monthly term opened on
the 1st never straddles; an annual term opened 2025-01-16 straddles every
January from 2026 (G12b); an annual term opened on the 1st never straddles
(G10: "full month, no proration").

## 6 · Billing

**6.1 A subscription-month row exists iff the subscription was effective for
at least one day in that calendar month**, on or before the as-of date. A
month with no effective day gets no row — never a zero row (PRINCIPLES rule
3; G5 has no 2025-05 row, G6 no 2026-03 row).

**6.2 Licence-days and licence-months.** For each effective day *t* in the
month, the effective quantity on *t* is *E(t)*. `licence_days = Σ E(t)`, an
integer. `licence_months = licence_days / days_in_month`, kept exact
(published to six decimals; compared between paths as `licence_days`).

**6.3 Amount.** `billable_amount_cents = round_half_up(licence_days ×
rate_cents / days_in_month)`, rounded once, at the subscription-month line. In
integer arithmetic that is `(licence_days × rate_cents × 2 + days_in_month)
div (2 × days_in_month)`. With rates of 1,000 and 1,200 cents and months of
28–31 days an exact half-cent cannot occur, so the tie rule is stated for
completeness and is never the reason two paths differ.

**6.4 Month-end quantities and the gap.** `effective_quantity_at_month_end` is
*E* on the last day of the month, or 0 if the subscription had ended before
it. `register_quantity_at_month_end` is the register quantity on the last day
of the month. `gap_quantity = effective − register` (≥ 0 by 4.2; a negative
value is a validation failure). `gap_amount_cents = gap_quantity ×
rate_cents`.

**6.5 Partial month.** `is_partial_month = true` iff the row's licence-days
differ from `days_in_month × effective_quantity_at_month_end` — the
subscription either opened, ended, or changed quantity inside the month.

## 7 · Invoice roll-up

One `fact_invoice_line` per **partner × month** for the Partner channel, and
per **customer × month** for the Direct channel. `invoice_amount_cents` is the
sum of the constituent subscription-months' `billable_amount_cents`.
`constituent_count` and `constituent_sum_cents` are re-derived by joining each
subscription-month to its line through the customer dimension, and
`tie_out_difference_cents = invoice_amount_cents − constituent_sum_cents` must
be 0 on every line. It is published even when it is zero. Revenue share,
settlement and currency are out of scope.

## 8 · Measure-specific rules

**8.1 Deferral (M-05).** For every accepted `REDUCE` or `CANCEL`, the
*scheduled landing date* is the day after the `term_end` of the term in which
it was received (per 2.2, a boundary-day transaction is in the new term).
`days_pending = landing_date − received_date`. `landed_by_as_of` is true iff
the landing date is on or before the as-of date. `took_effect_as_scheduled`
is true iff `landed_by_as_of` and, for a `REDUCE`, no later accepted `ADD`,
`REDUCE` or `CANCEL` was received in the same term. The distribution is
reported over **all** accepted `REDUCE` and `CANCEL` rows, because the wait the
rule imposes is the exhibit; the count that later changed is reported beside
it.

**8.2 Percentiles.** Nearest-rank: sort ascending, take the value at
1-based position `ceil(p × n)`. Median is *p* = 0.5.

**8.3 Register quantity at a date (M-02).** The `requested_quantity` of the
last accepted `NEW`, `ADD`, `REDUCE` or `CANCEL` with `received_date` on or
before the date.

## 9 · Worked examples — the golden fixture

`tests/golden/golden_events.csv` and `golden_expected.csv` are the executable
form of these rules and were written before any engine code. Rates per §0,
proration per §6, boundaries per §3.

| Case | What it exercises | Rule |
|---|---|---|
| G1 | Prorated add on an annual term: 10×31 + 10×16 over 31 = 15.1613 → $151.61 | 4.2, 6.2, 6.3 |
| G2 | Deferred reduce on annual: eleven months at 20 with the register at 10; derived term opens at 10 | 4.2, 4.4, 5.1 |
| G3 | Deferred reduce on monthly: lands 2025-03-01, 19 days pending | 4.2, 8.1 |
| G4 | Renewal nobody sent: every 2026 row `derived` | 3.5, 5.2 |
| G5 | Cancel, monthly: held to 2025-04-30; no May row | 4.3, 3.6, 6.1 |
| G6 | Cancel, annual: register 0 and gap 8 for the rest of the term | 4.3, 6.4 |
| G7 | Add voids a pending reduce; derived renewal opens at 12 | 4.2, 4.4 |
| G8 | Three rejects: `REDUCE_AFTER_CANCEL`, `REDUCE_TO_ZERO`, `NOOP_QUANTITY` | 1.2, 4.5 |
| G9 | Latest reduce wins: renewal opens at 12 | 4.2, 4.4 |
| G10 | Event on a boundary day: boundary first, then the add; full month | 2.2 |
| G11 | Prorated add on monthly: 10×31 + 5×11 over 31 = 11.7742 → $141.29 | 6.2, 6.3 |
| G12 | Mid-month open: 10×16 over 31 = 5.1613 → $51.61 | 3.1, 6.2 |
| G12b | Straddled boundary: 10×15 + 5×16 over 31 = 7.4194 → $74.19; `straddles_boundary` | 3.2, 5.3 |
| G13 | Add between register and effective: raises the pending target, effective unchanged; then `DUPLICATE_CANCEL` | 4.2 (row 2), 1.2 |
| G14 | Monthly opened 2025-01-31, reduce lands 2025-02-28 under the clamp: Feb 10×27 + 6×1 over 28 = 9.8571 → $118.29 | 3.3, 3.4 |
| G15 | Direct channel: identical arithmetic, customer × month invoice line | 7 |

## 10 · Ambiguities in the brief closed by this document

Listed so the report can carry them. Each is a place where two faithful
implementations of D3–D9 as written could have disagreed.

1. **The rejection vocabulary was not total.** A second `CANCEL` had no
   reason. `DUPLICATE_CANCEL` added (1.2).
2. **An `ADD` or `REDUCE` whose quantity lies between the register and the
   effective quantity was undefined** — D8 defined `ADD` only for *q* > *E* and
   `REDUCE` only for *q* < *E*. Closed by 4.2: the effect follows the quantity
   against the effective; the label is recorded as sent; a customer raising a
   pending reduction target is the natural case (G13).
3. **`derived` on a month lying across two manufactured terms**, which D8's
   "wholly inside a derived term" read as false for every monthly-term month
   not opened on the 1st. Closed by 5.2.
4. **`straddles_boundary`** as "a boundary falls inside the month" would flag
   a term opening on the 1st. Closed by 5.3.
5. **M-05's "date it took effect"** for a reduction later voided, superseded,
   or still pending at as-of. Closed by 8.1: the scheduled landing date, over
   all accepted rows, with the changed-count beside it.
6. **What a `CANCEL` row carries as `requested_quantity`**, and what the
   register shows after one. Closed by 1.1 and 4.3: 0, so M-02's "`CANCEL`
   sets it to 0" and the check "register equals the last accepted requested
   quantity" are the same statement.
7. **Term attributes for the term open at the as-of date.** Closed by 3.7–3.8.
8. **Leap-day annual boundaries and whether the chain remembers its anchor.**
   Closed by 3.2 and 3.4; not exercised by the window.
9. **Which percentile definition.** Closed by 8.2.
10. **Whether M-05 counts a `CANCEL`'s landing as `term_end` or the day after.**
    Closed by 8.1 as the day after, so G3's "19 days" and a cancel's wait are
    measured the same way.
