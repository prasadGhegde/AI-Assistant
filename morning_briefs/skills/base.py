from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Sequence

from morning_briefs.models import ExtractedNote, RawItem
from morning_briefs.utils import clean_text, merge_unique


@dataclass(frozen=True)
class KeywordSubSkill:
    name: str
    description: str
    keywords: Sequence[str]
    weight: float = 1.0

    def score(self, item: RawItem) -> float:
        haystack = f"{item.headline} {item.excerpt}".lower()
        hits = sum(1 for keyword in self.keywords if keyword.lower() in haystack)
        if hits == 0:
            return 0.0
        return min(1.0, 0.25 + hits * 0.2) * self.weight


class DomainSkill:
    category = ""
    display_name = ""
    subskills: Sequence[KeywordSubSkill] = ()
    importance_keywords: Sequence[str] = ()

    def score_item(self, item: RawItem, lookback_hours: int) -> float:
        freshness = 0.35
        if item.freshness_hours is not None:
            freshness = max(0.0, 1.0 - item.freshness_hours / max(lookback_hours * 1.5, 1))
        subskill_score = sum(subskill.score(item) for subskill in self.subskills)
        importance = self._importance_score(item)
        source = max(0.2, item.source_weight)
        return round((freshness * 1.6 + subskill_score + importance) * source, 4)

    def matching_subskills(self, item: RawItem) -> List[str]:
        matches = [
            subskill.name for subskill in self.subskills if subskill.score(item) > 0
        ]
        return matches or ["general_signal"]

    def build_note(self, item: RawItem, score: float) -> ExtractedNote:
        subskills = self.matching_subskills(item)
        tags = merge_unique([*item.tags, *subskills])
        note = self.note_sentence(item, subskills)
        return ExtractedNote(
            category=self.category,
            headline=clean_text(item.headline, 220),
            source_name=item.source_name,
            url=item.url,
            published_at=item.published_at,
            excerpt=clean_text(item.excerpt, 420),
            note=note,
            score=score,
            subskills=subskills,
            tags=tags,
            why_it_matters=self.why_it_matters(item, subskills),
        )

    def note_sentence(self, item: RawItem, subskills: Iterable[str]) -> str:
        labels = ", ".join(subskills)
        excerpt = clean_text(item.excerpt, 180)
        if excerpt:
            return f"{item.source_name} flags this as a {labels} story: {excerpt}"
        return f"{item.source_name} flags this as a {labels} story."

    def why_it_matters(self, item: RawItem, subskills: Iterable[str]) -> str:
        return "It could shape workday risk, leadership attention, and the agenda for follow-up monitoring."

    def _importance_score(self, item: RawItem) -> float:
        haystack = f"{item.headline} {item.excerpt}".lower()
        hits = sum(1 for keyword in self.importance_keywords if keyword in haystack)
        return min(1.0, hits * 0.18)
