from morning_briefs.skills.base import KeywordSubSkill


class MacroRatesSubSkill(KeywordSubSkill):
    def __init__(self) -> None:
        super().__init__(
            name="macro_rates",
            description="Central banks, inflation, yields, jobs data, currencies, and commodities.",
            keywords=(
                "fed",
                "federal reserve",
                "rates",
                "yield",
                "inflation",
                "jobs",
                "dollar",
                "oil",
                "gold",
                "treasury",
            ),
            weight=1.2,
        )


class EarningsMoversSubSkill(KeywordSubSkill):
    def __init__(self) -> None:
        super().__init__(
            name="earnings_movers",
            description="Single-stock catalysts, earnings surprises, guidance, and premarket movers.",
            keywords=(
                "earnings",
                "profit",
                "revenue",
                "guidance",
                "shares",
                "stock",
                "premarket",
                "downgrade",
                "upgrade",
                "forecast",
            ),
            weight=1.1,
        )


class SectorRotationSubSkill(KeywordSubSkill):
    def __init__(self) -> None:
        super().__init__(
            name="sector_rotation",
            description="Leadership changes across tech, financials, energy, healthcare, and defensives.",
            keywords=(
                "sector",
                "tech stocks",
                "banks",
                "financials",
                "energy stocks",
                "healthcare",
                "industrial",
                "consumer",
                "rotation",
                "rally",
            ),
            weight=0.95,
        )
