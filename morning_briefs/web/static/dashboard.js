const data = window.MORNING_BRIEF || {};

const positions = [
  [24, 36],
  [44, 24],
  [62, 46],
  [37, 63],
  [70, 28],
  [53, 70],
];

const radarPositions = [
  [50, 20],
  [68, 38],
  [44, 46],
  [30, 64],
  [74, 72],
];

function section(name) {
  return (data.sections && data.sections[name]) || [];
}

function text(value, fallback = "") {
  return value || fallback;
}

function link(label, url) {
  if (!url) {
    return label;
  }
  return `<a href="${escapeAttr(url)}" target="_blank" rel="noreferrer">${escapeHtml(label)}</a>`;
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

function renderSignals(containerId, notes) {
  const container = document.getElementById(containerId);
  container.innerHTML = notes.map((note) => `
    <article class="signal">
      <strong>${link(note.headline, note.url)}</strong>
      <p>${escapeHtml(note.why_it_matters || note.note || "")}</p>
    </article>
  `).join("");
}

function renderHotspots() {
  const hotspots = document.getElementById("hotspots");
  hotspots.innerHTML = section("geopolitics").map((note, index) => {
    const [left, top] = positions[index % positions.length];
    return `<span class="hotspot" title="${escapeAttr(note.headline)}" style="left:${left}%;top:${top}%"></span>`;
  }).join("");
}

function renderRadar() {
  const pips = document.getElementById("radarPips");
  pips.innerHTML = section("technology_ai").map((note, index) => {
    const [left, top] = radarPositions[index % radarPositions.length];
    return `<span class="pip" title="${escapeAttr(note.headline)}" style="left:${left}%;top:${top}%"></span>`;
  }).join("");
}

function renderHeatMap() {
  const notes = section("markets");
  const heatMap = document.getElementById("heatMap");
  const classes = ["hot", "cool", "neutral"];
  heatMap.innerHTML = notes.map((note, index) => `
    <article class="heat-tile ${classes[index % classes.length]}">
      <strong>${escapeHtml(note.headline)}</strong>
      <span>${escapeHtml(note.source_name || "Source")}</span>
    </article>
  `).join("");
}

function renderMovers() {
  const movers = data.market_movers || [];
  const board = document.getElementById("moversBoard");
  if (!movers.length) {
    board.innerHTML = `<article class="mover"><strong>No ticker-heavy mover found yet</strong><p>Check the market feed after premarket updates.</p></article>`;
    return;
  }
  board.innerHTML = movers.map((mover) => `
    <article class="mover">
      <strong>${escapeHtml(mover.ticker || "MOVE")}: ${link(mover.headline || "", mover.url)}</strong>
      <p>${escapeHtml(mover.source || "")}</p>
    </article>
  `).join("");
}

function renderWatchList() {
  const watch = data.watchlist || [];
  document.getElementById("watchList").innerHTML = watch.map((item) => `
    <article class="watch-item">${escapeHtml(item)}</article>
  `).join("");
}

function renderScript() {
  const target = document.getElementById("scriptText");
  const lines = String(data.script_markdown || "").split("\n");
  target.innerHTML = lines.map((line) => {
    const trimmed = line.trim();
    if (!trimmed) {
      return "";
    }
    if (trimmed.startsWith("## ")) {
      return `<h3>${escapeHtml(trimmed.slice(3))}</h3>`;
    }
    if (trimmed.startsWith("# ")) {
      return `<h2>${escapeHtml(trimmed.slice(2))}</h2>`;
    }
    if (trimmed.startsWith("- [")) {
      const match = trimmed.match(/^- \[([^\]]+)\]\(([^)]+)\)/);
      if (match) {
        return `<p>${link(match[1], match[2])}</p>`;
      }
    }
    return `<p>${escapeHtml(trimmed)}</p>`;
  }).join("");
}

function setupAudio() {
  const button = document.getElementById("playButton");
  const audio = document.getElementById("briefAudio");
  if (!data.audio_src) {
    button.disabled = true;
    button.textContent = "No audio yet";
    return;
  }
  button.addEventListener("click", () => {
    audio.play();
  });
}

function renderWarnings() {
  const warnings = data.warnings || [];
  const target = document.getElementById("warnings");
  target.innerHTML = warnings.map((warning) => `<p>${escapeHtml(warning)}</p>`).join("");
}

document.getElementById("matterLine").textContent = text(data.what_matters_today, "No signal line generated yet.");
document.getElementById("wordCount").textContent = `${data.word_count || 0} words`;
document.getElementById("modelUsed").textContent = `signals: ${text(data.model_used && data.model_used.signals, "n/a")} | script: ${text(data.model_used && data.model_used.script, "n/a")}`;

renderHotspots();
renderRadar();
renderHeatMap();
renderMovers();
renderSignals("geoList", section("geopolitics"));
renderSignals("techList", section("technology_ai"));
renderWatchList();
renderScript();
setupAudio();
renderWarnings();
