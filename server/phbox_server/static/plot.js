// Interactive time-series charts on canvas. Charts in one group share their time
// window and crosshair: hover shows a tooltip, dragging zooms into a section,
// double-click resets, arrow keys step through the readings.

const reducedMotion = () => matchMedia("(prefers-reduced-motion: reduce)").matches;

// first index with ts[i] >= x
function lowerBound(ts, x) {
  let lo = 0, hi = ts.length;
  while (lo < hi) { const mid = (lo + hi) >> 1; if (ts[mid] < x) lo = mid + 1; else hi = mid; }
  return lo;
}

function niceStep(raw) {
  const p = 10 ** Math.floor(Math.log10(raw));
  const m = raw / p;
  return (m <= 1 ? 1 : m <= 2 ? 2 : m <= 2.5 ? 2.5 : m <= 5 ? 5 : 10) * p;
}

const SECOND = 1000, MINUTE = 60 * SECOND, HOUR = 60 * MINUTE, DAY = 24 * HOUR;
const TIME_STEPS = [10 * SECOND, 30 * SECOND, MINUTE, 2 * MINUTE, 5 * MINUTE, 10 * MINUTE, 15 * MINUTE,
  30 * MINUTE, HOUR, 2 * HOUR, 3 * HOUR, 6 * HOUR, 12 * HOUR, DAY, 2 * DAY];

function timeTicks(x0, x1, maxTicks) {
  const step = TIME_STEPS.find((s) => (x1 - x0) / s <= maxTicks) ?? 7 * DAY;
  const offset = new Date(x0).getTimezoneOffset() * MINUTE; // align ticks to local clock time
  const ticks = [];
  for (let x = Math.ceil((x0 - offset) / step) * step + offset; x <= x1; x += step) ticks.push(x);
  return { ticks, step };
}

class ChartGroup {
  constructor() {
    this.charts = [];
    this.full = [0, 1];
    this.view = [0, 1];
    this.hoverT = null;
    this.active = null;
    this.maxGap = Infinity;
    this.minSpan = 2 * MINUTE;
    this.onViewChange = null;
    this.frame = null;
  }

  add(chart) { this.charts.push(chart); chart.group = this; return chart; }

  zoomed() {
    const tolerance = (this.full[1] - this.full[0]) * 0.001;
    return this.view[0] > this.full[0] + tolerance || this.view[1] < this.full[1] - tolerance;
  }

  // A new full window; an unzoomed view follows it, a zoomed view stays where it is.
  setFull(x0, x1) {
    const following = !this.zoomed();
    this.full = [x0, x1];
    if (following) this.view = [x0, x1];
    this.renderAll();
  }

  setView(a, b, animate = true) {
    if (b - a < this.minSpan) { const mid = (a + b) / 2; a = mid - this.minSpan / 2; b = mid + this.minSpan / 2; }
    a = Math.max(a, this.full[0]);
    b = Math.min(b, this.full[1]);
    cancelAnimationFrame(this.frame);
    const from = [...this.view];
    const done = () => { this.view = [a, b]; this.renderAll(); this.onViewChange?.(); };
    if (!animate || reducedMotion()) return done();
    const start = performance.now(), duration = 340;
    const step = (now) => {
      const p = Math.min(1, (now - start) / duration), e = 1 - (1 - p) ** 3;
      this.view = [from[0] + (a - from[0]) * e, from[1] + (b - from[1]) * e];
      this.renderAll();
      if (p < 1) this.frame = requestAnimationFrame(step); else done();
    };
    this.frame = requestAnimationFrame(step);
  }

  reset() { this.setView(this.full[0], this.full[1]); }

  hover(t, chart = this.active) {
    this.hoverT = t;
    this.active = chart;
    this.charts.forEach((c) => c.drawHover());
  }

  renderAll() { this.charts.forEach((c) => c.render()); }
}

class TimeChart {
  // options: value(row) -> number|null, digits, minSpan, tooltip(row) -> [[value, label], ...], label
  constructor(el, options) {
    this.el = el;
    this.o = { digits: 2, minSpan: 0, ...options };
    this.rows = [];
    this.ts = [];
    this.geom = null;
    el.classList.add("chart");
    el.tabIndex = 0;
    el.setAttribute("role", "group");
    el.setAttribute("aria-label", `${options.label}. ${t("zoomHint")}`);
    this.canvas = h("canvas", { "aria-hidden": "true" });
    this.xLine = h("div", { class: "chart-x", hidden: true });
    this.dot = h("div", { class: "chart-dot", hidden: true });
    this.select = h("div", { class: "chart-select", hidden: true });
    this.tip = h("div", { class: "chart-tip", hidden: true });
    el.replaceChildren(this.canvas, this.select, this.xLine, this.dot, this.tip);
    new ResizeObserver(() => this.render()).observe(el);
    this.bindEvents();
  }

  setRows(rows) {
    this.rows = rows;
    this.ts = rows.map((r) => r._t);
  }

  // ---------- geometry ----------

  tAt(px) {
    const g = this.geom;
    const [x0, x1] = this.group.view;
    return x0 + ((px - g.pad.l) / (g.w - g.pad.l - g.pad.r)) * (x1 - x0);
  }

  nearest(t) {
    if (!this.rows.length) return -1;
    const [x0, x1] = this.group.view;
    let i = lowerBound(this.ts, t);
    if (i > 0 && (i === this.ts.length || t - this.ts[i - 1] < this.ts[i] - t)) i -= 1;
    while (i >= 0 && this.o.value(this.rows[i]) == null) i -= 1; // skip readings without a value
    if (i < 0 || this.ts[i] < x0 || this.ts[i] > x1) return -1;
    return i;
  }

  // ---------- drawing ----------

  render() {
    const el = this.el, dpr = window.devicePixelRatio || 1;
    const w = el.clientWidth, hgt = el.clientHeight;
    if (!w || !hgt) return;
    this.canvas.width = Math.round(w * dpr);
    this.canvas.height = Math.round(hgt * dpr);
    const ctx = this.canvas.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, hgt);

    const css = getComputedStyle(el);
    const color = (name) => css.getPropertyValue(name).trim();
    const font = `12px "Instrument Sans", system-ui, sans-serif`;
    const pad = { l: 50, r: 14, t: 12, b: 28 };
    const [x0, x1] = this.group.view;
    const plotW = w - pad.l - pad.r, plotH = hgt - pad.t - pad.b;
    const X = (x) => pad.l + ((x - x0) / (x1 - x0 || 1)) * plotW;

    // visible readings, plus one on each side so lines run to the edges
    const i0 = Math.max(0, lowerBound(this.ts, x0) - 1);
    const i1 = Math.min(this.rows.length, lowerBound(this.ts, x1) + 1);
    let lo = Infinity, hi = -Infinity;
    for (let i = i0; i < i1; i++) {
      const v = this.o.value(this.rows[i]);
      if (v == null || this.ts[i] < x0 || this.ts[i] > x1) continue;
      lo = Math.min(lo, v); hi = Math.max(hi, v);
    }
    ctx.font = font;
    if (lo === Infinity) {
      this.geom = null;
      ctx.fillStyle = color("--ink-3");
      ctx.textAlign = "center";
      ctx.fillText(t("noData"), w / 2, hgt / 2);
      this.drawHover();
      return;
    }

    // value axis: keep a minimum span so sensor noise does not fill the height
    let span = Math.max(hi - lo, this.o.minSpan, 1e-9);
    const mid = (hi + lo) / 2;
    let y0 = mid - span * 0.56, y1 = mid + span * 0.56;
    const yStep = niceStep((y1 - y0) / 4);
    y0 = Math.floor(y0 / yStep) * yStep;
    y1 = Math.ceil(y1 / yStep) * yStep;
    const Y = (v) => pad.t + (1 - (v - y0) / (y1 - y0)) * plotH;
    this.geom = { w, hgt, pad, X, Y };

    // gridlines and value labels
    const tickDigits = Math.max(0, -Math.floor(Math.log10(yStep) + 1e-9));
    ctx.strokeStyle = color("--rule");
    ctx.lineWidth = 1;
    ctx.fillStyle = color("--ink-3");
    ctx.textAlign = "right";
    ctx.textBaseline = "middle";
    for (let v = y0; v <= y1 + yStep / 2; v += yStep) {
      const y = Math.round(Y(v)) + 0.5;
      ctx.beginPath(); ctx.moveTo(pad.l, y); ctx.lineTo(w - pad.r, y); ctx.stroke();
      ctx.fillText(fmt.number(v, tickDigits), pad.l - 10, y);
    }

    // time labels
    const { ticks, step } = timeTicks(x0, x1, Math.max(2, Math.floor(plotW / 110)));
    ctx.fillStyle = color("--ink-3");
    ctx.textAlign = "center";
    ctx.textBaseline = "alphabetic";
    for (const x of ticks) {
      const d = new Date(x);
      const midnight = d.getHours() === 0 && d.getMinutes() === 0 && d.getSeconds() === 0;
      const text = step >= DAY || (midnight && step >= HOUR)
        ? d.toLocaleDateString(locale(), { weekday: "short", day: "numeric" })
        : d.toLocaleTimeString(locale(), { hour: "2-digit", minute: "2-digit", ...(step < MINUTE && { second: "2-digit" }) });
      const px = Math.min(Math.max(X(x), pad.l + 20), w - pad.r - 20);
      ctx.fillText(text, px, hgt - 8);
    }

    // the line, thinned to the first, lowest, highest and last reading of each pixel column
    const segments = [];
    let seg = null, col = null, prevT = -Infinity;
    const flush = () => {
      if (!col) return;
      const pts = [col.first, ...(col.minI < col.maxI ? [col.min, col.max] : [col.max, col.min]), col.last];
      seg.push(...pts);
      col = null;
    };
    for (let i = i0; i < i1; i++) {
      const v = this.o.value(this.rows[i]);
      if (v == null) continue;
      const x = this.ts[i];
      if (x - prevT > this.group.maxGap) { flush(); seg = []; segments.push(seg); }
      prevT = x;
      const px = Math.round(X(x)), pt = [X(x), Y(v)];
      if (col && col.px === px) {
        if (v < col.minV) { col.minV = v; col.min = pt; col.minI = i; }
        if (v > col.maxV) { col.maxV = v; col.max = pt; col.maxI = i; }
        col.last = pt;
      } else {
        flush();
        col = { px, first: pt, last: pt, min: pt, max: pt, minV: v, maxV: v, minI: i, maxI: i };
      }
    }
    flush();

    ctx.save();
    ctx.beginPath();
    ctx.rect(pad.l, pad.t - 4, plotW, plotH + 8);
    ctx.clip();
    for (const s of segments) {
      if (!s.length) continue;
      ctx.beginPath();
      s.forEach(([x, y], k) => (k ? ctx.lineTo(x, y) : ctx.moveTo(x, y)));
      ctx.lineTo(s.at(-1)[0], pad.t + plotH);
      ctx.lineTo(s[0][0], pad.t + plotH);
      ctx.closePath();
      ctx.fillStyle = color("--accent-wash");
      ctx.fill();
      ctx.beginPath();
      s.forEach(([x, y], k) => (k ? ctx.lineTo(x, y) : ctx.moveTo(x, y)));
      ctx.strokeStyle = color("--accent");
      ctx.lineWidth = 2;
      ctx.lineJoin = "round";
      ctx.lineCap = "round";
      ctx.stroke();
    }
    ctx.restore();

    // end marker on the newest reading
    const last = this.rows.length - 1;
    if (last >= 0 && this.ts[last] >= x0 && this.ts[last] <= x1 && this.o.value(this.rows[last]) != null) {
      ctx.beginPath();
      ctx.arc(X(this.ts[last]), Y(this.o.value(this.rows[last])), 6, 0, 2 * Math.PI);
      ctx.fillStyle = color("--surface");
      ctx.fill();
      ctx.beginPath();
      ctx.arc(X(this.ts[last]), Y(this.o.value(this.rows[last])), 4, 0, 2 * Math.PI);
      ctx.fillStyle = color("--accent");
      ctx.fill();
    }
    this.drawHover();
  }

  drawHover() {
    const g = this.geom, t0 = this.group.hoverT;
    const i = g && t0 != null ? this.nearest(t0) : -1;
    const hide = i < 0;
    this.xLine.hidden = hide;
    this.dot.hidden = hide;
    this.tip.hidden = hide || this.group.active !== this;
    if (hide) return;
    const row = this.rows[i], x = g.X(this.ts[i]), y = g.Y(this.o.value(row));
    this.xLine.style.left = `${x}px`;
    this.dot.style.left = `${x}px`;
    this.dot.style.top = `${y}px`;
    if (this.tip.hidden) return;
    this.tip.replaceChildren(
      h("div", { class: "tip-time" }, fmt.dateTime(row.t)),
      ...this.o.tooltip(row).map(([value, label], k) =>
        h("div", { class: "tip-row" }, k === 0 ? h("i", { class: "tip-key" }) : null, h("b", {}, value), h("span", {}, label))));
    const tipW = this.tip.offsetWidth;
    this.tip.style.left = `${x + 14 + tipW > g.w ? x - 14 - tipW : x + 14}px`;
  }

  // ---------- interaction ----------

  bindEvents() {
    const el = this.el;
    let drag = null;
    const localX = (e) => e.clientX - el.getBoundingClientRect().left;

    el.addEventListener("pointermove", (e) => {
      if (!this.geom) return;
      const x = localX(e);
      if (drag) {
        const a = Math.max(this.geom.pad.l, Math.min(drag.x, x));
        const b = Math.min(this.geom.w - this.geom.pad.r, Math.max(drag.x, x));
        this.select.hidden = b - a < 4;
        this.select.style.left = `${a}px`;
        this.select.style.width = `${b - a}px`;
      }
      this.group.hover(this.tAt(x), this);
    });
    el.addEventListener("pointerleave", () => { if (!drag) this.group.hover(null); });
    el.addEventListener("pointerdown", (e) => {
      if (e.button !== 0 || !this.geom) return;
      drag = { x: localX(e) };
      el.setPointerCapture(e.pointerId);
    });
    el.addEventListener("pointerup", (e) => {
      if (!drag) return;
      const x = localX(e);
      this.select.hidden = true;
      if (Math.abs(x - drag.x) > 8) {
        const [a, b] = [this.tAt(Math.min(drag.x, x)), this.tAt(Math.max(drag.x, x))];
        this.group.setView(a, b);
      }
      drag = null;
    });
    el.addEventListener("dblclick", () => this.group.reset());
    el.addEventListener("focus", () => {
      if (this.group.hoverT == null && this.rows.length) this.group.hover(this.ts.at(-1), this);
    });
    el.addEventListener("blur", () => this.group.hover(null));
    el.addEventListener("keydown", (e) => {
      const i = this.nearest(this.group.hoverT ?? this.ts.at(-1));
      const move = { ArrowLeft: -1, ArrowRight: 1, Home: -Infinity, End: Infinity }[e.key];
      if (e.key === "Escape") { this.group.reset(); return; }
      if (move == null || i < 0) return;
      e.preventDefault();
      const [x0, x1] = this.group.view;
      const visible = this.ts.map((x, k) => k).filter((k) => this.ts[k] >= x0 && this.ts[k] <= x1);
      const pos = visible.indexOf(i);
      const next = visible[Math.min(visible.length - 1, Math.max(0, Number.isFinite(move) ? pos + move : move < 0 ? 0 : visible.length - 1))];
      this.group.hover(this.ts[next], this);
    });
  }
}
