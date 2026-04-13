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

function allNotes() {
  return ["geopolitics", "technology_ai", "markets"].flatMap((category) =>
    section(category).map((note, index) => ({category, index, note}))
  );
}

function compactDate(value) {
  if (!value) {
    return "";
  }
  try {
    return new Date(value).toLocaleString([], {
      month: "short",
      day: "numeric",
    });
  } catch {
    return value;
  }
}

function firstSentence(value, fallback) {
  const raw = text(value, "").trim();
  if (!raw) {
    return fallback;
  }
  const normalized = raw
    .replace(/^#+\s*/g, "")
    .replace(/\s+/g, " ")
    .trim();
  const match = normalized.match(/^(.+?[.!?])(?:\s|$)/);
  return (match ? match[1] : normalized).trim();
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
  const weather = data.weather || {};
  const temp = weather.temperature == null
    ? "weather data unavailable"
    : `${Math.round(weather.temperature)}${weather.temperature_unit || ""}`;
  const feels = weather.apparent_temperature == null
    ? ""
    : `, feels like ${Math.round(weather.apparent_temperature)}${weather.temperature_unit || ""}`;
  document.getElementById("weatherHeadline").textContent =
    `${text(weather.location_name, "Your location")}: ${temp}${feels}, ${text(weather.conditions, "mixed conditions")}`;
  document.getElementById("weatherAdvice").textContent =
    text(weather.advisory, "Check the local weather before stepping out.");
}

function renderWatchList() {
  const watch = data.watchlist || [];
  document.getElementById("watchList").innerHTML = watch.length
    ? watch.map((item) => `<article class="watch-item">${escapeHtml(item)}</article>`).join("")
    : `<article class="watch-item">No watch item passed the filter yet.</article>`;
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

function renderWarnings() {
  const warnings = data.warnings || [];
  document.getElementById("warnings").innerHTML =
    warnings.map((warning) => `<p>${escapeHtml(warning)}</p>`).join("");
}

function renderCategory(category) {
  if (!category || currentCategory === category) {
    return;
  }
  currentCategory = category;
  document.getElementById("categoryKicker").textContent = "Intel sequence";
  document.getElementById("categoryTitle").textContent = categoryLabels[category] || "Morning signal";
  renderSupportStack(category, -1);
  renderStoryRail(category, "");
  renderSourceStack(category);
}

function renderSupportStack(category, activeIndex) {
  const notes = section(category);
  const stack = document.getElementById("supportStack");
  if (!notes.length) {
    stack.innerHTML = `<article class="support-card"><strong>No constructive clipping</strong><p>No story passed the current filter for this pane.</p></article>`;
    return;
  }
  const selected = notes
    .map((note, index) => ({note, index}))
    .filter((item) => activeIndex < 0 || Math.abs(item.index - activeIndex) <= 1)
    .slice(0, 3);
  const cards = selected.length ? selected : notes.slice(0, 3).map((note, index) => ({note, index}));
  stack.innerHTML = cards.map(({note, index}) => `
    <article class="support-card ${index === activeIndex ? "is-active" : Math.abs(index - activeIndex) === 1 ? "is-near" : ""}">
      <span>${index === activeIndex ? "Current" : index < activeIndex ? "Previous" : "Next"}</span>
      <strong>${escapeHtml(note.headline)}</strong>
      <p>${escapeHtml(note.source_name || "Source")}</p>
    </article>
  `).join("");
}

function renderStoryRail(category, activeKey) {
  const topics = cueTopics().filter((topic) => topic.section === category);
  const rail = document.getElementById("storyRail");
  if (!topics.length) {
    rail.innerHTML = `<article class="story-dot"><span>00</span><strong>No active story cue</strong></article>`;
    return;
  }
  rail.innerHTML = topics.map((topic, index) => `
    <article class="story-dot ${topic.key === activeKey ? "is-active" : ""}">
      <span>${String(index + 1).padStart(2, "0")}</span>
      <strong>${escapeHtml(topic.headline || "Story cue")}</strong>
    </article>
  `).join("");
}

function renderSourceStack(category) {
  const notes = section(category);
  const stack = document.getElementById("sourceStack");
  document.getElementById("sourceCount").textContent = `${notes.length} items`;
  stack.innerHTML = notes.slice(0, 6).map((note) => `
    <article class="source-card">
      <small>${escapeHtml(note.source_name || "Source")}</small>
      <strong>${link(note.headline || "Untitled", note.url)}</strong>
      <p>${escapeHtml(compactDate(note.published_at))}</p>
    </article>
  `).join("") || `<article class="source-card"><strong>No source in focus</strong><p>Waiting for the first clipping.</p></article>`;
}

function cleanImplication(value) {
  return text(value, "Watch whether this turns into a practical decision point today.")
    .replace(/^why (it|this) matters( today)?\s*:\s*/i, "")
    .replace(/^this is important because\s*/i, "");
}

function activateClipping(topic) {
  const note = noteForTopic(topic);
  if (!note) {
    return;
  }
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
  document.getElementById("storyCounter").textContent =
    `${String(Math.max(index + 1, 1)).padStart(2, "0")} / ${String(Math.max(categoryTopics.length, 1)).padStart(2, "0")}`;
  renderSupportStack(topic.section, topic.index);
  renderStoryRail(topic.section, topic.key);
  renderSourceStack(topic.section);
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
    if (presentationMode) {
      startPresentationClock();
    }
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
    if (!briefAudio.ended) {
      stopAudioSyncLoop();
    }
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
  if (playbackStarting || !briefAudio.paused) {
    return;
  }
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
  if (!media || !media.src) {
    return Promise.resolve();
  }
  if (media.readyState >= 2) {
    return Promise.resolve();
  }
  media.load();
  return new Promise((resolve, reject) => {
    const timeout = window.setTimeout(() => {
      cleanup();
      resolve();
    }, 7000);
    function cleanup() {
      window.clearTimeout(timeout);
      media.removeEventListener("canplay", onReady);
      media.removeEventListener("loadeddata", onReady);
      media.removeEventListener("error", onError);
    }
    function onReady() {
      cleanup();
      resolve();
    }
    function onError() {
      cleanup();
      reject(new Error(`${label} media failed to load`));
    }
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
  if (!musicAudio.src || data.browser_music_enabled === false || data.music_enabled === false) {
    return;
  }
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
  if (!musicAudio || !musicAudio.src) {
    return;
  }
  if (musicFadeFrame) {
    cancelAnimationFrame(musicFadeFrame);
  }
  const startVolume = musicAudio.volume;
  const startedAt = performance.now();
  function step(now) {
    const progress = Math.min((now - startedAt) / Math.max(durationMs, 1), 1);
    musicAudio.volume = startVolume + (targetVolume - startVolume) * progress;
    if (progress < 1) {
      musicFadeFrame = requestAnimationFrame(step);
    }
  }
  musicFadeFrame = requestAnimationFrame(step);
}

function startPresentationClock() {
  if (presentationStartedAt != null) {
    return;
  }
  presentationStartedAt = performance.now();
  requestAnimationFrame(tickPresentationClock);
}

function tickPresentationClock() {
  if (presentationStartedAt == null) {
    return;
  }
  const elapsed = (performance.now() - presentationStartedAt) / 1000;
  if (!briefAudio || briefAudio.paused || briefAudio.currentTime < 0.25) {
    updateActiveCue(elapsed);
  }
  if (elapsed < totalTimelineSeconds() + 15) {
    requestAnimationFrame(tickPresentationClock);
  }
}

function startAudioSyncLoop() {
  if (audioSyncFrame) {
    return;
  }
  const tick = () => {
    if (!briefAudio || briefAudio.paused || briefAudio.ended) {
      audioSyncFrame = null;
      return;
    }
    updateActiveCue(audioToTimelineSeconds(briefAudio), audioProgressRatio(briefAudio));
    audioSyncFrame = requestAnimationFrame(tick);
  };
  audioSyncFrame = requestAnimationFrame(tick);
}

function stopAudioSyncLoop() {
  if (!audioSyncFrame) {
    return;
  }
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
    if (!cue || !fill) {
      return;
    }
    const duration = Math.max(cue.end - cue.start, 0.01);
    const ratio = seconds <= cue.start ? 0 : seconds >= cue.end ? 1 : (seconds - cue.start) / duration;
    fill.style.width = `${Math.min(Math.max(ratio, 0), 1) * 100}%`;
    node.classList.toggle("is-complete", seconds >= cue.end);
    if (state) {
      if (seconds >= cue.end) {
        state.textContent = "Done";
      } else if (seconds >= cue.start) {
        state.textContent = `${Math.max(Math.round(ratio * 100), 1)}% live`;
      } else {
        state.textContent = "Queued";
      }
    }
  });
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

function startClosingCountdown() {
  if (closingCountdownStarted) {
    return;
  }
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
    if (!value) {
      input.focus();
      return;
    }
    input.value = "";
    submitFollowup(value);
  });
}

function submitFollowup(question) {
  if (followupComplete) {
    return;
  }
  followupComplete = true;
  if (countdownTimer) {
    window.clearInterval(countdownTimer);
  }
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
  if (!form) {
    return;
  }
  form.querySelectorAll("input, button").forEach((node) => {
    node.disabled = disabled;
  });
}

function completeSession(reason) {
  if (sessionComplete) {
    return;
  }
  sessionComplete = true;
  if (countdownTimer) {
    window.clearInterval(countdownTimer);
  }
  setFollowupDisabled(true);
  fadeMusicTo(0, 1200);
  fetch("/api/session/complete", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({reason}),
  }).catch(() => {});
  window.setTimeout(() => {
    window.close();
  }, 900);
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
renderWatchList();
renderScript();
renderWarnings();
renderSourceStack("geopolitics");
renderCategory("geopolitics");
setupFollowupForm();
setupAudio();
updateActiveCue(0);
