from morning_briefs.skills.base import KeywordSubSkill


class RegionalSecuritySubSkill(KeywordSubSkill):
    def __init__(self) -> None:
        super().__init__(
            name="regional_security",
            description="Conflict, military posture, elections, unrest, and cross-border risk.",
            keywords=(
                "war",
                "strike",
                "ceasefire",
                "missile",
                "border",
                "troops",
                "election",
                "unrest",
                "attack",
                "security",
            ),
            weight=1.15,
        )


class DiplomacySanctionsSubSkill(KeywordSubSkill):
    def __init__(self) -> None:
        super().__init__(
            name="diplomacy_sanctions",
            description="Summits, sanctions, alliances, treaties, and high-level diplomacy.",
            keywords=(
                "summit",
                "sanction",
                "sanctions",
                "minister",
                "diplomat",
                "talks",
                "deal",
                "alliance",
                "treaty",
                "embassy",
            ),
            weight=1.05,
        )


class EnergyTradeRoutesSubSkill(KeywordSubSkill):
    def __init__(self) -> None:
        super().__init__(
            name="energy_trade_routes",
            description="Oil, gas, shipping lanes, export controls, and trade chokepoints.",
            keywords=(
                "oil",
                "gas",
                "energy",
                "shipping",
                "red sea",
                "tariff",
                "trade",
                "export",
                "supply chain",
                "pipeline",
            ),
            weight=1.0,
        )
