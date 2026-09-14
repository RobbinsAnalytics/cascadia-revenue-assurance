# Certified measure register

*Stage 1 artifact. Owner of every measure below: **Aaron Robbins**. As-of
**2026-06-30**. Every figure is generated from seed 20260911 and is synthetic;
see `governance/generator_assumptions.md`. No figure here is a claim about any
real book of business.*

Every measure carries a written definition, a named owner, lineage to source
fields, and a stated limit. **A figure that appears in any output and is not
defined here is not certified and must not be published.** The values
themselves live in `data/conformed/measures_manifest.json`, written by the
build; this document defines them and does not restate them.

**Independent validation.** `src/validate_measures.py` re-derives every
published cell down a separately written path — a set-based SQL derivation in
DuckDB over a generated calendar, where the builder is a record-at-a-time
state machine in Python — and compares subscription-month by
subscription-month, term by term, invoice line by invoice line, and every M-
value below. **Nothing is published unless that script exits zero.** A measure
that only agrees with itself has not been validated. The two paths share no
code and were both written from `governance/entitlement-rules.md` (D12).

**There is no accuracy, error-rate or correctness-percent measure in this
register, and none may be added (D13).** The module's only correctness claim
is that the independent re-derivation agrees and that the golden fixture
(`tests/golden/`, written before any engine code) passes on both paths. That
is a statement about method.

---

## The population, and the two numbers the module is about

| | |
|---|---|
| **Customers** | 4,000 — 3,800 through three synthetic partners, 200 Direct |
| **Subscriptions** | 4,397 — about 60% annual, 40% monthly; a tenth of customers hold two |
| **Transactions** | 7,493 received, rejected ones included |
| **Window** | 2024-07-01 to 2026-06-30; every figure stated at 2026-06-30 |

**Register quantity** is what the customer last asked for. **Effective
quantity** is what they are billable for. The rules that separate them are in
`governance/entitlement-rules.md`: an add lands at once, a reduction lands at
the next term boundary, a cancellation rides out the term. Every measure below
is a view of that separation.

**"Effective", never "actual".** Nothing in this module is observed billing.
Effective quantity is derived from the event stream under stated rules; the
`derived` flag says which rows rest on a renewal nobody sent.

---

## M-01 · Effective billable quantity at a date

> **Definition.** Licences effective on a given day for a subscription, or the
> sum across any dimension. Published at the as-of date as the sum over every
> subscription effective that day.

| | |
|---|---|
| **Owner** | Aaron Robbins |
| **Output** | `fact_billable_month.effective_quantity_at_month_end`; `measures_manifest.json` → `M-01` |
| **Lineage** | `fact_order_event` (accepted rows) → `fact_entitlement_term` → daily segments → month end |
| **Population** | Every subscription with at least one effective day in the month |

**Limits.**
- Day grain only. Same-day ordering inside a day is rule 2.2 (boundary first,
  then `transaction_id`), and nothing finer exists.
- At a month end, a subscription that ended earlier in the month contributes 0
  here and still has a row (its licence-days are in M-04).
- **Stage 2 lineage.** The page's Exhibit 3 plots this measure at each of the
  24 month ends in the window: the sum of `effective_quantity_at_month_end`
  over `fact_billable_month` per `month_key`. Those 24 values are written by
  the build to `data/conformed/measures_stage2.json` under
  `M-01_M-02_monthly_series`, and re-derived by Path 2. They are M-01 at 24
  dates, not a new measure.

## M-02 · Register (contracted) quantity at a date

> **Definition.** What the register shows — the naive answer. The
> `requested_quantity` of the last accepted transaction on or before the date;
> a `CANCEL` sets it to 0.

| | |
|---|---|
| **Owner** | Aaron Robbins |
| **Output** | `fact_billable_month.register_quantity_at_month_end`; `dim_subscription.register_quantity` (at as-of); `measures_manifest.json` → `M-02` |
| **Lineage** | `fact_order_event` where `accepted`, last by `(received_date, transaction_id)` |
| **Population** | As M-01 |

**Limits.**
- **This is the number a query against `dim_subscription` returns, and it is
  wrong about the invoice every month a deferral is outstanding.** That is the
  module's subject, not a defect in the measure.
- Rejected transactions never move it (rule 1.2).
- **Stage 2 lineage.** Exhibit 3 plots this measure beside M-01 at the same
  24 month ends: the sum of `register_quantity_at_month_end` per `month_key`,
  in the same `M-01_M-02_monthly_series` block. M-02 at 24 dates, not a new
  measure.

## M-03 · Entitlement gap

> **Definition.** M-01 minus M-02, in licences and in cents, per
> subscription-month at month end, and summed over any dimension. In dollars
> it is the gap in licences times the term type's monthly rate. This is the
> **deferred-downgrade backlog**, and it includes cancellations riding out
> their term.

| | |
|---|---|
| **Owner** | Aaron Robbins |
| **Output** | `fact_billable_month.gap_quantity`, `.gap_amount_cents`; `measures_manifest.json` → `M-03` |
| **Lineage** | M-01 and M-02 on the same row |
| **Population** | As M-01 |

**Limits.**
- **≥ 0 by construction** (rule 4.2: the register never exceeds the effective
  quantity). A negative value is a validation failure, not a finding, and
  `src/validate.py` exits non-zero on one.
- The dollar figure is the month-end gap at the monthly rate. It is a
  run-rate exposure at that instant, not a sum of over-billing to date; the
  sum over all months is published separately as `gap_cents_all_months`.
- **The backlog share of a month's billable** divides the as-of month's gap
  dollars by that month's `billable_amount_cents`. A subscription that opened
  late in the month contributes a prorated denominator and a full-quantity
  numerator; the ratio is a snapshot, not a rate of revenue at risk.

### M-03a · Entitlement gap at as-of, by term type and cause

> **Definition.** M-03's dollars and licences at the as-of month end, split by
> term type and by **cause**: a subscription-month is `cancel_riding_out` when
> the subscription's term instance containing the as-of date carries
> `cancel_pending = true`, and `deferred_reduction` otherwise. Four cells,
> each with cents, subscription-months and licences. The four cents values
> sum to M-03 `cents_at_as_of` exactly, and the build asserts it.

| | |
|---|---|
| **Owner** | Aaron Robbins |
| **Output** | `data/conformed/measures_stage2.json` → `M-03a_gap_at_as_of_by_term_type_and_cause` |
| **Lineage** | `fact_billable_month` (as-of month, `gap_amount_cents > 0`) joined to `fact_entitlement_term` on the term whose `term_start ≤ as-of ≤ term_end` |
| **Population** | Every subscription-month in the as-of month with a positive gap |

**Limits.**
- **Cause is a property of the subscription's current term, not of each
  licence in the gap.** A subscription with a pending reduction *and* a
  pending cancellation counts wholly as `cancel_riding_out`, because the
  cancellation is what decides that no next term opens (rule 4.3). The
  reduction target on such a term is recorded and never lands.
- A month-end snapshot of one month. It says where the June 2026 backlog
  sits; it is not a rate over the window.
- **Read the counts beside the dollars.** In this snapshot cancellations are
  the larger dollars and deferred reductions the larger count; a chart that
  shows only one of the two invites the wrong sentence.

## M-04 · Prorated period revenue

> **Definition.** `billable_amount_cents` summed over any dimension, with the
> share attributable to partial months reported alongside. A subscription-month
> is *partial* when its licence-days differ from the month length times its
> month-end quantity — it opened, ended or changed quantity inside the month.

| | |
|---|---|
| **Owner** | Aaron Robbins |
| **Output** | `fact_billable_month.billable_amount_cents`, `.is_partial_month`; `measures_manifest.json` → `M-04` |
| **Lineage** | `licence_days` (rule 6.2) × `dim_term_type.rate_cents_per_licence_month` ÷ `days_in_month`, rounded half-up once (rule 6.3) |
| **Population** | Every subscription-month with ≥ 1 effective day |

**Limits.**
- Actual days in the month, never 30/360 (D5). A one-constant change
  elsewhere; here, a different module.
- Rounded once, at the subscription-month line. Invoices (M-08) sum rounded
  lines, so they tie by construction; the tie-out proves the join, not the
  rounding.
- **Not revenue recognised, not cash, not settled.** Revenue share, settlement
  and currency are out of scope (D10).

## M-05 · Deferral exposure by term type

> **Definition.** For every deferred order — every accepted `CANCEL`, and every
> accepted order whose effect was a pending reduction — the days from
> `received_date` to the boundary at which it was scheduled to take effect.
> Reported by term type as count, median, 90th percentile and maximum
> (nearest-rank, rule 8.2), with the count that had landed by the as-of date,
> the count that took effect as scheduled, and the backlog dollars (M-03 at
> as-of) each term type carries.

| | |
|---|---|
| **Owner** | Aaron Robbins |
| **Output** | `fact_deferral.csv`; `measures_manifest.json` → `M-05` |
| **Lineage** | `fact_order_event` (accepted) placed in its term via `fact_entitlement_term` → `landing_date = term_end + 1` |
| **Population** | All deferred orders, including those later voided, superseded, or still pending at as-of |

**This is the module's clearest exhibit: the same reduction waits up to about
30 days on a monthly term and up to about 364 on an annual one.**

**Limits.**
- The wait is the *scheduled* wait. A reduction later voided by an add, or
  replaced by a later reduction, is counted at the wait the rule imposed on it
  when it was received; `took_effect_as_scheduled` says which ones actually
  landed unchanged. The rule's asymmetry is the exhibit; the customer changing
  their mind again is a separate fact and is reported beside it.
- A `CANCEL` lands the day after its term ends. A `REDUCE` lands on the day
  the next term opens. Those are the same date (rule 8.1), so the two kinds
  are measured alike.
- Nearest-rank percentiles on integer days. With hundreds of rows per term
  type the choice of percentile definition moves the figure by at most a day.

### M-05a · Deferral exposure by term type and transaction type

> **Definition.** M-05's `days_pending` distribution cut a second way, by
> the deferred order's `transaction_type` as sent — `REDUCE`, `CANCEL`, and
> `ADD` — with count, nearest-rank median and 90th percentile, minimum and
> maximum per cell; plus, per term type, a histogram of `days_pending` in
> 30-day bins from 0 to 360 (a bin labelled 300 holds 300 ≤ days < 330).

| | |
|---|---|
| **Owner** | Aaron Robbins |
| **Output** | `data/conformed/measures_stage2.json` → `M-05a_deferral_by_term_type_and_transaction_type`, `M-05a_histogram_30_day_bins` |
| **Lineage** | `fact_deferral` (`term_type`, `transaction_type`, `days_pending`) |
| **Population** | All deferred orders, as M-05 |

**Limits.**
- **The `ADD` rows are real deferrals.** An accepted order labelled `ADD`
  whose quantity lay between the register and the effective quantity raised
  a pending reduction target rather than adding licences (rule 4.2, second
  row); it waits for the boundary like any reduction. The label is the
  sender's; the effect is what M-05 measures.
- Nearest-rank percentiles (rule 8.2); a `median_low` would differ by at
  most one day on even counts and is not what is published.
- The histogram's right tail is partly the window's edge (see M-05). The
  bins are published so the shape can be drawn without re-deriving it.

## M-06 · Derived share

> **Definition.** The share of `fact_billable_month` rows, and of
> `billable_amount_cents`, whose every effective day lies in a manufactured
> term — a renewal no transaction marked. Also the count of derived terms
> against all terms.

| | |
|---|---|
| **Owner** | Aaron Robbins |
| **Output** | `fact_billable_month.derived`; `fact_entitlement_term.derived`; `measures_manifest.json` → `M-06` |
| **Lineage** | Rule 3.5 (manufacture) and rule 5.2 (month flag) |
| **Population** | Every subscription-month; every term instance |

**This is "the renewal nobody sent" made countable.**

**Limits.**
- **Derived is not the same as guessed.** Every derived row follows from a
  written rule applied to an observed absence, and is flagged so it can be
  excluded (D6). It is not a filled gap in the sense PRINCIPLES rule 3 forbids.
- Monthly terms dominate this share by construction: every month after the
  first is a manufactured term. Read the figure by term type before reading it
  in total.
- A month with days in the observed first term and days in the first
  manufactured term is *not* derived (rule 5.2) and is flagged
  `straddles_boundary` instead.

### M-06a · Derived share by term type

> **Definition.** M-06's row share split by term type: for each of `annual`
> and `monthly`, the count of `fact_billable_month` rows, the count with
> `derived = true`, and the share.

| | |
|---|---|
| **Owner** | Aaron Robbins |
| **Output** | `data/conformed/measures_stage2.json` → `M-06a_derived_share_by_term_type` |
| **Lineage** | `fact_billable_month.derived`, `.term_type` |
| **Population** | Every subscription-month |

**Limits.**
- **The blended M-06 figure hides two different books.** Every monthly-term
  month after the first is a manufactured term by construction, so the
  monthly share is high by design; the annual share is the one that says how
  much of the book has renewed inside the window. Read them separately.
- Row share, not dollar share; the dollar split is in M-06 unsplit and is
  not restated here.

## M-07 · Rejected-transaction rate

> **Definition.** Rejected transactions divided by transactions received, in
> total and by `rejection_reason`.

| | |
|---|---|
| **Owner** | Aaron Robbins |
| **Output** | `fact_order_event.accepted`, `.rejection_reason`; `measures_manifest.json` → `M-07` |
| **Lineage** | Rule 1.2 applied by the engine to every received row |
| **Population** | Every transaction received, `NEW` included |

**Limits.**
- **The denominator includes every `NEW`.** The generator's refusal rate is
  set per active subscription-*month* (about 0.5%), and a subscription-month
  produces a transaction only about 6.5% of the time, so the rate of refusals
  among *transactions* is several times higher than 0.5%. The brief's expected
  band for this figure did not make that conversion; see the Stage 1 report.
- `src/validate.py` checks that the engine refused exactly the rows the
  generator intended to be refused, by reason. That is a consistency gate
  between two parts of one build, not a measure, and it is not published as a
  rate.
- This is a rate of *refused orders*, a fact about the synthetic senders. It
  says nothing about the engine.

## M-08 · Invoice tie-out

> **Definition.** The count of invoice lines and the count with
> `tie_out_difference_cents ≠ 0`, where each line's `invoice_amount_cents` is
> summed from its subscription-months' own channel attributes and its
> `constituent_sum_cents` is re-derived by joining each subscription-month to
> its line through `dim_customer`.

| | |
|---|---|
| **Owner** | Aaron Robbins |
| **Output** | `fact_invoice_line.csv`; `governance/reconciliation.md`; `measures_manifest.json` → `M-08` |
| **Lineage** | `fact_billable_month` → `dim_subscription` (amount path) and → `dim_customer` (constituent path), rule 7 |
| **Population** | Every partner × month and every Direct customer × month with a billable subscription-month |

**Must be zero. Published anyway** (PRINCIPLES rule 9): the value is the
discipline of checking, and `governance/reconciliation.md` lists every line
with its difference, zeros included.

**Limits.**
- The tie-out proves the join, not the rounding — by D5, invoices sum already
  rounded lines.
- Partner lines are in aggregate per partner; what the partner then does with
  its own customers is out of scope (D10).

---

## No M- for accuracy or error rate

See D13. An "accuracy %" would imply a comparison against some other
implementation taken as ground truth. This module has no ground truth other
than its own rules, and the only correctness statement it makes is about
method: two independently written paths agree on every cell, and a
hand-specified fixture written before either passes on both.

## Measures deliberately not certified

**Revenue per partner net of revenue share.** No share, settlement or currency
exists in the model (D10).

**Anything from `dim_subscription.register_quantity` presented as billing.**
That column is M-02 at as-of and is published so that the naive query's
answer is visible beside the derived one, not so that it can be used as one.

**Any figure at a grain finer than a day.** Rule 2.2 orders a day; nothing
orders within it except `transaction_id`, which is a sequence and not a time.
