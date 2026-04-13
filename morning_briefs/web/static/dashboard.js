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

const VISUAL_SYNC_LEAD_SECONDS = 0.42;

const playButton = document.getElementById("playButton");
const audioStatus = document.getElementById("audioStatus");
const musicStatus = document.getElementById("musicStatus");
const briefAudio = document.getElementById("briefAudio");
const musicAudio = document.getElementById("musicAudio");

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
  if (code == null) return "◈";
  const c = Number(code);
  if (c === 0) return "☀";
  if (c <= 2) return "⛅";
  if (c <= 3) return "☁";
  if (c <= 49) return "🌫";
  if (c <= 69) return "🌧";
  if (c <= 84) return "🌦";
  if (c <= 94) return "⛈";
  return "⛈";
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
    const tags = [...(w.carry || []), ...(w.wear || [])].filter(Boolean).slice(0, 6);
    carryEl.innerHTML = tags.map((t) => `<span class="weather-carry-tag">${escapeHtml(t)}</span>`).join("");
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

function toggleCategoryCards(category) {
  document.querySelectorAll(".category-card").forEach((node) => {
    const categories = (node.dataset.category || "").split(/\s+/).filter(Boolean);
    const visible = categories.includes(category);
    node.classList.toggle("hidden", !visible);
  });
}

function renderSourceStack(category) {
  const notes = section(category);
  const stack = document.getElementById("sourceStack");
  const count = document.getElementById("sourceCount");
  if (!stack || !count) return;

  const links = notes.slice(0, 3);
  count.textContent = `${links.length} links`;
  stack.innerHTML = links.map((note) => `
    <article class="source-card source-link-compact">
      <small>${escapeHtml(note.source_name || "source")}</small>
      <strong>${link(note.headline || "Untitled", note.url)}</strong>
    </article>
  `).join("") || `<article class="source-card source-link-compact"><strong>No links for this section.</strong></article>`;
}

function renderSectorHeatmap() {
  const grid = document.getElementById("sectorGrid");
  if (!grid) return;
  const moduleData = (((intel().markets || {}).sector_heatmap) || {});
  const items = moduleData.items || [];
  if (!items.length) {
    grid.innerHTML = `<div class="sector-cell heat-flat"><div class="sector-ticker">N/A</div><span class="sector-pct flat">Unavailable</span></div>`;
    return;
  }
  grid.innerHTML = items.slice(0, 9).map((row) => {
    const intensity = Number(row.intensity || 0);
    let cls = "heat-flat";
    if (row.band === "high") cls = "heat-pos-strong";
    else if (row.band === "medium") cls = "heat-pos";
    else if (row.band === "low") cls = "heat-flat";
    return `<div class="sector-cell ${cls}">
      <div class="sector-ticker">${escapeHtml(row.name || "Sector")}</div>
      <span class="sector-pct pos">${escapeHtml(String(row.hits || 0))} hits</span>
      <span class="sector-name">${escapeHtml(String(intensity))}% intensity</span>
    </div>`;
  }).join("");
}

function renderGeopoliticsPanels() {
  const instabilityGrid = document.getElementById("countryInstabilityGrid");
  const debtClockPanel = document.getElementById("debtClockPanel");
  const disasterGrid = document.getElementById("disasterCascadeGrid");
  if (!instabilityGrid || !debtClockPanel || !disasterGrid) return;

  const geo = intel().geopolitics || {};
  const instability = (geo.country_instability || {}).items || [];
  instabilityGrid.innerHTML = instability.slice(0, 8).map((row) => `
    <article class="intel-chip-card">
      <span>${escapeHtml(row.name || "Region")}</span>
      <strong>${escapeHtml(String(row.score == null ? "--" : row.score))}</strong>
    </article>
  `).join("") || `<article class="intel-chip-card"><span>No data</span><strong>--</strong></article>`;

  const debt = geo.national_debt_clock || {};
  debtClockPanel.innerHTML = debt.available
    ? `<article class="intel-chip-card intel-wide">
         <span>US debt</span>
         <strong>${escapeHtml(debt.display || "Unavailable")}</strong>
         <small>${escapeHtml(debt.updated_at || "")}</small>
       </article>`
    : `<article class="intel-chip-card intel-wide"><span>Debt clock</span><strong>Unavailable</strong></article>`;

  const disasters = (geo.disaster_cascade || {}).items || [];
  disasterGrid.innerHTML = disasters.slice(0, 8).map((row) => `
    <article class="intel-chip-card intel-disaster">
      <span>${escapeHtml(row.type || "Event")}</span>
      <strong>${escapeHtml(row.title || "Unnamed")}</strong>
      <small>${escapeHtml(compactDate(row.time))}</small>
    </article>
  `).join("") || `<article class="intel-chip-card"><span>No active events</span><strong>--</strong></article>`;

  const riskEl = document.getElementById("geoStrategicRisk");
  if (riskEl) {
    const risk = geo.strategic_risk || {};
    riskEl.innerHTML = `<article class="intel-chip-card intel-wide"><span>risk status</span><strong>${escapeHtml(risk.label || "Unavailable")}</strong><small>${escapeHtml(risk.detail || "")}</small></article>`;
  }

  const feedEl = document.getElementById("geoIntelFeed");
  if (feedEl) {
    const feed = (geo.intel_feed || {}).items || [];
    feedEl.innerHTML = feed.map((row) => `<article class="intel-chip-card"><span>${escapeHtml(row.region || "region")}</span><strong>${escapeHtml(row.headline || "")}</strong></article>`).join("") || `<article class="intel-chip-card"><span>feed</span><strong>No live feed</strong></article>`;
  }

  [
    ["geoEscalationGrid", (geo.escalation_monitor || {}).items || [], "level"],
    ["geoForcePostureGrid", (geo.force_posture || {}).items || [], "status"],
    ["geoSanctionsGrid", (geo.sanctions_pressure || {}).items || [], "pressure"],
    ["geoRegionalRiskGrid", (geo.regional_risk || {}).items || [], "score"],
  ].forEach(([id, rows, field]) => {
    const el = document.getElementById(id);
    if (!el) return;
    el.innerHTML = rows.map((row) => `<article class="intel-chip-card"><span>${escapeHtml(row.name || row.region || "region")}</span><strong>${escapeHtml(String(row[field] ?? row.value ?? "--"))}</strong></article>`).join("") || `<article class="intel-chip-card"><span>module</span><strong>Unavailable</strong></article>`;
  });
}

function renderMarketPanels() {
  const metalsGrid = document.getElementById("marketMetalsGrid");
  const cryptoGrid = document.getElementById("marketCryptoGrid");
  const fearPanel = document.getElementById("fearGreedPanel");
  const fxGrid = document.getElementById("marketFxGrid");
  const energyGrid = document.getElementById("marketEnergyGrid");
  const macroGrid = document.getElementById("marketMacroGrid");
  const breadthPanel = document.getElementById("marketBreadthPanel");
  const headlinesPanel = document.getElementById("marketHeadlinesStream");
  if (!metalsGrid || !cryptoGrid || !fearPanel) return;

  const markets = intel().markets || {};
  const metals = (markets.metals_materials || {}).items || [];
  metalsGrid.innerHTML = metals.length
    ? metals.map((row) => `<article class="intel-chip-card"><span>${escapeHtml(row.name)}</span><strong>${escapeHtml(String(row.mentions))} mentions</strong></article>`).join("")
    : `<article class="intel-chip-card"><span>Metals/materials</span><strong>No live signals</strong></article>`;

  const crypto = (markets.crypto || {}).items || [];
  cryptoGrid.innerHTML = crypto.length
    ? crypto.map((row) => {
      const change = row.change_24h == null ? "--" : `${row.change_24h >= 0 ? "+" : ""}${row.change_24h.toFixed(2)}%`;
      return `<article class="intel-chip-card"><span>${escapeHtml(row.symbol)}</span><strong>$${Number(row.price_usd).toLocaleString()}</strong><small>${escapeHtml(change)}</small></article>`;
    }).join("")
    : `<article class="intel-chip-card"><span>Crypto</span><strong>Unavailable</strong></article>`;

  const fg = markets.fear_greed || {};
  fearPanel.innerHTML = `<article class="intel-chip-card intel-wide">
    <span>${escapeHtml(fg.mode === "fallback_proxy" ? "Fear & greed (proxy)" : "Fear & greed")}</span>
    <strong>${escapeHtml(fg.value == null ? "--" : `${fg.value} / 100`)}</strong>
    <small>${escapeHtml(fg.label || "Unavailable")}</small>
  </article>`;

  if (fxGrid) {
    const rows = (markets.fx || {}).items || [];
    fxGrid.innerHTML = rows.map((row) => `<article class="intel-chip-card"><span>${escapeHtml(row.pair || "FX")}</span><strong>${escapeHtml(String(row.rate ?? "--"))}</strong></article>`).join("") || `<article class="intel-chip-card"><span>FX</span><strong>Unavailable</strong></article>`;
  }

  if (energyGrid) {
    const rows = (markets.energy || {}).items || [];
    energyGrid.innerHTML = rows.map((row) => `<article class="intel-chip-card"><span>${escapeHtml(row.name || "Energy")}</span><strong>${escapeHtml(String(row.value ?? "--"))}</strong><small>${escapeHtml(row.unit || "")}</small></article>`).join("") || `<article class="intel-chip-card"><span>Energy</span><strong>Unavailable</strong></article>`;
  }

  if (macroGrid) {
    const rows = (markets.macro_movers || {}).items || [];
    macroGrid.innerHTML = rows.map((row) => `<article class="intel-chip-card"><span>${escapeHtml(row.name || "Macro")}</span><strong>${escapeHtml(String(row.value ?? "--"))}</strong><small>${escapeHtml(row.change || "")}</small></article>`).join("") || `<article class="intel-chip-card"><span>Macro</span><strong>Unavailable</strong></article>`;
  }

  if (breadthPanel) {
    const breadth = markets.breadth || {};
    breadthPanel.innerHTML = `<article class="intel-chip-card intel-wide"><span>breadth mode</span><strong>${escapeHtml(breadth.label || "Unavailable")}</strong><small>${escapeHtml(breadth.detail || "")}</small></article>`;
  }

  if (headlinesPanel) {
    const rows = (markets.headlines || {}).items || [];
    headlinesPanel.innerHTML = rows.map((row) => `<article class="intel-chip-card"><span>${escapeHtml(row.source || "source")}</span><strong>${escapeHtml(row.headline || "")}</strong></article>`).join("") || `<article class="intel-chip-card"><span>headlines</span><strong>No market headlines</strong></article>`;
  }
}

function renderTechPanels() {
  const grid = document.getElementById("techMetricsGrid");
  const labGrid = document.getElementById("techLabActivityGrid");
  const infraGrid = document.getElementById("techInfrastructureGrid");
  const enterpriseGrid = document.getElementById("techEnterpriseGrid");
  const fundingGrid = document.getElementById("techFundingGrid");
  const headlinesGrid = document.getElementById("techHeadlinesGrid");
  const ossGrid = document.getElementById("techOpenSourceGrid");
  const devGrid = document.getElementById("techDeveloperGrid");
  if (!grid) return;
  const tech = (intel().technology_ai || {});
  const metrics = (((intel().technology_ai || {}).metrics) || []);
  grid.innerHTML = metrics.map((m) => `
    <article class="intel-chip-card intel-wide">
      <span>${escapeHtml(m.label || "Metric")}</span>
      <strong>${escapeHtml(m.value == null ? "--" : String(m.value))}</strong>
      <small>${escapeHtml(m.detail || "")}</small>
    </article>
  `).join("") || `<article class="intel-chip-card intel-wide"><span>AI metrics</span><strong>Unavailable</strong></article>`;

  const writeList = (el, rows, labelField = "name", valueField = "value") => {
    if (!el) return;
    el.innerHTML = rows.map((row) => `<article class="intel-chip-card"><span>${escapeHtml(row[labelField] || "item")}</span><strong>${escapeHtml(String(row[valueField] ?? row.label ?? "--"))}</strong><small>${escapeHtml(row.detail || "")}</small></article>`).join("") || `<article class="intel-chip-card"><span>module</span><strong>Unavailable</strong></article>`;
  };

  writeList(labGrid, (tech.lab_activity || {}).items || []);
  writeList(infraGrid, (tech.infrastructure || {}).items || []);
  writeList(enterpriseGrid, (tech.enterprise_adoption || {}).items || []);
  writeList(fundingGrid, (tech.funding_deals || {}).items || []);

  if (headlinesGrid) {
    const rows = (tech.headlines || {}).items || [];
    headlinesGrid.innerHTML = rows.map((row) => `<article class="intel-chip-card"><span>${escapeHtml(row.source || "source")}</span><strong>${escapeHtml(row.headline || "")}</strong></article>`).join("") || `<article class="intel-chip-card"><span>headlines</span><strong>No AI headlines</strong></article>`;
  }
  if (ossGrid) {
    const rows = (tech.open_source || {}).items || [];
    ossGrid.innerHTML = rows.map((row) => `<article class="intel-chip-card"><span>${escapeHtml(row.name || "oss")}</span><strong>${escapeHtml(row.value || row.headline || "")}</strong></article>`).join("") || `<article class="intel-chip-card"><span>open-source</span><strong>Unavailable</strong></article>`;
  }
  if (devGrid) {
    const rows = (tech.developer_tooling || {}).items || [];
    devGrid.innerHTML = rows.map((row) => `<article class="intel-chip-card"><span>${escapeHtml(row.name || "dev")}</span><strong>${escapeHtml(row.value || row.headline || "")}</strong></article>`).join("") || `<article class="intel-chip-card"><span>developer</span><strong>Unavailable</strong></article>`;
  }
}

function renderCategory(category) {
  if (!category || currentCategory === category) return;
  currentCategory = category;
  const kickerEl = document.getElementById("categoryKicker");
  if (kickerEl) {
    kickerEl.innerHTML = `<span class="status-dot status-live"></span>Intel sequence`;
  }
  const titleEl = document.getElementById("categoryTitle");
  if (titleEl) {
    titleEl.textContent = categoryLabels[category] || "Morning signal";
  }
  toggleCategoryCards(category);
  renderSourceStack(category);
}

function cleanImplication(value) {
  return text(value, "Watch the follow-through, not just the headline.")
    .replace(/^why (it|this) matters( today)?\s*:\s*/i, "")
    .replace(/^this is important because\s*/i, "");
}

function activateClipping(topic) {
  const note = noteForTopic(topic);
  if (!note) return;
  const active = document.getElementById("activeClipping");
  active.classList.add("is-pivoting");
  window.setTimeout(() => active.classList.remove("is-pivoting"), 280);

  document.getElementById("activeSource").textContent = note.source_name || "Source";
  document.getElementById("activeTime").textContent = compactDate(note.published_at);
  document.getElementById("activeHeadline").textContent = note.headline || "Active clipping";
  document.getElementById("activePointOne").textContent = note.note || note.excerpt || "Signal is still resolving.";
  document.getElementById("activePointTwo").textContent = cleanImplication(note.why_it_matters || note.note);
  document.getElementById("activeExcerpt").textContent = note.excerpt || note.note || "No excerpt was provided for this source.";

  const categoryTopics = cueTopics().filter((cue) => cue.section === topic.section);
  const index = categoryTopics.findIndex((cue) => cue.key === topic.key);
  const counterEl = document.getElementById("storyCounter");
  if (counterEl) {
    counterEl.textContent =
      `${String(Math.max(index + 1, 1)).padStart(2, "0")} / ${String(Math.max(categoryTopics.length, 1)).padStart(2, "0")}`;
  }
  renderSourceStack(topic.section);
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
  activateClipping(topic);
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
  let seconds = Math.max(Number(data.followup_timeout_seconds || 10), 1);
  value.textContent = String(seconds);
  message.textContent = "Type one quick follow-up if you want me to check a thread before I close.";
  setFollowupDisabled(false);
  input.focus({preventScroll: true});
  countdownTimer = window.setInterval(() => {
    seconds -= 1;
    value.textContent = String(Math.max(seconds, 0));
    if (seconds <= 0) {
      window.clearInterval(countdownTimer);
      followupComplete = true;
      setFollowupDisabled(true);
      message.textContent = `Nothing else queued. Have a great day, ${text(data.user_name, "Prasad")}.`;
      completeSession("typed_followup_timeout");
    }
  }, 1000);
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
  fetch("/api/session/complete", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({reason}),
  }).catch(() => {});
  window.setTimeout(() => { window.close(); }, 900);
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
renderSourceStack("geopolitics");
renderCategory("geopolitics");
renderSectorHeatmap();
renderGeopoliticsPanels();
renderMarketPanels();
renderTechPanels();
setupFollowupForm();
setupAudio();
updateActiveCue(0);
runBootSequence();
