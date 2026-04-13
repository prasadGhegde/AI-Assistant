# Morning Briefs

Morning Briefs is a local-first Mac morning assistant that generates a polished, cinematic work briefing at 8:00 a.m. It collects high-signal news, filters out low-value noise, adds current weather, writes a conversational script, creates MP3 narration with OpenAI text to speech, and opens a synchronized browser dashboard while the narration plays.

The target experience is premium, energetic, conversational, useful, and visually alive. It should not feel robotic, static, corny, or filled with generic news filler.

## Briefing Flow

1. Greeting and premium intro screen for Prasad.
2. Weather with temperature, conditions, carry/wear guidance, and useful rain, wind, or sun cautions.
3. Geopolitics.
4. Technology and AI.
5. Stock market.
6. Watch list for today.
7. Closing question, followed by a silent 10-second typed follow-up window.

Each spoken news section explains the practical implication naturally in the prose. Markdown headings exist for structure and dashboard synchronization, but they are not spoken.

## What It Creates

Every run writes:

- Raw collected source links, headlines, excerpts, timestamps, source names, and quality decisions:
  `data/raw/latest_sources.json`
- Extracted notes and ranked developments:
  `data/processed/latest_notes.json`
- Weather snapshot:
  `data/processed/latest_weather.json`
- Latest Markdown script:
  `output/scripts/latest.md`
- Latest MP3 narration:
  `output/audio/latest.mp3`
- Latest synchronized dashboard:
  `output/dashboard/latest.html`

## Architecture

```text
MorningBriefs/
  config/
    sources.json              # RSS source manifest
    news_quality.json         # filtering and relevance policy
    briefing_profile.json     # flow, section timing, tone contract
    skills_catalog.json       # category and subskill registry notes
  morning_briefs/
    collector.py              # gathers RSS links and excerpts
    quality.py                # blocks gossip/filler and scores source quality
    weather.py                # current weather and carry/wear guidance
    extractor.py              # ranks signals and dedupes stories
    writer.py                 # writes the timed Markdown narration script
    tts.py                    # streams Ryan-first OpenAI speech output to MP3
    dashboard.py              # renders dashboard data and timing cues
    browser.py                # opens and closes Chrome in presentation mode
    server.py                 # Flask backend for dashboard, follow-ups, and session audio
    skills/
      geopolitics.py
      technology_ai.py
      markets.py
      weather/SKILL.md
      subskills/
  SKILL.md                    # canonical product skill contract
  skills.md                   # lowercase mirror for older local references
  launchd/
  scripts/
```

The core pipeline is:

```text
collect -> good-news quality filter -> extract signals -> fetch weather -> write script -> synthesize Ryan MP3 -> render dashboard cues -> open Chrome -> browser audio drives UI sync -> listen for follow-up -> close tab
```

## Setup

```bash
cd /Users/prasadhegde/Documents/MorningBriefs
make setup
cp .env.example .env
```

Edit `.env` and add:

```bash
OPENAI_API_KEY=your_key_here
```

Optional weather and personalization settings:

```bash
MORNING_BRIEFS_USER_NAME=Prasad
MORNING_BRIEFS_WEATHER_LOCATION=Berlin
MORNING_BRIEFS_WEATHER_LAT=52.52
MORNING_BRIEFS_WEATHER_LON=13.405
MORNING_BRIEFS_WEATHER_TEMPERATURE_UNIT=celsius
MORNING_BRIEFS_WEATHER_WIND_UNIT=kmh
```

Optional model tuning:

```bash
OPENAI_SIGNAL_MODEL=gpt-5.4-mini
OPENAI_WRITER_MODEL=gpt-5.4
OPENAI_TTS_MODEL=gpt-4o-mini-tts
OPENAI_TTS_VOICE=ryan
MORNING_BRIEFS_FORCE_RYAN=true
OPENAI_TTS_FALLBACK_VOICE=cedar
MORNING_BRIEFS_AUDIO_DRIVER=browser
MORNING_BRIEFS_VOICE_EFFECT_ENABLED=true
MORNING_BRIEFS_VOICE_EFFECT_MODE=subtle_assistant
MORNING_BRIEFS_VOICE_EFFECT_DEFAULT_PRESET=jarvis_clean
MORNING_BRIEFS_VOICE_EFFECT_RENDER_ALL=true
```

## Run Manually

Generate, open the browser, and play the briefing:

```bash
python3 -m morning_briefs run --play
```

Or:

```bash
make briefing
```

Generate without audio and without opening the browser:

```bash
python3 -m morning_briefs run --skip-tts --no-open
```

Serve the latest dashboard:

```bash
python3 -m morning_briefs dashboard
```

Then visit:

```text
http://127.0.0.1:8765
```

## Browser And Audio Sync

When `run --play` is used, Chrome opens directly in kiosk fullscreen presentation mode with an isolated per-run Chrome profile, so an already-open Chrome session cannot ignore the presentation flags. The browser audio element plays the briefing. The UI reads the actual audio time on animation frames, builds cue proportions from the script section word counts, scales those proportions to the real MP3 duration, moves through greeting, weather, news, watch list, and closing, and highlights the active story/card as Ryan speaks.

The `afplay` path remains available when `MORNING_BRIEFS_AUDIO_DRIVER=afplay`, but the default is browser-driven audio because it gives the strongest narration-to-UI synchronization. If Chrome blocks autoplay, use the `Start Ryan` button; the UI will sync from actual audio playback once started.

At the close, Ryan asks one useful follow-up question and then stops. The dashboard opens a typed follow-up box for 10 seconds and does not start microphone listening. If you type a question, the local Flask backend returns a fast text answer in the UI, leaves it visible briefly, and then closes the Chrome tab. If there is no reply, the dashboard closes cleanly without a broken listening state.

Fullscreen launch is controlled with:

```bash
MORNING_BRIEFS_BROWSER_FULLSCREEN=true
MORNING_BRIEFS_BROWSER_KIOSK=true
MORNING_BRIEFS_BROWSER_HIDE_FULLSCREEN_TOOLBAR=true
MORNING_BRIEFS_BROWSER_RESTORE_FULLSCREEN_TOOLBAR=true
```

Kiosk mode is the default presentation path because it is the reliable Chrome fullscreen mode on macOS. The launcher also asks Chrome to enter native macOS fullscreen and, when accessibility permissions allow it, temporarily unchecks `View > Always Show Toolbar in Full Screen`; it restores that setting when the briefing closes. Set kiosk mode to `false` only if you specifically want normal browser chrome.

## Background Music

When music is enabled, Morning Briefs uses the local uploaded file at `assets/audio/jarvis_proper_8min.wav`. The browser plays that WAV under Ryan during presentation and ducks it while narration is active. The file is 380 seconds long, so the script target is capped to fit under 6 minutes and 20 seconds. Install `ffmpeg` to additionally mix the same WAV into the final MP3 with automatic sidechain ducking so the voice stays dominant:

```bash
brew install ffmpeg
```

If `ffmpeg` is unavailable, the run still completes, the browser music still plays during presentation, and the app warns that music could not be mixed into the MP3.

## Narration Framework

Morning Briefs uses a controlled narration framework instead of letting the model freestyle the opening and closing each day. The curated phrase banks live in `config/narration_phrases.json`, and the product rules are documented in `SKILL.md`. Each run selects one approved greeting, operation name, intro template, transition line per section, watchlist intro, closing, and final question. Recent selections are tracked in `data/narration_history.json` so the same greeting, operation name, and closing are not reused too frequently.

Preview the approved variation without collecting news:

```bash
python3 scripts/sample_narration.py --count 5
```

To add more approved lines later, append entries to the relevant array in `config/narration_phrases.json`; no business logic changes are required. Entries can remain strings, or later be changed to objects with `text` and `weight` fields for weighted randomization.

## Voice Effect

After OpenAI TTS generates Ryan's clean narration, Morning Briefs can render a batch of premium AI-assistant voice textures using `ffmpeg`. The default playback preset is `jarvis_clean`; `MORNING_BRIEFS_VOICE_EFFECT_RENDER_ALL=true` also saves comparison renders for every speech-friendly preset.

```bash
MORNING_BRIEFS_VOICE_EFFECT_ENABLED=true
MORNING_BRIEFS_VOICE_EFFECT_DEFAULT_PRESET=jarvis_clean
MORNING_BRIEFS_VOICE_EFFECT_RENDER_ALL=true
MORNING_BRIEFS_VOICE_EFFECT_SAVE_WAVS=true
```

Presets currently include `clean_ai`, `subtle_assistant`, `jarvis_clean`, `jarvis_like`, `radio_comms`, `tactical_brief`, `hologram`, `synthetic_warm`, `stronger_robot`, `bitcrushed_bot`, and `masked_vocoder_style`. They are designed as general premium AI/radio/synthetic textures, not as voice cloning.

When enabled, the audio pipeline preserves the clean TTS reference and writes:

```text
output/audio/original_tts.wav
output/audio/robotic_tts.wav
output/audio/briefing_clean.mp3
output/audio/briefing_voice_01_clean_ai.mp3
output/audio/briefing_voice_01_clean_ai_final.mp3
```

The app plays only the configured default final mix automatically. The other variants are saved alongside it for manual comparison. If `ffmpeg` is unavailable, the run continues with the original TTS and records a warning.

Each run also writes diagnostics to:

```text
logs/latest_diagnostics.json
```

That file includes raw article counts, accepted/rejected counts, extracted note counts, final script section lengths, the selected narration plan, and saved voice variant paths.

## Schedule At 8:00 A.M. On Mac

Install the launchd job:

```bash
make install-launchd
```

The plist lives at:

```text
launchd/com.prasad.morningbriefs.plist
```

It runs:

```text
scripts/run_daily.sh
```

At 8:00 a.m. local Mac time, Morning Briefs generates the briefing, opens the browser, and plays the MP3.

Unload the job:

```bash
make unload-launchd
```

## Source Quality

Edit `config/sources.json` to tune source selection. Edit `config/news_quality.json` to adjust filters.

The quality layer rejects or down-ranks:

- Celebrity, gossip, entertainment, relationship, or influencer stories.
- Person-versus-person commentary unless it has direct geopolitical, technological, or financial significance.
- Opinion-heavy items without hard news value.
- Low-value reaction articles.
- Vague trend summaries without concrete developments.
- Filler roundups and SEO explainers when better source material exists.
- Doom-heavy, panic-driven, gloomy, or depressing stories when good-news-only mode is enabled.

Good-news-only mode is enabled by default with `MORNING_BRIEFS_GOOD_NEWS_ONLY=true`. It favors constructive diplomacy, breakthroughs, approvals, strong demand, earnings beats, useful investment, de-escalation, progress, and forward-looking developments. Raw JSON keeps quality scores and reasons, so you can see why a story was accepted or rejected.

## Voice And Model Choices

The default `.env.example` keeps signal extraction on `gpt-5.4-mini` and moves script writing to `gpt-5.4` for stronger prose. The default speech model is `gpt-4o-mini-tts` with Ryan enforced by `MORNING_BRIEFS_FORCE_RYAN=true`, so greeting, weather, news, watch list, and the spoken closing question use the same Ryan-first TTS path. Follow-up answers are typed in the UI for reliability.

If the OpenAI API account/runtime does not accept `ryan` as a speech voice, the synthesizer retries the whole clip with `OPENAI_TTS_FALLBACK_VOICE=cedar` and records a warning. This avoids mixing voices mid-session. The code avoids cloning or naming any copyrighted character voice. The speech implementation uses the OpenAI Audio API speech endpoint with streaming response output; see the official [OpenAI audio and speech guide](https://platform.openai.com/docs/guides/audio?lang=python).

## Tests

```bash
make test
```

The tests cover story-key normalization, TTS chunking, cross-category duplicate avoidance, good-news filtering, Ryan-first config, shortened weather timing, and the fallback script contract.

## Notes

Morning Briefs is local-first, but collection needs internet access for RSS/weather and OpenAI access for model writing and MP3 narration. If network or OpenAI access is unavailable, the app still saves raw JSON, extracted notes, a fallback script, and the dashboard, with warnings.
