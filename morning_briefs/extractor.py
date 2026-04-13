from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional, Tuple

from .config import AppConfig
from .llm import OpenAIModelClient
from .models import ExtractedNote, RawItem, SignalPackage
from .skills import build_skill_registry
from .skills.markets import MarketsSkill
from .utils import clean_text, compact_for_prompt, normalize_story_key


SECTION_LIMITS = {
    "geopolitics": 5,
    "technology_ai": 5,
    "markets": 3,
}


class SignalExtractor:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.skills = build_skill_registry()
        self.llm = OpenAIModelClient(config)

    def extract(
        self, raw_items: List[RawItem], generated_at: datetime
    ) -> Tuple[SignalPackage, List[str]]:
        warnings: List[str] = []
        sections = self._heuristic_sections(raw_items)
        what_matters_today = self._heuristic_what_matters(sections)
        watchlist = self._heuristic_watchlist(sections)
        market_movers = self._market_movers(raw_items)

        package = SignalPackage(
            generated_at=generated_at.isoformat(),
            lookback_hours=self.config.last_hours,
            what_matters_today=what_matters_today,
            sections=sections,
            market_movers=market_movers,
            watchlist=watchlist,
        )

        refined = self._refine_with_model(package)
        if refined is not None:
            package = refined
            package.model_used = self.config.openai_signal_model
        elif self.config.openai_api_key:
            warnings.append("OpenAI signal refinement failed; used local heuristics.")
        else:
            warnings.append("OPENAI_API_KEY not set; used local heuristic extraction.")
        if not any(package.sections.values()):
            warnings.append(
                "No source passed the news-quality filter; check sources or loosen config/news_quality.json."
            )
        package.warnings.extend(warnings)
        return package, warnings

    def _heuristic_sections(
        self, raw_items: List[RawItem]
    ) -> Dict[str, List[ExtractedNote]]:
        sections: Dict[str, List[ExtractedNote]] = {}
        used_story_keys = set()

        for category in ("geopolitics", "technology_ai", "markets"):
            skill = self.skills[category]
            candidates = []
            for item in raw_items:
                if item.category != category:
                    continue
                if not item.is_relevant:
                    continue
                if (
                    item.freshness_hours is not None
                    and item.freshness_hours > self.config.last_hours * 2
                ):
                    continue
                score = skill.score_item(item, self.config.last_hours) + item.quality_score
                candidates.append((score, item))

            notes = []
            for score, item in sorted(candidates, key=lambda pair: pair[0], reverse=True):
                story_key = normalize_story_key(item.headline)
                if story_key in used_story_keys:
                    continue
                used_story_keys.add(story_key)
                notes.append(skill.build_note(item, score))
                if len(notes) >= SECTION_LIMITS[category]:
                    break
            sections[category] = notes
        return sections

    def _heuristic_what_matters(
        self, sections: Dict[str, List[ExtractedNote]]
    ) -> str:
        top_notes = [
            notes[0].headline for notes in sections.values() if notes
        ][:3]
        if not top_notes:
            return "A quiet feed set means the main task today is to verify sources before drawing a hard conclusion."
        joined = "; ".join(top_notes)
        return (
            "What matters today: start with the cross-current between "
            f"{joined}. These are the stories most likely to shape meetings, risk calls, and market tone."
        )

    def _heuristic_watchlist(
        self,
        sections: Dict[str, List[ExtractedNote]],
    ) -> List[str]:
        watch_items = []
        for category, notes in sections.items():
            if not notes:
                continue
            label = category.replace("_", " ").title()
            watch_items.append(f"{label}: track follow-through on {notes[0].headline}.")
        return watch_items[:5]

    def _market_movers(self, raw_items: List[RawItem]) -> List[Dict[str, str]]:
        skill = self.skills.get("markets")
        if isinstance(skill, MarketsSkill):
            market_items = [
                item for item in raw_items if item.category == "markets" and item.is_relevant
            ]
            return skill.extract_movers(market_items)
        return []

    def _refine_with_model(self, package: SignalPackage) -> Optional[SignalPackage]:
        if not self.llm.available:
            return None
        schema = signal_schema()
        payload = {
            "generated_at": package.generated_at,
            "lookback_hours": package.lookback_hours,
            "sections": {
                category: [
                    {
                        "headline": note.headline,
                        "source_name": note.source_name,
                        "url": note.url,
                        "published_at": note.published_at,
                        "excerpt": note.excerpt,
                        "note": note.note,
                        "subskills": note.subskills,
                        "score": note.score,
                    }
                    for note in notes
                ]
                for category, notes in package.sections.items()
            },
            "market_movers": package.market_movers,
        }
        result = self.llm.json_response(
            system=(
                "You are a morning briefing signal editor. Use only the supplied source items. "
                "Prefer the last 24 hours, include exact dates when they matter, avoid duplicate "
                "stories across categories, and make every why_it_matters line conversational."
            ),
            user=(
                "Convert these source notes into top developments for geopolitics, technology_ai, "
                "and markets. Keep the original URLs and source names. Return JSON only.\n"
                + compact_for_prompt(payload)
            ),
            schema_name="morning_brief_signals",
            schema=schema,
            model=self.config.openai_signal_model,
            max_output_tokens=3600,
        )
        if not result:
            return None
        return self._package_from_model(result, package)

    def _package_from_model(
        self, result: Dict[str, object], original: SignalPackage
    ) -> SignalPackage:
        original_by_url = {
            note.url: note
            for notes in original.sections.values()
            for note in notes
        }
        sections: Dict[str, List[ExtractedNote]] = {}
        for category in ("geopolitics", "technology_ai", "markets"):
            notes = []
            for item in result.get("sections", {}).get(category, [])[
                : SECTION_LIMITS[category]
            ]:
                url = item.get("url", "")
                source = original_by_url.get(url)
                if source is None:
                    continue
                notes.append(
                    ExtractedNote(
                        category=category,
                        headline=clean_text(item.get("headline") or source.headline, 220),
                        source_name=source.source_name,
                        url=source.url,
                        published_at=source.published_at,
                        excerpt=source.excerpt,
                        note=clean_text(item.get("development") or source.note, 500),
                        score=float(item.get("priority", source.score)),
                        subskills=source.subskills,
                        tags=source.tags,
                        why_it_matters=clean_text(
                            item.get("why_it_matters") or source.why_it_matters, 280
                        ),
                    )
                )
            sections[category] = notes or original.sections.get(category, [])

        watchlist = [
            clean_text(value, 220)
            for value in result.get("watchlist", [])
            if isinstance(value, str)
        ][:5]
        return SignalPackage(
            generated_at=original.generated_at,
            lookback_hours=original.lookback_hours,
            what_matters_today=clean_text(
                str(result.get("what_matters_today") or original.what_matters_today),
                360,
            ),
            sections=sections,
            market_movers=original.market_movers,
            watchlist=watchlist or original.watchlist,
            model_used=self.config.openai_signal_model,
            warnings=original.warnings,
        )


def signal_schema() -> Dict[str, object]:
    note = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "headline": {"type": "string"},
            "url": {"type": "string"},
            "development": {"type": "string"},
            "why_it_matters": {"type": "string"},
            "priority": {"type": "number"},
        },
        "required": [
            "headline",
            "url",
            "development",
            "why_it_matters",
            "priority",
        ],
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "what_matters_today": {"type": "string"},
            "sections": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "geopolitics": {"type": "array", "items": note},
                    "technology_ai": {"type": "array", "items": note},
                    "markets": {"type": "array", "items": note},
                },
                "required": ["geopolitics", "technology_ai", "markets"],
            },
            "watchlist": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["what_matters_today", "sections", "watchlist"],
    }
