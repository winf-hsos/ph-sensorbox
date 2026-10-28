// Shared helpers for the dashboard pages: translations, formatting, API, live stream, chart.

const TEXT = {
  de: {
    title: "pH-Sensorbox",
    overview: "Übersicht",
    admin: "Verwaltung",
    noBoxes: "Noch keine freigegebenen Boxen.",
    lastContact: "letzter Kontakt",
    never: "nie",
    ago: "vor",
    uncalibrated: "unkalibriert",
    calibrated: "kalibriert",
    temperature: "Temperatur",
    voltage: "Spannung",
    range: "Zeitraum",
    export: "Export",
    calibrations: "Kalibrierungen",
    noCalibrations: "Keine Kalibrierung, der pH-Wert folgt der Nennkennlinie der Atlas-Platine.",
    time: "Zeit",
    probe: "Sonde",
    slope: "Steilheit",
    offset: "Offset bei pH 7",
    points: "Punkte",
    noData: "Keine Messwerte in diesem Zeitraum.",
    boxes: "Boxen",
    status: "Status",
    name: "Name",
    location: "Ort",
    intervals: "Intervalle (s)",
    approve: "Freigeben",
    block: "Sperren",
    save: "Speichern",
    pending: "wartet",
    approved: "freigegeben",
    blocked: "gesperrt",
    addCalibration: "Kalibrierung eintragen",
    box: "Box",
    bufferPh: "Puffer-pH",
    useCurrent: "aktuellen Wert übernehmen",
    saveCalibration: "Kalibrierung speichern",
    saved: "Gespeichert.",
    calHint: "Zwei oder drei Puffer; den Wert erst übernehmen, wenn er sich nicht mehr ändert (unter 1 mV pro Minute).",
  },
  en: {
    title: "pH Sensor Box",
    overview: "Overview",
    admin: "Administration",
    noBoxes: "No approved boxes yet.",
    lastContact: "last contact",
    never: "never",
    ago: "",
    uncalibrated: "uncalibrated",
    calibrated: "calibrated",
    temperature: "Temperature",
    voltage: "Voltage",
    range: "Range",
    export: "Export",
    calibrations: "Calibrations",
    noCalibrations: "No calibration; the pH follows the nominal curve of the Atlas board.",
    time: "Time",
    probe: "Probe",
    slope: "Slope",
    offset: "Offset at pH 7",
    points: "Points",
    noData: "No readings in this range.",
    boxes: "Boxes",
    status: "Status",
    name: "Name",
    location: "Location",
    intervals: "Intervals (s)",
    approve: "Approve",
    block: "Block",
    save: "Save",
    pending: "pending",
    approved: "approved",
    blocked: "blocked",
    addCalibration: "Add calibration",
    box: "Box",
    bufferPh: "Buffer pH",
    useCurrent: "use current value",
    saveCalibration: "Save calibration",
    saved: "Saved.",
    calHint: "Two or three buffers; take the value only once it has settled (below 1 mV per minute).",
  },
};

function storedLang() {
  try { return localStorage.getItem("lang"); } catch { return null; }
}

let lang = storedLang() || (navigator.language.startsWith("de") ? "de" : "en");
const t = (key) => TEXT[lang][key] ?? key;

function applyText() {
  document.documentElement.lang = lang;
  document.querySelectorAll("[data-t]").forEach((el) => { el.textContent = t(el.dataset.t); });
  const toggle = document.getElementById("lang");
  if (toggle) toggle.textContent = lang === "de" ? "EN" : "DE";
}

function initPage(onLangChange) {
  applyText();
  document.getElementById("lang").addEventListener("click", () => {
    lang = lang === "de" ? "en" : "de";
    try { localStorage.setItem("lang", lang); } catch { /* private mode */ }
    applyText();
    onLangChange?.();
  });
}

const fmt = {
  ph: (v) => (v == null ? "–" : v.toFixed(2)),
  temp: (v) => (v == null ? "–" : `${v.toFixed(1)} °C`),
  mv: (v) => (v == null ? "–" : `${v.toFixed(1)} mV`),
  time: (iso) => new Date(iso).toLocaleString(lang === "de" ? "de-DE" : "en-GB"),
  ago(iso) {
    if (!iso) return t("never");
    const s = Math.max(0, Math.round((Date.now() - new Date(iso)) / 1000));
    const span = s < 90 ? `${s} s` : s < 5400 ? `${Math.round(s / 60)} min` : `${Math.round(s / 3600)} h`;
    return lang === "de" ? `${t("ago")} ${span}` : `${span} ago`;
  },
};

// Green while uploads arrive on time, yellow when overdue, grey when never seen.
function contactState(box) {
  if (!box.last_seen) return "";
  const age = (Date.now() - new Date(box.last_seen)) / 1000;
  return age < 3 * box.upload_interval_s ? "ok" : "warn";
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) throw new Error(`${response.status} ${await response.text()}`);
  return response.json();
}

function live(handlers) {
  const source = new EventSource("/api/v1/stream");
  for (const [event, handler] of Object.entries(handlers)) {
    source.addEventListener(event, (e) => handler(JSON.parse(e.data)));
  }
  return source;
}

const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => `&#${c.charCodeAt(0)};`);

// A small line chart on a canvas: points are [Date, value]; gaps longer than maxGap ms break the line.
// minSpan keeps sensor noise from filling the whole height when the values barely change.
function drawChart(canvas, points, { label = "", digits = 2, maxGap = Infinity, minSpan = 0 } = {}) {
  const dpr = window.devicePixelRatio || 1;
  const w = canvas.clientWidth, h = canvas.clientHeight;
  canvas.width = w * dpr;
  canvas.height = h * dpr;
  const ctx = canvas.getContext("2d");
  ctx.scale(dpr, dpr);
  ctx.clearRect(0, 0, w, h);
  const css = getComputedStyle(document.documentElement);
  const muted = css.getPropertyValue("--muted"), line = css.getPropertyValue("--line");
  ctx.font = "12px system-ui, sans-serif";
  ctx.fillStyle = muted;
  if (points.length < 2) {
    ctx.fillText(t("noData"), 10, 20);
    return;
  }
  const pad = { l: 52, r: 12, t: 18, b: 24 };
  const xs = points.map((p) => +p[0]), ys = points.map((p) => p[1]);
  const x0 = Math.min(...xs), x1 = Math.max(...xs);
  let y0 = Math.min(...ys), y1 = Math.max(...ys);
  const span = Math.max(minSpan, 1e-6);
  if (y1 - y0 < span) {
    const mid = (y0 + y1) / 2;
    y0 = mid - span / 2;
    y1 = mid + span / 2;
  }
  const margin = (y1 - y0) * 0.08;
  y0 -= margin; y1 += margin;
  const X = (x) => pad.l + ((x - x0) / (x1 - x0 || 1)) * (w - pad.l - pad.r);
  const Y = (y) => h - pad.b - ((y - y0) / (y1 - y0)) * (h - pad.t - pad.b);

  ctx.strokeStyle = line;
  ctx.lineWidth = 1;
  for (let i = 0; i <= 4; i++) {
    const v = y0 + ((y1 - y0) * i) / 4, y = Y(v);
    ctx.beginPath(); ctx.moveTo(pad.l, y); ctx.lineTo(w - pad.r, y); ctx.stroke();
    ctx.fillText(v.toFixed(digits), 4, y + 4);
  }
  const locale = lang === "de" ? "de-DE" : "en-GB";
  const long = x1 - x0 > 36 * 3600e3, short = x1 - x0 < 15 * 60e3;
  for (let i = 0; i <= 4; i++) {
    const x = x0 + ((x1 - x0) * i) / 4, d = new Date(x);
    const text = long ? d.toLocaleDateString(locale, { day: "2-digit", month: "2-digit" })
      : d.toLocaleTimeString(locale, { hour: "2-digit", minute: "2-digit", ...(short && { second: "2-digit" }) });
    ctx.fillText(text, Math.min(X(x) - 14, w - pad.r - 34), h - 6);
  }
  ctx.fillText(label, pad.l, 12);

  ctx.strokeStyle = css.getPropertyValue("--accent");
  ctx.lineWidth = 1.6;
  ctx.beginPath();
  points.forEach(([d, v], i) => {
    const gap = i > 0 && +d - +points[i - 1][0] > maxGap;
    if (i === 0 || gap) ctx.moveTo(X(+d), Y(v)); else ctx.lineTo(X(+d), Y(v));
  });
  ctx.stroke();
}
