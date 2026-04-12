import unittest
from dataclasses import replace
from datetime import datetime

from morning_briefs.config import load_config
from morning_briefs.extractor import SignalExtractor
from morning_briefs.models import ExtractedNote, RawItem, SignalPackage
from morning_briefs.writer import ScriptWriter


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
        config = replace(load_config(), openai_api_key="")
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
            watchlist=["Track source updates."],
        )
        script, _ = ScriptWriter(config).write(signals, now)
        self.assertIn("## Geopolitics", script.markdown)
        self.assertIn("## Technology and AI", script.markdown)
        self.assertIn("## Stock market", script.markdown)
        self.assertIn("Why it matters today:", script.markdown)


if __name__ == "__main__":
    unittest.main()
