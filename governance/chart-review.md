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
Widths reached (K6): 320 · 625 · 626 · 1040 — derived per chart by
               src/render_charts.py from window.CASCADIA_BREAKPOINTS = [560];
               every chart's host crosses 560 between viewports 625/626
               (docs/renders/k6-ladder.json). 320 is the narrowest supported
               width; 1040 the design width. (The first build declared a
               second breakpoint at 900 and rendered 965/966 as well; it went
               with Chart 2's in-plot annotation in Round 1.)
Once per publish (K7, K8): K7 PASS — every asset URL carries a content hash
               (asset_v); K8 PASS — og:title/description/image/url and
               twitter:card/image present, image URL absolute, favicon linked.
               The og:image URL names a thumbnail the site-side session has
               not yet produced (see "Owed", below).
Reading panel (7.4): RUN 2026-09-14, Cowork side, simulated, 4 seats,
               widths 320 and 1040 — record in §3; every finding
               dispositioned in §3c; Round 1 changes in §4.
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

## 3 · Reading panel (Rule 7.4) — RUN 2026-09-14, Cowork side

Run Cowork-side 2026-09-14 against the renders committed at `bbedb1f`. Four
agents, one message, parallel, blind to each other, the design system, the
build notes and the source data. Widths given: 320 and 1040 (domain seats also
received the page's five data tables as plain text; the visualization seat
received images only). Filed here verbatim from the panel record delivered to
Aaron (`READING-PANEL-Revenue-Assurance-2026-09-14.md`); condensed only where
the record itself was condensed.

### Transport certification — the panel's own

```
transport            Cowork, four subagents spawned in one message
injects              the connected projects' CLAUDE.md files and the skills
                     list reach a Cowork subagent beneath its prompt (measured
                     on the Fee Examiner panel, 2026-09-10; same transport)
blind                not certified
basis                the same class of leak the Fee Examiner record measured
                     directly; not re-measured for this run. Filenames and
                     one-line descriptions travel; rule content does not. No
                     seat's return referenced the design system, a rule
                     number, or the panel process by name.
```

### 3a · Roster block

```
READING PANEL — Cascadia Revenue Assurance — 2026-09-14
Decision served (Rule 0.1): the finance / revenue-operations owner who signs the
  monthly partner invoice run; operational (every run) with a tactical consequence
  (whether to keep invoicing from the register at all)
Charts panelled: 4   States: default (static page; no other states exist)
Nature: simulated

  Seat 1  Director of Revenue Operations, mid-sized B2B subscription software
          company selling partly through channel partners, 14 yrs
          — simulated — why this seat: signs the invoice run the page is about;
          accountable when a partner disputes it. Reads for "will this survive an
          audit and how much is at stake"
  Seat 2  Senior Revenue Accountant, same kind of company, 11 yrs; closes in five
          days and explains variances she did not cause
          — simulated — why this seat: the person who has to book whatever the
          register-vs-effective gap turns out to be. Reads for "owed, should-not-
          recognise, or timing difference", and for counts mixed with dollars
  Seat 3  Channel Account Manager at a reseller partner, 7 yrs; not an analyst
          — simulated — why this seat: the partner's side of the consolidated
          invoice. The person the numbers are about, at the literacy the room
          actually has. Reads for "is my company billed correctly and which of my
          customers is this"
  Seat 4  visualization reader   — simulated — canvas only; tables and arithmetic
          excluded

Blindness asserted: design system ☑ · review and build notes ☑ · source data ☑ ·
                    intended finding from outside the artifact ☑ · other seats' output ☑
Run: parallel ☑    Author's pre-panel notes recorded: ☑  (governance/pre-panel-notes.md,
                    21 items, sealed at bbedb1f — N is measured against it)
```

### 3b · Return blocks — verbatim (condensed to the fields the disposition table cites; full seat transcripts are on file with Aaron)

**Seat 1 (Director of Revenue Ops)** — Chart 1: *"What does 'deferred order' actually mean here… I need to know how many of those went through a partner versus direct."* Gap: *"Dollars. This is order counts and days, and I can't get from 845 orders to a number I can put in front of Finance."* — Chart 2: *"Which direction is this money flowing? … I can't tell from this whether it's over-billing exposure, under-billing, or simply contractual run-off, and that's the entire question for whether I sign the invoice run."* Gap: *"I couldn't reconcile '127 subscription-months' against '3,556 licences'… I don't know what a subscription-month is."* — Chart 3: *"Which of these two lines do we invoice from? … I need to know which one is the system of record."* Gap: *"the paragraph says the gap peaked at 6,964 in January 2026, and I went looking for that peak on the chart and there's no marker."* — Chart 4: *"Is the 83% expected? … the 18.6% annual is the one that worries me: annual renewals should have a renewal order behind them."* Gap: *"The paragraph mentions '19,111 of 23,508 term instances are manufactured', which is a different denominator from the 50,110 rows in the title."*

**Seat 2 (Senior Revenue Accountant)** — Chart 1 sentence carries the claim; gap: *"Dollars… I also looked for the split between reductions and cancellations and it isn't here — they're pooled… The two panels share a 670 axis so the annual bars are all squashed under 120 — I could read the shape but not the heights."* — Chart 2: *"There's about $59K a month of run-rate on licences customers have already cancelled or reduced… this chart uses three different counts for the same bars… The word 'backlog' also threw me — to me backlog means contracted-not-yet-billed, and this isn't that. On the phone the axis ran out to $145K and the two monthly bars disappeared entirely."* — Chart 3: sentence notes the 5,875 figure ties exactly to Chart 2's four licence counts summed. Gap: *"The peak — 6,964 in January 2026, 8.9% — is in the paragraph but not marked on the chart… No dollar axis… at this scale the gap is a thin band and you can't read its shape."* — Chart 4 sentence: *"I'd have to say I don't fully follow… I can't tell whether that's just auto-renew working as designed or a flag that a chunk of the billing data was derived rather than recorded"* → does not carry the title's claim. Closing note: *"on every chart there's a paragraph above the title that repeats the whole chart in prose. I read that first, and half the figures I quoted came from there rather than from the picture."*

**Seat 3 (Channel Account Manager)** — Chart 1: *"is this real data from our account, or a made-up example?"* — Chart 2 sentence: *"there's about $59K a month still being billed at June that shouldn't be"* (reads the gap as over-billing). Gap: *"Whose money it is… I also couldn't square '127 subscription-months' with '3,556 licences'… I gave up on it."* — Chart 3: *"If 'effective' is what you bill us and 'register' is what I see in the partner portal, then you're telling me I'm paying for 5,875 licences I can't see."* — Chart 4 sentence: does not carry the claim (*"I didn't follow what that meant"*).

**Seat 4 (visualization reader)** — full technical return in the delivered panel record. Key items: Chart 1 — *"The 670 tick sits right on top of 600 and reads as a mistake… No gridlines, so annual bar heights… can only be guessed."* Chart 2 — *"the title quotes two sums ($56,180 and $59,264) that are not drawn anywhere… on the phone the axis stretches to $145K, which makes the two monthly bars vanish entirely."* Chart 3 — *"The plot's dominant message is the growth; the title's message is the gap, which is the smallest thing on the plot… '5.7%': not drawn… Grayscale: at risk."* Chart 4 — sound in form; *"the annotation sits in the gap between the two bars… it looks like it might describe the empty space to the right of the annual bar."*

### 3c · Disposition block — pooled, deduplicated, sorted by n

**One entry is updated from the panel's own recommendation: #11.** The panel recommended keeping Chart 1's shared y-axis (Rule 6.2) and adding bar labels. Aaron's direct read of the rendering (§3e below) overrides this: independent axes per panel. Recorded as an author override, not a panel error, and written into `governance/decision-record.md` as D15 so the deviation reads as a decision rather than an oversight.

| # | Finding, in the reviewer's words | Seats | n | Chart | Defect? | Novel? | Disposition | Rule |
|---|---|---|---|---|---|---|---|---|
| 2 | *"The paragraph says the gap peaked at 6,964 in January 2026, and I went looking for that peak on the chart and there's no marker"* | 1,2,3,4 | **4** | 3 | yes | no | **fixed** — annotate the Jan 2026 peak at the data | 3.4 |
| 3 | *"What is 'manufactured,' in plain terms? … took me two reads"* | 1,2,3,4 | **4** | 4 | yes | no | **fixed** — retitle in plain words, say "by design" | 3.2 |
| 1 | *"Which of these two lines do we invoice from?"* | 1,2,3 | **3** | 3, 2 | yes | yes | **fixed** — one sentence naming which quantity the invoice is computed from | 3.2 · 4.3 |
| 4 | *"Dollars… no dollars again… no dollar figure"* | 1,2,3 | **3** | 1,3,4 | yes | yes | **fixed** — dollars on 3 and 4 (Chart 1 stays in counts, points to Chart 2) | 0.1 · 4.3 |
| 5 | *"I couldn't square '127 subscription-months' against '3,556 licences'"* | 1,2,3 | **3** | 2 | yes | no | **fixed** — one unit per bar, licences | 4.3 · 2.9 |
| 6 | *"the gap is a thin band… 'every one of 24 months' is not verifiable… for the first ~6 months"* | 2,3,4 | **3** | 3 | yes | no | **fixed** — add a gap-share sub-panel below the two lines | 3.2 · 6.2 |
| 7 | *"On the phone the axis ran out to $145K and the two monthly bars disappeared… on desktop the biggest one uses less than half the axis"* | 1,2,4 | **3** | 2 | yes | no | **fixed** — annotation leaves the plot; axis ends near the data (Aaron's note reinforces this) | 2.4 · K1 |
| 8 | *"Three different denominators are in play… (19,111 of 23,508, which is 81%, not 83% or 44%)"* | 1,2 | 2 | 4 | yes | yes | **fixed** — one grain, subscription-month rows | K2 · 5.2 |
| 9 | *"The word 'backlog' also threw me — to me backlog means contracted-not-yet-billed"* | 1,2 | 2 | 2 | yes | yes | **fixed** — "gap" page-wide | 3.2 |
| 10 | *"Are these orders still open as of 30 June, or every order ever deferred?"* | 1,2 | 2 | 1 | yes | yes | **fixed** — state the population in the subtitle | 4.3 |
| 11 | *"The two panels share a 670 axis so the annual bars are all squashed under 120"* | 2,4 | 2 | 1 | yes | no | **superseded** — see note above; independent axes per panel (Aaron, §3e; D15) | 3.6 · 2.4 |
| 12 | *"the coloured annotation is moved below the source/footer line, severed from the plot"* | 2,4 | 2 | 1–4 | yes | no | **fixed** — note sits under the plot, above the strip, at narrow widths | 4.2 |
| 13 | *"The final month (Jun 2026) has no tick label"* | 2,4 | 2 | 3 | yes | yes | **fixed** — June is a labelled tick at every width | 3.2 · K4 |
| 14 | *"The bar labels drop the unit"* | 3,4 | 2 | 2 | yes | yes | **fixed** — resolved with #5 | 5.5 |
| 15 | *"there's a paragraph above the title that repeats the whole chart in prose. I read that first"* | 2,4 | 2 | 1–4 | yes | yes | **fixed** — summary rendered visually below the title, not above; DOM order unchanged (5.1) | 5.1 |
| 18 | *"The 670 tick… reads as a mistake"* | 4 | 1 | 1, 3 | yes | yes | **fixed** — axis max never renders as its own tick | K4 · 2.4 |
| 19 | *"'$56,180 … on annual terms': not drawn… the total is not drawn either"* | 4 | 1 | 2 | yes | yes | **fixed** — draw the annual subtotal and total as reference marks | 3.2 |
| 20 | *"The annotation floats in empty space… rather than pointing at the gap"* | 4 | 1 | 3 | yes | yes | **fixed** — leader to the June gap | 3.4 |
| 21 | *"Grayscale: at risk… the pale salmon fill will print as a faint tint or nothing"* | 4 | 1 | 3 | yes | yes | **fixed** — differentiate lines by weight/dash, not hue alone | 5.4 |
| 22 | *"the annotation sits in the gap between the two bars… looks like it might describe the empty space"* | 4 | 1 | 4 | yes | yes | **fixed** — anchor to the monthly bar's end | 3.4 |
| 25 | *"the dashed median line… is hard to see"* | 4 | 1 | 1 | yes | no | **accepted** — a contrasting dash if Chart 1 is touched anyway (it is) | 3.4 |
| 16 | *"nothing per account or customer, so I can't go back to anyone with it"* | 1,3 | 2 | 2 | no | no | **accepted** — one sentence saying why, not silence | — |
| 23 | *"the split between reductions and cancellations… isn't here — they're pooled"* | 2 | 1 | 1 | no | no | **accepted** — mention the detail table exists | — |
| 17 | *"is this real data from our account, or a made-up example?"* | 1,3 | 2 | 1 | no | no | **rejected** — the disclosure worked as designed | — |
| 24 | *"I cannot see 16 specifically — a 30-day bin is too coarse"* | 4 | 1 | 1 | no | no | **rejected** — preference, not a misreading | — |
| 26 | *"annual renewals should have a renewal order behind them. What is the paper trail"* | 1 | 1 | 4 | no | no | **rejected as a defect, kept as evidence** — the module's thesis, correctly read | — |

### 3d · Summary line

```
PANEL: 4 seats, simulated · 4 charts · findings 26 · defects 21 · novel 13
       fixed 20 · accepted 3 · rejected 3 · multi-seat defects 15
       D = 5.25 defects/chart · N = 0.62 novel share · R = 0.12 rejected share
```

Neither retirement trigger is near. N is measured against `pre-panel-notes.md`
as sealed at `bbedb1f`.

### 3e · Aaron's direct read, Round 1 (2026-09-14) — three defects a static panel could not find

Recorded verbatim, with the disposition of each in §4 (Round 1 disposition).

1. *No tooltip appears on mouse hover over any of the four charts.* — the live
   page, not a render.
2. *"These charts don't need the same axis. It is a bunch of dead space. 1st
   chart the x axis has 11 empty values. 2nd chart never goes above 200, so
   everything after that is dead space."* — Chart 1; overrides panel #11.
3. *"x axis is too long again. should end at ~$40K."* — Chart 2; the same root
   cause as panel #7.

## 4 · Round 1 disposition — what changed, finding by finding (2026-09-14)

Applied in one session on `build/stage-2-page` after the panel record and
Aaron's direct read. Every new figure the changes show was already certified
(M-05 `landed_by_as_of`, M-03a licences, M-06 `cents_derived_share`, the
M-01/M-02 monthly series); no measure file changed and Path 2 needed no new
leaf. The Checklist A table in §1 is read with this section: where the two
disagree, this section is the later statement.

| Finding | What changed | Where |
|---|---|---|
| #1 (which quantity is invoiced) | One sentence, repeated where a screenshot would strand it (Rule 4.3): the decision paragraph, Chart 2's subtitle, Chart 3's subtitle. *"Invoices are computed from the effective quantity; the register is what the customer sees. Billed from the register instead, June 2026 would under-bill by $59,264."* | `build_page.py` |
| #2 (Jan 2026 peak) | A second, subordinate annotation (12 px) on Chart 3's new share panel at the January 2026 bar: *"Peak Jan 2026: 6,964 licences, 8.9%"*. One dominant annotation remains (the June one, 13 px). | `page.js` c3 |
| #3 (plain words, by design) | Chart 4 retitled: *"83% of monthly-term billing rows and 19% of annual-term rows sit in a term that auto-renewed with no order behind it"*; subtitle opens "By design:"; annotation *"By design: every monthly term after the first auto-renews without an order"*. | `build_page.py` |
| #4 (dollars) | Chart 3's annotation carries the June dollars ($59,264 a month); Chart 4's subtitle carries M-06's dollar share (48.2%); Chart 2's subtitle carries the dollar figures. Chart 1 stays in counts and its subtitle says "In dollars: Chart 2". | `build_page.py` |
| #5, #14 (one unit per bar) | Chart 2 is drawn in **licences**: axis, bars and value labels; the four figures are asserted at build time to sum to M-03's 5,875. Title restated in licences; dollars and subscription-months in subtitle, tooltip and table. | `build_page.py`, `page.js` c2 |
| #6 (thin band) | Chart 3 gains a second panel beneath the lines: one bar per month, gap as a share of effective, every bar above zero, own nice axis. | `page.js` c3 |
| #7, Aaron 3c (axis too long) | Chart 2's annotation is never in the plot; the axis bound is derived from the longest value label only and rounded to nice ticks. At 1040 the axis ends at **5,000 licences** against a longest bar of 3,556 (71%); at 320 it ends at 7,500 (the three-tick narrow axis). | `page.js` c2 |
| #8 (one grain) | The term-instance count (19,111 of 23,508) is gone from Chart 4's title, subtitle, summary and the page's governance note; "subscription-month rows" throughout. It remains in the codebook. | `build_page.py` |
| #9 ("backlog") | Zero occurrences of the word on the page (grep of `docs/index.html`). "Gap" throughout, matching the measure's own name. | `build_page.py` |
| #10 (population) | Chart 1's subtitle: *"for all 1,460 deferred orders received in the window, landed or still pending (845 annual, 615 monthly; 452 and 588 had reached their boundary by 2026-06-30)"*. | `build_page.py` |
| #11 (shared axis) → **superseded** | Each Chart 1 panel takes its own vertical scale (monthly 0–800 by 200; annual 0–200 by 50) and is trimmed to its populated bins (monthly 2 of 13; annual 13 of 13); panel widths follow bin counts with a floor for the panel label. The subtitle says so. Decision record **D15**. | `page.js` c1 |
| #12 (note below the strip) | Card children carry CSS `order`: chart, note, navigator, strip, summary, tables. The note sits between the plot and the strip at every width. | `build_page.py` (styles) |
| #13 (June tick) | Chart 3's x-axis is on the lower panel with `showMaxLabel` and `showMinLabel`; "Jun 2026" (or "Jun '26") is labelled at every width. | `page.js` c3 |
| #15 (summary read first) | Summary stays first in the DOM (Rule 5.1) and renders below the strip in secondary ink; the finding title is the first thing a sighted reader meets. **Open item for VIZ-PRINCIPLES 5.1** (see Owed). | `build_page.py` (styles) |
| #18 (max tick crowding) | `niceAxis()`: every value-axis bound is a whole number of nice ticks and the interval is set with it, so the maximum is a regular tick (Chart 1: 800 and 200; Chart 3: 125K and 15%; Chart 2: 5,000). | `page.js` |
| #19 (subtotals not drawn) | Chart 2 draws each term type's subtotal as a label on a zero-opacity `markArea` spanning its two rows: *"Annual total 5,618 of 5,875 licences"*, *"Monthly total 257 of 5,875 licences"*. The grand total is in the title and both labels. **Not drawn as a reference line**: a line at 5,875 would push the axis past the data, which is the thing Aaron's read and #7 asked to stop. | `page.js` c2 |
| #20 (annotation floats) | A vertical leader from the June effective point up to the annotation, which is right-aligned to it. | `page.js` c3 |
| #21 (grayscale) | Register line dashed, effective line solid and heavier; the fill is a third channel, not the only one. | `page.js` c3 |
| #22 (Chart 4 annotation placement) | Annotation right-aligned to the monthly bar's end, directly beneath it, clear of the bar by half its height plus a leader's length; a short leader is drawn from the bar's end into the band. | `page.js` c4 |
| #25 (median line faint) | A paper halo under a heavier dash; the line stops at the panel's tallest bar with a horizontal label above it. | `page.js` c1 |
| #16 (per partner) — accepted | Governance note under Chart 2: *"Nothing on this page is shown per partner or per customer, by decision…"* with the reason. | `build_page.py` |
| #23 (split by label) — accepted | Chart 1's subtitle: *"The split by order label is in the table beneath."* | `build_page.py` |
| #17, #24, #26 — rejected | No change, per §3c. | — |
| Aaron 3a (tooltips) | **Not reproduced.** Hover probes in headless Chromium at 320, 626, 1040, under touch emulation (tap and mouse), under reduced motion, on bars and on empty plot regions all rendered the tooltip on every chart, before any change. The vendored ECharts tests `triggerOn` by substring, so the undocumented `'mousemove|mouseout'` token was inert; it is nonetheless replaced by the documented `'mousemove'`. One environment found where the page shows no charts at all: the desktop app's Browser pane loads the file as a `data:` snapshot in which no script runs. Which browser and path Aaron used is the open question. | `page.js` `tip()` |

**Checklist A after Round 1 (delta only).** 2.2 for Chart 1 now reads "two panels, one axis each, **independent scales (D15)**"; 6.2 is not claimed for Chart 1. K1 for Charts 1, 2 and 3 now reads "bound = whole nice ticks via `niceAxis`, derived from the data". 5.4 for Chart 3 now PASS by dash and weight. 3.4 for Chart 3 now records two annotations, one dominant. 7.1/7.4: **panel run, findings dispositioned** — the invariant that was open is closed. Widths reached: 320, 625, 626, 1040.

**Preference score after Round 1, as the author reads it: 0.** Invariant failures: 0.

## Owed

- **VIZ-PRINCIPLES.md Rule 5.1 open item, from panel #15:** DOM order and
  visual order are different requirements, and 5.1 currently conflates them
  ("a short text summary in the DOM before the chart"). Two seats read the
  summary first and quoted it instead of the plot. Proposed: the summary is
  first in the DOM and may render after the chart; the rule should say which
  order it means. Filed for a `cascadia-standards` session; not applied from
  here.
- The site-side session: `projects/cascadia-revenue-assurance.qmd`, a
  `_quarto.yml` entry, and the thumbnail at the `og:image` URL this page
  already carries (`https://www.robbinsanalytics.com/assets/thumb-revenue-assurance.png`).
  Until that file exists the social card renders without an image. The
  `og:url` names the path the Fee Examiner precedent's pattern implies; the
  site-side session confirms it.
- The reading panel (Cowork), then the author's disposition (Code), then
  Aaron's read (Code). This page does not ship before the first of those.

## Verdict

**After Round 1 (2026-09-14): zero INVARIANT failures, preference score 0,
several N/A.** The panel has run and every finding is dispositioned (§3c,
§4); the one invariant that was open (7.1 / 7.4) is closed. **The page ships
when Aaron's own read of the rebuilt rendering says so** — his Round 1 notes
are applied (§3e, §4); a second panel pass is recommended against only if
he judges Chart 1's independent axes or Chart 3's new panel to be a change
of form rather than of geometry (the author's view: geometry, no second pass
needed). The tooltip report (3a) is not reproduced and stays open until the
browser and path it was seen in are known.
