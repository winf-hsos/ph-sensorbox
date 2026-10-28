// Shared helpers for the dashboard pages: texts, number formats, theme, pH scale, API, live stream.

const TEXT = {
  de: {
    brand: "pH-Sensorbox",
    overview: "Übersicht",
    admin: "Verwaltung",
    theme: "Hell oder dunkel",
    langSwitch: "Switch to English",
    backToOverview: "Übersicht",
    ledeNone: "Noch keine Box ist freigegeben.",
    ledeAll: (n) => (n === 1 ? "Eine aktive Box." : `${n} aktive Boxen.`),
    ledeSome: (n, live) => `${n} ${n === 1 ? "Box" : "Boxen"}, ${live === 0 ? "keine" : live} davon aktiv.`,
    emptyTitle: "Hier erscheinen die Messboxen, sobald sie freigegeben sind.",
    emptyBody: "Eine neue Box meldet sich von selbst und wartet in der Verwaltung auf die Freigabe.",
    emptyLink: "Zur Verwaltung",
    live: "misst",
    late: "verzögert",
    none: "keine Daten",
    lastReading: "letzte Messung",
    never: "noch keine",
    ago: (s) => `vor ${s}`,
    calibrated: "kalibriert",
    uncalibrated: "unkalibriert",
    temperature: "Temperatur",
    voltage: "Spannung",
    calibration: "Kalibrierung",
    calibratedOn: (d) => `am ${d}`,
    phScale: (v) => `pH ${v} auf der Skala von 0 bis 14`,
    range: "Zeitraum",
    resetZoom: "Ausschnitt zurücksetzen",
    zoomHint: "Ziehen vergrößert einen Ausschnitt, Doppelklick zeigt wieder alles.",
    days7: "7 Tage",
    phChart: "pH-Wert",
    tempChart: "Temperatur in °C",
    noData: "In diesem Zeitraum gibt es keine Messwerte.",
    valuesTable: "Messwerte als Tabelle",
    time: "Zeit",
    samples: "Proben",
    calibrations: "Kalibrierungen",
    noCalibrations: "Noch keine Kalibrierung. Der pH-Wert folgt der Nennkennlinie der Atlas-Platine und ist deshalb nur ein Richtwert.",
    probe: "Sonde",
    points: "Pufferpunkte",
    slope: "Steilheit",
    offset: "Spannung bei pH 7",
    notFound: "Diese Box gibt es nicht oder sie ist noch nicht freigegeben.",
    pendingTitle: "Neue Boxen",
    pendingHint: "Vergleiche die Kennung mit der Anzeige an der Box, bevor du sie freigibst.",
    boxes: "Alle Boxen",
    status: "Status",
    name: "Name",
    location: "Ort",
    sampleInterval: "Messintervall (s)",
    uploadInterval: "Sendeintervall (s)",
    approve: "Freigeben",
    block: "Sperren",
    unblock: "Entsperren",
    save: "Speichern",
    saved: "Gespeichert.",
    pending: "wartet auf Freigabe",
    approved: "freigegeben",
    blocked: "gesperrt",
    addCalibration: "Kalibrierung eintragen",
    calHint: "Zwei oder drei Puffer. Übernimm einen Wert erst, wenn er sich kaum noch ändert, also weniger als 1 mV pro Minute. Jeder Wert wird sofort als Zwischenstand gespeichert, du kannst die Seite also zum Wechseln der Lösung verlassen.",
    draftSaved: (time) => `Zwischenstand gespeichert um ${time}.`,
    draftLoaded: (time) => `Zwischenstand vom ${time} geladen.`,
    taken: (time) => `übernommen ${time}`,
    startOver: "Neu beginnen",
    needTwo: "Es fehlen noch Werte: Mindestens zwei Puffer brauchen Spannung und Temperatur.",
    lastCalibration: "Letzte Kalibrierung",
    notCalibrated: "Diese Box ist noch nicht kalibriert.",
    allCalibrations: "Alle Kalibrierungen dieser Box",
    calibratedAt: "Kalibriert",
    box: "Box",
    bufferPh: "Puffer-pH",
    useCurrent: "Aktuellen Wert übernehmen",
    saveCalibration: "Kalibrierung speichern",
    calSaved: (s, o) => `Kalibrierung gespeichert: Steilheit ${s}, Spannung bei pH 7 ${o}.`,
    noApproved: "Es gibt noch keine freigegebene Box.",
    loginTitle: "Anmelden zur Verwaltung",
    loginHint: "Die Verwaltung braucht das Verwaltungspasswort. Ansehen und Herunterladen der Messwerte geht ohne Anmeldung.",
    password: "Passwort",
    login: "Anmelden",
    wrongPassword: "Das Passwort stimmt nicht.",
    logout: "Abmelden",
  },
  en: {
    brand: "pH Sensor Box",
    overview: "Overview",
    admin: "Administration",
    theme: "Light or dark",
    langSwitch: "Auf Deutsch umschalten",
    backToOverview: "Overview",
    ledeNone: "No box has been approved yet.",
    ledeAll: (n) => (n === 1 ? "One active box." : `${n} active boxes.`),
    ledeSome: (n, live) => (n === 1 ? "1 box, none active." : `${n} boxes, ${live === 0 ? "none" : live} of them active.`),
    emptyTitle: "Measuring boxes appear here once they are approved.",
    emptyBody: "A new box registers by itself and waits for approval in the administration.",
    emptyLink: "Go to administration",
    live: "measuring",
    late: "delayed",
    none: "no data",
    lastReading: "last reading",
    never: "none yet",
    ago: (s) => `${s} ago`,
    calibrated: "calibrated",
    uncalibrated: "uncalibrated",
    temperature: "Temperature",
    voltage: "Voltage",
    calibration: "Calibration",
    calibratedOn: (d) => `on ${d}`,
    phScale: (v) => `pH ${v} on the scale from 0 to 14`,
    range: "Range",
    resetZoom: "Reset zoom",
    zoomHint: "Drag to zoom into a section, double-click to see everything again.",
    days7: "7 days",
    phChart: "pH value",
    tempChart: "Temperature in °C",
    noData: "There are no readings in this range.",
    valuesTable: "Readings as a table",
    time: "Time",
    samples: "Samples",
    calibrations: "Calibrations",
    noCalibrations: "No calibration yet. The pH follows the nominal curve of the Atlas board and is only a rough value.",
    probe: "Probe",
    points: "Buffer points",
    slope: "Slope",
    offset: "Voltage at pH 7",
    notFound: "This box does not exist or has not been approved yet.",
    pendingTitle: "New boxes",
    pendingHint: "Compare the id with the one shown on the box before you approve it.",
    boxes: "All boxes",
    status: "Status",
    name: "Name",
    location: "Location",
    sampleInterval: "Sample interval (s)",
    uploadInterval: "Upload interval (s)",
    approve: "Approve",
    block: "Block",
    unblock: "Unblock",
    save: "Save",
    saved: "Saved.",
    pending: "waiting for approval",
    approved: "approved",
    blocked: "blocked",
    addCalibration: "Add a calibration",
    calHint: "Two or three buffers. Take a value only once it has settled, at less than 1 mV per minute. Every value is saved as progress right away, so you can leave the page while changing the solution.",
    draftSaved: (time) => `Progress saved at ${time}.`,
    draftLoaded: (time) => `Progress from ${time} loaded.`,
    taken: (time) => `taken ${time}`,
    startOver: "Start over",
    needTwo: "Values are missing: at least two buffers need a voltage and a temperature.",
    lastCalibration: "Last calibration",
    notCalibrated: "This box has not been calibrated yet.",
    allCalibrations: "All calibrations of this box",
    calibratedAt: "Calibrated",
    box: "Box",
    bufferPh: "Buffer pH",
    useCurrent: "Use current value",
    saveCalibration: "Save calibration",
    calSaved: (s, o) => `Calibration saved: slope ${s}, voltage at pH 7 ${o}.`,
    noApproved: "No box has been approved yet.",
    loginTitle: "Log in to the administration",
    loginHint: "The administration needs the admin password. Viewing and downloading readings works without logging in.",
    password: "Password",
    login: "Log in",
    wrongPassword: "The password is not correct.",
    logout: "Log out",
  },
};

function stored(key) {
  try { return localStorage.getItem(key); } catch { return null; }
}

function store(key, value) {
  try { localStorage.setItem(key, value); } catch { /* private mode: keep the default */ }
}

let lang = stored("lang") || (navigator.language.startsWith("de") ? "de" : "en");
const t = (key, ...args) => {
  const value = TEXT[lang][key] ?? key;
  return typeof value === "function" ? value(...args) : value;
};
const locale = () => (lang === "de" ? "de-DE" : "en-GB");

// ---------- numbers and times ----------

const fmt = {
  number: (v, digits) => (v == null ? "–" : new Intl.NumberFormat(locale(), {
    minimumFractionDigits: digits, maximumFractionDigits: digits }).format(v)),
  ph: (v) => fmt.number(v, 2),
  temp: (v) => (v == null ? "–" : `${fmt.number(v, 1)} °C`),
  mv: (v) => (v == null ? "–" : `${fmt.number(v, 1)} mV`),
  dateTime: (iso) => new Date(iso).toLocaleString(locale(), {
    day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit", second: "2-digit" }),
  date: (iso) => new Date(iso).toLocaleDateString(locale(), { day: "numeric", month: "long", year: "numeric" }),
  dateShortTime: (iso) => new Date(iso).toLocaleString(locale(), {
    day: "numeric", month: "long", year: "numeric", hour: "2-digit", minute: "2-digit" }),
  time: (iso) => new Date(iso).toLocaleTimeString(locale(), { hour: "2-digit", minute: "2-digit", second: "2-digit" }),
  ago(iso) {
    if (!iso) return t("never");
    const s = Math.max(0, Math.round((Date.now() - new Date(iso)) / 1000));
    const span = s < 90 ? `${s} s` : s < 5400 ? `${Math.round(s / 60)} min` : s < 172800 ? `${Math.round(s / 3600)} h` : `${Math.round(s / 86400)} d`;
    return t("ago", span);
  },
};

// live: uploads arrive on time; late: overdue; none: never seen
function contactState(box) {
  if (!box.last_seen) return "none";
  const age = (Date.now() - new Date(box.last_seen)) / 1000;
  return age < 3 * box.upload_interval_s ? "live" : "late";
}

// ---------- DOM ----------

function h(tag, attrs = {}, ...children) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v == null || v === false) continue;
    if (k === "class") el.className = v;
    else if (k === "style") el.style.cssText = v;
    else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else el.setAttribute(k, v === true ? "" : v);
  }
  for (const child of children.flat()) {
    if (child == null || child === false) continue;
    el.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return el;
}

// view-transition-name must be an identifier; box ids are [A-Za-z0-9_-]
const vtName = (part, id) => `${part}-b${id}`;

function scale(ph, { ticks = [0, 7, 14] } = {}) {
  const el = h("div", { class: "scale", role: "img" },
    h("div", { class: "scale-bar" }),
    h("div", { class: "scale-needle" }),
    h("div", { class: "scale-ticks" }, ticks.map((v) => h("span", {}, v))));
  setScale(el, ph);
  return el;
}

function setScale(el, ph) {
  if (ph == null || Number.isNaN(ph)) {
    el.setAttribute("data-empty", "");
    el.setAttribute("aria-label", "pH –");
    return;
  }
  el.removeAttribute("data-empty");
  const pos = Math.min(14, Math.max(0, ph)) / 14 * 100;
  el.style.setProperty("--pos", `${pos}%`);
  el.setAttribute("aria-label", t("phScale", fmt.ph(ph)));
}

function readout(el, ph) {
  el.replaceChildren(fmt.ph(ph), h("small", {}, "pH"));
}

function flash(el) {
  el.classList.add("fresh");
  setTimeout(() => el.classList.remove("fresh"), 700);
}

// ---------- page frame ----------

const ICON_MOON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5Z"/></svg>';
const ICON_SUN = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><circle cx="12" cy="12" r="4"/><path d="M12 2.5v2M12 19.5v2M2.5 12h2M19.5 12h2M5.3 5.3l1.4 1.4M17.3 17.3l1.4 1.4M5.3 18.7l1.4-1.4M17.3 6.7l1.4-1.4"/></svg>';

function currentTheme() {
  const set = document.documentElement.dataset.theme;
  if (set) return set;
  return matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function applyTheme() {
  const saved = stored("theme");
  if (saved) document.documentElement.dataset.theme = saved;
}

function header(active) {
  const themeButton = h("button", { class: "icon-button", type: "button", "aria-label": t("theme"), title: t("theme") });
  themeButton.innerHTML = currentTheme() === "dark" ? ICON_SUN : ICON_MOON;
  themeButton.addEventListener("click", () => {
    const next = currentTheme() === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    store("theme", next);
    themeButton.innerHTML = next === "dark" ? ICON_SUN : ICON_MOON;
    window.dispatchEvent(new Event("themechange"));
  });
  const langButton = h("button", { class: "icon-button", type: "button", "aria-label": t("langSwitch"), title: t("langSwitch") },
    lang === "de" ? "EN" : "DE");
  langButton.addEventListener("click", () => {
    store("lang", lang === "de" ? "en" : "de");
    location.reload();
  });
  return h("header", { class: "wrap topbar" },
    h("a", { class: "brand", href: "/" }, h("span", { class: "brand-mark", "aria-hidden": "true" }), h("span", {}, t("brand"))),
    h("nav", { class: "nav" },
      h("a", { href: "/", "aria-current": active === "overview" ? "page" : null }, t("overview")),
      h("a", { href: "/admin", "aria-current": active === "admin" ? "page" : null }, t("admin"))),
    h("div", { class: "tools" }, langButton, themeButton));
}

function initPage(active) {
  applyTheme();
  document.documentElement.lang = lang;
  document.body.prepend(header(active));
}

// ---------- API and live stream ----------

async function api(path, options = {}) {
  const response = await fetch(path, { headers: { "Content-Type": "application/json" }, ...options });
  if (!response.ok) {
    const error = new Error(`${response.status} ${await response.text()}`);
    error.status = response.status;
    throw error;
  }
  return response.json();
}

// EventSource reconnects by itself; onResync runs after every reconnect so that
// readings sent while the connection was down are fetched again.
function live(handlers, onResync) {
  const source = new EventSource("/api/v1/stream");
  let opened = false;
  source.addEventListener("open", () => {
    if (opened) onResync?.();
    opened = true;
  });
  for (const [event, handler] of Object.entries(handlers)) {
    source.addEventListener(event, (e) => handler(JSON.parse(e.data)));
  }
  return source;
}
