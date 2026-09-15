/**
 * Cascadia Revenue Assurance — chart layer (Stage 2, after the reading panel
 * and Aaron's first direct read, 2026-09-14).
 *
 * Reads the build-time data block written by src/build_page.py. No figure or
 * sentence is composed here that is not already in that block (K2): every
 * title, subtitle, annotation, summary and aria-label arrives as a string,
 * and this file decides geometry only.
 *
 * FOUR CHARTS. Two call cascadiaNavigator (Rule 5.1 layer 3): Chart 1, whose
 * finding is the SHAPE of two distributions, and Chart 3, whose finding is a
 * SEQUENCE over 24 month ends. Charts 2 and 4 are ranked bars whose table
 * carries the finding as well as the canvas does, and carry an L3 shape
 * clause in their summary instead.
 *
 * ANNOTATIONS. Charts 1, 3 and 4 carry theirs in the plot at the design width
 * and as a note under the plot below the declared breakpoint (Rule 5.5 drop
 * order, step 4). Chart 2's annotation is ALWAYS the note under the plot
 * (panel finding #7, Aaron's read): reserving room for it inside the frame
 * pushed the axis to twice the data at every width.
 *
 * ENTITY COLOURS ARE FIXED ACROSS THE PAGE (Rule 2.3.1): annual = Evergreen,
 * monthly = Glacier, wherever a term type is encoded. Chart 3 encodes two
 * different entities — the effective line (Evergreen, solid, the series the
 * title is about) and the register line (Rain, dashed, directly labelled) —
 * and shades the gap between them in Madrona, the unfavourable hue, with the
 * sign carried by the annotation and the labels (Rule 2.3.2). Dash and weight
 * separate the two lines without hue (panel #21, Rule 5.4).
 *
 * AXIS BOUNDS are derived by niceAxis(): the bound is a multiple of a nice
 * tick step, so the axis maximum is never rendered as its own crowded tick
 * (panel #18). Chart 1's panels each take their own bound and their own bin
 * range (Aaron, overriding panel #11 — decision record D15).
 */
(function () {
  'use strict';

  var D = JSON.parse(document.getElementById('cascadia-data').textContent);
  var C = CASCADIA.colors, INK = CASCADIA.textInk;
  var SANS = CASCADIA.sans, SERIF = CASCADIA.serif;

  var TT = { annual: C.evergreen, monthly: C.glacier };
  var TT_INK = { annual: INK.evergreen, monthly: INK.glacier };

  function el(id) { return document.getElementById(id); }
  function nf(n) { return Number(n).toLocaleString('en-US'); }
  function pct(x, dp) { return (100 * x).toFixed(dp == null ? 1 : dp) + '%'; }

  /* ---- measured text, never guessed ---------------------------------- */
  var _m = document.createElement('canvas').getContext('2d');
  function textWidth(text, font) { _m.font = font; return _m.measureText(String(text)).width; }
  /**
   * Wrap a sentence at SPACES ONLY, measured in the font it will render in,
   * and return it with explicit newlines. ECharts' own 'break' overflow treats
   * every ASCII punctuation mark and every non-ASCII character as a break
   * opportunity, so left to itself it split a title inside "$35,560".
   */
  function prewrap(text, px, font) {
    _m.font = font;
    var words = String(text).split(' '), lines = [], cur = '';
    for (var i = 0; i < words.length; i++) {
      var test = cur ? cur + ' ' + words[i] : words[i];
      if (_m.measureText(test).width > px && cur) { lines.push(cur); cur = words[i]; }
      else { cur = test; }
    }
    lines.push(cur);
    return lines.join('\n');
  }
  var TITLE_FONT = '600 17px ' + SERIF, SUB_FONT = '12px ' + SANS, ANN_FONT = '13px ' + SERIF;

  function titleBlock(L, finding, subtitle) {
    var px = L.w - 14 - 10;
    var f = prewrap(finding, px, TITLE_FONT), s = prewrap(subtitle, px, SUB_FONT);
    var tl = f.split('\n').length, sl = s.split('\n').length;
    return { title: cascadiaTitle(f, s, { width: L.w - 14 }),
             top: Math.round(6 + tl * 26 + 6 + sl * 18 + 14) };
  }
  function annotation(text, opts) {
    var w = opts.width || 180;
    var mp = cascadiaAnnotation(prewrap(text, w - 6, ANN_FONT), opts);
    if (opts.fontSize) mp.data[0].label.fontSize = opts.fontSize;
    return mp;
  }

  /**
   * A value-axis bound that is a whole number of nice ticks (K1: derived from
   * the data; panel #18: the max never renders as its own crowded tick).
   * Returns {max, interval}; both go on the axis so the last tick IS the max.
   */
  function niceAxis(maxVal, headroom, ticks) {
    var target = (maxVal * headroom) / (ticks || 4);
    var mag = Math.pow(10, Math.floor(Math.log(target) / Math.LN10));
    var step = null, cands = [1, 2, 2.5, 5, 10];
    for (var i = 0; i < cands.length; i++) {
      if (cands[i] * mag >= target) { step = cands[i] * mag; break; }
    }
    return { max: Math.ceil((maxVal * headroom) / step) * step, interval: step };
  }

  /**
   * EVERY WIDTH AT WHICH THIS PAGE CHANGES ITS MIND, DECLARED IN ONE PLACE.
   * One breakpoint. Below it Chart 1's panels stack, in-plot annotations
   * become the note under the plot, and value labels drop their unit words.
   * Measured on the HOST element's width, not the window. The second
   * breakpoint the first build carried (900, for Chart 2's in-plot
   * annotation) is gone with that annotation's in-plot placement.
   */
  var BP = { narrow: 560 };
  window.CASCADIA_BREAKPOINTS = [BP.narrow];

  function layout(host) {
    var w = host.clientWidth || CASCADIA.minCanvasPx;
    return {
      w: w,
      narrow: w < BP.narrow,
      tapTip: !(window.matchMedia &&
                window.matchMedia('(hover: hover) and (pointer: fine)').matches)
    };
  }

  /**
   * Tooltip: tap-to-pin at a fixed position on touch, hover-following
   * otherwise (Rule 5.5). triggerOn takes only the tokens ECharts documents:
   * 'mousemove' for a fine pointer, 'mousemove|click' for touch. (The first
   * build passed 'mousemove|mouseout'; the vendored build tests the string by
   * substring so it still fired, but an undocumented token is not something
   * to leave in place.)
   */
  function tip(L, opts) {
    return {
      show: true,
      trigger: opts.trigger || 'item',
      confine: true,
      appendToBody: false,
      triggerOn: L.tapTip ? 'mousemove|click' : 'mousemove',
      position: L.tapTip ? function (pt, params, dom, rect, size) {
        var cw = size.contentSize[0], chh = size.contentSize[1];
        var x = Math.max(4, Math.min(Math.round(pt[0] - cw / 2), size.viewSize[0] - cw - 4));
        var y = Math.round(pt[1] - chh - 18);
        if (y < 4) y = Math.round(pt[1] + 26);
        return [x, y];
      } : undefined,
      formatter: opts.formatter
    };
  }

  /**
   * The common tail: sizing, strip, summary, access layers, the note.
   * Visual order inside the card is set by CSS `order` (chart, note,
   * navigator, strip, summary, tables) so the summary stays FIRST in the DOM
   * for Rule 5.1 and renders below the canvas for a sighted reader (panel
   * #15), and the note sits between the plot and the strip (panel #12).
   */
  function finish(host, ch, spec, L) {
    cascadiaResize(host, ch);
    cascadiaProvenance(host, spec.provenance);
    el('sum-' + host.id).textContent = spec.summary;
    cascadiaAccessible(host, { label: spec.ariaLabel, summaryId: 'sum-' + host.id,
                               tableId: 'tbl-' + host.id });
    if (spec.nav) cascadiaNavigator(host, spec.nav);
    var note = el('note-' + host.id);
    if (note) note.hidden = !(spec.noteVisible == null ? L.narrow : spec.noteVisible);
    return ch;
  }

  function mount(id, build) {
    var host = el(id), state = { mode: null, chart: null };
    function run() {
      var L = layout(host), mode = L.narrow ? 'n' : 'w';
      if (state.chart && state.mode === mode) return;
      if (state.chart) state.chart.dispose();
      state.mode = mode;
      state.chart = build(host, L);
    }
    run();
    var t = null;
    window.addEventListener('resize', function () {
      if (t) clearTimeout(t);
      t = setTimeout(run, 120);
    });
  }

  /* ================= Chart 1 · two deferral distributions ================= */
  mount('c1', function (host, L) {
    var d = D.c1;
    var tb = titleBlock(L, d.finding, d.subtitle), top = tb.top;
    var side = !L.narrow;
    var panelLabelH = 24, P = side ? 280 : 200, axisH = 52;

    // Each panel keeps only its populated bins (through the last non-zero
    // count) and takes its own scale — Aaron's read, D15. The annual panel
    // carries the annotation, so it gets more headroom.
    function trim(counts) { var n = counts.length; while (n > 1 && counts[n - 1] === 0) n--; return n; }
    var panels = [
      { key: 'monthly', name: 'Monthly term', data: d.monthly, idx: 0, nBins: trim(d.monthly), headroom: 1.15 },
      { key: 'annual',  name: 'Annual term',  data: d.annual,  idx: 1, nBins: trim(d.annual),  headroom: 1.55 }
    ];
    panels.forEach(function (p) {
      p.bins = d.bins.slice(0, p.nBins);
      p.axis = niceAxis(Math.max.apply(null, p.data.slice(0, p.nBins)), p.headroom, 4);
    });
    // Side by side, the panels take width in proportion to their bin counts,
    // with a floor so a two-bin panel still has room for its title and label.
    var total = panels[0].nBins + panels[1].nBins;
    // ...and never narrower than its own panel label plus the y-axis column.
    var label0W = textWidth(panels[0].name + ' — ' + nf(d.n[panels[0].key]) + ' orders', '600 12px ' + SANS);
    var share0 = side ? Math.max(0.26, (label0W + 56) / L.w, Math.min(0.5, panels[0].nBins / total)) : 1;
    var gridTop = top + panelLabelH;
    host.style.height = (side ? gridTop + P + axisH + 8
                              : gridTop + 2 * (P + axisH) + panelLabelH + 8) + 'px';
    var leftW = Math.round(L.w * share0);
    var grids = side
      ? [{ left: 8, width: leftW - 30, top: gridTop, height: P, containLabel: true },
         { left: leftW + 10, right: 12, top: gridTop, height: P, containLabel: true }]
      : [{ left: 8, right: 12, top: gridTop, height: P, containLabel: true },
         { left: 8, right: 12, top: gridTop + P + axisH + panelLabelH, height: P, containLabel: true }];
    var gridW = [side ? grids[0].width : L.w - 20, side ? L.w - grids[1].left - 12 : L.w - 20];
    var labelY = [gridTop - panelLabelH + 4, side ? gridTop - panelLabelH + 4 : gridTop + P + axisH + 4];
    var labelRight = [side ? L.w - grids[0].left - grids[0].width : 12, 12];

    var binLabel = function (b) { return b + '–' + (b + 29); };
    function axes(p) {
      return {
        x: { type: 'category', gridIndex: p.idx, data: p.bins.map(binLabel),
             name: 'days pending, 30-day bins', nameLocation: 'middle', nameGap: 30,
             axisLabel: { hideOverlap: true },
             axisTick: { show: false } },
        y: { type: 'value', gridIndex: p.idx, min: 0, max: p.axis.max, interval: p.axis.interval }
      };
    }
    function medianLine(p) {
      var med = d.median[p.key], x = med / 30 - 0.5;
      var topVal = Math.max.apply(null, p.data.slice(0, p.nBins));
      var seg = function (style) {
        return [{ xAxis: x, yAxis: 0, lineStyle: style }, { xAxis: x, yAxis: topVal, lineStyle: style }];
      };
      return {
        symbol: 'none', silent: true,
        label: { show: false },
        data: [
          // a paper halo beneath the dash, so it reads against a bar of its own hue (panel #25)
          seg({ type: 'solid', color: C.paper, width: 4, opacity: 0.9 }),
          (function () {
            var s = seg({ type: 'dashed', color: TT_INK[p.key], width: 1.5 });
            s[1].label = { show: true, position: 'end', rotate: 0, distance: 6,
                           formatter: 'median ' + nf(med) + ' days',
                           fontFamily: SANS, fontSize: 12, color: TT_INK[p.key],
                           align: x < 1 ? 'left' : 'center', offset: x < 1 ? [-6, 0] : [0, 0] };
            return s;
          })()
        ]
      };
    }
    var modalIdx = d.bins.indexOf(d.modalBin.annual);
    var series = panels.map(function (p) {
      var s = {
        name: p.name, type: 'bar', xAxisIndex: p.idx, yAxisIndex: p.idx, data: p.data.slice(0, p.nBins),
        itemStyle: { color: TT[p.key] }, barCategoryGap: p.nBins <= 3 ? '45%' : '12%',
        markLine: medianLine(p)
      };
      if (p.key === 'annual' && !L.narrow) {
        s.markPoint = annotation(d.annotation, {
          color: TT.annual, coord: [modalIdx, d.annual[modalIdx]], position: 'top', distance: 34,
          align: 'right', width: Math.min(230, Math.round(gridW[1] * 0.6)), container: L.w
        });
      }
      return s;
    });
    var a0 = axes(panels[0]), a1 = axes(panels[1]);
    var ch = echarts.init(host, 'cascadia');
    ch.setOption({
      title: tb.title,
      grid: grids,
      xAxis: [a0.x, a1.x], yAxis: [a0.y, a1.y],
      graphic: panels.map(function (p, i) {
        return { type: 'text', right: labelRight[i], top: labelY[i], silent: true,
                 style: { text: p.name + ' — ' + nf(d.n[p.key]) + ' orders', fill: TT_INK[p.key],
                          font: '600 12px ' + SANS, textAlign: 'right' } };
      }),
      tooltip: tip(L, {
        trigger: 'item',
        formatter: function (q) {
          var b = d.bins[q.dataIndex];
          return q.seriesName + '<br>' + b + '–' + (b + 29) + ' days: ' + nf(q.value) + ' orders';
        }
      }),
      series: series
    });
    return finish(host, ch, {
      provenance: d.provenance, summary: d.summary, ariaLabel: d.ariaLabel,
      nav: { chart: ch, label: d.ariaLabel,
             series: panels.map(function (p) {
               return { name: p.name + ' (' + nf(d.n[p.key]) + ' orders)',
                        summary: 'median ' + nf(d.median[p.key]) + ' days, maximum ' + nf(d.max[p.key]),
                        points: p.bins.map(function (b, i) {
                          return { label: b + ' to ' + (b + 29) + ' days', value: nf(p.data[i]) + ' orders',
                                   seriesIndex: p.idx, dataIndex: i };
                        }) };
             }) }
    }, L);
  });

  /* ================= Chart 2 · the gap by term type and cause, in licences ================= */
  mount('c2', function (host, L) {
    var d = D.c2, rows = d.rows;
    var tb = titleBlock(L, d.finding, d.subtitle), top = tb.top;
    var labelW = L.narrow ? 104 : Math.max(120, Math.min(230, Math.round(L.w * 0.32)));
    // Rule 5.5 declared abbreviations at the narrow width:
    //   "cancellations riding out the term" -> "cancellations", "deferred reductions" -> "reductions",
    //   "3,556 licences" -> "3,556" (the unit stays in the axis name).
    var catLabel = function (r) {
      return L.narrow ? r.label.replace(' riding out the term', '').replace('deferred ', '') : r.label;
    };
    var valueLabel = function (r) { return L.narrow ? nf(r.licences) : nf(r.licences) + ' licences'; };
    var maxLic = Math.max.apply(null, rows.map(function (r) { return r.licences; }));
    var labelPx = Math.max.apply(null, rows.map(function (r) { return textWidth(valueLabel(r), '12px ' + SANS); }));
    var gridRight = 16;
    var plotW = Math.max(120, L.w - labelW - 8 - gridRight - 20);
    // K1: the bound is derived so the longest value label fits inside the frame,
    // then rounded to a whole number of nice ticks. No room is reserved for an
    // annotation: it is the note under the plot at every width (panel #7).
    var fit = Math.max(0.5, 1 - (labelPx + 28) / plotW);
    var ax = niceAxis(maxLic / fit, 1.0, L.narrow ? 3 : 5);
    var perRow = 52;
    host.style.height = (top + rows.length * perRow + 70) + 'px';
    // Group subtotals drawn on the canvas (panel #19), as a label on a
    // zero-opacity markArea spanning each term type's two rows.
    var groups = {};
    rows.forEach(function (r, i) {
      var g = groups[r.termType] || (groups[r.termType] = { first: i, last: i, licences: 0 });
      g.last = i; g.licences += r.licences;
    });
    var markAreaData = Object.keys(groups).map(function (tt) {
      var g = groups[tt];
      return [{ yAxis: g.first, itemStyle: { color: 'transparent', opacity: 0 },
                label: { show: true, position: 'insideRight', fontFamily: SANS, fontSize: 12,
                         color: TT_INK[tt], formatter: tt.charAt(0).toUpperCase() + tt.slice(1) +
                           (L.narrow ? ' ' : ' total ') + nf(g.licences) + ' of ' + nf(d.totalLicences) +
                           (L.narrow ? '' : ' licences') } },
              { yAxis: g.last }];
    });
    var ch = echarts.init(host, 'cascadia');
    ch.setOption({
      title: tb.title,
      grid: { left: 8, right: gridRight, bottom: 34, top: top, containLabel: true },
      xAxis: { type: 'value', min: 0, max: ax.max, interval: ax.interval,
               name: 'licences the register does not show', nameLocation: 'middle', nameGap: 28,
               axisLabel: { formatter: function (v) { return nf(v); } } },
      yAxis: { type: 'category', inverse: true, data: rows.map(catLabel),
               axisLabel: { width: labelW, overflow: 'break', lineHeight: 15,
                            verticalAlign: 'middle', interval: 0, margin: 10 } },
      tooltip: tip(L, {
        trigger: 'item',
        formatter: function (q) {
          var r = rows[q.dataIndex];
          return r.label + '<br>' + nf(r.licences) + ' licences, ' + r.dollars + ' per month<br>' +
                 nf(r.months) + ' subscription-months';
        }
      }),
      series: [{
        type: 'bar', barCategoryGap: '38%',
        data: rows.map(function (r) {
          return { value: r.licences, itemStyle: { color: TT[r.termType] },
                   label: { color: TT_INK[r.termType] } };
        }),
        label: { show: true, position: 'right', fontFamily: SANS, fontSize: 12,
                 formatter: function (q) { return valueLabel(rows[q.dataIndex]); } },
        markArea: { silent: true, data: markAreaData }
      }]
    });
    return finish(host, ch, { provenance: d.provenance, summary: d.summary, ariaLabel: d.ariaLabel,
                              noteVisible: true }, L);
  });

  /* ================= Chart 3 · register vs effective, month by month, with the gap share beneath ================= */
  mount('c3', function (host, L) {
    var d = D.c3, pts = d.points, n = pts.length;
    var tb = titleBlock(L, d.finding, d.subtitle), top = tb.top;
    var endLabelW = Math.ceil(Math.max(textWidth('Effective', '12px ' + SANS), textWidth('Register', '12px ' + SANS))) + 14;
    var plotW = Math.max(160, L.w - 70 - endLabelW);
    var eff = pts.map(function (p) { return p.effective; });
    var reg = pts.map(function (p) { return p.register; });
    var gap = pts.map(function (p) { return p.gap; });
    var shr = pts.map(function (p) { return Math.round(1000 * p.share) / 10; });   // percent, one decimal
    // Rule 1.3: bank the top panel to the data. The share panel beneath is a
    // fixed small height: its job is "every month above zero", not slope.
    var plotH = cascadiaBankedHeight(eff, plotW, { min: 200, max: 360 }) || 280;
    var panelGap = 34, shareH = L.narrow ? 90 : 110, axisH = 40;
    var shareTop = top + plotH + panelGap + 18;
    host.style.height = (shareTop + shareH + axisH + 6) + 'px';
    // Rule 2.1: the title makes a ratio claim ("5.7%"), so the axis includes
    // zero. K1: bounds derived, as whole ticks (panel #18).
    var maxEff = Math.max.apply(null, eff);
    var axTop = niceAxis(maxEff, 1.2, 5);
    var axShr = niceAxis(Math.max.apply(null, shr), 1.25, 3);
    var last = pts[n - 1];
    var peakIdx = pts.map(function (p) { return p.month; }).indexOf(d.peak.month);
    var xLabel = function (p) {
      return L.narrow ? p.label.replace(/ (\d\d)(\d\d)$/, " '$2") : p.label;   // declared abbreviation (5.5)
    };
    var leaderTop = last.effective * 1.045;   // the leader from the June point up to the annotation (panel #20)
    var ch = echarts.init(host, 'cascadia');
    ch.setOption({
      title: tb.title,
      grid: [
        { left: 8, right: endLabelW + 8, top: top, height: plotH, containLabel: true },
        { left: 8, right: endLabelW + 8, top: shareTop, height: shareH, containLabel: true }
      ],
      axisPointer: { link: [{ xAxisIndex: 'all' }] },
      xAxis: [
        { type: 'category', gridIndex: 0, data: pts.map(xLabel), boundaryGap: false,
          axisLabel: { show: false }, axisTick: { show: false } },
        // June 2026 is always a labelled tick (panel #13): showMaxLabel forces the
        // endpoint; hideOverlap thins the rest (K4).
        { type: 'category', gridIndex: 1, data: pts.map(xLabel), boundaryGap: false,
          axisLabel: { hideOverlap: true, interval: 'auto', showMinLabel: true, showMaxLabel: true },
          axisTick: { show: false } }
      ],
      yAxis: [
        { type: 'value', gridIndex: 0, min: 0, max: axTop.max, interval: axTop.interval,
          name: 'licences', nameLocation: 'end', nameGap: 8,
          nameTextStyle: { color: C.slateMoss, fontFamily: SANS, fontSize: 12, align: 'left' },
          axisLabel: { formatter: function (v) { return v >= 1000 ? (v / 1000) + 'K' : String(v); } } },
        { type: 'value', gridIndex: 1, min: 0, max: axShr.max, interval: axShr.interval,
          name: 'gap as a share of effective', nameLocation: 'end', nameGap: 8,
          nameTextStyle: { color: C.slateMoss, fontFamily: SANS, fontSize: 12, align: 'left' },
          axisLabel: { formatter: function (v) { return v + '%'; } } }
      ],
      tooltip: tip(L, {
        trigger: 'axis',
        formatter: function (qs) {
          var p = pts[qs[0].dataIndex];
          return p.label + '<br>Effective: ' + nf(p.effective) + '<br>Register: ' + nf(p.register) +
                 '<br>Gap: ' + nf(p.gap) + ' (' + pct(p.share) + ')';
        }
      }),
      series: [
        // Register: base of the stack. Rain, DASHED (a non-hue channel, panel #21),
        // with a direct end label in Slate moss (2.3.6 exception).
        { name: 'Register', type: 'line', stack: 'g', data: reg, showSymbol: false, symbol: 'none',
          lineStyle: { color: C.rain, width: 2, type: 'dashed' }, itemStyle: { color: C.rain }, z: 3,
          endLabel: { show: true, formatter: 'Register', color: C.slateMoss, fontFamily: SANS,
                      fontSize: 12, distance: 8, valueAnimation: false } },
        // Gap: stacked on the register, so its top edge is the effective line,
        // solid and heavier; the band between is the gap in the unfavourable hue.
        { name: 'Gap', type: 'line', stack: 'g', data: gap, showSymbol: false, symbol: 'none',
          lineStyle: { color: C.evergreen, width: 2.5 }, itemStyle: { color: C.evergreen },
          areaStyle: { color: C.madrona, opacity: 0.30 }, z: 2,
          endLabel: { show: true, formatter: 'Effective', color: INK.evergreen, fontFamily: SANS,
                      fontSize: 12, distance: 8, valueAnimation: false } },
        // Effective, unstacked and invisible: the anchor for the leader, the
        // annotation and the navigator (a markPoint on a stacked series sits at
        // the series' own value, not its stacked position).
        { name: 'Effective', type: 'line', data: eff, showSymbol: false, symbol: 'none',
          lineStyle: { opacity: 0 }, itemStyle: { opacity: 0 }, tooltip: { show: false }, z: 1,
          markLine: L.narrow ? undefined : {
            symbol: 'none', silent: true, label: { show: false },
            lineStyle: { color: INK.madrona, width: 1, type: 'solid' },
            data: [[{ coord: [n - 1, last.effective] }, { coord: [n - 1, leaderTop] }]]
          },
          markPoint: L.narrow ? undefined : annotation(d.annotation, {
            color: C.madrona, coord: [n - 1, leaderTop], position: 'top', distance: 4,
            align: 'right', width: Math.min(280, Math.round(plotW * 0.5)), container: L.w
          }) },
        // The gap share, one bar per month: every month above zero is the
        // panel's own test of "every one of 24 months" (panel #6).
        { name: 'Gap share', type: 'bar', xAxisIndex: 1, yAxisIndex: 1, data: shr,
          itemStyle: { color: C.madrona }, barCategoryGap: '25%',
          markPoint: L.narrow ? undefined : annotation(d.peakAnnotation, {
            color: C.madrona, coord: [peakIdx, shr[peakIdx]], position: 'top', distance: 6,
            align: peakIdx > n / 2 ? 'right' : 'left', width: 200, fontSize: 12, container: L.w
          }) }
      ]
    });
    return finish(host, ch, {
      provenance: d.provenance, summary: d.summary, ariaLabel: d.ariaLabel,
      nav: { chart: ch, label: d.ariaLabel,
             series: [
               { name: 'Effective licences', summary: 'rises from ' + nf(pts[0].effective) + ' to ' + nf(last.effective),
                 points: pts.map(function (p, i) { return { label: p.label, value: nf(p.effective), seriesIndex: 2, dataIndex: i }; }) },
               { name: 'Register licences', summary: 'rises from ' + nf(pts[0].register) + ' to ' + nf(last.register),
                 points: pts.map(function (p, i) { return { label: p.label, value: nf(p.register), seriesIndex: 0, dataIndex: i }; }) },
               { name: 'Gap, effective minus register', summary: 'ends at ' + nf(last.gap) + ' licences, ' + pct(last.share) + ' of effective',
                 points: pts.map(function (p, i) { return { label: p.label, value: nf(p.gap) + ' (' + pct(p.share) + ')', seriesIndex: 3, dataIndex: i }; }) }
             ] }
    }, L);
  });

  /* ================= Chart 4 · derived share by term type ================= */
  mount('c4', function (host, L) {
    var d = D.c4, rows = d.rows;
    var tb = titleBlock(L, d.finding, d.subtitle), top = tb.top;
    var labelW = L.narrow ? 84 : Math.max(90, Math.min(150, Math.round(L.w * 0.22)));
    var valueLabel = function (r) {
      return L.narrow ? pct(r.share) : pct(r.share) + ' (' + nf(r.derived) + ' of ' + nf(r.rows) + ' rows)';
    };
    var labelPx = Math.ceil(Math.max.apply(null, rows.map(function (r) { return textWidth(valueLabel(r), '12px ' + SANS); })));
    var band = L.narrow ? 70 : 84;
    host.style.height = (top + rows.length * band + 56) + 'px';
    var mi = rows.findIndex(function (r) { return r.termType === 'monthly'; });
    var mv = Math.round(1000 * rows[mi].share) / 10;
    var ch = echarts.init(host, 'cascadia');
    var option = {
      title: tb.title,
      // 100 is a true ceiling on a share, not a fit to this build's numbers (K1).
      grid: { left: 8, right: labelPx + 16, bottom: 34, top: top, containLabel: true },
      xAxis: { type: 'value', min: 0, max: 100, interval: L.narrow ? 50 : 20,
               name: 'share of subscription-month rows', nameLocation: 'middle', nameGap: 28,
               axisLabel: { formatter: function (v) { return v + '%'; } } },
      yAxis: { type: 'category', inverse: true, data: rows.map(function (r) { return r.label; }),
               axisLabel: { width: labelW, overflow: 'break', lineHeight: 15,
                            verticalAlign: 'middle', interval: 0, margin: 10 } },
      tooltip: tip(L, {
        trigger: 'item',
        formatter: function (q) {
          var r = rows[q.dataIndex];
          return r.label + ': ' + pct(r.share) + '<br>' + nf(r.derived) + ' of ' + nf(r.rows) +
                 ' subscription-month rows sit in a term that auto-renewed with no order behind it';
        }
      }),
      series: [{
        type: 'bar', barCategoryGap: '46%',
        data: rows.map(function (r) {
          return { value: Math.round(1000 * r.share) / 10, itemStyle: { color: TT[r.termType] },
                   label: { color: TT_INK[r.termType] } };
        }),
        label: { show: true, position: 'right', fontFamily: SANS, fontSize: 12,
                 formatter: function (q) { return valueLabel(rows[q.dataIndex]); } }
      }]
    };
    if (!L.narrow) {
      // A short leader from the monthly bar's end down into the band between
      // the bars, and the annotation at its foot, right-aligned to the bar's
      // end (panel #22): the sentence is tied to that bar, not to the space
      // beside the annual one. The leader uses the xAxis/yAxis form, which
      // accepts a fractional category position; a markPoint `coord` on a
      // category axis rounds to the nearest band, so the annotation is
      // anchored at the bar's centre and pushed clear of it by distance
      // (half the bar height plus the leader's length).
      var barHalf = Math.round(band * 0.54 / 2), leader = 14;
      option.series[0].markLine = {
        symbol: 'none', silent: true, label: { show: false },
        lineStyle: { color: TT_INK.monthly, width: 1, type: 'solid' },
        data: [[{ xAxis: mv, yAxis: mi }, { xAxis: mv, yAxis: mi + 0.44 }]]
      };
      option.series[0].markPoint = annotation(d.annotation, {
        color: TT.monthly, coord: [mv, mi], position: 'bottom', distance: barHalf + leader,
        align: 'right', width: 300, container: L.w
      });
    }
    ch.setOption(option);
    return finish(host, ch, { provenance: d.provenance, summary: d.summary, ariaLabel: d.ariaLabel }, L);
  });

})();
