# Morning Briefs

**A local-first tactical AI morning briefing for macOS.**

Morning Briefs turns the start of the workday into a cinematic mission debrief: live weather, high-signal geopolitics, technology and AI updates, markets, spoken narration, background music, and a synchronized tactical dashboard. It is built for a fast morning readout that feels premium, useful, and alive rather than static or generic.

> Operation Daybreak: Ryan narrates, the dashboard moves, and the active intelligence cards follow the briefing in real time.

## What It Does

Morning Briefs collects fresh source material, filters noise, extracts the strongest signals, writes a polished spoken script, generates Ryan-first OpenAI TTS narration, mixes in a music bed, and opens a Chrome presentation dashboard. The browser view advances with the audio, highlights the active topic, and closes cleanly after the final follow-up window.

The result is a local Mac assistant that feels closer to a tactical operations console than a normal news page.

## Highlights

- Mission-style morning debrief with curated greetings, operation names, transitions, and closings.
- Synchronized audio and dashboard choreography driven by real browser playback time.
- Dedicated flow for greeting, weather, geopolitics, technology/AI, markets, and typed follow-up.
- Dense modular intelligence-card UI inspired by command-center dashboards.
- OpenAI TTS narration with Ryan-first voice configuration and fallback handling.
- Optional robotic/premium AI voice post-processing via `ffmpeg`.
- Background music bed using a local WAV file, with browser playback and MP3 mixing support.
- Active-card highlighting, progress rail, fullscreen Chrome presentation, and automatic close.
- Weather guidance with temperature, conditions, wear/carry recommendation, and alerts.
- Market readouts for crypto, crude oil, FX, sector heat, macro movers, and sentiment.
- Deterministic fake-data fallback for empty cards, marked with a red dot so mock values are never confused with live data.
- Configurable source quality filters, good-news preference, narration phrase banks, and model choices.

## Screenshots

Add screenshots to `docs/screenshots/` and update the links below before publishing a visual release.

| View | Description |
| --- | --- |
| `docs/screenshots/greeting.png` | Operation boot / greeting screen |
| `docs/screenshots/weather.png` | Tactical field-conditions board |
| `docs/screenshots/intel-wall.png` | Modular geopolitics, technology, and markets dashboard |
| `docs/screenshots/followup.png` | Typed follow-up / mission close state |

GitHub-friendly image pattern:

```md
![Operation Daybreak dashboard](docs/screenshots/intel-wall.png)
```

## Demo Video

Use this section for the public product demo.

Recommended GitHub pattern:

```md
[![Watch Operation Daybreak](docs/screenshots/video-thumbnail.png)](https://github.com/user-attachments/assets/your-demo-video-id)
```

You can also point the thumbnail at YouTube or Vimeo:

```md
[![Watch Operation Daybreak](docs/screenshots/video-thumbnail.png)](https://www.youtube.com/watch?v=YOUR_VIDEO_ID)
```

## How It Works

```text
RSS / APIs / weather
        |
        v
quality filter -> signal extraction -> script writer
        |                              |
        v                              v
 raw JSON + notes              Markdown + spoken text
        |                              |
        v                              v
 dashboard data + cue timeline    OpenAI TTS + voice FX + music
        |                              |
        +---------------> Chrome presentation <---------------+
```

The browser presentation is not a passive page. It receives a timeline, plays the narration in the browser, reads the actual audio time, advances sections, highlights the active card, keeps the music bed under the voice, and posts a completion signal so the Python runner can close Chrome.

## Project Structure

```text
MorningBriefs/
  config/                         # sources, quality policy, narration phrase banks
  morning_briefs/
    collector.py                  # RSS/source collection
    quality.py                    # relevance and good-news filtering
    extractor.py                  # signal extraction and ranking
    writer.py                     # Markdown + spoken script generation
    tts.py                        # OpenAI speech synthesis
    audio_fx.py                   # ffmpeg voice effect presets
    music.py                      # music-bed mixing
    weather.py                    # weather and carry/wear guidance
    intel_data.py                 # dashboard data modules and mock fallbacks
    dashboard.py                  # static dashboard render + timeline data
    browser.py                    # Chrome launch, fullscreen, and close orchestration
    server.py                     # local Flask dashboard/follow-up server
    web/
      static/dashboard.css
      static/dashboard.js
      templates/dashboard.html
  assets/audio/                   # local background music
  docs/screenshots/               # README screenshot and video thumbnail assets
  launchd/                        # macOS 8 a.m. scheduling plist
  scripts/                        # launchd, dashboard fixture, audio test helpers
  tests/                          # pipeline contract tests
  SKILL.md                        # product behavior contract
  skills.md                       # runtime-readable behavior contract
```

## Requirements

- macOS
- Python 3.9+
- Google Chrome
- OpenAI API key
- `ffmpeg` for voice effects and MP3 music mixing
- Optional: macOS Accessibility permission for Chrome fullscreen toolbar control

Install `ffmpeg`:

```bash
brew install ffmpeg
```

## Setup

```bash
git clone https://github.com/prasadGhegde/AI-Assistant.git
cd AI-Assistant
make setup
cp .env.example .env
```

Edit `.env`:

```bash
OPENAI_API_KEY=your_key_here
MORNING_BRIEFS_USER_NAME=Prasad
MORNING_BRIEFS_WEATHER_LOCATION=Berlin
MORNING_BRIEFS_WEATHER_LAT=52.52
MORNING_BRIEFS_WEATHER_LON=13.405
```

## Run

Generate and play the full briefing:

```bash
make briefing
```

Equivalent direct command:

```bash
python3 -m morning_briefs run --play
```

Generate without TTS or browser launch:

```bash
python3 -m morning_briefs run --skip-tts --no-open
```

Replay the latest saved dashboard/audio without source fetching, OpenAI calls, or TTS generation:

```bash
make replay
```

Render a static dashboard fixture from the latest saved JSON:

```bash
make dashboard_fixture
```

## Configuration

Most behavior is controlled through `.env`.

```bash
# Models and voice
OPENAI_SIGNAL_MODEL=gpt-5.4-mini
OPENAI_WRITER_MODEL=gpt-5.4
OPENAI_TTS_MODEL=gpt-4o-mini-tts
OPENAI_TTS_VOICE=ryan
MORNING_BRIEFS_FORCE_RYAN=true
OPENAI_TTS_FALLBACK_VOICE=cedar

# Presentation
MORNING_BRIEFS_AUDIO_DRIVER=browser
MORNING_BRIEFS_OPEN_BROWSER=true
MORNING_BRIEFS_BROWSER_APP="Google Chrome"
MORNING_BRIEFS_BROWSER_CLOSE_ON_END=true
MORNING_BRIEFS_BROWSER_KIOSK=true
MORNING_BRIEFS_BROWSER_FULLSCREEN=true

# Music and voice effects
MORNING_BRIEFS_MUSIC_ENABLED=true
MORNING_BRIEFS_MUSIC_SOURCE=/absolute/path/to/assets/audio/jarvis_proper_8min.wav
MORNING_BRIEFS_VOICE_EFFECT_ENABLED=true
MORNING_BRIEFS_VOICE_EFFECT_DEFAULT_PRESET=jarvis_clean
MORNING_BRIEFS_VOICE_EFFECT_RENDER_ALL=false

# Dashboard testing
MORNING_BRIEFS_USE_FAKE_DATA_WHEN_EMPTY=true
```

### Narration Phrase Banks

Curated greetings, operation names, transitions, closings, and timeout lines live in:

```text
config/narration_phrases.json
```

The writer selects from approved banks so the structure stays consistent while the wording still varies. Add new lines to the JSON arrays to extend the assistant without changing business logic.

### Fake Data Fallback

`MORNING_BRIEFS_USE_FAKE_DATA_WHEN_EMPTY=true` only fills cards when real data is missing. It does not override real provider data. Mock-backed cards display:

- a `mock` status pill
- a small red dot in the top-right corner
- deterministic, domain-specific values tuned for visual testing

## Outputs

Every full run writes local artifacts:

```text
data/raw/latest_sources.json          # collected source links and excerpts
data/processed/latest_notes.json      # extracted notes and ranked sections
data/processed/latest_weather.json    # weather snapshot
output/scripts/latest.md              # latest Markdown script
output/audio/latest.mp3               # latest narration mix
output/dashboard/latest.html          # latest dashboard
logs/latest_diagnostics.json          # run diagnostics
```

These are local runtime artifacts and are ignored for normal repository work.

## Scheduling At 8 A.M.

Install the launchd job:

```bash
make install-launchd
```

Unload it:

```bash
make unload-launchd
```

The plist lives at:

```text
launchd/com.prasad.morningbriefs.plist
```

## Testing

```bash
make test
```

The contract tests cover filtering, narration planning, fallback script behavior, dashboard timing, fake-data fallback, weather wording, and the replayable UI path.

## Roadmap

- Add curated screenshot and video assets to the README.
- Add richer market data providers for breadth, sectors, commodities, and rates.
- Add optional structured transcripts with per-sentence timestamps.
- Add a persistent local archive browser for previous briefings.
- Add more polished preset packs for voice effects and music beds.

## Safety And Scope

Morning Briefs is an informational local assistant. It is not financial, legal, medical, or security advice. It uses source filtering and model-generated summaries, so important decisions should still be checked against primary sources.

## License

No license file is currently included. Add a `LICENSE` file before distributing or accepting external contributions.


Video Reference


https://github.com/user-attachments/assets/4253e792-a351-410e-8c50-543126dea56d




