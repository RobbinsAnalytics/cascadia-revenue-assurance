# Decision record — Cascadia Revenue Assurance

*Owner: Aaron Robbins. Opened 2026-09-11, Stage 1 (data layer).*

Each decision below is a fact about this synthetic business, with its reason
and its counterfactual. **A decision here is never a claim about how any real
company operates.** A decision that never becomes an instruction is not
adopted, so each names the file or mechanism that carries it.

---

## D1 · The register records orders, not effective state

`fact_order_event` is the register: one row per transaction received, accepted
or not. The module's subject is the gap between what that register implies and
`fact_billable_month`.

*Counterfactual:* if the register tracked effective state there would be no
module.

**Carried by:** `governance/codebook.md` (grain and observed/derived marks);
`src/build_entitlement.py`.

## D2 · Two channels, one state machine

Direct and Partner subscriptions obey identical rules. They differ in
**source** (`contract_record` for Direct, `partner_api_order` for Partner, on
every event row) and in **who is invoiced** (Direct: the customer; Partner:
the partner, in aggregate — D10).

*Counterfactual:* channel-specific rules would double the state machine's
surface and add nothing to the thesis.

**Carried by:** `governance/entitlement-rules.md`, which has no channel
branch; `fact_order_event.source`.

## D3 · Term is a dimension with two members, priced differently

Annual: $10.00 per licence per month. Monthly: $12.00 per licence per month.
An annual commitment prices below twelve monthly periods. Prices are fixed for
the whole window.

*Counterfactual:* mid-window price changes are a Stage 3 candidate. They add
a `dim_price_list` effective-dating problem that is real but orthogonal.

**Carried by:** `dim_term_type`; rules §0; each derivation path restates the
two rates with a comment saying so.

## D4 · Billing is monthly, in arrears, by calendar month, at the term type's monthly-equivalent rate

For both term types. An annual subscription is billed one-twelfth per month,
not upfront. Term length therefore governs **when a reduction or cancellation
lands** and **what a licence costs**, and nothing else.

*Counterfactual:* upfront annual billing moves proration into a one-off debit
line and turns the deferred-downgrade backlog into a deferred-revenue question
rather than an invoice line. The invoice-line form is the one the thesis
needs.

**Carried by:** rules §6.

## D5 · Proration is by calendar day, actual days in the month, on licence-days

`licence_months = Σ(quantity × days at that quantity) / days_in_month`, exact;
amount = that times the rate, rounded half-up to cents **once, at the
subscription-month line**. Invoices sum rounded lines, so the roll-up ties by
construction and the tie-out proves the join, not the rounding.

*Counterfactual:* 30/360 proration is common in finance and would be a
one-constant change; actual-day is chosen because the golden fixture is easier
to hand-check.

**Carried by:** rules §6.2–6.3; `tests/golden/golden_expected.csv`.

## D6 · Auto-renewal is the default and no renewal transaction exists

At a term end with no pending cancellation the state machine **manufactures**
a new term instance. Every row in `fact_entitlement_term` and
`fact_billable_month` carries `derived = true` when no source event opened the
term it belongs to.

**This is derivation under a stated rule, flagged. It is not the filling of a
gap that PRINCIPLES rule 3 forbids.** Rule 3 forbids inventing a value where
the source is silent and presenting it as observed. Here the source is not
silent: the *absence* of a cancellation is the signal the rule is defined on,
the rule is written down (rules §3.5), and every row it produces is marked so
a reader can count them (M-06) or exclude them. A filled gap hides that
nothing was observed; a derived row says so on the row.

*Counterfactual:* an explicit renewal event would make the fact fully
observed and remove the module's most interesting claim.

**Carried by:** rules §3.5, §5; the `derived` column on both facts; M-06.

## D7 · Term boundaries

Annual: `term_end = term_start + 1 year − 1 day`. Monthly: `term_end` is the
day before the same day-of-month next month, clamped to month end (opened
2025-01-31 → ends 2025-02-27; the next term opens 2025-02-28). Each term is
computed from its own start; the anchor is not remembered.

*Counterfactual:* remembering the anchor (every term opening on the 31st
where it exists) is what some systems do. It is more state for no gain in the
thesis, and the clamp-and-drift rule is the one that is easy to hand-check.

**Carried by:** rules §3.2–3.4; G14.

## D8 · Event semantics

Four transaction types, all carrying an absolute requested quantity. Rejected
transactions are kept, never dropped, with a reason from a fixed vocabulary.

*Counterfactual:* silently discarding rejects is how a register and an
invoice come to disagree for reasons nobody can reconstruct.

**Carried by:** rules §1, §4.

## D9 · Same-day ordering

Within one calendar day: the term boundary first, then transactions in
`(received_date, transaction_id)` order. Never by row order. `transaction_id`
is monotonic in the generator for exactly this reason.

*Counterfactual:* a tie broken by row order is a tie a parallel engine does
not guarantee. A precedent elsewhere in this estate caught exactly that.

**Carried by:** rules §2; `src/generate.py` assigns ids after sorting by date.

## D10 · Invoice grain and reconciliation

The entitlement fact is at customer-subscription-month grain for every
channel. `fact_invoice_line` is a roll-up: Partner → one line per partner ×
month; Direct → one line per customer × month. `governance/reconciliation.md`
publishes, per line, the constituent sum and the difference, which must be
zero to the cent. **Revenue share, settlement and currency are out of scope**
and no column, note or figure here implies otherwise.

*Counterfactual:* invoicing at subscription grain for every channel would make
the tie-out trivial and remove the join the tie-out exists to prove.

**Carried by:** rules §7; `src/build_entitlement.py`; `src/validate.py`
(tie-out gate).

## D11 · Population and movement

4,000 customers: 3,800 Partner across three synthetic partners at 55/30/15,
200 Direct with larger licence counts. Term mix about 60% annual / 40%
monthly. Window 2024-07-01 to 2026-06-30, openings throughout. Monthly
movement per active subscription about 3% `ADD`, 2% `REDUCE`, 1% `CANCEL`,
0.5% a rejected transaction. As-of 2026-06-30.

These are arbitrary. They are disclosed as the generator's parameter block in
`governance/generator_assumptions.md`, beside the realised mix. **Every output
carries the disclosure that the data is seeded and synthetic. No figure in
this module may be read as a claim about any real book of business.**

*Counterfactual:* a population large enough to look like a real book would
invite exactly the reading this module refuses.

**Carried by:** `src/generate.py` parameter block; `data/raw/manifest.json`;
the `DISCLOSURE` string on every output.

## D12 · The two paths are written to be different, not merely separate

Path 1 (`src/build_entitlement.py`) is a record-at-a-time state machine in
pure Python. Path 2 (`src/validate_measures.py`) is set-based SQL in DuckDB:
a generated calendar, window functions, term boundaries by date arithmetic,
no per-row iteration. They share no helper module and no intermediate table
beyond `fact_order_event` and `dim_*`. Path 2 is written from
`governance/entitlement-rules.md` only.

**Stated plainly:** one session wrote both paths. The independence is by
construction — different method, no shared code, the rules document as the
only common input — not by author. A disagreement between them is still a
finding, because a state machine and a set of window functions do not share a
bug by accident.

*Counterfactual:* two implementations that share a helper share its defects,
and agreeing with yourself is not validation.

**Carried by:** the two files' imports (neither names the other);
`src/test_golden.py` runs both.

## D13 · No accuracy, error-rate or "correctness %" measure exists, and none may be added

The module's correctness claim is that an independent re-derivation agrees
and that the golden fixture passes. That is a statement about method, and it
is the only kind of correctness statement this estate makes.

*Counterfactual:* an "accuracy %" implies a comparison against some other
implementation as ground truth. This module has no ground truth other than
its own rules, and would be lying to present one.

**Carried by:** `governance/metric_register.md` (no such M- exists);
`CLAUDE.md` hard constraint 2.

## D14 · Closures made by the build session, 2026-09-11

Ten places where D3–D9 as briefed could have let the two paths legitimately
disagree were closed in `governance/entitlement-rules.md` §10 before any
engine code was written. The two that change the vocabulary or the
semantics rather than merely sharpen them:

- **`DUPLICATE_CANCEL`** added to the rejection vocabulary, because six reasons
  could not classify a second `CANCEL`.
- **The effect of an accepted quantity order follows its quantity against the
  effective quantity; the type label is recorded as sent** (rules §4.2). The
  alternative — rejecting a label that disagrees with the direction — makes
  acceptance depend recursively on earlier acceptance and cannot be expressed
  without per-row iteration, which would have forced Path 2 to stop being
  set-based. The chosen rule keeps every rejection reason decidable from the
  transaction and the accepted history without recursion.

*Counterfactual:* leaving them open and letting the paths disagree would have
been a defect in the rules, per D12, discovered later at more cost.

**Carried by:** rules §1.2, §4.2, §10; G13 in the golden fixture.

## D15 · Chart 1's two panels take independent scales — an author override of the reading panel

**Decided 2026-09-14 by Aaron, on his direct read of the rendering.**

The Stage 2 page's first chart shows the deferral distribution for monthly and
annual terms as two panels. The reading panel (finding #11, two seats) asked
that the panels keep one shared vertical scale, per VIZ-PRINCIPLES Rule 6.2,
and that bar labels be added so the squashed annual bars could be read. Aaron
read the same render and decided the other way, verbatim: *"These charts
don't need the same axis. It is a bunch of dead space. 1st chart the x axis has
11 empty values. 2nd chart never goes above 200, so everything after that is
dead space."*

**So each panel takes its own vertical scale and is trimmed to its populated
bins.** The monthly panel has non-zero counts in 2 of 13 bins and a tallest
bar of 580; the annual panel spreads across all 13 with a tallest bar of 116.
On one scale the annual panel, which carries the thesis, reached a fifth of
its height. The cost is stated: the two panels are no longer comparable by
eye, and the subtitle says so ("each panel is drawn on its own scale").

**This is an override of a panel finding, recorded as one.** The panel was
not wrong to cite Rule 6.2; the author judged the dead-space cost higher than
the cross-panel comparability benefit for two ranges that differ five-fold.
Recorded here so it reads as a decision rather than an oversight.

*Counterfactual:* keeping the shared scale and labelling the bars, as the
panel asked. It would have kept 6.2 and left the chart's subject at a fifth
of its canvas.

**Carried by:** `docs/assets/page.js` (Chart 1, `niceAxis` per panel, `trim`);
`governance/chart-review.md` §3c #11 ("superseded"); the chart's subtitle.
