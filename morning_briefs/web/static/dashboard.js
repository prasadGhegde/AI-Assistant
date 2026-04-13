const data = window.MORNING_BRIEF || {};
const params = new URLSearchParams(window.location.search);
const presentationMode = params.get("presentation") === "1";
const autoPlay = params.get("autoplay") === "1";
const externalAudio = params.get("external_audio") === "1";

const categoryLabels = {
  geopolitics: "Geopolitics",
  technology_ai: "Technology and AI",
  markets: "Stock market",
};

const phaseOrder = [
  ["greeting", "Greeting"],
  ["weather", "Weather"],
  ["geopolitics", "Geopolitics"],
  ["technology_ai", "Technology"],
  ["markets", "Markets"],
  ["closing_question", "Close"],
];

let lastSectionKey = "";
let lastTopicKey = "";
let currentCategory = "";
let presentationStartedAt = null;
let closingCountdownStarted = false;
let countdownTimer = null;
let followupComplete = false;
let sessionComplete = false;
let playbackStarting = false;
let musicFadeFrame = null;
let audioSyncFrame = null;
let worldClockTimer = null;
let finalCloseInProgress = false;

const VISUAL_SYNC_LEAD_SECONDS = 0.42;

const playButton = document.getElementById("playButton");
const audioStatus = document.getElementById("audioStatus");
const musicStatus = document.getElementById("musicStatus");
const briefAudio = document.getElementById("briefAudio");
const musicAudio = document.getElementById("musicAudio");
const closingAudio = document.getElementById("closingAudio");

if (presentationMode) {
  document.body.classList.add("presentation-active");
}

function section(name) {
  return (data.sections && data.sections[name]) || [];
}

function intel() {
  return data.intel || {};
}

function text(value, fallback = "") {
  return value || fallback;
}

function escapeHtml(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function escapeAttr(value) {
  return escapeHtml(value).replaceAll("'", "&#39;");
}

function link(label, url) {
  if (!url) {
    return escapeHtml(label);
  }
  return `<a href="${escapeAttr(url)}" target="_blank" rel="noreferrer">${escapeHtml(label)}</a>`;
}

function cueSections() {
  return ((data.presentation_timeline || {}).sections || []);
}

function cueTopics() {
  return ((data.presentation_timeline || {}).topics || []);
}

function totalTimelineSeconds() {
  return Math.max((data.presentation_timeline || {}).total_seconds || 1, 1);
}

function audioToTimelineSeconds(audio) {
  if (audio && Number.isFinite(audio.duration) && audio.duration > 0) {
    return (audio.currentTime / audio.duration) * totalTimelineSeconds();
  }
  return audio ? audio.currentTime : 0;
}

function audioProgressRatio(audio) {
  if (audio && Number.isFinite(audio.duration) && audio.duration > 0) {
    return Math.min(Math.max(audio.currentTime / audio.duration, 0), 1);
  }
  return null;
}

function screenForCue(key) {
  if (["geopolitics", "technology_ai", "markets"].includes(key)) {
    return "news";
  }
  return key;
}

function noteForTopic(topic) {
  if (!topic) {
    return null;
  }
  return section(topic.section)[topic.index] || null;
}

function compactDate(value) {
  if (!value) {
    return "";
  }
  try {
    return new Date(value).toLocaleString([], {month: "short", day: "numeric"});
  } catch {
    return value;
  }
}

function firstSentence(value, fallback) {
  const raw = text(value, "").trim();
  if (!raw) {
    return fallback;
  }
  const normalized = raw.replace(/^#+\s*/g, "").replace(/\s+/g, " ").trim();
  const match = normalized.match(/^(.+?[.!?])(?:\s|$)/);
  return (match ? match[1] : normalized).trim();
}

function weatherIconForCode(code) {
  if (code == null) return "WX";
  const c = Number(code);
  if (c === 0) return "CLR";
  if (c <= 2) return "PART";
  if (c <= 3) return "CLD";
  if (c <= 49) return "FOG";
  if (c <= 69) return "RAIN";
  if (c <= 84) return "SHWR";
  if (c <= 94) return "STORM";
  return "WX";
}

function runBootSequence() {
  const items = [
    {label: "SYS INIT", cls: "ok"},
    {label: "AUDIO ROUTE", cls: "ok"},
    {label: "INTEL FEED", cls: "ok"},
    {label: "BRIEFING LOCK", cls: "ok"},
  ];
  const container = document.getElementById("bootStatusItems");
  if (!container) return;
  items.forEach((item, idx) => {
    window.setTimeout(() => {
      const span = document.createElement("span");
      span.className = `boot-status-item ${item.cls}`;
      span.textContent = `▸ ${item.label}`;
      container.appendChild(span);
    }, idx * 260);
  });
}

function renderPhaseRail() {
  const rail = document.getElementById("phaseRail");
  rail.innerHTML = phaseOrder.map(([key, label], index) => `
    <div class="phase-item" data-phase="${escapeAttr(key)}">
      <div class="phase-row">
        <span>${String(index + 1).padStart(2, "0")}</span>
        <strong>${escapeHtml(label)}</strong>
        <small class="phase-state">Queued</small>
      </div>
      <div class="phase-fill"><i></i></div>
    </div>
  `).join("");
}

function renderWeather() {
  const w = data.weather || {};
  document.querySelectorAll("#screen-weather .intel-card").forEach((node) => {
    node.classList.toggle("is-mock-data", Boolean(w.mock));
  });
  const tempEl = document.getElementById("weatherTemp");
  const feelsEl = document.getElementById("weatherFeels");
  const iconEl = document.getElementById("weatherIcon");
  const condEl = document.getElementById("weatherCond");
  const windEl = document.getElementById("weatherWind");
  const precipEl = document.getElementById("weatherPrecip");
  const cloudEl = document.getElementById("weatherCloud");
  const briefEl = document.getElementById("weatherBriefText");
  const locEl = document.getElementById("weatherLocation");

  if (locEl) locEl.textContent = w.location_name || "—";
  if (tempEl) {
    tempEl.textContent = w.temperature != null
      ? `${Math.round(w.temperature)}${w.temperature_unit || "°"}`
      : "—";
  }
  if (feelsEl) {
    feelsEl.textContent = w.apparent_temperature != null
      ? `feels ${Math.round(w.apparent_temperature)}${w.temperature_unit || "°"}`
      : "";
  }
  if (iconEl) iconEl.textContent = weatherIconForCode(w.weather_code);
  if (condEl) condEl.textContent = w.conditions || "—";
  if (windEl) windEl.textContent = w.wind_speed != null ? `${Math.round(w.wind_speed)} ${w.wind_unit || "km/h"}` : "—";
  if (precipEl) precipEl.textContent = w.precipitation_probability != null ? `${w.precipitation_probability}%` : "—";
  if (cloudEl) cloudEl.textContent = w.cloud_cover != null ? `${w.cloud_cover}%` : "—";
  if (briefEl) briefEl.textContent = w.advisory || "No field advisory at this time.";

  const carryEl = document.getElementById("weatherCarry");
  if (carryEl) {
    const tags = [...(w.carry || []), ...(w.wear || [])].filter(Boolean).slice(0, 3);
    carryEl.innerHTML = tags.length
      ? tags.map((t) => `<span class="weather-carry-tag">${escapeHtml(t)}</span>`).join("")
      : `<span class="weather-carry-tag">standard kit</span>`;
  }

  const timelineEl = document.getElementById("weatherTimeline");
  if (timelineEl) {
    const hourly = w.hourly || [];
    timelineEl.innerHTML = hourly.slice(0, 8).map((row) => `
      <article class="intel-chip-card">
        <span>${escapeHtml(row.time || "--")}</span>
        <strong>${escapeHtml(row.temperature == null ? "--" : `${Math.round(row.temperature)}${w.temperature_unit || "°"}`)}</strong>
        <small>${escapeHtml(row.precipitation_probability == null ? "" : `${row.precipitation_probability}% precip`)}</small>
      </article>
    `).join("") || `<article class="intel-chip-card"><span>timeline</span><strong>Unavailable</strong></article>`;
  }

  const alertsEl = document.getElementById("weatherAlerts");
  if (alertsEl) {
    const alerts = w.alerts || [];
    alertsEl.innerHTML = alerts.map((item) => `
      <article class="intel-chip-card"><span>alert</span><strong>${escapeHtml(item)}</strong></article>
    `).join("") || `<article class="intel-chip-card"><span>alerts</span><strong>No severe alerts</strong></article>`;
  }
}

function renderWorldClock() {
  function update() {
    const now = new Date();
    const options = {hour: "2-digit", minute: "2-digit", hour12: false};
    const india = now.toLocaleTimeString("en-GB", {...options, timeZone: "Asia/Kolkata"});
    const us = now.toLocaleTimeString("en-US", {...options, timeZone: "America/New_York"});
    const china = now.toLocaleTimeString("en-GB", {...options, timeZone: "Asia/Shanghai"});
    const indiaEl = document.getElementById("clockIndia");
    const usEl = document.getElementById("clockUS");
    const chinaEl = document.getElementById("clockChina");
    if (indiaEl) indiaEl.textContent = india;
    if (usEl) usEl.textContent = us;
    if (chinaEl) chinaEl.textContent = china;
  }
  update();
  if (worldClockTimer) {
    clearInterval(worldClockTimer);
  }
  worldClockTimer = window.setInterval(update, 30000);
}

function cleanImplication(value) {
  return text(value, "Watch the follow-through, not just the headline.")
    .replace(/^why (it|this) matters( today)?\s*:\s*/i, "")
    .replace(/^this is important because\s*/i, "");
}

function isMockModule(module) {
  return Boolean(module && module.mock);
}

function cardShell({title, kicker, status = "", size = "standard", body = "", topicKey = "", extraClass = "", cardId = "", mock = false}) {
  const topicAttr = topicKey ? ` data-topic-key="${escapeAttr(topicKey)}"` : "";
  const idAttr = cardId ? ` data-card-id="${escapeAttr(cardId)}"` : "";
  const statusHtml = status ? `<span class="card-pill">${escapeHtml(status)}</span>` : "";
  const mockClass = mock ? " is-mock-data" : "";
  return `
    <article class="intel-card dashboard-card card-${escapeAttr(size)} ${escapeAttr(extraClass)}${mockClass}"${topicAttr}${idAttr}>
      <header class="card-head">
        <span class="card-kicker">${escapeHtml(kicker || "module")}</span>
        ${statusHtml}
      </header>
      ${title ? `<h3 class="card-title">${escapeHtml(title)}</h3>` : ""}
      ${body}
    </article>
  `;
}

function topicKey(category, index) {
  return `${category}-${index}`;
}

function unavailable(label, detail = "Provider unavailable for this run.") {
  return `
    <div class="module-empty">
      <span>Unavailable</span>
      <strong>${escapeHtml(label)}</strong>
      <small>${escapeHtml(detail)}</small>
    </div>
  `;
}

function displayValue(value) {
  if (value == null || value === "") {
    return "--";
  }
  if (typeof value === "number" && Number.isFinite(value)) {
    const abs = Math.abs(value);
    const digits = abs >= 100 ? 2 : abs >= 1 ? 3 : 5;
    return new Intl.NumberFormat(undefined, {maximumFractionDigits: digits}).format(value);
  }
  return String(value);
}

function detailValue(row, detailField) {
  const value = row[detailField] || row.unit || row.change || row.updated_at;
  if (!value) {
    return "";
  }
  if (detailField === "time" || detailField === "updated_at") {
    return compactDate(value) || String(value);
  }
  return String(value);
}

function storyBriefCard(category, title, kicker) {
  const note = section(category)[0];
  if (!note) {
    return cardShell({
      title,
      kicker,
      size: "wide",
      status: "gap",
      extraClass: "board-story is-unavailable",
      body: unavailable("No primary story", "The source pipeline did not return a strong lead item."),
    });
  }
  const signal = firstSentence(note.note || note.excerpt, "Signal is resolving.");
  const implication = firstSentence(cleanImplication(note.why_it_matters || note.note), "Watch the follow-through, not just the headline.");
  return cardShell({
    title,
    kicker,
    size: "wide",
    status: "lead",
    topicKey: topicKey(category, 0),
    extraClass: "board-story board-story-lead",
    body: `
      <div class="story-source-row">
        <span>${escapeHtml(note.source_name || "source")}</span>
        <span>${escapeHtml(compactDate(note.published_at) || "live")}</span>
      </div>
      <h4 class="story-title">${escapeHtml(note.headline || "Untitled signal")}</h4>
      <div class="signal-pair">
        <article><span>Signal</span><strong>${escapeHtml(signal)}</strong></article>
        <article><span>Implication</span><strong>${escapeHtml(implication)}</strong></article>
      </div>
    `,
  });
}

function storyCards(category, startIndex = 1, limit = 2) {
  return section(category).slice(startIndex, startIndex + limit).map((note, offset) => {
    const index = startIndex + offset;
    return cardShell({
      title: `Signal ${String(index + 1).padStart(2, "0")}`,
      kicker: note.source_name || categoryLabels[category] || "source",
      size: "standard",
      status: compactDate(note.published_at) || "live",
      topicKey: topicKey(category, index),
      extraClass: "board-story board-story-compact",
      body: `
        <h4 class="story-title story-title-small">${escapeHtml(note.headline || "Untitled signal")}</h4>
        <p class="story-note">${escapeHtml(note.note || note.excerpt || "Signal still resolving.")}</p>
      `,
    });
  }).join("");
}

function miniRows(rows, options = {}) {
  const labelField = options.labelField || "name";
  const valueField = options.valueField || "value";
  const detailField = options.detailField || "detail";
  const rowsHtml = (rows || []).map((row) => `
    <article class="intel-chip-card">
      <span>${escapeHtml(row[labelField] || row.region || row.source || row.symbol || row.pair || row.type || "item")}</span>
      <strong>${escapeHtml(displayValue(row[valueField] ?? row.label ?? row.headline ?? row.display ?? row.rate ?? row.value))}</strong>
      ${detailValue(row, detailField) ? `<small>${escapeHtml(detailValue(row, detailField))}</small>` : ""}
    </article>
  `).join("");
  return rowsHtml || unavailable(options.emptyLabel || "No live rows", options.emptyDetail || "The provider returned no usable values.");
}

function barRows(rows, labelField = "name", valueField = "score") {
  const numeric = (rows || []).map((row) => Number(row[valueField] ?? row.intensity ?? row.events ?? 0)).filter(Number.isFinite);
  const maxValue = Math.max(...numeric, 1);
  const html = (rows || []).map((row) => {
    const value = Number(row[valueField] ?? row.intensity ?? row.events ?? 0);
    const normalized = maxValue > 100 ? value / maxValue * 100 : maxValue <= 10 ? value / maxValue * 100 : value;
    const width = Math.min(Math.max(normalized, 0), 100);
    return `
      <div class="bar-row">
        <span>${escapeHtml(row[labelField] || "item")}</span>
        <div class="bar-track"><i style="width:${width}%"></i></div>
        <strong>${escapeHtml(displayValue(row[valueField] ?? row.intensity))}</strong>
      </div>
    `;
  }).join("");
  return html || unavailable("No ranked signal", "Not enough accepted items to calculate this module.");
}

function topPulseCard({title, kicker, status = "live", value, detail, extraClass = "", mock = false}) {
  return cardShell({
    title,
    kicker,
    status,
    size: "metric-card",
    extraClass: `gauge-card top-pulse-card ${extraClass}`,
    mock,
    body: `<div class="gauge-value">${escapeHtml(displayValue(value))}</div><div class="gauge-label">${escapeHtml(detail || "")}</div>`,
  });
}

function metricsByLabel(metrics) {
  const out = {};
  (metrics || []).forEach((metric) => {
    out[String(metric.label || "").toLowerCase()] = metric;
  });
  return out;
}

function sourceUtilityCard(category) {
  const links = section(category).slice(0, 4);
  const body = links.map((note) => `
    <a class="source-tiny" href="${escapeAttr(note.url || "#")}" target="_blank" rel="noreferrer">
      <span>${escapeHtml(note.source_name || "source")}</span>
      <strong>${escapeHtml(note.headline || "Untitled")}</strong>
    </a>
  `).join("") || unavailable("No source links", "No source URLs were included in this section.");
  return cardShell({
    title: "",
    kicker: "Source utility",
    status: `${links.length} links`,
    size: "compact",
    extraClass: "source-utility-card",
    body: `<div class="source-tiny-stack">${body}</div>`,
  });
}

function sectionHeadlineStream(category, rows, title, mock = false) {
  const used = new Set(section(category).slice(0, 3).map((note) => String(note.headline || "").toLowerCase()));
  const uniqueRows = (rows || []).filter((row) => {
    const key = String(row.headline || "").toLowerCase();
    if (!key || used.has(key)) return false;
    used.add(key);
    return true;
  }).slice(0, 5);
  const body = uniqueRows.map((row) => `
    <article class="stream-row">
      <span>${escapeHtml(row.source || "source")}</span>
      <strong>${escapeHtml(row.headline || "Untitled")}</strong>
    </article>
  `).join("") || unavailable("No extra headlines", "Main story cards already cover the accepted items.");
  return cardShell({title, kicker: "headline stream", status: mock ? "mock" : "", size: "list-stream", mock, body: `<div class="intel-stream">${body}</div>`});
}

function sectorHeatmapCard() {
  const moduleData = (((intel().markets || {}).sector_heatmap) || {});
  const items = moduleData.items || [];
  const body = items.length ? `
    <div class="sector-grid dense-sector-grid">
      ${items.slice(0, 9).map((row) => {
        const intensity = Number(row.intensity || 0);
        let cls = "heat-flat";
        if (row.band === "high") cls = "heat-pos-strong";
        else if (row.band === "medium") cls = "heat-pos";
        return `<div class="sector-cell ${cls}">
          <div class="sector-ticker">${escapeHtml(row.name || "Sector")}</div>
          <span class="sector-pct pos">${escapeHtml(String(row.hits || 0))}</span>
          <span class="sector-name">${escapeHtml(String(intensity))}%</span>
        </div>`;
      }).join("")}
    </div>
  ` : unavailable("Sector heatmap", "No market-sector signals in accepted stories.");
  return cardShell({title: "Sector heatmap", kicker: "equity sectors", status: isMockModule(moduleData) ? "mock" : "derived", size: "chart-card", mock: isMockModule(moduleData), body});
}

function buildMarketsBoard() {
  const markets = intel().markets || {};
  const cryptoModule = markets.crypto || {};
  const fxModule = markets.fx || {};
  const energyModule = markets.energy || {};
  const metalsModule = markets.metals_materials || {};
  const macroModule = markets.macro_movers || {};
  const headlinesModule = markets.headlines || {};
  const crypto = (cryptoModule.items || []).map((row) => ({
    symbol: row.symbol,
    value: row.price_usd == null ? "--" : `$${Number(row.price_usd).toLocaleString()}`,
    detail: row.change_24h == null ? "" : `${row.change_24h >= 0 ? "+" : ""}${row.change_24h.toFixed(2)}% 24h`,
  }));
  const metals = (metalsModule.items || []).map((row) => ({
    name: row.name,
    value: row.value || `${displayValue(row.mentions)} mentions`,
    detail: row.unit || "",
  }));
  const fg = markets.fear_greed || {};
  const breadth = markets.breadth || {};
  return [
    storyBriefCard("markets", "Main market brief", "market signal"),
    storyCards("markets", 1, 2),
    topPulseCard({title: "Market pulse", kicker: "breadth", status: isMockModule(breadth) ? "mock" : "derived", value: breadth.label || "Balanced", detail: breadth.detail || "No market breadth available.", mock: isMockModule(breadth)}),
    sectorHeatmapCard(),
    cardShell({title: "Crypto tracker", kicker: "BTC / ETH / SOL", status: isMockModule(cryptoModule) ? "mock" : "live", size: "metric-card", mock: isMockModule(cryptoModule), body: `<div class="intel-mini-grid">${miniRows(crypto, {labelField: "symbol", emptyLabel: "Crypto tracker"})}</div>`}),
    cardShell({title: "FX board", kicker: "currency watch", status: isMockModule(fxModule) ? "mock" : fxModule.available ? "live" : "gap", size: "metric-card", mock: isMockModule(fxModule), body: `<div class="intel-mini-grid">${miniRows(fxModule.items || [], {labelField: "pair", valueField: "rate", emptyLabel: "FX board"})}</div>`}),
    cardShell({title: "Oil and energy", kicker: "energy desk", status: isMockModule(energyModule) ? "mock" : energyModule.available ? "live" : "gap", size: "metric-card", mock: isMockModule(energyModule), body: `<div class="intel-mini-grid">${miniRows(energyModule.items || [], {emptyLabel: "Energy prices"})}</div>`}),
    cardShell({title: "Metals and materials", kicker: "materials tape", status: isMockModule(metalsModule) ? "mock" : "derived", size: "metric-card", mock: isMockModule(metalsModule), body: `<div class="intel-mini-grid">${miniRows(metals, {emptyLabel: "Metals/materials", emptyDetail: "No metals signals in accepted market stories."})}</div>`}),
    topPulseCard({title: "Fear and greed", kicker: fg.mode === "fallback_proxy" ? "VIX proxy" : "sentiment", status: isMockModule(fg) ? "mock" : fg.available ? "live" : "gap", value: fg.value == null ? "--" : `${fg.value}/100`, detail: fg.label || "Unavailable", mock: isMockModule(fg)}),
    cardShell({title: "Macro movers", kicker: "rates and bonds", status: isMockModule(macroModule) ? "mock" : macroModule.available ? "live" : "gap", size: "data-table", mock: isMockModule(macroModule), body: `<div class="intel-mini-grid">${miniRows(macroModule.items || [], {emptyLabel: "Macro movers"})}</div>`}),
    sectionHeadlineStream("markets", headlinesModule.items || [], "Market headlines", isMockModule(headlinesModule)),
    sourceUtilityCard("markets"),
  ].join("");
}

function buildGeopoliticsBoard() {
  const geo = intel().geopolitics || {};
  const risk = geo.strategic_risk || {};
  const debt = geo.national_debt_clock || {};
  const instability = geo.country_instability || {};
  const feed = geo.intel_feed || {};
  const regional = geo.regional_risk || {};
  const disasters = geo.disaster_cascade || {};
  const escalation = geo.escalation_monitor || {};
  const posture = geo.force_posture || {};
  const sanctions = geo.sanctions_pressure || {};
  return [
    storyBriefCard("geopolitics", "Main geopolitical brief", "situation lead"),
    storyCards("geopolitics", 1, 2),
    topPulseCard({title: "Strategic risk", kicker: "overview", status: isMockModule(risk) ? "mock" : "composite", value: risk.label || "--", detail: risk.detail || "No risk detail available.", mock: isMockModule(risk)}),
    cardShell({title: "Country instability", kicker: "ranked intensity", status: isMockModule(instability) ? "mock" : "derived", size: "data-table", mock: isMockModule(instability), body: `<div class="bar-list">${barRows(instability.items || [])}</div>`}),
    cardShell({title: "Intel feed", kicker: "live tape", status: isMockModule(feed) ? "mock" : "derived", size: "list-stream", mock: isMockModule(feed), body: `<div class="intel-stream">${miniRows(feed.items || [], {labelField: "region", valueField: "headline", emptyLabel: "Intel feed"})}</div>`}),
    cardShell({title: "National debt clock", kicker: debt.source || "provider", status: isMockModule(debt) ? "mock" : debt.available ? "live" : "gap", size: "metric-card", mock: isMockModule(debt), body: debt.available ? `<div class="module-callout"><strong>${escapeHtml(debt.display || "--")}</strong><span>${escapeHtml(debt.updated_at || "")}</span></div>` : unavailable("US debt clock", "FiscalData provider did not return a usable value.")}),
    cardShell({title: "Regional risk", kicker: "theater map", status: isMockModule(regional) ? "mock" : "derived", size: "metric-card", mock: isMockModule(regional), body: `<div class="bar-list">${barRows(regional.items || [])}</div>`}),
    cardShell({title: "Disaster cascade", kicker: "natural hazards", status: isMockModule(disasters) ? "mock" : disasters.available ? "live" : "quiet", size: "list-stream", mock: isMockModule(disasters), body: `<div class="intel-stream">${miniRows(disasters.items || [], {labelField: "type", valueField: "title", detailField: "time", emptyLabel: "No active events"})}</div>`}),
    cardShell({title: "Escalation monitor", kicker: "regional cues", status: isMockModule(escalation) ? "mock" : "derived", size: "metric-card", mock: isMockModule(escalation), body: `<div class="intel-mini-grid">${miniRows(escalation.items || [], {emptyLabel: "Escalation monitor"})}</div>`}),
    cardShell({title: "Force posture", kicker: "military activity", status: isMockModule(posture) ? "mock" : "derived", size: "metric-card", mock: isMockModule(posture), body: `<div class="intel-mini-grid">${miniRows(posture.items || [], {emptyLabel: "Force posture"})}</div>`}),
    cardShell({title: "Economic warfare", kicker: "sanctions / trade", status: isMockModule(sanctions) ? "mock" : "derived", size: "metric-card", mock: isMockModule(sanctions), body: `<div class="intel-mini-grid">${miniRows(sanctions.items || [], {emptyLabel: "Economic pressure"})}</div>`}),
    sourceUtilityCard("geopolitics"),
  ].join("");
}

function buildTechnologyBoard() {
  const tech = intel().technology_ai || {};
  const metrics = metricsByLabel(tech.metrics || []);
  const metricsMock = Boolean(tech.metrics_mock || (tech.metrics || []).some((row) => row && row.mock));
  const lab = tech.lab_activity || {};
  const infra = tech.infrastructure || {};
  const adoption = tech.enterprise_adoption || {};
  const deals = tech.funding_deals || {};
  const headlines = tech.headlines || {};
  const openSource = tech.open_source || {};
  const tooling = tech.developer_tooling || {};
  const storyCount = metrics["ai stories in brief"];
  const sourceCount = metrics["unique ai sources"];
  const pulseDetail = [
    storyCount ? `${displayValue(storyCount.value)} stories` : "",
    sourceCount ? `${displayValue(sourceCount.value)} sources` : "",
  ].filter(Boolean).join(" / ") || "Accepted AI signal rollup";
  return [
    storyBriefCard("technology_ai", "Main AI brief", "lead development"),
    storyCards("technology_ai", 1, 2),
    topPulseCard({title: "AI pulse", kicker: "section rollup", status: metricsMock ? "mock" : "derived", value: sourceCount ? `${displayValue(sourceCount.value)} src` : "AI", detail: pulseDetail, mock: metricsMock}),
    cardShell({title: "AI metrics summary", kicker: "pipeline rollup", status: metricsMock ? "mock" : "derived", size: "data-table", mock: metricsMock, body: `<div class="intel-mini-grid">${miniRows(tech.metrics || [], {labelField: "label", valueField: "value", emptyLabel: "AI metrics"})}</div>`}),
    cardShell({title: "Model and lab activity", kicker: "frontier labs", status: isMockModule(lab) ? "mock" : "derived", size: "metric-card", mock: isMockModule(lab), body: `<div class="intel-mini-grid">${miniRows(lab.items || [], {emptyLabel: "Lab activity"})}</div>`}),
    cardShell({title: "AI infrastructure", kicker: "chips / cloud", status: isMockModule(infra) ? "mock" : "derived", size: "metric-card", mock: isMockModule(infra), body: `<div class="intel-mini-grid">${miniRows(infra.items || [], {emptyLabel: "Infrastructure"})}</div>`}),
    cardShell({title: "Enterprise adoption", kicker: "deployments", status: isMockModule(adoption) ? "mock" : "derived", size: "metric-card", mock: isMockModule(adoption), body: `<div class="intel-mini-grid">${miniRows(adoption.items || [], {emptyLabel: "Enterprise adoption"})}</div>`}),
    cardShell({title: "Funding and deals", kicker: "capital flow", status: isMockModule(deals) ? "mock" : "derived", size: "metric-card", mock: isMockModule(deals), body: `<div class="intel-mini-grid">${miniRows(deals.items || [], {emptyLabel: "Funding/deals"})}</div>`}),
    sectionHeadlineStream("technology_ai", headlines.items || [], "AI headlines stream", isMockModule(headlines)),
    cardShell({title: "Open-source ecosystem", kicker: "OSS movement", status: isMockModule(openSource) ? "mock" : "derived", size: "list-stream", mock: isMockModule(openSource), body: `<div class="intel-stream">${miniRows(openSource.items || [], {emptyLabel: "Open-source"})}</div>`}),
    cardShell({title: "Developer tooling", kicker: "agents / APIs", status: isMockModule(tooling) ? "mock" : "derived", size: "metric-card", mock: isMockModule(tooling), body: `<div class="intel-mini-grid">${miniRows(tooling.items || [], {emptyLabel: "Developer tooling"})}</div>`}),
    sourceUtilityCard("technology_ai"),
  ].join("");
}

function renderIntelBoard(category) {
  const wall = document.getElementById("intelWall");
  if (!wall) return;
  const builders = {
    markets: buildMarketsBoard,
    geopolitics: buildGeopoliticsBoard,
    technology_ai: buildTechnologyBoard,
  };
  const build = builders[category] || buildGeopoliticsBoard;
  wall.dataset.category = category;
  wall.innerHTML = build();
  Array.from(wall.children).forEach((node, index) => {
    node.style.setProperty("--card-index", index);
  });
}

function renderCategory(category) {
  if (!category) return;
  const changed = currentCategory !== category;
  currentCategory = category;
  const kickerEl = document.getElementById("categoryKicker");
  if (kickerEl) {
    kickerEl.innerHTML = `<span class="status-dot status-live"></span>Intel wall`;
  }
  const titleEl = document.getElementById("categoryTitle");
  if (titleEl) {
    titleEl.textContent = categoryLabels[category] || "Morning signal";
  }
  if (changed) {
    renderIntelBoard(category);
  }
}

function highlightTopic(topic) {
  const wall = document.getElementById("intelWall");
  if (!wall || !topic) return;
  const categoryTopics = cueTopics().filter((cue) => cue.section === topic.section);
  const index = categoryTopics.findIndex((cue) => cue.key === topic.key);
  const counterEl = document.getElementById("storyCounter");
  if (counterEl) {
    counterEl.textContent =
      `${String(Math.max(index + 1, 1)).padStart(2, "0")} / ${String(Math.max(categoryTopics.length, 1)).padStart(2, "0")}`;
  }
  wall.querySelectorAll("[data-topic-key]").forEach((node) => {
    node.classList.toggle("is-topic-active", node.dataset.topicKey === topic.key);
  });
  const target = Array.from(wall.querySelectorAll("[data-topic-key]"))
    .find((node) => node.dataset.topicKey === topic.key);
  if (target) {
    target.classList.add("is-pivoting");
    window.setTimeout(() => target.classList.remove("is-pivoting"), 360);
    target.scrollIntoView({behavior: "smooth", block: "center", inline: "nearest"});
  }
}

function activateSection(key) {
  lastSectionKey = key;
  const screen = screenForCue(key);
  const label = phaseOrder.find(([phase]) => phase === key)?.[1] || categoryLabels[key] || "Briefing";
  document.getElementById("phaseReadout").textContent = label;
  document.body.classList.toggle("phase-news", screen === "news");
  document.querySelectorAll(".app-screen").forEach((node) => {
    node.classList.toggle("is-screen-active", node.dataset.screen === screen);
  });
  document.querySelectorAll(".phase-item").forEach((node) => {
    node.classList.toggle("is-active", node.dataset.phase === key);
  });

  if (screen === "news") {
    renderCategory(key);
  }
}

function activateTopic(topic) {
  lastTopicKey = topic.key;
  renderCategory(topic.section);
  highlightTopic(topic);
}

function renderScript() {
  const target = document.getElementById("scriptText");
  const lines = String(data.script_markdown || "").split("\n");
  target.innerHTML = lines.map((line) => {
    const trimmed = line.trim();
    if (!trimmed) return "";
    if (trimmed.startsWith("## ")) return `<h3>${escapeHtml(trimmed.slice(3))}</h3>`;
    if (trimmed.startsWith("# ")) return `<h2>${escapeHtml(trimmed.slice(2))}</h2>`;
    if (trimmed.startsWith("- [")) {
      const match = trimmed.match(/^- \[([^\]]+)\]\(([^)]+)\)/);
      if (match) return `<p>${link(match[1], match[2])}</p>`;
    }
    return `<p>${escapeHtml(trimmed)}</p>`;
  }).join("");
}

function renderWarnings() {
  const warnings = data.warnings || [];
  document.getElementById("warnings").innerHTML = warnings.map((warning) => `<p>${escapeHtml(warning)}</p>`).join("");
}

function setupAudio() {
  if (data.music_src) {
    musicAudio.src = data.music_src;
    musicAudio.volume = 0;
    musicStatus.textContent = "Music file loaded";
  } else {
    musicStatus.textContent = "No music file routed";
  }
  if (closingAudio && data.timeout_closing_audio_src) {
    closingAudio.src = data.timeout_closing_audio_src;
  }

  if (!data.audio_src) {
    playButton.disabled = true;
    playButton.textContent = "No audio";
    audioStatus.textContent = "No narration MP3 generated";
    if (presentationMode) startPresentationClock();
    return;
  }

  playButton.textContent = autoPlay ? "Auto start armed" : "Start Ryan";
  playButton.addEventListener("click", () => beginPlayback("user"));
  briefAudio.addEventListener("loadedmetadata", () => {
    audioStatus.textContent = `Narration ready / ${Math.round(briefAudio.duration)}s`;
  });
  briefAudio.addEventListener("play", () => {
    document.body.classList.add("audio-running");
    playButton.textContent = "Ryan active";
    audioStatus.textContent = "Ryan narrating";
    startAudioSyncLoop();
    fadeMusicTo(musicNarrationVolume(), 700);
  });
  briefAudio.addEventListener("pause", () => {
    if (!briefAudio.ended) stopAudioSyncLoop();
  });
  briefAudio.addEventListener("timeupdate", () => updateActiveCue(audioToTimelineSeconds(briefAudio), audioProgressRatio(briefAudio)));
  briefAudio.addEventListener("seeking", () => updateActiveCue(audioToTimelineSeconds(briefAudio), audioProgressRatio(briefAudio)));
  briefAudio.addEventListener("ratechange", () => updateActiveCue(audioToTimelineSeconds(briefAudio), audioProgressRatio(briefAudio)));
  briefAudio.addEventListener("ended", () => {
    stopAudioSyncLoop();
    updateActiveCue(totalTimelineSeconds(), 1);
    document.body.classList.remove("audio-running");
    playButton.textContent = "Briefing complete";
    audioStatus.textContent = "Typed follow-up window open";
    fadeMusicTo(musicOpenVolume(), 1000);
    startClosingCountdown();
  });
  briefAudio.addEventListener("error", () => {
    audioStatus.textContent = "Narration audio failed to load";
    playButton.textContent = "Audio error";
    playButton.classList.add("is-blocked");
  });

  if (autoPlay && !externalAudio) {
    window.addEventListener("load", () => {
      window.setTimeout(() => beginPlayback("autoplay"), 550);
    });
  }
  if (externalAudio) {
    playButton.textContent = "Mac audio active";
    document.body.classList.add("audio-running");
    startPresentationClock();
  }
}

async function beginPlayback(reason) {
  if (playbackStarting || !briefAudio.paused) return;
  playbackStarting = true;
  playButton.classList.remove("is-blocked");
  playButton.disabled = true;
  audioStatus.textContent = reason === "autoplay" ? "Starting Ryan automatically" : "Starting Ryan";
  try {
    await waitForMediaReady(briefAudio, "narration");
    await startMusic();
    briefAudio.currentTime = 0;
    await briefAudio.play();
    playbackStarting = false;
  } catch (error) {
    playbackStarting = false;
    playButton.disabled = false;
    playButton.textContent = "Start Ryan";
    playButton.classList.add("is-blocked");
    const name = error && (error.name || error.message) ? (error.name || error.message) : "playback blocked";
    audioStatus.textContent = `Autoplay blocked by browser: ${name}. Click Start Ryan.`;
    fadeMusicTo(0, 500);
  }
}

function waitForMediaReady(media, label) {
  if (!media || !media.src) return Promise.resolve();
  if (media.readyState >= 2) return Promise.resolve();
  media.load();
  return new Promise((resolve, reject) => {
    const timeout = window.setTimeout(() => { cleanup(); resolve(); }, 7000);
    function cleanup() {
      window.clearTimeout(timeout);
      media.removeEventListener("canplay", onReady);
      media.removeEventListener("loadeddata", onReady);
      media.removeEventListener("error", onError);
    }
    function onReady() { cleanup(); resolve(); }
    function onError() { cleanup(); reject(new Error(`${label} media failed to load`)); }
    media.addEventListener("canplay", onReady, {once: true});
    media.addEventListener("loadeddata", onReady, {once: true});
    media.addEventListener("error", onError, {once: true});
  });
}

function musicNarrationVolume() {
  return Math.min(Math.max(Number(data.music_volume || 0.24), 0.06), 0.45);
}

function musicOpenVolume() {
  return Math.min(musicNarrationVolume() * 1.35, 0.52);
}

async function startMusic() {
  if (!musicAudio.src || data.browser_music_enabled === false || data.music_enabled === false) return;
  try {
    await waitForMediaReady(musicAudio, "music");
    musicAudio.currentTime = 0;
    await musicAudio.play();
    musicStatus.textContent = "Music bed active";
    fadeMusicTo(musicOpenVolume(), 900);
  } catch (error) {
    const name = error && (error.name || error.message) ? (error.name || error.message) : "music blocked";
    musicStatus.textContent = `Music blocked: ${name}`;
  }
}

function fadeMusicTo(targetVolume, durationMs) {
  if (!musicAudio || !musicAudio.src) return;
  if (musicFadeFrame) cancelAnimationFrame(musicFadeFrame);
  const startVolume = musicAudio.volume;
  const startedAt = performance.now();
  function step(now) {
    const progress = Math.min((now - startedAt) / Math.max(durationMs, 1), 1);
    musicAudio.volume = startVolume + (targetVolume - startVolume) * progress;
    if (progress < 1) musicFadeFrame = requestAnimationFrame(step);
  }
  musicFadeFrame = requestAnimationFrame(step);
}

function startPresentationClock() {
  if (presentationStartedAt != null) return;
  presentationStartedAt = performance.now();
  requestAnimationFrame(tickPresentationClock);
}

function tickPresentationClock() {
  if (presentationStartedAt == null) return;
  const elapsed = (performance.now() - presentationStartedAt) / 1000;
  if (!briefAudio || briefAudio.paused || briefAudio.currentTime < 0.25) {
    updateActiveCue(elapsed);
  }
  if (elapsed < totalTimelineSeconds() + 15) requestAnimationFrame(tickPresentationClock);
}

function startAudioSyncLoop() {
  if (audioSyncFrame) return;
  const tick = () => {
    if (!briefAudio || briefAudio.paused || briefAudio.ended) { audioSyncFrame = null; return; }
    updateActiveCue(audioToTimelineSeconds(briefAudio), audioProgressRatio(briefAudio));
    audioSyncFrame = requestAnimationFrame(tick);
  };
  audioSyncFrame = requestAnimationFrame(tick);
}

function stopAudioSyncLoop() {
  if (!audioSyncFrame) return;
  cancelAnimationFrame(audioSyncFrame);
  audioSyncFrame = null;
}

function updateActiveCue(seconds, audioRatio = null) {
  const sections = cueSections();
  const topics = cueTopics();
  const totalSeconds = totalTimelineSeconds();
  const visualSeconds = Math.min(seconds + VISUAL_SYNC_LEAD_SECONDS, totalSeconds);
  const activeSection = sections.find((cue) => visualSeconds >= cue.start && visualSeconds < cue.end) || sections[sections.length - 1];
  const activeTopic = topics.find((cue) => visualSeconds >= cue.start && visualSeconds < cue.end);
  const percent = Math.min(100, (audioRatio == null ? seconds / totalSeconds : audioRatio) * 100);
  const railPercent = Math.min(100, (visualSeconds / totalSeconds) * 100);
  document.getElementById("progressBar").style.width = `${percent}%`;
  document.getElementById("railProgress").style.height = `${railPercent}%`;
  updatePhaseProgress(visualSeconds);

  if (activeSection && activeSection.key !== lastSectionKey) {
    activateSection(activeSection.key);
  }
  if (activeTopic && activeTopic.key !== lastTopicKey) {
    activateTopic(activeTopic);
  }
}

function updatePhaseProgress(seconds) {
  const sections = cueSections();
  document.querySelectorAll(".phase-item").forEach((node) => {
    const cue = sections.find((sectionCue) => sectionCue.key === node.dataset.phase);
    const fill = node.querySelector(".phase-fill i");
    const state = node.querySelector(".phase-state");
    if (!cue || !fill) return;
    const duration = Math.max(cue.end - cue.start, 0.01);
    const ratio = seconds <= cue.start ? 0 : seconds >= cue.end ? 1 : (seconds - cue.start) / duration;
    fill.style.width = `${Math.min(Math.max(ratio, 0), 1) * 100}%`;
    node.classList.toggle("is-complete", seconds >= cue.end);
    if (state) {
      if (seconds >= cue.end) state.textContent = "Done";
      else if (seconds >= cue.start) state.textContent = `${Math.max(Math.round(ratio * 100), 1)}% live`;
      else state.textContent = "Queued";
    }
  });
}

function startClosingCountdown() {
  if (closingCountdownStarted) return;
  closingCountdownStarted = true;
  followupComplete = false;
  const value = document.getElementById("countdownValue");
  const message = document.getElementById("countdownMessage");
  const input = document.getElementById("followupInput");
  let seconds = Math.max(Number(data.followup_timeout_seconds || 0), 1);
  value.textContent = String(seconds);
  message.textContent = "Type one quick follow-up if you want me to check a thread before I close.";
  setFollowupDisabled(false);
  input.focus({preventScroll: true});
  countdownTimer = window.setInterval(() => {
    seconds -= 1;
    value.textContent = String(Math.max(seconds, 0));
    if (seconds <= 0) {
      window.clearInterval(countdownTimer);
      runTimeoutClose();
    }
  }, 1000);
}

async function runTimeoutClose() {
  if (finalCloseInProgress) return;
  finalCloseInProgress = true;
  followupComplete = true;
  setFollowupDisabled(true);
  await playTimeoutClosing();
  completeSession("typed_followup_timeout");
}

async function playTimeoutClosing() {
  const message = document.getElementById("countdownMessage");
  const line = text(
    data.timeout_closing_line,
    `Okay, no further questions on the board. I am closing the mission now. Have a strong day, Captain.`
  );
  message.textContent = line;
  let src = data.timeout_closing_audio_src || "";
  if (!src) {
    src = await fetchClosingAudio(line);
  }
  if (!closingAudio || !src) {
    audioStatus.textContent = "Closing text displayed";
    return;
  }
  try {
    if (closingAudio.src !== src) {
      closingAudio.src = src;
    }
    await waitForMediaReady(closingAudio, "closing");
    closingAudio.currentTime = 0;
    fadeMusicTo(Math.min(musicNarrationVolume(), 0.18), 400);
    audioStatus.textContent = "Closing mission call";
    await closingAudio.play();
    const durationMs = Number.isFinite(closingAudio.duration)
      ? Math.min(Math.max(closingAudio.duration * 1000 + 1800, 5000), 14000)
      : 9000;
    await waitForMediaEnd(closingAudio, durationMs);
  } catch (error) {
    audioStatus.textContent = "Closing text displayed";
  }
}

async function fetchClosingAudio(fallbackLine) {
  try {
    const response = await fetch("/api/closing", {method: "POST"});
    if (!response.ok) return "";
    const payload = await response.json();
    if (payload.answer) {
      document.getElementById("countdownMessage").textContent = payload.answer || fallbackLine;
    }
    return payload.audio_src || "";
  } catch (error) {
    return "";
  }
}

function waitForMediaEnd(media, timeoutMs) {
  return new Promise((resolve) => {
    const timeout = window.setTimeout(() => { cleanup(); resolve(); }, timeoutMs);
    function cleanup() {
      window.clearTimeout(timeout);
      media.removeEventListener("ended", onEnded);
      media.removeEventListener("error", onEnded);
    }
    function onEnded() { cleanup(); resolve(); }
    media.addEventListener("ended", onEnded, {once: true});
    media.addEventListener("error", onEnded, {once: true});
  });
}

function setupFollowupForm() {
  const form = document.getElementById("followupForm");
  const input = document.getElementById("followupInput");
  setFollowupDisabled(true);
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const value = input.value.trim();
    if (!value) { input.focus(); return; }
    input.value = "";
    submitFollowup(value);
  });
}

function submitFollowup(question) {
  if (followupComplete) return;
  followupComplete = true;
  if (countdownTimer) window.clearInterval(countdownTimer);
  closingCountdownStarted = true;
  document.getElementById("countdownValue").textContent = "0";
  const message = document.getElementById("countdownMessage");
  message.textContent = "One moment. I am checking the brief.";
  setFollowupDisabled(true);
  fetch("/api/followup", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({question}),
  })
    .then((response) => response.ok ? response.json() : Promise.reject(response))
    .then((payload) => {
      const answer = payload.answer || `Noted. I will keep ${question} on the radar.`;
      message.textContent = answer;
      window.setTimeout(() => completeSession("typed_followup_answered"), Math.min(Math.max(answer.length * 45, 7000), 12000));
    })
    .catch(() => {
      const answer = `Noted. I will keep ${question} on the radar.`;
      message.textContent = answer;
      window.setTimeout(() => completeSession("typed_followup_fallback"), 7000);
    });
}

function setFollowupDisabled(disabled) {
  const form = document.getElementById("followupForm");
  if (!form) return;
  form.querySelectorAll("input, button").forEach((node) => { node.disabled = disabled; });
}

function completeSession(reason) {
  if (sessionComplete) return;
  sessionComplete = true;
  if (countdownTimer) window.clearInterval(countdownTimer);
  setFollowupDisabled(true);
  fadeMusicTo(0, 1200);
  const payload = JSON.stringify({reason});
  if (navigator.sendBeacon) {
    try {
      navigator.sendBeacon("/api/session/complete", new Blob([payload], {type: "application/json"}));
    } catch (error) {
      // Keep the fetch path below as the reliable fallback.
    }
  }
  fetch("/api/session/complete", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: payload,
    keepalive: true,
  }).catch(() => {});
  window.setTimeout(() => { window.close(); }, 1400);
}

document.getElementById("greetingHeadline").textContent = firstSentence(
  data.script_sections && data.script_sections.greeting,
  text(data.narration_plan && data.narration_plan.opening_line, "Good morning.")
);
document.getElementById("operationName").textContent =
  text(data.narration_plan && data.narration_plan.operation_name, "Operation Daybreak");
document.getElementById("closingQuestion").textContent =
  text(data.script_sections && data.script_sections.closing_question, "Any questions on Operation Daybreak, Captain?");
document.getElementById("wordCount").textContent = `${data.word_count || 0} words`;
document.getElementById("modelUsed").textContent =
  `signals: ${text(data.model_used && data.model_used.signals, "n/a")} | script: ${text(data.model_used && data.model_used.script, "n/a")}`;

renderPhaseRail();
renderWeather();
renderWorldClock();
renderScript();
renderWarnings();
renderCategory("geopolitics");
setupFollowupForm();
setupAudio();
updateActiveCue(0);
runBootSequence();
