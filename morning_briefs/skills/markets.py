from __future__ import annotations

import re
from typing import Dict, List

from morning_briefs.models import RawItem
from morning_briefs.skills.base import DomainSkill
from morning_briefs.skills.subskills import (
    EarningsMoversSubSkill,
    MacroRatesSubSkill,
    SectorRotationSubSkill,
)


TICKER_RE = re.compile(r"\b[A-Z]{1,5}\b")


class MarketsSkill(DomainSkill):
    category = "markets"
    display_name = "Stock market"
    subskills = (
        MacroRatesSubSkill(),
        EarningsMoversSubSkill(),
        SectorRotationSubSkill(),
    )
    importance_keywords = (
        "fed",
        "inflation",
        "yield",
        "earnings",
        "shares",
        "stock",
        "market",
        "nasdaq",
        "s&p",
        "dow",
        "guidance",
        "forecast",
        "oil",
        "dollar",
    )

    def why_it_matters(self, item: RawItem, subskills) -> str:
        return (
            "Why it matters today: it can set the tone for risk, cash decisions, and which "
            "names deserve a closer look before the market narrative hardens."
        )

    def extract_movers(self, items: List[RawItem]) -> List[Dict[str, str]]:
        movers = []
        for item in items:
            tickers = [
                ticker
                for ticker in TICKER_RE.findall(f"{item.headline} {item.excerpt}")
                if ticker not in {"CEO", "CFO", "ETF", "Fed", "AI", "US", "UK"}
            ]
            if not tickers:
                continue
            movers.append(
                {
                    "ticker": tickers[0],
                    "headline": item.headline,
                    "source": item.source_name,
                    "url": item.url,
                }
            )
            if len(movers) >= 8:
                break
        return movers
