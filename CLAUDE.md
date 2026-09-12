# Cascadia Revenue Assurance — what an agent needs to know

A synthetic, industry-agnostic subscription-licensing business, built to show
that what a customer is **contracted for** and what they are **billable for**
are different numbers — and that deliberately asymmetric add/reduce/cancel
timing rules let the gap sit unreconciled for up to eleven months on an
annual term, with nothing erroring and no register showing it. Remote is
`RobbinsAnalytics/cascadia-revenue-assurance`.

**The estate's session rules — surfaces, guards, and the traps that have each
cost a session — are at
`C:\Projects\cascadia-standards\governance\SESSION-RULES.md`.** Read §1–§7 and
stop at the line. What gets published is governed by `PRINCIPLES.md` in the
same directory. This file carries only what is true of this repo.

## Stage 1 is the data layer only — no page exists yet

This repo currently builds no page, draws no chart, and makes no live or
scheduled network call. It stops at a set of published numbers, reported to
Aaron before anything is drawn. **Stage 2 — the page — is a separate brief**,
issued after Aaron has read Stage 1's numbers. Do not anticipate it here.

## Two hard constraints, before anything else

**1 · No real company, customer, product, partner, carrier, CRM or system name
anywhere in this repository.** Every figure is generated from a fixed seed and
disclosed as such on every output (`governance/decision-record.md`, D11, once
Part 1 writes it). Synthetic partner names must not resemble real ones. This
is a model of a problem shape, never a claim about any real book of business.

**2 · No accuracy, error-rate or "correctness %" measure may exist here, ever
(D13).** This module's only correctness claim is that an independently
written second path (`src/validate_measures.py`) re-derives every published
cell and agrees, and that a hand-specified golden fixture, written before any
engine code, passes. That is a statement about method. Do not add a measure
that states or implies a comparison against any other implementation.

## Two derivation paths, independent by construction (D12)

`src/build_entitlement.py` (Path 1 — a record-at-a-time state machine in pure
Python) and `src/validate_measures.py` (Path 2 — set-based SQL in DuckDB) will
share no helper module and no intermediate table beyond `fact_order_event` and
`dim_*`. **Path 2 is written from `governance/entitlement-rules.md` only —
never by reading Path 1's code.** If a rule is ambiguous enough that the two
paths could legitimately disagree, that is a defect in the rules document, not
in either path: fix the document, then both paths.

## Naming follows REMOTE-CONVENTION.md

Local directory and GitHub repository are both `cascadia-revenue-assurance` —
the one-name rule, second repository under it after `cascadia-fee-examiner`.
No `-analytics` suffix.

## The freeze

`data/raw/*` is the frozen snapshot, written by `src/generate.py` from seed
20260911 and committed on 2026-09-11 as its own commit. `governance/freeze.toml`
protects `data/raw/*`, `data/conformed/*` and
`governance/generator_assumptions.md`; `src/validate_freeze.py` is the estate
template, verbatim, and must exit zero before anything is published.

**The template gate cannot tell an untracked file from an unchanged one.** It
compares with `git diff --quiet <baseline> -- <path>`, and an untracked path
produces no diff, so a protected file that exists on disk but was never
committed passes. Observed on 2026-09-11, before the freeze commit. A passing
gate is therefore a claim about committed files only; check `git status` too.

Regenerating is a deliberate act. Change `SEED` or the parameter block, rerun
the generator, and re-freeze with a commit that says so — never edit a file
under `data/` by hand.

## Committing

**Stage by name — never the two blanket forms.** They are denied in
`.claude/settings.json`, and that block does **not** bind under
`bypassPermissions`. What binds is
`.claude/hooks/no_blanket_add_or_force_push.py`, a `PreToolUse` hook.

**Line-ending churn will not be cosmetic once data exists** — it would make
"the frozen snapshot is untouched" unassertable. `.gitattributes` prevents it
and landed in this first commit; the git `pre-commit` gate catches what gets
through and fails closed. **It is inert until `git config core.hooksPath
.githooks` has been run in this clone**, and on POSIX it is also inert unless
`.githooks/pre-commit` is tracked `100755`. Both were done at initialisation —
confirm with `git ls-files -s .githooks/pre-commit`. Run
`python .claude/hooks/hook_test_matrix.py` to confirm the guards behave.

**This repo needs an entry in `cascadia-standards/governance/hook_manifest.json`
and cannot write one.** That entry is authored from a session rooted in
`cascadia-standards`. Until it lands, `check_hook_drift.py` names this repo as
undeclared estate-wide. **That is the honest signal, not breakage — do not
"fix" it from here.**

**This repo's own first commit was made from a session rooted at
`C:\Projects`, deliberately.** Creating the repo and installing the guard
layer is Part 0 of this build, and hooks load only from the primary working
directory, so that session was never governed by the hooks it was installing.
Part 1 (the engine, the generator, the golden fixture) runs in a fresh session
rooted **here**, where the guard is live rather than merely present.

## Generated, not authored

`data/raw/*`, `data/conformed/*` (every `dim_*`, every `fact_*`,
`measures_manifest.json`, `manifest.json`), `governance/generator_assumptions.md`
and `governance/reconciliation.md` are build outputs. Hand-editing any of them
is a recurring failure mode elsewhere in this estate — regenerate instead. The
build order is `generate.py` → `build_dimensions.py` → `build_entitlement.py`,
then the four gates: `validate.py`, `validate_measures.py`, `validate_freeze.py`,
`test_golden.py`. All four must exit zero before anything under
`data/conformed/` is committed.

## Three facts that are not in the code and have already mattered

- **Path 2 reads `data/raw/order_events.csv`, not `fact_order_event.csv`.**
  The conformed table carries Path 1's `accepted` and `rejection_reason`
  columns; a Path 2 that read them would be validating Path 1 against itself.
- **The rejection vocabulary has seven reasons, not the brief's six.**
  `DUPLICATE_CANCEL` was added because a second `CANCEL` had no class. The
  list, with precedence, is `governance/entitlement-rules.md` §1.2.
- **`governance/entitlement-rules.md` is normative and both paths are written
  from it.** If the paths disagree, fix the document first (D12), then both
  paths; do not patch one path to match the other.
