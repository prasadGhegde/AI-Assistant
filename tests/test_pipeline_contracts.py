import unittest
import tempfile
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from morning_briefs.audio_fx import VoiceEffectProcessor
from morning_briefs.browser import BrowserPresenter
from morning_briefs.config import load_config
from morning_briefs.dashboard import DashboardRenderer
from morning_briefs.extractor import SignalExtractor
from morning_briefs.intel_data import DashboardIntelCollector
from morning_briefs.models import ExtractedNote, RawItem, ScriptPackage, SignalPackage, WeatherReport
from morning_briefs.narration import NarrationPlanner
from morning_briefs.quality import NewsQualityFilter
from morning_briefs.server import create_app
from morning_briefs.weather import weather_guidance
from morning_briefs.writer import ScriptWriter, strip_markdown_for_speech


def raw_item(category, headline, url):
    return RawItem(
        id=f"{category}-{url}",
        category=category,
        source_name="Test Source",
        source_url="https://example.com/feed",
        headline=headline,
        url=url,
        excerpt="A short excerpt about AI, rates, sanctions, and markets.",
        published_at="2026-04-12T06:00:00+00:00",
        collected_at="2026-04-12T06:10:00+00:00",
        tags=["test"],
        source_weight=1.0,
        freshness_hours=1.0,
    )


class PipelineContractsTest(unittest.TestCase):
    def test_quality_filter_blocks_gossip(self):
        config = replace(load_config(), openai_api_key="")
        item = raw_item(
            "technology_ai",
            "Celebrity fans react after ex says something about AI feud",
            "https://example.com/gossip",
        )
        decision = NewsQualityFilter(config).evaluate(item)
        self.assertFalse(decision.is_relevant)
        self.assertTrue(any(reason.startswith("blocked:") for reason in decision.reasons))

    def test_good_news_filter_blocks_doom_when_not_constructive(self):
        config = replace(load_config(), openai_api_key="", good_news_only=True)
        item = raw_item(
            "markets",
            "Stocks plunge as recession panic hits market",
            "https://example.com/doom",
        )
        decision = NewsQualityFilter(config).evaluate(item)
        self.assertFalse(decision.is_relevant)
        self.assertTrue(any(reason.startswith("negative_tone:") for reason in decision.reasons))

    def test_default_tts_voice_is_ryan_first(self):
        config = load_config()
        self.assertEqual(config.openai_tts_voice, "ryan")
        self.assertTrue(config.openai_tts_allow_fallback)
        self.assertTrue(config.browser_fullscreen)
        self.assertTrue(config.browser_kiosk_mode)
        self.assertTrue(config.browser_hide_toolbar_in_fullscreen)

    def test_browser_presenter_launches_direct_chrome_kiosk(self):
        config = replace(
            load_config(),
            chrome_user_data_dir=Path("/tmp/morning-briefs-test-chrome"),
            browser_kiosk_mode=True,
            presentation_start_delay_seconds=0,
        )
        presenter = BrowserPresenter(config)
        with patch.object(
            presenter,
            "_chrome_executable",
            return_value="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        ), patch.object(
            presenter, "_prepare_native_fullscreen", return_value=[]
        ), patch("morning_briefs.browser.subprocess.Popen") as popen:
            warnings = presenter.open_url(
                "http://127.0.0.1:8765/?presentation=1&autoplay=1",
                presentation=True,
            )
        self.assertEqual(warnings, [])
        command = popen.call_args.args[0]
        self.assertEqual(
            command[0], "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        )
        self.assertIn("--kiosk", command)
        self.assertNotIn("--start-fullscreen", command)
        self.assertTrue(
            any(
                arg.startswith("--user-data-dir=/tmp/morning-briefs-test-chrome/presentation-")
                for arg in command
            )
        )

    def test_extractor_avoids_cross_category_duplicate_headlines(self):
        config = replace(load_config(), openai_api_key="")
        extractor = SignalExtractor(config)
        items = [
            raw_item("geopolitics", "Leaders agree new AI sanctions deal", "https://example.com/a"),
            raw_item("technology_ai", "Leaders agree new AI sanctions deal", "https://example.com/b"),
            raw_item("technology_ai", "New chip platform reaches data centers", "https://example.com/c"),
            raw_item("markets", "Stocks watch Fed rates and earnings", "https://example.com/d"),
        ]
        sections = extractor._heuristic_sections(items)
        tech_headlines = [note.headline for note in sections["technology_ai"]]
        self.assertNotIn("Leaders agree new AI sanctions deal", tech_headlines)

    def test_fallback_script_contains_required_sections(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = replace(
                load_config(),
                openai_api_key="",
                narration_history_path=Path(tmpdir) / "narration_history.json",
            )
            now = datetime(2026, 4, 12, 8, 0, tzinfo=config.timezone)
            note = ExtractedNote(
                category="geopolitics",
                headline="Ceasefire talks resume",
                source_name="Test Source",
                url="https://example.com/geo",
                published_at="2026-04-12T06:00:00+00:00",
                excerpt="Talks resume after overnight diplomacy.",
                note="Negotiators are testing whether the agreement can hold through the morning.",
                score=1.0,
                subskills=["diplomacy_sanctions"],
                tags=["test"],
                why_it_matters="Why it matters today: it can change the risk tone before meetings begin.",
            )
            signals = SignalPackage(
                generated_at=now.isoformat(),
                lookback_hours=24,
                what_matters_today="A diplomatic thread, an AI thread, and a market thread all need attention.",
                sections={
                    "geopolitics": [note],
                    "technology_ai": [replace(note, category="technology_ai", headline="AI platform update lands")],
                    "markets": [replace(note, category="markets", headline="Markets watch rates")],
                },
            )
            script, _ = ScriptWriter(config).write(signals, now)
            plan = script.narration_plan
            self.assertIn(plan["opening_line"], script.markdown)
            self.assertIn(plan["closing_line"], script.markdown)
            self.assertIn("## Geopolitics", script.markdown)
            self.assertIn("## Technology and AI", script.markdown)
            self.assertIn("## Stock market", script.markdown)
            self.assertIn("## Closing question", script.markdown)
            self.assertNotIn("The watch list turns the briefing into action", script.markdown)
            self.assertNotIn("I will pause for ten seconds", script.markdown)
            self.assertNotIn("From Test Source", script.spoken_text)
            self.assertNotIn("Second signal:", script.spoken_text)
            self.assertNotIn(signals.what_matters_today, script.sections["greeting"])

    def test_narration_planner_selects_from_curated_banks(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = replace(
                load_config(),
                narration_history_path=Path(tmpdir) / "narration_history.json",
            )
            planner = NarrationPlanner(config)
            now = datetime(2026, 4, 12, 8, 0, tzinfo=config.timezone)
            plan = planner.select(now, persist=False)
            banks = planner.banks
            self.assertIn(plan.greeting, banks["greetings"])
            self.assertIn(plan.operation_name, banks["operation_names"])
            self.assertIn(plan.closing, banks["closings"])
            self.assertIn(plan.final_question, banks["final_questions"])
            self.assertIn(plan.timeout_closing, [entry["text"] if isinstance(entry, dict) else entry for entry in banks["timeout_closings"]])
            self.assertIn(plan.operation_name, plan.opening_line)
            self.assertTrue(plan.timeout_closing_line.endswith("Captain."))

    def test_sparse_model_script_falls_back_cleanly(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = replace(
                load_config(),
                openai_api_key="test-key",
                narration_history_path=Path(tmpdir) / "narration_history.json",
            )
            now = datetime(2026, 4, 12, 8, 0, tzinfo=config.timezone)
            note = ExtractedNote(
                category="geopolitics",
                headline="Constructive diplomacy resumes",
                source_name="Test Source",
                url="https://example.com/geo",
                published_at="2026-04-12T06:00:00+00:00",
                excerpt="Diplomats returned to talks after a productive weekend.",
                note="Negotiators are testing a practical channel that could lower tension and support trade planning.",
                score=1.0,
                why_it_matters="It gives teams a cleaner risk signal before the workday begins.",
            )
            signals = SignalPackage(
                generated_at=now.isoformat(),
                lookback_hours=24,
                what_matters_today="Constructive diplomacy, useful AI deployment, and market resilience are in focus.",
                sections={
                    "geopolitics": [note],
                    "technology_ai": [replace(note, category="technology_ai", headline="AI deployment expands")],
                    "markets": [replace(note, category="markets", headline="Market breadth improves")],
                },
            )
            sparse = (
                "# Operation Test\n\n"
                "## Greeting\nHello.\n\n"
                "## Weather\nWeather.\n\n"
                "## Geopolitics\nGlobal transition.\n\n"
                "## Technology and AI\nTechnology transition.\n\n"
                "## Stock market\nMarket transition.\n\n"
                "## Closing question\nQuestion?"
            )
            with patch.object(ScriptWriter, "_write_with_model", return_value=sparse):
                script, warnings = ScriptWriter(config).write(signals, now)
            self.assertNotIn("## Greeting\nHello.", script.markdown)
            self.assertNotIn("## Weather\nWeather.", script.markdown)
            self.assertGreater(script.word_count, 180)
            self.assertTrue(any("incomplete draft" in warning for warning in warnings))

    def test_fallback_script_does_not_speak_timestamps(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = replace(
                load_config(),
                openai_api_key="",
                narration_history_path=Path(tmpdir) / "narration_history.json",
            )
            now = datetime(2026, 4, 12, 8, 0, tzinfo=config.timezone)
            note = ExtractedNote(
                category="technology_ai",
                headline="The Download: how humans make decisions",
                source_name="MIT Technology Review",
                url="https://example.com/tech",
                published_at="2026-04-12T06:00:00+00:00",
                excerpt="A short source excerpt.",
                note="Researchers are comparing how human judgment and AI systems diverge under pressure.",
                score=1.0,
                why_it_matters="It can change how teams think about decision support tools.",
            )
            signals = SignalPackage(
                generated_at=now.isoformat(),
                lookback_hours=24,
                what_matters_today="Decision quality and tool choice are in focus.",
                sections={
                    "geopolitics": [],
                    "technology_ai": [note],
                    "markets": [],
                },
            )
            script, _ = ScriptWriter(config).write(signals, now)
            self.assertNotIn("The source timestamp is", script.markdown)
            self.assertNotIn("The Download:", script.spoken_text)

    def test_weather_fallback_does_not_repeat_carry_sentence(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = replace(
                load_config(),
                openai_api_key="",
                narration_history_path=Path(tmpdir) / "narration_history.json",
            )
            now = datetime(2026, 4, 12, 8, 0, tzinfo=config.timezone)
            note = ExtractedNote(
                category="markets",
                headline="Market breadth improves",
                source_name="Test Source",
                url="https://example.com/market",
                published_at="2026-04-12T06:00:00+00:00",
                excerpt="A constructive market update.",
                note="The market tone is constructive.",
                score=1.0,
                why_it_matters="It keeps the risk read steady.",
            )
            weather = WeatherReport(
                location_name="Berlin",
                latitude=52.52,
                longitude=13.405,
                observed_at=now.isoformat(),
                temperature=13,
                apparent_temperature=9,
                temperature_unit="°C",
                conditions="light rain",
                weather_code=61,
                wind_speed=18,
                wind_gusts=None,
                wind_unit="km/h",
                precipitation_probability=70,
                cloud_cover=90,
                carry=["umbrella"],
                wear=["light jacket"],
                advisory="Light rain in the forecast, it is 13 degrees. Carry umbrella and wear light jacket.",
            )
            signals = SignalPackage(
                generated_at=now.isoformat(),
                lookback_hours=24,
                what_matters_today="Constructive markets are in focus.",
                sections={"geopolitics": [], "technology_ai": [], "markets": [note]},
            )
            script, _ = ScriptWriter(config).write(signals, now, weather)
            weather_text = script.sections["weather"].lower()
            self.assertEqual(weather_text.count("carry umbrella"), 1)
            self.assertEqual(weather_text.count("wear light jacket"), 1)

    def test_market_fallback_speaks_real_btc_and_oil_snapshot(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = replace(
                load_config(),
                openai_api_key="",
                narration_history_path=Path(tmpdir) / "narration_history.json",
            )
            now = datetime(2026, 4, 12, 8, 0, tzinfo=config.timezone)
            note = ExtractedNote(
                category="markets",
                headline="Market breadth improves",
                source_name="Test Source",
                url="https://example.com/market",
                published_at="2026-04-12T06:00:00+00:00",
                excerpt="A constructive market update.",
                note="The market tone is constructive.",
                score=1.0,
                why_it_matters="It keeps the risk read steady.",
            )
            signals = SignalPackage(
                generated_at=now.isoformat(),
                lookback_hours=24,
                what_matters_today="Constructive markets are in focus.",
                sections={"geopolitics": [], "technology_ai": [], "markets": [note]},
            )
            market_snapshot = {
                "crypto": {"items": [{"symbol": "BTC", "price_usd": 72158, "change_24h": 1.4}]},
                "energy": {"items": [{"name": "Brent crude", "value": 83.2, "unit": "USD/bbl"}]},
            }
            script, _ = ScriptWriter(config).write(
                signals,
                now,
                market_snapshot=market_snapshot,
            )
            self.assertIn("Bitcoin is holding around 72,200 dollars, holding firm.", script.spoken_text)
            self.assertIn("Brent crude is trading near 83 dollars a barrel, still elevated.", script.spoken_text)

    def test_voice_effect_warns_without_ffmpeg(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            config = replace(
                load_config(),
                output_dir=root,
                voice_effect_enabled=True,
                ffmpeg_path="not-a-real-ffmpeg",
            )
            config.audio_dir.mkdir(parents=True, exist_ok=True)
            mp3 = config.audio_dir / "voice.mp3"
            mp3.write_bytes(b"fake mp3")
            processed, warnings = VoiceEffectProcessor(config).process(mp3)
            self.assertEqual(processed, mp3)
            self.assertTrue(any("ffmpeg was not found" in warning for warning in warnings))

    def test_followup_endpoint_returns_text_only(self):
        config = replace(load_config(), openai_api_key="")
        app = create_app(config)
        response = app.test_client().post(
            "/api/followup",
            json={"question": "What should I watch in markets?"},
        )
        payload = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(payload["audio_src"])
        self.assertTrue(payload["answer"])

    def test_spoken_text_skips_structural_headings(self):
        spoken = strip_markdown_for_speech(
            "# Morning Brief\n\n## Weather\nBright and useful.\n\n## Source links\n- [x](https://example.com)"
        )
        self.assertEqual(spoken, "Bright and useful.")

    def test_weather_timeline_stays_short(self):
        config = replace(load_config(), openai_api_key="")
        now = datetime(2026, 4, 12, 8, 0, tzinfo=config.timezone)
        note = ExtractedNote(
            category="markets",
            headline="AI chipmaker raises guidance after strong demand",
            source_name="Test Source",
            url="https://example.com/market",
            published_at="2026-04-12T06:00:00+00:00",
            excerpt="The company raised guidance after strong demand.",
            note="The constructive signal is stronger enterprise demand.",
            score=1.0,
            why_it_matters="It keeps risk appetite constructive without leaning on hype.",
        )
        signals = SignalPackage(
            generated_at=now.isoformat(),
            lookback_hours=24,
            what_matters_today="Constructive AI demand is the cleanest signal.",
            sections={"geopolitics": [], "technology_ai": [], "markets": [note]},
        )
        script = ScriptPackage(
            generated_at=now.isoformat(),
            title="Test",
            markdown="",
            spoken_text="",
            word_count=1000,
            sections={"weather": "Bright and brief.", "markets": "A useful market signal."},
        )
        timeline = DashboardRenderer(config)._presentation_timeline(script, signals)
        weather = next(cue for cue in timeline["sections"] if cue["key"] == "weather")
        self.assertLessEqual(weather["duration"], 25)

    def test_news_timeline_does_not_use_old_fixed_sixty_eight_second_floor(self):
        config = replace(load_config(), openai_api_key="")
        now = datetime(2026, 4, 12, 8, 0, tzinfo=config.timezone)
        note = ExtractedNote(
            category="markets",
            headline="AI chipmaker raises guidance after strong demand",
            source_name="Test Source",
            url="https://example.com/market",
            published_at="2026-04-12T06:00:00+00:00",
            excerpt="The company raised guidance after strong demand.",
            note="The constructive signal is stronger enterprise demand.",
            score=1.0,
            why_it_matters="It keeps risk appetite constructive without leaning on hype.",
        )
        signals = SignalPackage(
            generated_at=now.isoformat(),
            lookback_hours=24,
            what_matters_today="Constructive AI demand is the cleanest signal.",
            sections={"geopolitics": [], "technology_ai": [], "markets": [note]},
        )
        script = ScriptPackage(
            generated_at=now.isoformat(),
            title="Test",
            markdown="",
            spoken_text="",
            word_count=100,
            sections={"markets": "A useful market signal."},
        )
        timeline = DashboardRenderer(config)._presentation_timeline(script, signals)
        markets = next(cue for cue in timeline["sections"] if cue["key"] == "markets")
        self.assertLess(markets["duration"], 30)

    def test_dashboard_css_does_not_truncate_story_cards(self):
        css = (Path(__file__).parents[1] / "morning_briefs/web/static/dashboard.css").read_text()
        self.assertNotIn("text-overflow", css)
        self.assertNotIn("-webkit-line-clamp", css)
        self.assertNotIn("display: -webkit-box", css)

    def test_mock_dashboard_fallback_marks_empty_modules(self):
        config = replace(load_config(), use_fake_data_when_empty=True)
        payload = {
            "markets": {"crypto": {"available": False, "items": []}, "energy": {"available": False, "items": []}},
            "geopolitics": {"escalation_monitor": {"items": []}},
            "technology_ai": {"developer_tooling": {"items": []}},
        }
        changed = DashboardIntelCollector(config)._apply_mock_fallbacks(payload)
        self.assertTrue(changed)
        self.assertTrue(payload["markets"]["crypto"]["mock"])
        self.assertTrue(payload["markets"]["energy"]["mock"])
        self.assertTrue(payload["geopolitics"]["escalation_monitor"]["mock"])
        self.assertTrue(payload["technology_ai"]["developer_tooling"]["mock"])

    def test_dashboard_uses_modular_intel_wall_not_hero_clipping(self):
        root = Path(__file__).parents[1]
        template = (root / "morning_briefs/web/templates/dashboard.html").read_text()
        script = (root / "morning_briefs/web/static/dashboard.js").read_text()
        css = (root / "morning_briefs/web/static/dashboard.css").read_text()
        self.assertIn('id="intelWall"', template)
        self.assertIn('id="closingAudio"', template)
        self.assertIn("navigator.sendBeacon", script)
        self.assertIn("is-mock-data", css)
        self.assertIn("function buildMarketsBoard", script)
        self.assertIn("function buildGeopoliticsBoard", script)
        self.assertIn("function buildTechnologyBoard", script)
        markets_board = script[script.index("function buildMarketsBoard") : script.index("function buildGeopoliticsBoard")]
        geopolitics_board = script[script.index("function buildGeopoliticsBoard") : script.index("function buildTechnologyBoard")]
        technology_board = script[script.index("function buildTechnologyBoard") : script.index("function renderIntelBoard")]
        self.assertLess(markets_board.index('storyBriefCard("markets"'), markets_board.index("sectorHeatmapCard()"))
        self.assertLess(geopolitics_board.index('storyBriefCard("geopolitics"'), geopolitics_board.index("Country instability"))
        self.assertLess(technology_board.index('storyBriefCard("technology_ai"'), technology_board.index("AI metrics summary"))
        self.assertNotIn("activeClipping", template)
        self.assertNotIn("activeClipping", script)
        self.assertNotIn("source-dossier", template)
        self.assertIn("overflow:hidden", css)

    def test_makefile_has_saved_replay_command(self):
        makefile = (Path(__file__).parents[1] / "Makefile").read_text()
        self.assertIn("replay:", makefile)
        self.assertIn("python3 -m morning_briefs replay", makefile)
        self.assertIn("dashboard_fixture:", makefile)

    def test_weather_guidance_adds_umbrella_and_jacket(self):
        carry, wear, advisory = weather_guidance(
            condition="rain",
            temperature=8,
            apparent_temperature=6,
            unit="°C",
            wind_speed=18,
            wind_gusts=45,
            wind_unit="km/h",
            precipitation_probability=70,
            cloud_cover=90,
        )
        self.assertIn("umbrella", carry)
        self.assertIn("light jacket", wear)
        self.assertIn("gusts", advisory)


if __name__ == "__main__":
    unittest.main()
