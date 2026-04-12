from __future__ import annotations

from morning_briefs.models import RawItem
from morning_briefs.skills.base import DomainSkill
from morning_briefs.skills.subskills import (
    ChipsComputeSubSkill,
    CyberPolicySubSkill,
    FrontierAISubSkill,
)


class TechnologyAISkill(DomainSkill):
    category = "technology_ai"
    display_name = "Technology and AI"
    subskills = (
        FrontierAISubSkill(),
        ChipsComputeSubSkill(),
        CyberPolicySubSkill(),
    )
    importance_keywords = (
        "ai",
        "model",
        "agent",
        "chip",
        "gpu",
        "data center",
        "regulation",
        "cyber",
        "breach",
        "openai",
        "nvidia",
        "microsoft",
        "google",
    )

    def why_it_matters(self, item: RawItem, subskills) -> str:
        return (
            "Why it matters today: it may change what tools teams can use, what infrastructure "
            "gets scarce, and which AI risks need a same-day decision."
        )
