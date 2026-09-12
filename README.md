# Cascadia Revenue Assurance

A synthetic, industry-agnostic subscription-licensing business, built to show
that **what a customer is contracted for and what they are billable for are
different numbers** — and that the gap, created by deliberately asymmetric
add/reduce/cancel timing rules, can sit unreconciled for up to eleven months
on an annual term, with nothing erroring and no register showing it.

## Why "Revenue Assurance"

Revenue assurance is the discipline of checking that what a business bills
agrees with what its own rules say it should bill. This module builds the
smallest version of that discipline: one event stream, one set of timing
rules, and a contracted-quantity register that will not tell you, on its own,
where the two parted ways.

## What Stage 1 proves

1. Effective entitlement can be modelled as a governed, effective-dated
   temporal fact, derived once from an event stream by a record-at-a-time
   state machine — not re-derived by hand each period.
2. The answer is checkable: a second, independently written, set-based SQL
   path re-derives every published cell and must agree, against a
   hand-specified golden fixture written before any engine code.
3. The derived rows — the renewals nobody sent — are declared as derived,
   never hidden.

Stage 1 builds no page and draws no chart; it stops at the numbers. Stage 2,
a page, is a separate brief, issued after the numbers are read.

## Everything in this repository is synthetic

Every figure is generated from a fixed seed and disclosed as such on every
output. No real company, customer, product, partner, carrier, CRM or system
name appears anywhere in this repository, in a commit message, or in any
report drawn from it. This is a model of a problem shape, not a claim about
any real book of business.

## Repository and folder names match

Local `cascadia-revenue-assurance`, remote `cascadia-revenue-assurance` — the
estate's one-name convention (`REMOTE-CONVENTION.md`), the second repository
under it after `cascadia-fee-examiner`.
