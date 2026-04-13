from __future__ import annotations

from morning_briefs.models import RawItem
from morning_briefs.skills.base import DomainSkill
from morning_briefs.skills.subskills import (
    DiplomacySanctionsSubSkill,
    EnergyTradeRoutesSubSkill,
    RegionalSecuritySubSkill,
)


class GeopoliticsSkill(DomainSkill):
    category = "geopolitics"
    display_name = "Geopolitics"
    subskills = (
        RegionalSecuritySubSkill(),
        DiplomacySanctionsSubSkill(),
        EnergyTradeRoutesSubSkill(),
    )
    importance_keywords = (
        "war",
        "ceasefire",
        "sanction",
        "election",
        "strike",
        "summit",
        "tariff",
        "oil",
        "shipping",
        "china",
        "russia",
        "ukraine",
        "israel",
        "taiwan",
    )

    def why_it_matters(self, item: RawItem, subskills) -> str:
        return (
            "A constructive diplomatic signal can steady risk appetite, supply-chain assumptions, "
            "and executive attention before the workday is fully underway."
        )
