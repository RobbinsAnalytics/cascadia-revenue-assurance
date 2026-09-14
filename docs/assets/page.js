/**
 * Cascadia Revenue Assurance — chart layer (Stage 2).
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
 * EVERY CHART CALLS cascadiaAnnotation at the design width (Rule 3.4). At the
 * narrow width the annotation prose leaves the plot (Rule 5.5 drop order,
 * step 4) and is shown as a visible note under the chart instead, so the
 * sentence is never lost, only moved.
 *
 * ENTITY COLOURS ARE FIXED ACROSS THE PAGE (Rule 2.3.1): annual = Evergreen,
 * monthly = Glacier, wherever a term type is encoded. Chart 3 encodes two
 * different entities — the effective line (Evergreen, the series the title
 * is about) and the register line (Rain, directly labelled) — and shades the
 * gap between them in Madrona, the unfavourable hue, with the sign carried by
 * the annotation and the labels (Rule 2.3.2).
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
  function usd(cents) {
    var c = Math.round(Math.abs(cents)), s = cents < 0 ? '-' : '';
    return s + '$' + nf(Math.floor(c / 100)) + (c % 100 ? '.' + String(c % 100).padStart(2, '0') : '');
  }
  function pct(x, dp) { return (100 * x).toFixed(dp == null ? 1 : dp) + '%'; }

  /* ---- measured text, never guessed ---------------------------------- */
  var _m = document.createElement('canvas').getContext('2d');
  function textWidth(text, font) { _m.font = font; return _m.measureText(String(text)).width; }
  function wrappedLines(text, px, font) {
    _m.font = font;
    var words = String(text).split(' '), lines = 1, cur = '';
    for (var i = 0; i < words.length; i++) {
      var test = cur ? cur + ' ' + words[i] : words[i];
      if (_m.measureText(test).width > px && cur) { lines++; cur = words[i]; }
      else { cur = test; }
    }
    return lines;
  }
  /**
   * Wrap a sentence at SPACES ONLY, measured in the font it will render in,
   * and return it with explicit newlines. ECharts' own 'break' overflow treats
   * every ASCII punctuation mark and every non-ASCII character as a break
   * opportunity, so left to itself it split a title inside "$35,560" (after
   * the comma) and could split "330–359" at the dash. A figure broken across
   * two lines reads as two figures. Pre-wrapped lines each fit their width,
   * so the renderer never has to choose a break of its own.
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

  /** The theme's title block, pre-wrapped, plus the height it will take (17px/26 serif + 12px/18 sans). */
  function titleBlock(L, finding, subtitle) {
    var px = L.w - 14 - 10;
    var f = prewrap(finding, px, TITLE_FONT), s = prewrap(subtitle, px, SUB_FONT);
    var tl = f.split('\n').length, sl = s.split('\n').length;
    return { title: cascadiaTitle(f, s, { width: L.w - 14 }),
             top: Math.round(6 + tl * 26 + 6 + sl * 18 + 14) };
  }
  /** An annotation pre-wrapped to its own box width, in the serif it renders in. */
  function annotation(text, opts) {
    var w = opts.width || 180;
    return cascadiaAnnotation(prewrap(text, w - 6, ANN_FONT), opts);
  }

  /**
   * EVERY WIDTH AT WHICH THIS PAGE CHANGES ITS MIND, DECLARED IN ONE PLACE.
   * K6's ladder is derived from this list by src/render_charts.py. One
   * breakpoint: below it, Chart 1's panels stack instead of sitting side by
   * side, in-plot annotations move out of the plot, and value labels drop
   * their unit words. Measured on the HOST element's width, not the window.
   */
  var BP = { narrow: 560, roomy: 900 };
  window.CASCADIA_BREAKPOINTS = [BP.narrow, BP.roomy];
  // BP.roomy exists for Chart 2 alone: its in-plot annotation needs the bar,
  // a long value label and 200 px of prose to fit on one row. Measured: at a
  // host width of 900 the row holds them with the bar at a third of the plot;
  // at 760 it did not (the prose clipped at the frame). Below BP.roomy that
  // chart's annotation is the note under the chart; the other three switch at
  // BP.narrow. Declared here, not measured ad hoc, so K6 renders both sides.

  function layout(host) {
    var w = host.clientWidth || CASCADIA.minCanvasPx;
    return {
      w: w,
      narrow: w < BP.narrow,
      roomy: w >= BP.roomy,
      tapTip: !(window.matchMedia &&
                window.matchMedia('(hover: hover) and (pointer: fine)').matches)
    };
  }

  /** Tooltip: tap-to-pin at a fixed position on touch, hover-following otherwise (Rule 5.5). */
  function tip(L, opts) {
    return {
      show: true,
      trigger: opts.trigger || 'item',
      confine: true,
      appendToBody: false,
      triggerOn: L.tapTip ? 'mousemove|click' : 'mousemove|mouseout',
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

  /** The common tail: sizing, strip, summary, access layers, the narrow-width note. */
  function finish(host, ch, spec, L) {
    cascadiaResize(host, ch);
    cascadiaProvenance(host, spec.provenance);
    el('sum-' + host.id).textContent = spec.summary;
    cascadiaAccessible(host, { label: spec.ariaLabel, summaryId: 'sum-' + host.id,
                               tableId: 'tbl-' + host.id });
    if (spec.nav) cascadiaNavigator(host, spec.nav);
    var note = el('note-' + host.id);
    // Prose leaves the plot at narrow widths (5.5 step 4) and becomes a
    // visible note under the chart; the sentence is moved, never dropped.
    if (note) note.hidden = !(spec.noteVisible == null ? L.narrow : spec.noteVisible);
    return ch;
  }

  /**
   * Build once for the width the host has, and rebuild only when the host
   * crosses the declared breakpoint. cascadiaResize handles every other
   * resize. Rebuilding disposes the old instance first; the strip and the
   * navigator are idempotent by owner, so nothing accumulates (Rule 6.7).
   */
  function mount(id, build) {
    var host = el(id), state = { mode: null, chart: null };
    function run() {
      var L = layout(host), mode = (L.narrow ? 'n' : 'w') + (L.roomy ? 'r' : 't');
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
    var maxCount = Math.max.apply(null, d.annual.concat(d.monthly));
    // One shared scale for both panels (6.2). The tallest bar is the monthly
    // spike; the annotation sits above the tallest ANNUAL bar, which is far
    // below it, so the headroom needed is small. Derived from the data (K1).
    var yMax = Math.ceil(maxCount * 1.15 / 10) * 10;
    var gridTop = top + panelLabelH;
    host.style.height = (side ? gridTop + P + axisH + 8
                              : gridTop + 2 * (P + axisH) + panelLabelH + 8) + 'px';
    var leftW = side ? Math.round(L.w * 0.5) : L.w;
    var grids = side
      ? [{ left: 8, width: leftW - 30, top: gridTop, height: P, containLabel: true },
         { left: leftW + 10, right: 12, top: gridTop, height: P, containLabel: true }]
      : [{ left: 8, right: 12, top: gridTop, height: P, containLabel: true },
         { left: 8, right: 12, top: gridTop + P + axisH + panelLabelH, height: P, containLabel: true }];
    // Panel labels sit ABOVE each grid, right-aligned to its right edge, so
    // they never meet the y-axis ticks or a median label that starts at the
    // left edge (the monthly median is in the first bin).
    var gridW = [side ? grids[0].width : L.w - 8 - 12, side ? L.w - grids[1].left - 12 : L.w - 8 - 12];
    var labelY = [gridTop - panelLabelH + 4, side ? gridTop - panelLabelH + 4 : gridTop + P + axisH + 4];
    var labelRight = [side ? L.w - grids[0].left - grids[0].width : 12, 12];

    var binLabel = function (b) { return String(b); };
    function axes(idx) {
      return {
        x: { type: 'category', gridIndex: idx, data: d.bins.map(binLabel),
             name: 'days pending, 30-day bins', nameLocation: 'middle', nameGap: 30,
             axisLabel: { hideOverlap: true },           // K4: thinned by the renderer
             axisTick: { show: false } },
        y: { type: 'value', gridIndex: idx, min: 0, max: yMax, splitNumber: 4 }
      };
    }
    var a0 = axes(0), a1 = axes(1);
    var panels = [
      { key: 'monthly', name: 'Monthly term', data: d.monthly, idx: 0 },
      { key: 'annual',  name: 'Annual term',  data: d.annual,  idx: 1 }
    ];
    function medianLine(p) {
      var med = d.median[p.key], x = med / 30 - 0.5;
      // The line runs from the axis to the height of the panel's tallest bar,
      // no further: a full-height line would cross the annotation that sits
      // above the annual modal bar. Its label sits horizontally (Rule 2.8)
      // just above the line's end; the monthly median is in the first bin, so
      // that label is pushed right of the line rather than centred over the
      // y-axis ticks.
      var top = Math.max.apply(null, p.data);
      return {
        symbol: 'none', silent: true,
        lineStyle: { type: 'dashed', color: TT_INK[p.key], width: 1 },
        label: { show: true, position: 'end', rotate: 0, distance: 6,
                 formatter: 'median ' + nf(med) + ' days',
                 fontFamily: SANS, fontSize: 12, color: TT_INK[p.key],
                 align: x < 1 ? 'left' : 'center', offset: x < 1 ? [-6, 0] : [0, 0] },
        data: [[{ xAxis: x, yAxis: 0 }, { xAxis: x, yAxis: top }]]
      };
    }
    var modalIdx = d.bins.indexOf(d.modalBin.annual);
    var series = panels.map(function (p) {
      var s = {
        name: p.name, type: 'bar', xAxisIndex: p.idx, yAxisIndex: p.idx, data: p.data,
        itemStyle: { color: TT[p.key] }, barCategoryGap: '12%',
        markLine: medianLine(p)
      };
      if (p.key === 'annual' && !L.narrow) {
        // Above the modal bar (the tallest annual bar, so nothing beside it is
        // higher -- K3), right-aligned to that bar's centre so the box extends
        // LEFT over the headroom and never past the panel's right edge.
        // distance 34: the median label sits in the ~20 px above the tallest
        // bar's height, so the box starts above that band (K3, and no text on
        // text). The axis bound above reserves the room.
        s.markPoint = annotation(d.annotation, {
          color: TT.annual, coord: [modalIdx, d.annual[modalIdx]], position: 'top', distance: 34,
          align: 'right', width: Math.min(230, Math.round(gridW[1] * 0.6)), container: L.w
        });
      }
      return s;
    });
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
                        points: d.bins.map(function (b, i) {
                          return { label: b + ' to ' + (b + 29) + ' days', value: nf(p.data[i]) + ' orders',
                                   seriesIndex: p.idx, dataIndex: i };
                        }) };
             }) }
    }, L);
  });

  /* ================= Chart 2 · backlog by term type and cause ================= */
  mount('c2', function (host, L) {
    var d = D.c2, rows = d.rows;
    var tb = titleBlock(L, d.finding, d.subtitle), top = tb.top;
    var inPlot = L.roomy;                 // the annotation's placement switches at BP.roomy
    var labelW = L.narrow ? 104 : Math.max(120, Math.min(230, Math.round(L.w * 0.32)));
    // Rule 5.5: at the narrow width a direct label may be ABBREVIATED by a
    // declared mapping, never deleted. The mapping, declared:
    //   "cancellations riding out the term" -> "cancellations", "deferred reductions" -> "reductions",
    //   "$35,560" -> "$35.6K", "(127 subscription-months)" -> "(127)".
    var catLabel = function (r) {
      return L.narrow ? r.label.replace(' riding out the term', '').replace('deferred ', '') : r.label;
    };
    var kUsd = function (cents) {
      var dlr = cents / 100;
      return dlr >= 1000 ? '$' + (Math.round(dlr / 100) / 10) + 'K' : '$' + nf(Math.round(dlr));
    };
    var valueLabel = function (r) {
      return L.narrow ? kUsd(r.cents) + ' (' + nf(r.months) + ')'
                      : r.dollars + ' (' + nf(r.months) + ' subscription-months)';
    };
    var maxDollars = rows[0].cents / 100;
    var labelPx = Math.max.apply(null, rows.map(function (r) { return textWidth(valueLabel(r), '12px ' + SANS); }));
    var annW = inPlot ? 200 : 0;
    var gridRight = 16;
    var plotW = Math.max(120, L.w - labelW - 8 - gridRight - 20);
    // Rule 2.1 / K1: the bound is derived so that the longest value label and,
    // at the design width, the annotation both fit inside the frame.
    var fit = 1 - (labelPx + annW + 28) / plotW;
    if (inPlot && fit < 0.25) {
      // The declared breakpoint should make this unreachable; if a font or a
      // longer figure ever changes that, say so rather than clip in silence.
      console.warn('[c2] annotation room is short at host width ' + L.w + '; raise BP.roomy');
    }
    var xMax = maxDollars / Math.max(0.25, fit);
    xMax = Math.ceil(xMax / 5000) * 5000;
    var perRow = 52;
    host.style.height = (top + rows.length * perRow + 70) + 'px';
    var ch = echarts.init(host, 'cascadia');
    var option = {
      title: tb.title,
      grid: { left: 8, right: gridRight, bottom: 34, top: top, containLabel: true },
      xAxis: { type: 'value', min: 0, max: xMax, splitNumber: L.narrow ? 3 : 5,
               name: 'dollars per month', nameLocation: 'middle', nameGap: 28,
               axisLabel: { formatter: function (v) { return v >= 1000 ? '$' + (v / 1000) + 'K' : '$' + v; } } },
      yAxis: { type: 'category', inverse: true, data: rows.map(catLabel),
               axisLabel: { width: labelW, overflow: 'break', lineHeight: 15,
                            verticalAlign: 'middle', interval: 0, margin: 10 } },
      tooltip: tip(L, {
        trigger: 'item',
        formatter: function (q) {
          var r = rows[q.dataIndex];
          return r.label + '<br>' + r.dollars + ' per month<br>' + nf(r.months) +
                 ' subscription-months, ' + nf(r.licences) + ' licences';
        }
      }),
      series: [{
        type: 'bar', barCategoryGap: '38%',
        data: rows.map(function (r) {
          return { value: r.cents / 100, itemStyle: { color: TT[r.termType] },
                   label: { color: TT_INK[r.termType] } };
        }),
        label: { show: true, position: 'right', fontFamily: SANS, fontSize: 12,
                 formatter: function (q) { return valueLabel(rows[q.dataIndex]); } }
      }]
    };
    if (inPlot) {
      // Beside the first bar, clear of its value label (K3): the distance is the
      // measured label width plus a gap, and the axis bound above reserved the room.
      var lbl0 = textWidth(valueLabel(rows[0]), '12px ' + SANS);
      option.series[0].markPoint = annotation(d.annotation, {
        color: TT[rows[0].termType], coord: [rows[0].cents / 100, 0], position: 'right',
        distance: Math.round(lbl0 + 18), align: 'left', width: annW, container: L.w
      });
    }
    ch.setOption(option);
    return finish(host, ch, { provenance: d.provenance, summary: d.summary, ariaLabel: d.ariaLabel,
                              noteVisible: !inPlot }, L);
  });

  /* ================= Chart 3 · register vs effective, month by month ================= */
  mount('c3', function (host, L) {
    var d = D.c3, pts = d.points, n = pts.length;
    var tb = titleBlock(L, d.finding, d.subtitle), top = tb.top;
    var endLabelW = Math.ceil(Math.max(textWidth('Effective', '12px ' + SANS), textWidth('Register', '12px ' + SANS))) + 14;
    var plotW = Math.max(160, L.w - 70 - endLabelW);
    var eff = pts.map(function (p) { return p.effective; });
    var reg = pts.map(function (p) { return p.register; });
    var gap = pts.map(function (p) { return p.gap; });
    // Rule 1.3: bank the shape to the data, not to a stylesheet default.
    var plotH = cascadiaBankedHeight(eff, plotW, { min: 220, max: 400 }) || 300;
    host.style.height = (top + plotH + 60) + 'px';
    // Rule 2.1: the title makes a ratio claim ("5.7%"), so the axis includes
    // zero. K1: the bound is derived, with headroom for the annotation.
    var maxEff = Math.max.apply(null, eff);
    var yMax = Math.ceil(maxEff * 1.22 / 10000) * 10000;
    var last = pts[n - 1];
    var xLabel = function (p) {
      return L.narrow ? p.label.replace(/ (\d\d)(\d\d)$/, " '$2") : p.label;   // declared abbreviation (5.5)
    };
    var ch = echarts.init(host, 'cascadia');
    ch.setOption({
      title: tb.title,
      grid: { left: 8, right: endLabelW + 8, top: top, height: plotH, containLabel: true },
      xAxis: { type: 'category', data: pts.map(xLabel), boundaryGap: false,
               axisLabel: { hideOverlap: true, interval: 'auto' },    // K4: thinned, never rotated
               axisTick: { show: false } },
      yAxis: { type: 'value', min: 0, max: yMax, splitNumber: 4,
               name: 'licences', nameLocation: 'end', nameGap: 8,
               nameTextStyle: { color: C.slateMoss, fontFamily: SANS, fontSize: 12, align: 'left' },
               axisLabel: { formatter: function (v) { return v >= 1000 ? (v / 1000) + 'K' : String(v); } } },
      tooltip: tip(L, {
        trigger: 'axis',
        formatter: function (qs) {
          var p = pts[qs[0].dataIndex];
          return p.label + '<br>Effective: ' + nf(p.effective) + '<br>Register: ' + nf(p.register) +
                 '<br>Gap: ' + nf(p.gap) + ' (' + pct(p.share) + ')';
        }
      }),
      series: [
        // Register: the base of the stack, Rain with a direct label (2.3.6 exception).
        { name: 'Register', type: 'line', stack: 'g', data: reg, showSymbol: false, symbol: 'none',
          lineStyle: { color: C.rain, width: 2 }, itemStyle: { color: C.rain }, z: 3,
          endLabel: { show: true, formatter: 'Register', color: C.slateMoss, fontFamily: SANS,
                      fontSize: 12, distance: 8, valueAnimation: false } },
        // Gap: stacked on the register, so its top edge is the effective line;
        // the band between is the gap, in the unfavourable hue.
        { name: 'Gap', type: 'line', stack: 'g', data: gap, showSymbol: false, symbol: 'none',
          lineStyle: { color: C.evergreen, width: 2 }, itemStyle: { color: C.evergreen },
          areaStyle: { color: C.madrona, opacity: 0.30 }, z: 2,
          endLabel: { show: true, formatter: 'Effective', color: INK.evergreen, fontFamily: SANS,
                      fontSize: 12, distance: 8, valueAnimation: false } },
        // Effective, unstacked and invisible: the anchor for the annotation and
        // the navigator, because a markPoint on a stacked series sits at the
        // series' own value, not its stacked position.
        { name: 'Effective', type: 'line', data: eff, showSymbol: false, symbol: 'none',
          lineStyle: { opacity: 0 }, itemStyle: { opacity: 0 }, tooltip: { show: false }, z: 1,
          // Above the last point, right-aligned to it, so the box extends LEFT
          // above a line that rises toward it, into headroom the axis bound
          // reserved (K3).
          markPoint: L.narrow ? undefined : annotation(d.annotation, {
            color: C.madrona, coord: [n - 1, last.effective], position: 'top', distance: 12,
            align: 'right', width: Math.min(260, Math.round(plotW * 0.5)), container: L.w
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
                 points: pts.map(function (p, i) { return { label: p.label, value: nf(p.gap) + ' (' + pct(p.share) + ')', seriesIndex: 1, dataIndex: i }; }) }
             ] }
    }, L);
  });

  /* ================= Chart 4 · derived share by term type ================= */
  mount('c4', function (host, L) {
    var d = D.c4, rows = d.rows;
    var tb = titleBlock(L, d.finding, d.subtitle), top = tb.top;
    var labelW = L.narrow ? 84 : Math.max(90, Math.min(150, Math.round(L.w * 0.22)));
    // Rule 5.5 declared abbreviation at the narrow width: the count clause is
    // dropped from the value label and stays in the table; the share never is.
    var valueLabel = function (r) {
      return L.narrow ? pct(r.share) : pct(r.share) + ' (' + nf(r.derived) + ' of ' + nf(r.rows) + ' rows)';
    };
    var labelPx = Math.ceil(Math.max.apply(null, rows.map(function (r) { return textWidth(valueLabel(r), '12px ' + SANS); })));
    var band = L.narrow ? 70 : 84;
    host.style.height = (top + rows.length * band + 56) + 'px';
    var ch = echarts.init(host, 'cascadia');
    var option = {
      title: tb.title,
      // 100 is a true ceiling on a share, not a fit to this build's numbers (K1).
      // The right padding is the measured label width, so a label at 100% would still fit.
      grid: { left: 8, right: labelPx + 16, bottom: 34, top: top, containLabel: true },
      xAxis: { type: 'value', min: 0, max: 100, splitNumber: L.narrow ? 2 : 5,
               name: 'share of billing rows', nameLocation: 'middle', nameGap: 28,
               axisLabel: { showMaxLabel: true, formatter: function (v) { return v + '%'; } } },
      yAxis: { type: 'category', inverse: true, data: rows.map(function (r) { return r.label; }),
               axisLabel: { width: labelW, overflow: 'break', lineHeight: 15,
                            verticalAlign: 'middle', interval: 0, margin: 10 } },
      tooltip: tip(L, {
        trigger: 'item',
        formatter: function (q) {
          var r = rows[q.dataIndex];
          return r.label + ': ' + pct(r.share) + '<br>' + nf(r.derived) + ' of ' + nf(r.rows) +
                 ' subscription-month rows sit in a manufactured term';
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
      // Under the monthly bar, right-aligned to its end, in the band between the
      // two bars. The data point sits at the bar's vertical CENTRE, so the
      // distance must clear half the bar's height or the label prints on the
      // bar (K3) -- the bar is 54% of the band under barCategoryGap 46%.
      var mi = rows.findIndex(function (r) { return r.termType === 'monthly'; });
      option.series[0].markPoint = annotation(d.annotation, {
        color: TT.monthly, coord: [Math.round(1000 * rows[mi].share) / 10, mi], position: 'bottom',
        distance: Math.round(band * 0.54 / 2) + 10, align: 'right', width: 260, container: L.w
      });
    }
    ch.setOption(option);
    return finish(host, ch, { provenance: d.provenance, summary: d.summary, ariaLabel: d.ariaLabel }, L);
  });

})();
