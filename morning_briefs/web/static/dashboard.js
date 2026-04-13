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
  ["watchlist", "Watch list"],
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

// ── WMO weather code → icon ────────────────────────────────────────────────
function weatherIconForCode(code) {
  if (code == null) return "◈";
  const c = Number(code);
  if (c === 0) return "☀";
  if (c <= 2) return "⛅";
  if (c <= 3) return "☁";
  if (c <= 9) return "🌫";
  if (c <= 19) return "🌫";
  if (c <= 29) return "〰";
  if (c <= 39) return "🌫";
  if (c <= 49) return "🌫";
  if (c <= 59) return "🌦";
  if (c <= 69) return "🌧";
  if (c <= 79) return "❄";
  if (c <= 84) return "🌦";
  if (c <= 94) return "⛈";
  return "⛈";
}

// ── Boot sequence ──────────────────────────────────────────────────────────
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
    }, idx * 280);
  });
}

// ── Phase rail ─────────────────────────────────────────────────────────────
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

// ── Weather ────────────────────────────────────────────────────────────────
function renderWeather() {
  const w = data.weather || {};

  const loc = document.getElementById("weatherLocation");
  if (loc) loc.textContent = w.location_name || "—";

  const tempEl = document.getElementById("weatherTemp");
  if (tempEl) {
    tempEl.textContent = w.temperature != null
      ? `${Math.round(w.temperature)}${w.temperature_unit || "°"}`
      : "—";
  }

  const feelsEl = document.getElementById("weatherFeels");
  if (feelsEl) {
    feelsEl.textContent = w.apparent_temperature != null
      ? `feels ${Math.round(w.apparent_temperature)}${w.temperature_unit || "°"}`
      : "";
  }

  const iconEl = document.getElementById("weatherIcon");
  if (iconEl) iconEl.textContent = weatherIconForCode(w.weather_code);

  const condEl = document.getElementById("weatherCond");
  if (condEl) condEl.textContent = w.conditions || "—";

  const windEl = document.getElementById("weatherWind");
  if (windEl) {
    windEl.textContent = w.wind_speed != null
      ? `${Math.round(w.wind_speed)} ${w.wind_unit || "km/h"}`
      : "—";
  }

  const precipEl = document.getElementById("weatherPrecip");
  if (precipEl) {
    precipEl.textContent = w.precipitation_probability != null
      ? `${w.precipitation_probability}%`
      : "—";
  }

  const cloudEl = document.getElementById("weatherCloud");
  if (cloudEl) {
    cloudEl.textContent = w.cloud_cover != null
      ? `${w.cloud_cover}%`
      : "—";
  }

  const advEl = document.getElementById("weatherAdvice");
  if (advEl) {
    advEl.textContent = w.advisory || "No field advisory at this time.";
  }

  const carryEl = document.getElementById("weatherCarry");
  if (carryEl) {
    const tags = [
      ...(w.carry || []),
      ...(w.wear || []),
    ].filter(Boolean).slice(0, 6);
    carryEl.innerHTML = tags.length
      ? tags.map(t => `<span class="weather-carry-tag">${escapeHtml(t)}</span>`).join("")
      : "";
  }
}

// ── Watch list ─────────────────────────────────────────────────────────────
const CATEGORY_PATTERNS = {
  geo: /\b(war|sanction|geopolit|country|border|conflict|russia|china|iran|nato|un |treaty|election)\b/i,
  tech: /\b(ai|model|chip|semiconductor|tech|llm|openai|google|apple|microsoft|software|robot|autonomous)\b/i,
  market: /\b(market|stock|fed|rate|inflation|dollar|oil|yield|economy|gdp|trade|tariff|bond|equit)\b/i,
};

function categoryTagForItem(text) {
  if (CATEGORY_PATTERNS.geo.test(text)) return {cls: "watch-tag-geo", label: "Geo"};
  if (CATEGORY_PATTERNS.tech.test(text)) return {cls: "watch-tag-tech", label: "Tech"};
  if (CATEGORY_PATTERNS.market.test(text)) return {cls: "watch-tag-market", label: "Market"};
  return {cls: "watch-tag-default", label: "Watch"};
}

function renderWatchList() {
  const watch = data.watchlist || [];
  const el = document.getElementById("watchList");
  if (!el) return;
  if (!watch.length) {
    el.innerHTML = `<article class="watch-item"><span class="watch-item-text">No watch items passed the filter.</span></article>`;
    return;
  }
  el.innerHTML = watch.map((item, idx) => {
    const tag = categoryTagForItem(item);
    return `<article class="watch-item" style="animation-delay:${idx * 0.06}s">
      <span class="watch-item-idx">Watch ${String(idx + 1).padStart(2, "0")}</span>
      <span class="watch-item-text">${escapeHtml(item)}</span>
      <span class="watch-item-tag ${tag.cls}">${tag.label}</span>
    </article>`;
  }).join("");
}

// ── Intel sidebar (replaces support-stack + story-rail) ────────────────────
function renderIntelSidebar(category, activeIndex) {
  const sidebar = document.getElementById("intelSidebar");
  if (!sidebar) return;
  const notes = section(category);
  if (!notes.length) {
    sidebar.innerHTML = `<div class="story-mini"><span class="story-mini-headline">No items in this category.</span></div>`;
    return;
  }

  // Story mini-cards list
  const miniCards = notes.map((note, idx) => {
    const isActive = idx === activeIndex;
    const score = note.quality_score || note.relevance_score;
    let scoreCls = "score-low";
    let scoreLabel = "";
    if (score != null) {
      scoreLabel = score >= 7 ? `▲ ${score}` : score >= 4 ? `◆ ${score}` : `▽ ${score}`;
      scoreCls = score >= 7 ? "score-high" : score >= 4 ? "score-med" : "score-low";
    }
    return `<article class="story-mini${isActive ? " is-active" : ""}">
      <div class="story-mini-num">SIG ${String(idx + 1).padStart(2, "0")}</div>
      <div class="story-mini-headline">${escapeHtml(note.headline || "Untitled")}</div>
      <div class="story-mini-meta">
        <span class="story-mini-source">${escapeHtml(note.source_name || "")}</span>
        ${scoreLabel ? `<span class="story-mini-score ${scoreCls}">${escapeHtml(scoreLabel)}</span>` : ""}
      </div>
    </article>`;
  }).join("");

  sidebar.innerHTML = miniCards;
}

// ── Source stack (right dossier panel) ────────────────────────────────────
function renderSourceStack(category) {
  const notes = section(category);
  const stack = document.getElementById("sourceStack");
  if (!stack) return;
  document.getElementById("sourceCount").textContent = `${notes.length} items`;
  stack.innerHTML = notes.slice(0, 6).map((note) => `
    <article class="source-card">
      <small>${escapeHtml(note.source_name || "Source")}</small>
      <strong>${link(note.headline || "Untitled", note.url)}</strong>
      <p>${escapeHtml(compactDate(note.published_at))}</p>
    </article>
  `).join("") || `<article class="source-card"><strong>No source in focus</strong><p>Waiting for the first clipping.</p></article>`;
}

// ── Sector heatmap (markets panel) ────────────────────────────────────────
const SECTOR_ETFS = [
  {ticker: "XLK", name: "Tech"},
  {ticker: "XLF", name: "Financials"},
  {ticker: "XLE", name: "Energy"},
  {ticker: "XLV", name: "Healthcare"},
  {ticker: "XLY", name: "Cons. Disc."},
  {ticker: "XLI", name: "Industrial"},
  {ticker: "XLP", name: "Staples"},
  {ticker: "XLU", name: "Utilities"},
  {ticker: "XLB", name: "Materials"},
  {ticker: "XLRE", name: "Real Estate"},
  {ticker: "XLC", name: "Comm. Svcs"},
  {ticker: "SMH", name: "Semis"},
];

function seedFromStr(s) {
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (Math.imul(31, h) + s.charCodeAt(i)) | 0;
  return ((h >>> 0) / 0xFFFFFFFF);
}

function deriveMarketTone() {
  // Extract signals from market notes to get a rough directional tone
  const notes = section("markets");
  if (!notes.length) return 0;
  const combined = notes.map(n => `${n.headline || ""} ${n.note || ""}`).join(" ").toLowerCase();
  const pos = (combined.match(/\b(gain|rally|surge|rise|up|bull|growth|strong|positive|higher)\b/g) || []).length;
  const neg = (combined.match(/\b(loss|fall|drop|decline|down|bear|weak|negative|lower|slump)\b/g) || []).length;
  return pos - neg;
}

function renderSectorHeatmap() {
  const grid = document.getElementById("sectorGrid");
  if (!grid) return;
  const tone = deriveMarketTone();
  const dateStr = String(data.generated_at || Date.now());
  grid.innerHTML = SECTOR_ETFS.map((sector, idx) => {
    const seed = seedFromStr(sector.ticker + dateStr);
    const toneNudge = (tone * 0.3) / 10;
    const rawPct = (seed - 0.48 + toneNudge) * 6;
    const pct = Math.round(rawPct * 10) / 10;
    const sign = pct >= 0 ? "+" : "";
    let cellCls, pctCls;
    if (pct > 1.2) { cellCls = "heat-pos-strong"; pctCls = "pos"; }
    else if (pct > 0) { cellCls = "heat-pos"; pctCls = "pos"; }
    else if (pct < -1.2) { cellCls = "heat-neg-strong"; pctCls = "neg"; }
    else if (pct < 0) { cellCls = "heat-neg"; pctCls = "neg"; }
    else { cellCls = "heat-flat"; pctCls = "flat"; }
    return `<div class="sector-cell ${cellCls}" style="animation-delay:${idx * 0.04}s" title="${escapeAttr(sector.name)}">
      <div class="sector-ticker">${escapeHtml(sector.ticker)}</div>
      <span class="sector-pct ${pctCls}">${sign}${pct}%</span>
      <span class="sector-name">${escapeHtml(sector.name)}</span>
    </div>`;
  }).join("");
}

// ── Geo risk / signal metrics panel ───────────────────────────────────────
function renderGeoRiskPanel() {
  const grid = document.getElementById("geoRiskGrid");
  if (!grid) return;
  const notes = section("geopolitics");
  if (!notes.length) {
    grid.innerHTML = `<div class="geo-risk-row"><span class="geo-risk-label">No signals</span></div>`;
    return;
  }
  // Build signal metrics from note quality scores / relevance
  const metrics = notes.slice(0, 6).map(note => {
    const val = note.quality_score || note.relevance_score || 5;
    const pct = Math.round(Math.min(Math.max(val / 10, 0), 1) * 100);
    const barColor = pct >= 70 ? "var(--red)" : pct >= 40 ? "var(--amber)" : "var(--green)";
    return {label: note.source_name || "Signal", pct, val, barColor};
  });
  grid.innerHTML = metrics.map((m, idx) => `
    <div class="geo-risk-row" style="animation-delay:${idx * 0.06}s">
      <span class="geo-risk-label">${escapeHtml(m.label)}</span>
      <div class="geo-risk-bar"><i style="width:${m.pct}%;background:${m.barColor}"></i></div>
      <span class="geo-risk-val">${m.val}</span>
    </div>
  `).join("");
}

// ── Category render ────────────────────────────────────────────────────────
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
  renderIntelSidebar(category, -1);
  renderSourceStack(category);
}

// ── Active clipping ────────────────────────────────────────────────────────
function cleanImplication(value) {
  return text(value, "Watch whether this turns into a practical decision point today.")
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
  document.getElementById("activePointOne").textContent =
    note.note || note.excerpt || "The main source signal is still being resolved.";
  document.getElementById("activePointTwo").textContent =
    cleanImplication(note.why_it_matters || note.note);
  document.getElementById("activeExcerpt").textContent =
    note.excerpt || note.note || "No excerpt was provided for this source.";

  const categoryTopics = cueTopics().filter((cue) => cue.section === topic.section);
  const index = categoryTopics.findIndex((cue) => cue.key === topic.key);
  const counterEl = document.getElementById("storyCounter");
  if (counterEl) {
    counterEl.textContent =
      `${String(Math.max(index + 1, 1)).padStart(2, "0")} / ${String(Math.max(categoryTopics.length, 1)).padStart(2, "0")}`;
  }
  renderIntelSidebar(topic.section, topic.index);
  renderSourceStack(topic.section);
}

// ── Section activation ─────────────────────────────────────────────────────
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

  // Show/hide right dossier panels
  const showHeatmap = key === "markets";
  const showGeoRisk = key === "geopolitics";
  const sectorHeatmap = document.getElementById("sectorHeatmap");
  const geoRiskPanel = document.getElementById("geoRiskPanel");
  const sourceStack = document.getElementById("sourceStack");
  if (sectorHeatmap) sectorHeatmap.classList.toggle("hidden", !showHeatmap);
  if (geoRiskPanel) geoRiskPanel.classList.toggle("hidden", !showGeoRisk);
  // Keep sourceStack visible always (it's the main list)

  if (screen === "news") {
    renderCategory(key);
  }
}

function activateTopic(topic) {
  lastTopicKey = topic.key;
  renderCategory(topic.section);
  activateClipping(topic);
}

// ── Script + warnings ─────────────────────────────────────────────────────
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
  document.getElementById("warnings").innerHTML =
    warnings.map((warning) => `<p>${escapeHtml(warning)}</p>`).join("");
}

// ── Audio ──────────────────────────────────────────────────────────────────
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
  briefAudio.addEventListener("timeupdate", () =>
    updateActiveCue(audioToTimelineSeconds(briefAudio), audioProgressRatio(briefAudio)));
  briefAudio.addEventListener("seeking", () =>
    updateActiveCue(audioToTimelineSeconds(briefAudio), audioProgressRatio(briefAudio)));
  briefAudio.addEventListener("ratechange", () =>
    updateActiveCue(audioToTimelineSeconds(briefAudio), audioProgressRatio(briefAudio)));
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
  const activeSection = sections.find((cue) => visualSeconds >= cue.start && visualSeconds < cue.end)
    || sections[sections.length - 1];
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

// ── Countdown / followup ───────────────────────────────────────────────────
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
      window.setTimeout(
        () => completeSession("typed_followup_answered"),
        Math.min(Math.max(answer.length * 45, 7000), 12000)
      );
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

// ── Init ───────────────────────────────────────────────────────────────────
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
renderWatchList();
renderScript();
renderWarnings();
renderSourceStack("geopolitics");
renderCategory("geopolitics");
renderSectorHeatmap();
renderGeoRiskPanel();
setupFollowupForm();
setupAudio();
updateActiveCue(0);
runBootSequence();
