# Chart review — Cascadia Revenue Assurance, the Stage 2 page

*Owner: Aaron Robbins. Opened 2026-09-14 by the build session. Companion to
`VIZ-PRINCIPLES.md` v2.8 and `CHART-REVIEW.md` v2.8 in `cascadia-standards`.
Everything on the page is synthetic, from seed 20260911, as of 2026-06-30.*

```
CASCADIA CHART REVIEW v2.8 — docs/index.html (four charts, c1–c4) — 2026-09-14
Class: detailed (all four)         Quadrant: explanatory
Relationships: c1 distribution · c2 magnitude (ranked, grouped by term type) ·
               c3 change over time · c4 magnitude (share)
States reached: default only — the page has no reader controls, so the default
               state is the only state (Rule 6.11 N/A)
Widths reached (K6): 320 · 625 · 626 · 965 · 966 · 1040 — derived per chart by
               src/render_charts.py from window.CASCADIA_BREAKPOINTS = [560, 900];
               every chart's host crosses 560 between viewports 625/626 and 900
               between 965/966 (docs/renders/k6-ladder.json). 320 is the narrowest
               supported width; 1040 the design width.
Once per publish (K7, K8): K7 PASS — every asset URL carries a content hash
               (asset_v); K8 PASS — og:title/description/image/url and
               twitter:card/image present, image URL absolute, favicon linked.
               The og:image URL names a thumbnail the site-side session has
               not yet produced (see "Owed", below).
Reading panel (7.4): NOT RUN. This session builds; the panel is the next
               session, Cowork-side, and files its record in §3 below.
```

## Transport certification — a field every panel record must carry

Copied in form from `cascadia-fee-examiner/governance/chart-review.md`, where
the estate first measured that blindness is a property of the transport as
well as of the prompt.

```
transport            none yet — no panel has run
injects              this repository's CLAUDE.md and the estate's CLAUDE.md
                     reach any subagent spawned from a Code session rooted
                     here, before its prompt; a Cowork session carries the
                     connected projects' CLAUDE.md files and the skills list
blind                not certified
basis                no panel has run from anywhere. This repository is a
                     contaminated transport for the same reason the Fee
                     Examiner repository was: CLAUDE.md names the design
                     system, the review rule and the module's intended
                     finding. The panel runs from Cowork and certifies (or
                     declines to certify) its own transport in §3.
```

## 0 · The brief the charts were built to (Rule 0.1, six answers; Rule 0.2)

| | |
|---|---|
| **Whose decision** | The finance or revenue-operations owner who signs the monthly partner invoice run — accountable for the number on the invoice, not the analyst who computes it |
| **Horizon** | Operational, monthly: every invoice run. With a tactical consequence: whether to keep billing from the register at all |
| **Literacy** | Reads a dimensional model and a distribution without help; will notice a sloppy one |
| **Benchmark** | The register's current quantity — the naive answer — against the effective quantity derived from the event stream under the rules |
| **Refresh** | Never. Frozen synthetic snapshot, as of 2026-06-30, seed 20260911; the page says so above the fold and in every strip |
| **Action available** | Stop invoicing from the register's current quantity; derive billable quantity from the event stream and the rules and reconcile the invoice to it |

**Quadrant: explanatory.** Checklist A in full. No reader controls. Four
charts, one finding each, static. **Argued with, not substituted:** the
"action available" is supported by the charts indirectly — they show the gap,
not an invoice line that was wrong — and that is recorded as pre-panel note
21 rather than papered over.

## 1 · Checklist A, per chart

Four charts, built by `src/build_page.py` (every figure) and
`docs/assets/page.js` (geometry only), rendered by `src/render_charts.py` at
the six widths above. Renders are in `docs/renders/`, one per chart per width
plus the whole page per width.

| Check | C1 deferral distributions | C2 backlog by cause | C3 register vs effective | C4 derived share |
|---|---|---|---|---|
| 0.1 / 0.2 / 0.3 | named above; explanatory; detailed | same | same | same |
| 1.1 relationship matches title | distribution — "median 16 days … median 229 days" | magnitude — "$56,180 of the $59,264 … $35,560 of that" | change over time — "in every one of 24 months … at June 2026" | magnitude — "83% … and 19%" |
| 1.2 encoding | position on common scale (bar height, shared y) | position (bar length) | position (line height) | position (bar length) |
| 1.3 aspect banked | N/A (histogram) | N/A | PASS — height from `cascadiaBankedHeight` on the effective series | N/A |
| 1.4 causal disclaimer | N/A | N/A | N/A | N/A |
| 2.1 baseline matches claim | counts from 0 | dollars from 0 | **ratio claim ("5.7%") → axis includes 0** | share from 0 |
| K1 axis extent ⊇ series extent, bounds derived | y max = 1.15 × tallest bar, computed; x is the bin list | x max computed from the longest value label and the annotation's width so both fit inside the frame | y max = 1.22 × max effective, computed | x max = 100, a true ceiling on a share |
| 2.2 single value axis | PASS (two panels, one axis each, same scale) | PASS | PASS | PASS |
| 2.3.1 slots fixed | annual Evergreen, monthly Glacier — held on c1, c2, c4 | same | effective Evergreen, register Rain, gap Madrona — see pre-panel note 14 | same as c1 |
| 2.3.2 sentiment not by colour alone | N/A (no sentiment) | N/A | gap in Madrona **and** named by annotation and end labels | N/A |
| 2.3.3 / 2.3.4 mark size | 40 px-class bars | bars | **2 px strokes, two hues (Evergreen, Rain) + Madrona fill**: within the trio's discipline (two hues on strokes); validated at block size only — the estate's open item 2 | bars |
| 2.3.5 ≤ 4 categories | 2 | 2 hues × 4 bars | 2 series + 1 band | 2 |
| 2.3.6 ≥ 3:1, Rain labelled | PASS | PASS | PASS-BY-EXCEPTION — Rain at 2.45:1 carries the direct end label "Register" in Slate moss (5.82:1) | PASS |
| 2.4 gridlines | none | none | none | none |
| 2.5 no decoration | PASS | PASS | PASS (flat 30% fill, no gradient) | PASS |
| 2.6 part-to-whole | N/A | N/A | N/A | N/A |
| 2.7 sort | natural order (bins) | PASS-BY-EXCEPTION (3.5) — term types kept adjacent, largest dollars first within each | time order | descending by share |
| 2.8 horizontal text | PASS — median labels forced `rotate: 0` after the first render drew them along the line (§2, #6) | PASS | PASS | PASS |
| 2.9 rounded to the decision | counts; medians in whole days | dollars to the dollar (a reconciliation figure), counts | thousands on the axis, exact at the end label and in the annotation | one decimal on the share |
| 3.1 finding title at top | PASS | PASS | PASS | PASS |
| 3.2 title readable from the plot | medians are drawn as labelled reference lines on each panel | every figure in the title is a bar or a label; "$56,180" is the sum of the two annual bars — PASS-BY-EXCEPTION (computed aggregate), table carries both addends | "every one of 24 months" is the shaded band never closing; "5,875" and "5.7%" are the annotation and the subtitle's basis statement — the 5.7% is a computed aggregate, PASS-BY-EXCEPTION with the table carrying gap and effective | both shares are the bars |
| 3.3 focus treatment | comparison chart: two fixed slots; one annotation, colour-matched to the annual series | comparison by term type; annotation matched to the annual bar | the effective line is the emphasised series; the register is Rain and labelled; annotation matched to the gap's hue (Madrona), which is the object of the claim — recorded as a deliberate reading of "the series the title talks about" | comparison; annotation matched to the monthly bar |
| 3.4 annotation at the mark, one dominant | one, at the annual modal bar | one, beside the first bar | one, at the last point | one, under the monthly bar |
| K3 no annotation over a mark | PASS at every width — the box sits above the tallest annual bar with the median label in the band beneath it | PASS at 966 and 1040 (in-plot), N/A below 900 (the sentence is the note under the chart) | PASS — box extends left above a line that rises toward it | PASS — box in the band between the bars, distance = half the bar height + 10 |
| 3.5 arrangement | the two panels are the comparison | term types adjacent, causes adjacent within | the two lines share one plot | the two bars are the comparison |
| 3.6 direct labels | panel labels above each grid, in the series ink | category labels; value labels in the series ink | end-of-line labels "Effective", "Register" | category labels; value labels in the series ink |
| 4.1 holes | no gaps: every bin is present, zero counts drawn as zero-height bars — **pre-panel note 2** | none | none | none |
| 4.2 strip | 3 segments, rendered | 3 | 3 | 3 |
| K5 rendered segment count | 3 at all six widths | 3 | 3 | 3 |
| 4.3 travels alone | the censoring caveat is on the chart (annotation and strip) | the "run rate, one month" caveat is in the strip | the "derived rows flagged" caveat is in the strip | the derived definition is in the strip |
| 4.5 uncertainty | N/A — every value exact by construction | N/A | N/A | N/A |
| 5.1 access layers | summary before the chart, table (two: bins; by label), **layer 3 navigator** (finding is shape) | summary, table; L3 shape clause in summary; no navigator (ranked bars) | summary, table, **navigator** (finding is sequence) | summary, table; L3 clause; no navigator |
| 5.2 description L1–L3, never L4 | type, axes, ranges, medians, modal bins, "spread across every bin" | type, axis, every bar's value, the larger-dollars/larger-count comparison | type, axes, ranges, extrema, "sits above at every month end", peak | type, axis, both shares, blended |
| K2 every figure traces to a build step | every string in the data block is composed in `build_page.py` from `measures_manifest.json` / `measures_stage2.json`; `page.js` composes no figure; unsubstituted-token guard fails the build; five cross-checks fail it on disagreement (as-of ×4, disclosure ×3, seed, M-03a=M-03, histogram sums=M-05 n, series end=M-01/M-02, M-06a rows=M-06) | same | same | same |
| 5.3 WCAG AA | 12 px minimum everywhere (theme); reflow at 320 asserted by `render_charts.py` (no horizontal overflow at any width); focus ring on the navigator; `color-scheme: light` | same | same | same |
| 5.4 monochrome | two panels are spatially separate; Rule 5.4 survives by position and label | bars distinguished by label | lines distinguished by end label; the fill by position between them | bars by label |
| 5.5 responsive | form constant; panels stack below 560; annotation prose moves out of the plot below 560; tick density thinned by the renderer (`hideOverlap`) | form constant; declared abbreviations for category and value labels below 560; annotation out of the plot below 900 | form constant; month labels abbreviated by a declared mapping below 560; annotation out below 560 | form constant; count clause dropped from value labels below 560 (kept in the table) |
| K4 tick interval derived | `hideOverlap: true`, no literal interval | ECharts `splitNumber`, no literal | `interval: 'auto'`, `hideOverlap` | `splitNumber`, `showMaxLabel` |
| 5.6 reduced motion | theme: animation off under `prefers-reduced-motion` | same | same | same |
| 5.7 dark mode | `color-scheme: light` declared | same | same | same |
| 7.1 / 7.4 panel | **NOT RUN** — fatal under 7.1 until it is; recorded, not claimed | same | same | same |
| 7.2 AI output cleared | the charts were model-built; this checklist was run in full by the build session, which is the author and cannot be the panel | same | same | same |
| K6 widths | 320 · 625 · 626 · 965 · 966 · 1040, recorded above | same | same | same |

**Preference score, as the author reads it: 0.** No PREFERENCE check is
failed on the author's own reading; the panel may disagree and its findings
enter §3.

**Invariant status: one open** — 7.1/7.4, because no panel has run. **The
page does not ship until it has.** Everything else is PASS or
PASS-BY-EXCEPTION as recorded.

## 2 · Findings from this build session's own review, before any panel

Not a panel — the author's look at every render on the ladder, recorded
because a later N (novel share) needs it. Every one of these required looking
at a rendered image; none was caught by K5, K6, the overflow check or the
unsubstituted-token guard. Suspicions that remain after these fixes are in
`pre-panel-notes.md`.

| # | What was wrong | How found | Fixed |
|---|---|---|---|
| 1 | Chart 1's y-axis name, panel label and monthly median label all landed in the top-left corner of the monthly panel and overprinted | `c1-1040.png`, first render | Axis name removed (the panel label carries the unit); panel labels moved above each grid, right-aligned; median label placed at the end of a line that now stops at the panel's tallest bar |
| 2 | Charts 1 and 3's annotations clipped at the right edge: `align: 'right'` on a markPoint label already right-aligns to the anchor, and an added `offset` pushed the box off the canvas | first render | Offsets removed |
| 3 | Chart 4's annotation printed on the lower edge of the monthly bar — the data point sits at the bar's vertical centre, so `position: 'bottom'` with a small distance lands inside the bar | `c4-1040.png` — a K3 failure | Distance set to half the bar height plus 10 px, measured from the band |
| 4 | Chart 4's plot area was 18 px wide at 320 px: right padding reserved for the full value label ate the plot | `render_charts.py` grid log, then `c4-320.png` | Value label drops its count clause below 560 (declared, kept in the table); label column narrowed |
| 5 | Chart 2's bars were near-invisible at 320 px: long category labels plus long value labels left a 109 px plot | grid log, `c2-320.png` | Declared abbreviations below 560 for both label kinds |
| 6 | Chart 1's median labels rendered rotated along the reference line | second render | `rotate: 0`; line shortened to the tallest bar so its label sits horizontally above it |
| 7 | Chart 1's annual median line ran up through the annotation text | second render | Line stops at the tallest bar; annotation raised 34 px above it |
| 8 | ECharts broke a title inside "$35,560" (after the comma) at 626 px; its `break` overflow treats every ASCII punctuation mark and every non-ASCII character as a break opportunity | `c2-626.png` | Every canvas sentence is pre-wrapped at spaces, measured in its render font, before ECharts sees it (`prewrap`) |
| 9 | Chart 2's in-plot annotation clipped at the frame between host widths 560 and about 900: the row cannot hold bar, value label and 200 px of prose there | `c2-626.png`, then `c2-826.png` after a first try at 760 | A second declared breakpoint at 900, measured; below it the sentence is the note under the chart; the axis-bound formula warns rather than silently clamping if the room is ever short again |
| 10 | Chart 1's shared y-scale carried 1.6× headroom it no longer needed once the annotation moved to the annual panel; the annual bars were a fifth of the panel | first render | Headroom reduced to 1.15×. **The shared scale itself is kept (Rule 6.2) and is pre-panel note 1** |

## 3 · Reading panel (Rule 7.4) — to be filed by the Cowork panel session

Not run. This section is left in the shape the panel record takes so the
next session has somewhere to file. Every chart carries a stable DOM id
(`c1`–`c4`) inside a `.chart-card`, which is what the panel's screenshotter
locates. The panel is given renders at the narrowest supported width (320)
and the design width (1040) at minimum; both exist in `docs/renders/`.

```
READING PANEL — docs/index.html — <date>
Decision served (Rule 0.1): the finance / revenue-operations owner who signs
                            the monthly partner invoice run; operational
Nature: <human | simulated>

  Seat 1  <role>          — why this seat: <reason tied to the decision>
  Seat 2  <role>          — why this seat: <reason>
  Seat 3  <role>          — why this seat: <reason>
  Seat 4  visualization   — canvas only; no tables, no data, no finding

Blindness confirmed: design system ☐ · review and build notes ☐ · source data ☐ ·
                     intended finding ☐ · other reviewers' output ☐
Run: parallel ☐          Widths given: ☐ 320  ☐ 1040  ☐ other: ____
```

Seat returns, the disposition table and the D / N / R line follow here when
the panel has run. **N is computed against `pre-panel-notes.md` as written on
2026-09-14**, not against anything the author remembers later.

## Owed

- The site-side session: `projects/cascadia-revenue-assurance.qmd`, a
  `_quarto.yml` entry, and the thumbnail at the `og:image` URL this page
  already carries (`https://www.robbinsanalytics.com/assets/thumb-revenue-assurance.png`).
  Until that file exists the social card renders without an image. The
  `og:url` names the path the Fee Examiner precedent's pattern implies; the
  site-side session confirms it.
- The reading panel (Cowork), then the author's disposition (Code), then
  Aaron's read (Code). This page does not ship before the first of those.

## Verdict

**DO NOT SHIP YET — one INVARIANT open (7.1 / 7.4, no panel run).** Zero
invariant failures on the author's own reading of the other checks; preference
score 0 as the author reads it; several N/A. The renders, the ladder, the
pre-panel notes and this record are what the panel needs.
