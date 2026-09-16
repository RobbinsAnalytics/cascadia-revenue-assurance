"""Render the page and every chart across the K6 width ladder.

CHART-REVIEW K6 is an INVARIANT: render at the narrowest supported width, the
design width, and the two viewports either side of every DECLARED breakpoint's
HOST-ELEMENT crossing -- not the window's. The ladder is DERIVED from
`window.CASCADIA_BREAKPOINTS`, declared once in docs/assets/page.js, and this
script fails closed if none are declared rather than falling back to a typed
pair. The mechanism follows cascadia-matter-ledger-analytics/src/render_charts.py,
the worked remedy CHART-REVIEW.md names; it is not mandated, the recorded
widths are.

320 px is Rule 5.3 / WCAG 1.4.10 reflow and what CASCADIA.minCanvasPx
hard-codes -- the floor the system claims to support.

The page is opened as a file:// URL. It makes no network request of any kind
(the Stage 2 brief's must-not), so no local server is needed either.

Checked at every width, and each is a FAIL that exits non-zero:
  * horizontal overflow -- Rule 5.3's 1.4.10 clause, asserted rather than assumed
  * the rendered provenance strip's segment count (K5): exactly 3 per chart
  * any page error or console error -- a chart that threw did not draw

Also printed, for the review record: the real ECharts grid rect per chart.

Output: docs/renders/<chart>-<width>.png, page-<width>.png, and
        docs/renders/k6-ladder.json (the widths reached and the crossings),
        which governance/chart-review.md cites rather than restates.

    python src/render_charts.py            # the K6 ladder, derived
    python src/render_charts.py 390 768    # explicit widths, for a look
"""
from __future__ import annotations

import json
import pathlib
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = pathlib.Path(__file__).resolve().parent.parent
DOCS = REPO / "docs"
OUT = DOCS / "renders"
URL = (DOCS / "index.html").resolve().as_uri()
DESIGN_WIDTH = 1040
NARROW_WIDTH = 320
SEARCH_MAX = 1600
CHARTS = ["c1", "c2", "c3", "c4"]
EXPECTED_SEGMENTS = 3


def k6_ladder(browser):
    """Binary-search, per chart and per declared breakpoint, the viewport at
    which that chart's HOST crosses the breakpoint; return both sides of it."""
    page = browser.new_page(viewport={"width": DESIGN_WIDTH, "height": 900})
    page.goto(URL, wait_until="load")
    page.wait_for_timeout(500)
    bps = page.evaluate("() => window.CASCADIA_BREAKPOINTS || null")
    if not bps:
        page.close()
        sys.exit("page.js declares no window.CASCADIA_BREAKPOINTS, so the K6 ladder "
                 "cannot be derived. Fail closed rather than fall back to a typed pair.")

    def host_width(viewport, cid):
        page.set_viewport_size({"width": viewport, "height": 900})
        page.wait_for_timeout(60)
        return page.evaluate("(id) => document.getElementById(id).clientWidth", cid)

    widths = {NARROW_WIDTH, DESIGN_WIDTH}
    crossings = []
    for cid in CHARTS:
        for b in bps:
            lo, hi = NARROW_WIDTH, SEARCH_MAX
            if host_width(hi, cid) < b or host_width(lo, cid) >= b:
                continue
            while hi - lo > 1:
                mid = (lo + hi) // 2
                if host_width(mid, cid) >= b:
                    hi = mid
                else:
                    lo = mid
            crossings.append({"chart": cid, "breakpoint": b, "below": lo, "above": hi})
            widths.add(lo)
            widths.add(hi)
    page.close()
    return sorted(widths), list(bps), crossings


def main() -> int:
    argv = sys.argv[1:]
    out_dir = OUT
    if "--out" in argv:
        i = argv.index("--out")
        out_dir = pathlib.Path(argv[i + 1])
        argv = argv[:i] + argv[i + 2:]
    widths = [int(a) for a in argv if a.isdigit()]
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.exit("playwright is required: pip install playwright && playwright install chromium")
    out_dir.mkdir(parents=True, exist_ok=True)

    overflow, segments, errors_at = [], [], []
    grid_log = {}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        bps, crossings = [], []
        if widths:
            print("explicit widths: %s" % ", ".join(str(w) for w in widths))
        else:
            widths, bps, crossings = k6_ladder(browser)
            print("K6 ladder derived from declared breakpoints %s" % bps)
            for c in crossings:
                print("  %s crosses host %d px between viewport %d and %d"
                      % (c["chart"], c["breakpoint"], c["below"], c["above"]))
            print("  widths: %s" % ", ".join(str(w) for w in widths))
        for width in widths:
            page = browser.new_page(viewport={"width": width, "height": 1600}, device_scale_factor=2)
            errs = []
            page.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
            page.on("pageerror", lambda e: errs.append(str(e)))
            page.goto(URL, wait_until="load")
            page.wait_for_timeout(1200)
            if errs:
                errors_at.append((width, errs[:5]))
                print("  ERRORS at %d px:" % width)
                for e in errs[:5]:
                    print("    " + e)
            page.screenshot(path=str(out_dir / ("page-%d.png" % width)), full_page=True)
            for cid in CHARTS:
                card = page.locator("#%s" % cid).locator("xpath=ancestor::div[contains(@class,'chart-card')]")
                target = card if card.count() else page.locator("#%s" % cid)
                target.screenshot(path=str(out_dir / ("%s-%d.png" % (cid, width))))
            seg = page.evaluate(
                """() => Array.from(document.querySelectorAll('.cascadia-provenance'))
                        .map(n => n.textContent.split(' \\u00b7 ').length)""")
            for cid, n in zip(CHARTS, seg):
                if n != EXPECTED_SEGMENTS:
                    segments.append((width, cid, n))
            grid = page.evaluate(
                """() => Object.fromEntries(%s.map(id => {
                     try {
                       const ch = echarts.getInstanceByDom(document.getElementById(id));
                       const gs = ch.getModel().findComponents({mainType: 'grid'});
                       return [id, gs.map(g => Math.round(g.coordinateSystem.getRect().width)).join('+')];
                     } catch (e) { return [id, 'n/a']; }
                   }))""" % json.dumps(CHARTS))
            grid_log[str(width)] = grid
            over = page.evaluate(
                """() => ({scroll: document.documentElement.scrollWidth,
                          client: document.documentElement.clientWidth})""")
            print("  width %d: strips %s  grid px %s" % (width, seg, grid))
            if over["scroll"] > over["client"] + 1:
                overflow.append((width, over["scroll"], over["client"]))
                print("  width %d: HORIZONTAL OVERFLOW scrollWidth %d > clientWidth %d"
                      % (width, over["scroll"], over["client"]))
            page.close()
        browser.close()

    (out_dir / "k6-ladder.json").write_text(json.dumps({
        "declared_breakpoints": bps, "widths_rendered": widths, "crossings": crossings,
        "charts": CHARTS, "narrowest": NARROW_WIDTH, "design": DESIGN_WIDTH,
        "grid_px_by_width": grid_log,
    }, indent=2) + "\n", encoding="utf-8", newline="\n")
    print("\nrenders in %s" % out_dir)

    failed = False
    if overflow:
        failed = True
        print("\nRULE 5.3 / WCAG 1.4.10 FAILED -- the page scrolls sideways:")
        for w, sw, cw in overflow:
            print("  at %d px the document is %d px wide (over by %d)" % (w, sw, sw - cw))
    if segments:
        failed = True
        print("\nK5 FAILED -- a provenance strip did not render %d segments:" % EXPECTED_SEGMENTS)
        for w, cid, n in segments:
            print("  %s at %d px: %d segments" % (cid, w, n))
    if errors_at:
        failed = True
        print("\nPAGE ERRORS -- a chart that threw did not draw:")
        for w, es in errors_at:
            print("  at %d px: %s" % (w, es[0]))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
