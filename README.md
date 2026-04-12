# Morning Briefs

Morning Briefs is a local-first Mac project that generates an eight-minute work morning briefing every day at 8:00 a.m. It collects fresh source links, extracts category signals, writes a conversational Markdown script, creates MP3 narration with OpenAI text to speech, and renders a bold local HTML dashboard.

The briefing sections are:

- Geopolitics
- Technology and AI
- Stock market
- Watch list for today

Each spoken section is written as prose and ends with a conversational `Why it matters today:` close.

## What It Creates

Every run writes:

- Raw collected source links, headlines, excerpts, timestamps, and source names:
  `data/raw/latest_sources.json`
- Extracted notes and ranked developments:
  `data/processed/latest_notes.json`
- Latest Markdown script:
  `output/scripts/latest.md`
- Latest MP3 narration:
  `output/audio/latest.mp3`
- Latest dashboard:
  `output/dashboard/latest.html`

## Architecture

```text
MorningBriefs/
  config/
    sources.json              # RSS source manifest
    briefing_profile.json     # section lengths and writing contract
    skills_catalog.json       # category and subskill registry notes
  morning_briefs/
    collector.py              # gathers RSS links and excerpts
    extractor.py              # ranks signals and dedupes stories
    writer.py                 # writes the 1000-1100 word Markdown script
    tts.py                    # streams OpenAI speech output to MP3
    dashboard.py              # renders the local HTML dashboard
    server.py                 # Flask backend for the dashboard
    skills/
      geopolitics.py
      technology_ai.py
      markets.py
      subskills/
  data/
  output/
  launchd/
  scripts/
```

The skill files are regular Python modules. Add new categories by creating another `DomainSkill`, adding subskills, and registering it in `morning_briefs/skills/__init__.py`.

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

The default text model is `gpt-5-mini`, and the default speech model is `gpt-4o-mini-tts`. You can change both in `.env`. The speech implementation uses the OpenAI Audio API speech endpoint with streaming response output; see the official [OpenAI audio and speech guide](https://platform.openai.com/docs/guides/audio?lang=python).

## Run Manually

```bash
python3 -m morning_briefs run --play
```

Or, after `make setup`:

```bash
make briefing
```

Use this during development if you want to skip MP3 generation:

```bash
python3 -m morning_briefs run --skip-tts
```

## Dashboard

After a run, open the generated dashboard directly:

```bash
open output/dashboard/latest.html
```

Or serve it through the Python backend:

```bash
python3 -m morning_briefs dashboard
```

Then visit:

```text
http://127.0.0.1:8765
```

The dashboard includes a geopolitics hotspot panel, technology trend radar, stock heat map, movers board, watch list, final script, and audio player. Browser autoplay can be blocked by the browser, so the scheduled 8:00 a.m. audio path uses Mac `afplay` from launchd.

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

That script calls:

```bash
python3 -m morning_briefs run --play
```

At 8:00 a.m. local Mac time, Morning Briefs generates the briefing and plays `output/audio/latest.mp3` with `afplay`.

Unload the job:

```bash
make unload-launchd
```

## Source And Skill Tuning

Edit `config/sources.json` to add, remove, or rebalance RSS feeds. Each source can define:

- `name`
- `url`
- `kind`
- `source_weight`
- `tags`

Edit skill modules under `morning_briefs/skills/` to tune ranking logic. The current subskills are:

- Geopolitics: regional security, diplomacy and sanctions, energy and trade routes
- Technology and AI: frontier AI, chips and compute, cyber and policy
- Markets: macro and rates, earnings and movers, sector rotation

## Tests

```bash
make test
```

The tests cover story-key normalization, TTS chunking, cross-category duplicate avoidance, and the fallback script contract.

## Notes

Morning Briefs is local-first, but collection still needs internet access to fetch RSS feeds, and narration/model writing needs `OPENAI_API_KEY`. If the key is missing, the project still saves raw JSON, extracted notes, a fallback Markdown script, and the dashboard; MP3 generation is skipped.
