from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

from .config import AppConfig
from .models import RawItem
from .utils import clean_text, load_json


@dataclass(frozen=True)
class QualityDecision:
    score: float
    is_relevant: bool
    reasons: List[str]


class NewsQualityFilter:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.policy = load_json(config.news_quality_path, default={})
        self.minimum_score = float(self.policy.get("minimum_quality_score", 0.58))

    def evaluate(self, item: RawItem) -> QualityDecision:
        text = clean_text(f"{item.headline} {item.excerpt}").lower()
        score = 0.48
        reasons: List[str] = []

        if item.freshness_hours is not None:
            if item.freshness_hours <= int(self.policy.get("freshness_bonus_hours", 24)):
                score += 0.22
                reasons.append("fresh")
            elif item.freshness_hours > self.config.last_hours * 2:
                score -= 0.24
                reasons.append("stale")

        signal_hits = self._hits(
            text, self.policy.get("category_signal_keywords", {}).get(item.category, [])
        )
        if signal_hits:
            score += min(0.34, 0.08 * len(signal_hits))
            reasons.append("category_signal:" + ",".join(signal_hits[:4]))
        else:
            score -= 0.12
            reasons.append("weak_category_signal")

        major_hits = self._hits(text, self.policy.get("major_significance_keywords", []))
        if major_hits:
            score += min(0.2, 0.05 * len(major_hits))
            reasons.append("major_significance:" + ",".join(major_hits[:3]))

        if self.config.good_news_only:
            positive_hits = self._hits(text, self.policy.get("positive_keywords", []))
            negative_hits = self._hits(text, self.policy.get("negative_keywords", []))
            if positive_hits:
                score += min(0.28, 0.07 * len(positive_hits))
                reasons.append("constructive:" + ",".join(positive_hits[:4]))
            if negative_hits and not positive_hits:
                score -= 0.55
                reasons.append("negative_tone:" + ",".join(negative_hits[:4]))
            elif negative_hits:
                score -= 0.18
                reasons.append("mixed_tone:" + ",".join(negative_hits[:3]))

        blocked_hits = self._hits(text, self.policy.get("blocked_keywords", []))
        if blocked_hits:
            score -= 0.65
            reasons.append("blocked:" + ",".join(blocked_hits[:3]))

        opinion_hits = self._hits(text, self.policy.get("opinion_markers", []))
        if opinion_hits and not major_hits:
            score -= 0.24
            reasons.append("opinion_heavy:" + ",".join(opinion_hits[:2]))

        low_value_hits = self._hits(text, self.policy.get("low_value_markers", []))
        if low_value_hits and not major_hits:
            score -= 0.18
            reasons.append("low_value:" + ",".join(low_value_hits[:2]))

        if len(item.excerpt) < 45:
            score -= 0.08
            reasons.append("thin_excerpt")

        score *= max(0.35, item.source_weight)
        score = round(max(0.0, min(score, 1.0)), 4)
        return QualityDecision(
            score=score,
            is_relevant=score >= self.minimum_score,
            reasons=reasons or ["accepted"],
        )

    def apply(self, item: RawItem) -> RawItem:
        decision = self.evaluate(item)
        item.quality_score = decision.score
        item.quality_reasons = decision.reasons
        item.is_relevant = decision.is_relevant
        return item

    def _hits(self, text: str, keywords: List[str]) -> List[str]:
        hits = []
        for keyword in keywords:
            normalized = str(keyword).strip().lower()
            if normalized and normalized in text:
                hits.append(normalized)
        return hits
