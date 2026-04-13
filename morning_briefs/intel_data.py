from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import requests

from .config import AppConfig
from .models import SignalPackage


class DashboardIntelCollector:
    """Collect compact, real-data intelligence widgets for dashboard side modules.

    Each provider returns either real values or an explicit unavailable state.
    No synthetic/random values are generated.
    """

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "MorningBriefs/0.1 dashboard-intel (personal local use)",
                "Accept": "application/json",
            }
        )

    def collect(self, signals: SignalPackage) -> Tuple[Dict[str, Any], List[str]]:
        warnings: List[str] = []
        geopolitics, geo_warnings = self._geopolitics_modules(signals)
        markets, market_warnings = self._markets_modules(signals)
        technology, tech_warnings = self._technology_modules(signals)
        warnings.extend(geo_warnings)
        warnings.extend(market_warnings)
        warnings.extend(tech_warnings)
        return {
            "geopolitics": geopolitics,
            "markets": markets,
            "technology_ai": technology,
        }, warnings

    def _json(self, url: str, *, params: Optional[Dict[str, Any]] = None) -> Any:
        response = self.session.get(url, params=params, timeout=self.config.fetch_timeout)
        response.raise_for_status()
        return response.json()

    def _geopolitics_modules(self, signals: SignalPackage) -> Tuple[Dict[str, Any], List[str]]:
        warnings: List[str] = []
        instability = self._country_instability_from_signals(signals)
        strategic_risk = self._strategic_risk(signals)
        intel_feed = self._intel_feed(signals)
        debt_clock, debt_warnings = self._national_debt_clock()
        warnings.extend(debt_warnings)
        disasters, disaster_warnings = self._disaster_cascade()
        warnings.extend(disaster_warnings)
        escalation = self._geo_keyword_card(signals, ["conflict", "strike", "missile", "drone", "border", "escalation"], "Escalation")
        posture = self._geo_keyword_card(signals, ["carrier", "navy", "troops", "drill", "aircraft", "deployment"], "Posture")
        sanctions = self._geo_keyword_card(signals, ["sanction", "export control", "tariff", "restriction", "embargo"], "Pressure")
        regional = self._regional_risk(signals)
        return {
            "country_instability": instability,
            "strategic_risk": strategic_risk,
            "intel_feed": intel_feed,
            "national_debt_clock": debt_clock,
            "disaster_cascade": disasters,
            "escalation_monitor": escalation,
            "force_posture": posture,
            "sanctions_pressure": sanctions,
            "regional_risk": regional,
        }, warnings

    def _strategic_risk(self, signals: SignalPackage) -> Dict[str, Any]:
        notes = signals.sections.get("geopolitics", [])
        if not notes:
            return {"label": "Unavailable", "detail": "No geopolitics notes available."}
        avg = sum(note.score for note in notes if note.score is not None) / max(len(notes), 1)
        if avg >= 7:
            label = "Elevated"
        elif avg >= 4:
            label = "Guarded"
        else:
            label = "Stable"
        return {
            "label": f"{label} ({avg:.1f})",
            "detail": "Composite from geopolitics signal scores in this briefing.",
        }

    def _intel_feed(self, signals: SignalPackage) -> Dict[str, Any]:
        notes = signals.sections.get("geopolitics", [])
        items = []
        for note in notes[:5]:
            items.append(
                {
                    "region": note.source_name,
                    "headline": note.headline,
                }
            )
        return {"items": items}

    def _geo_keyword_card(self, signals: SignalPackage, keywords: List[str], value_label: str) -> Dict[str, Any]:
        notes = signals.sections.get("geopolitics", [])
        counter: Counter[str] = Counter()
        for note in notes:
            blob = f"{note.headline} {note.note} {note.excerpt}".lower()
            if any(key in blob for key in keywords):
                counter[note.source_name or "General"] += 1
        items = []
        for name, count in counter.most_common(6):
            items.append({"name": name, "value": f"{value_label} {count}"})
        return {"items": items}

    def _regional_risk(self, signals: SignalPackage) -> Dict[str, Any]:
        buckets = {
            "Europe": ["europe", "ukraine", "russia", "nato", "eu"],
            "MENA": ["middle east", "iran", "israel", "gaza", "saudi"],
            "Asia-Pacific": ["china", "taiwan", "japan", "korea", "indo-pacific"],
            "Americas": ["us", "united states", "latam", "canada", "mexico"],
        }
        notes = signals.sections.get("geopolitics", [])
        items = []
        for region, terms in buckets.items():
            hits = 0
            for note in notes:
                blob = f"{note.headline} {note.note} {note.excerpt}".lower()
                if any(term in blob for term in terms):
                    hits += 1
            items.append({"name": region, "score": hits})
        return {"items": items}

    def _country_instability_from_signals(self, signals: SignalPackage) -> Dict[str, Any]:
        notes = signals.sections.get("geopolitics", [])
        if not notes:
            return {
                "available": False,
                "items": [],
                "source": "Local geopolitics signal extraction",
                "note": "No geopolitics items available in this run.",
            }

        countries = [
            "United States", "China", "India", "Russia", "Ukraine", "Iran", "Israel",
            "Taiwan", "Japan", "Germany", "France", "United Kingdom", "North Korea",
        ]
        keyword_map = {
            "us": "United States",
            "u.s.": "United States",
            "united states": "United States",
            "america": "United States",
            "china": "China",
            "india": "India",
            "russia": "Russia",
            "ukraine": "Ukraine",
            "iran": "Iran",
            "israel": "Israel",
            "taiwan": "Taiwan",
            "japan": "Japan",
            "germany": "Germany",
            "france": "France",
            "uk": "United Kingdom",
            "britain": "United Kingdom",
            "north korea": "North Korea",
        }

        counts: Counter[str] = Counter()
        for note in notes:
            blob = f"{note.headline} {note.note} {note.excerpt}".lower()
            for key, country in keyword_map.items():
                if key in blob:
                    counts[country] += 1

        if not counts:
            for note in notes[:3]:
                counts[note.source_name] += 1

        max_count = max(counts.values()) if counts else 1
        items = []
        for name, c in counts.most_common(8):
            score = int(round((c / max_count) * 100))
            items.append(
                {
                    "name": name,
                    "score": score,
                    "events": c,
                    "band": "high" if score >= 70 else "medium" if score >= 40 else "low",
                }
            )

        return {
            "available": True,
            "items": items,
            "source": "Local geopolitics signal extraction",
            "note": "Signal intensity derived from today's vetted geopolitical developments.",
        }

    def _national_debt_clock(self) -> Tuple[Dict[str, Any], List[str]]:
        warnings: List[str] = []
        out = {
            "available": False,
            "source": "US Treasury FiscalData",
            "source_url": "https://api.fiscaldata.treasury.gov/",
            "updated_at": None,
            "total_debt_usd": None,
            "display": "Unavailable",
        }
        try:
            payload = self._json(
                "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v2/accounting/od/debt_to_penny",
                params={"sort": "-record_date", "page[number]": 1, "page[size]": 1},
            )
            row = ((payload or {}).get("data") or [None])[0] or {}
            total = row.get("tot_pub_debt_out_amt")
            if total:
                total_float = float(total)
                out["available"] = True
                out["total_debt_usd"] = total_float
                out["display"] = self._human_dollars(total_float)
                out["updated_at"] = row.get("record_date")
        except Exception as exc:
            warnings.append(f"Debt clock provider unavailable: {exc}")
        return out, warnings

    def _disaster_cascade(self) -> Tuple[Dict[str, Any], List[str]]:
        warnings: List[str] = []
        events: List[Dict[str, Any]] = []

        # USGS significant earthquakes (real-time feed)
        try:
            payload = self._json(
                "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/significant_day.geojson"
            )
            features = (payload or {}).get("features") or []
            for item in features[:6]:
                props = item.get("properties") or {}
                events.append(
                    {
                        "type": "Earthquake",
                        "title": props.get("place") or "Unknown location",
                        "severity": props.get("mag"),
                        "time": self._ms_to_iso(props.get("time")),
                        "url": props.get("url"),
                        "source": "USGS",
                    }
                )
        except Exception as exc:
            warnings.append(f"USGS disaster feed unavailable: {exc}")

        # NASA EONET active natural events
        try:
            payload = self._json(
                "https://eonet.gsfc.nasa.gov/api/v3/events",
                params={"status": "open", "limit": 20},
            )
            rows = (payload or {}).get("events") or []
            for row in rows[:10]:
                categories = row.get("categories") or []
                cat = categories[0].get("title") if categories else "Event"
                geometry = row.get("geometry") or []
                latest = geometry[-1] if geometry else {}
                events.append(
                    {
                        "type": cat,
                        "title": row.get("title") or "Unnamed event",
                        "severity": None,
                        "time": latest.get("date"),
                        "url": row.get("link"),
                        "source": "NASA EONET",
                    }
                )
        except Exception as exc:
            warnings.append(f"EONET disaster feed unavailable: {exc}")

        events = sorted(events, key=lambda e: e.get("time") or "", reverse=True)[:12]
        return {
            "available": bool(events),
            "items": events,
            "source": "USGS + NASA EONET",
            "note": "Live natural hazard stream; ordered by most recent event time.",
        }, warnings

    def _markets_modules(self, signals: SignalPackage) -> Tuple[Dict[str, Any], List[str]]:
        warnings: List[str] = []
        sector_heatmap = self._sector_heatmap_from_signals(signals)
        metals = self._metals_materials_from_signals(signals)
        crypto, crypto_warnings = self._crypto_tracker()
        warnings.extend(crypto_warnings)
        fear_greed, fg_warnings = self._fear_greed_adapter()
        warnings.extend(fg_warnings)
        fx, fx_warnings = self._fx_tracker()
        warnings.extend(fx_warnings)
        energy, energy_warnings = self._energy_tracker()
        warnings.extend(energy_warnings)
        macro, macro_warnings = self._macro_movers()
        warnings.extend(macro_warnings)
        breadth = self._breadth_summary(signals)
        headlines = self._market_headlines(signals)
        return {
            "sector_heatmap": sector_heatmap,
            "metals_materials": metals,
            "crypto": crypto,
            "fear_greed": fear_greed,
            "fx": fx,
            "energy": energy,
            "macro_movers": macro,
            "breadth": breadth,
            "headlines": headlines,
        }, warnings

    def _fx_tracker(self) -> Tuple[Dict[str, Any], List[str]]:
        warnings: List[str] = []
        out = {"available": False, "items": [], "source": "open.er-api.com"}
        try:
            payload = self._json("https://open.er-api.com/v6/latest/USD")
            rates = payload.get("rates") or {}
            items = []
            for code in ["USD", "EUR", "GBP", "INR", "CNY"]:
                rate = rates.get(code)
                if rate is None:
                    continue
                items.append({"pair": f"USD/{code}", "rate": float(rate)})
            out["available"] = bool(items)
            out["items"] = items
        except Exception as exc:
            warnings.append(f"FX provider unavailable: {exc}")
        return out, warnings

    def _energy_tracker(self) -> Tuple[Dict[str, Any], List[str]]:
        warnings: List[str] = []
        items = []
        for name, series, unit in [
            ("WTI crude", "DCOILWTICO", "USD/bbl"),
            ("Brent crude", "DCOILBRENTEU", "USD/bbl"),
            ("Natural gas", "DHHNGSP", "USD/MMBtu"),
        ]:
            value, err = self._fred_latest(series)
            if err:
                warnings.append(f"Energy series {series} unavailable: {err}")
                continue
            if value is not None:
                items.append({"name": name, "value": round(value, 2), "unit": unit})
        return {"available": bool(items), "items": items, "source": "FRED"}, warnings

    def _macro_movers(self) -> Tuple[Dict[str, Any], List[str]]:
        warnings: List[str] = []
        items = []
        for name, series in [
            ("US 2Y", "DGS2"),
            ("US 10Y", "DGS10"),
            ("Fed funds", "FEDFUNDS"),
        ]:
            value, err = self._fred_latest(series)
            if err:
                warnings.append(f"Macro series {series} unavailable: {err}")
                continue
            if value is not None:
                items.append({"name": name, "value": f"{value:.2f}%", "change": "latest"})
        return {"available": bool(items), "items": items, "source": "FRED"}, warnings

    def _breadth_summary(self, signals: SignalPackage) -> Dict[str, Any]:
        notes = signals.sections.get("markets", [])
        if not notes:
            return {"label": "Unavailable", "detail": "No market notes in this run."}
        blob = " ".join(f"{n.headline} {n.note}".lower() for n in notes)
        positives = len([w for w in ["gain", "rally", "rise", "strong", "up"] if w in blob])
        negatives = len([w for w in ["drop", "fall", "weak", "down", "risk"] if w in blob])
        if positives > negatives:
            label = "Constructive"
        elif negatives > positives:
            label = "Defensive"
        else:
            label = "Balanced"
        return {"label": label, "detail": f"Positive cues {positives}, negative cues {negatives}."}

    def _market_headlines(self, signals: SignalPackage) -> Dict[str, Any]:
        notes = signals.sections.get("markets", [])
        return {
            "items": [
                {"source": note.source_name, "headline": note.headline}
                for note in notes[:5]
            ]
        }

    def _sector_heatmap_from_signals(self, signals: SignalPackage) -> Dict[str, Any]:
        notes = signals.sections.get("markets", [])
        if not notes:
            return {"available": False, "items": [], "source": "Market signal extraction"}

        sector_keywords = {
            "Technology": ["tech", "software", "semiconductor", "chip", "cloud", "ai"],
            "Financials": ["bank", "financial", "credit", "insurance", "yield"],
            "Energy": ["oil", "gas", "energy", "crude"],
            "Healthcare": ["health", "pharma", "biotech"],
            "Industrials": ["industrial", "manufacturing", "transport", "shipping"],
            "Consumer": ["retail", "consumer", "ecommerce", "spending"],
            "Materials": ["metal", "copper", "steel", "mining", "lithium", "materials"],
            "Utilities": ["utility", "power", "grid"],
        }
        counts = Counter({sector: 0 for sector in sector_keywords})
        for note in notes:
            blob = f"{note.headline} {note.note} {note.excerpt}".lower()
            for sector, terms in sector_keywords.items():
                if any(term in blob for term in terms):
                    counts[sector] += 1

        max_count = max(counts.values()) if any(counts.values()) else 1
        items = []
        for sector, count in counts.items():
            intensity = int(round((count / max_count) * 100)) if max_count else 0
            items.append({
                "name": sector,
                "intensity": intensity,
                "hits": count,
                "band": "high" if intensity >= 70 else "medium" if intensity >= 35 else "low",
            })
        items.sort(key=lambda i: i["intensity"], reverse=True)
        return {
            "available": True,
            "items": items,
            "source": "Market signal extraction",
            "note": "Sector intensity derived from today's accepted market coverage.",
        }

    def _metals_materials_from_signals(self, signals: SignalPackage) -> Dict[str, Any]:
        notes = signals.sections.get("markets", [])
        terms = {
            "Gold": ["gold", "bullion", "xau"],
            "Silver": ["silver", "xag"],
            "Copper": ["copper", "cu"],
            "Steel": ["steel"],
            "Lithium": ["lithium"],
        }
        counts = Counter({k: 0 for k in terms})
        for note in notes:
            blob = f"{note.headline} {note.note} {note.excerpt}".lower()
            for name, keys in terms.items():
                if any(key in blob for key in keys):
                    counts[name] += 1

        items = [{"name": k, "mentions": v} for k, v in counts.items() if v > 0]
        if not items:
            return {
                "available": False,
                "items": [],
                "source": "Market signal extraction",
                "note": "No materials/metals signals in current accepted stories.",
            }
        items.sort(key=lambda i: i["mentions"], reverse=True)
        return {
            "available": True,
            "items": items,
            "source": "Market signal extraction",
            "note": "Mentions across accepted market stories in this run.",
        }

    def _crypto_tracker(self) -> Tuple[Dict[str, Any], List[str]]:
        warnings: List[str] = []
        out = {
            "available": False,
            "items": [],
            "source": "CoinGecko",
            "source_url": "https://www.coingecko.com/",
        }
        try:
            payload = self._json(
                "https://api.coingecko.com/api/v3/simple/price",
                params={
                    "ids": "bitcoin,ethereum,solana",
                    "vs_currencies": "usd",
                    "include_24hr_change": "true",
                },
            )
            symbols = [("bitcoin", "BTC"), ("ethereum", "ETH"), ("solana", "SOL")]
            items = []
            for key, symbol in symbols:
                row = payload.get(key) or {}
                usd = row.get("usd")
                change = row.get("usd_24h_change")
                if usd is None:
                    continue
                items.append(
                    {
                        "symbol": symbol,
                        "price_usd": float(usd),
                        "change_24h": None if change is None else float(change),
                    }
                )
            out["available"] = bool(items)
            out["items"] = items
        except Exception as exc:
            warnings.append(f"Crypto provider unavailable: {exc}")
        return out, warnings

    def _fear_greed_adapter(self) -> Tuple[Dict[str, Any], List[str]]:
        warnings: List[str] = []

        # Primary provider (CNN) can block automated requests; keep adapter for future swap.
        try:
            payload = self._json("https://production.dataviz.cnn.io/index/fearandgreed/graphdata")
            score = (payload.get("fear_and_greed") or {}).get("score")
            rating = (payload.get("fear_and_greed") or {}).get("rating")
            if score is not None:
                return {
                    "available": True,
                    "value": int(score),
                    "label": rating or self._fear_label(int(score)),
                    "source": "CNN Fear & Greed",
                    "source_url": "https://www.cnn.com/markets/fear-and-greed",
                    "mode": "primary",
                }, warnings
        except Exception as exc:
            warnings.append(f"CNN Fear & Greed unavailable: {exc}")

        # Fallback proxy from VIX (real market volatility series).
        try:
            response = self.session.get(
                "https://fred.stlouisfed.org/graph/fredgraph.csv?id=VIXCLS",
                timeout=self.config.fetch_timeout,
            )
            response.raise_for_status()
            rows = [line.strip() for line in response.text.splitlines() if line.strip()]
            values: List[float] = []
            for row in rows[1:]:
                _date, value = row.split(",", 1)
                if value != ".":
                    values.append(float(value))
            if values:
                vix = values[-1]
                score = max(0, min(100, int(round(100 - (vix * 2.1)))))
                return {
                    "available": True,
                    "value": score,
                    "label": self._fear_label(score),
                    "source": "FRED VIX proxy",
                    "source_url": "https://fred.stlouisfed.org/series/VIXCLS",
                    "mode": "fallback_proxy",
                    "proxy_note": "Derived from VIX when CNN endpoint is unavailable.",
                }, warnings
        except Exception as exc:
            warnings.append(f"Fear/Greed fallback unavailable: {exc}")

        return {
            "available": False,
            "value": None,
            "label": "Unavailable",
            "source": "Fear/Greed adapter",
            "mode": "unavailable",
        }, warnings

    def _technology_modules(self, signals: SignalPackage) -> Tuple[Dict[str, Any], List[str]]:
        warnings: List[str] = []
        notes = signals.sections.get("technology_ai", [])

        quality_values = [n.score for n in notes if n.score is not None]
        avg_quality = round(sum(quality_values) / len(quality_values), 2) if quality_values else None
        unique_sources = len({n.source_name for n in notes if n.source_name})

        chip_terms = ["chip", "gpu", "semiconductor", "foundry", "cuda"]
        model_terms = ["model", "llm", "release", "inference", "fine-tune", "training"]
        policy_terms = ["regulation", "policy", "safety", "compliance", "law", "export control"]

        chip_hits = 0
        model_hits = 0
        policy_hits = 0
        for note in notes:
            blob = f"{note.headline} {note.note} {note.excerpt}".lower()
            if any(t in blob for t in chip_terms):
                chip_hits += 1
            if any(t in blob for t in model_terms):
                model_hits += 1
            if any(t in blob for t in policy_terms):
                policy_hits += 1

        metrics = [
            {
                "label": "AI stories in brief",
                "value": len(notes),
                "detail": "Accepted technology/AI primary stories in this run",
                "source": "MorningBriefs signal pipeline",
            },
            {
                "label": "Unique AI sources",
                "value": unique_sources,
                "detail": "Distinct sources represented in tech section",
                "source": "MorningBriefs signal pipeline",
            },
            {
                "label": "Average signal score",
                "value": avg_quality,
                "detail": "Average extractor priority score for tech notes",
                "source": "MorningBriefs signal pipeline",
            },
            {
                "label": "Chip / infra-linked items",
                "value": chip_hits,
                "detail": "Mentions of chips, GPU, semis, foundry, compute",
                "source": "MorningBriefs signal pipeline",
            },
            {
                "label": "Model cadence items",
                "value": model_hits,
                "detail": "Mentions of model releases/training/inference",
                "source": "MorningBriefs signal pipeline",
            },
            {
                "label": "Policy / governance items",
                "value": policy_hits,
                "detail": "Mentions of policy, compliance, regulation",
                "source": "MorningBriefs signal pipeline",
            },
        ]

        # Optional external metric: GitHub AI repo activity in last 24h
        try:
            since = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
            payload = self._json(
                "https://api.github.com/search/repositories",
                params={
                    "q": f"topic:artificial-intelligence pushed:>{since}",
                    "sort": "updated",
                    "order": "desc",
                    "per_page": 1,
                },
            )
            total = payload.get("total_count")
            if isinstance(total, int):
                metrics.append(
                    {
                        "label": "Open-source AI repos active (24h)",
                        "value": total,
                        "detail": "GitHub repositories with AI topic updated in last 24h",
                        "source": "GitHub Search API",
                    }
                )
        except Exception as exc:
            warnings.append(f"GitHub AI activity metric unavailable: {exc}")

        return {
            "available": True,
            "metrics": metrics,
            "lab_activity": self._tech_keyword_card(notes, {
                "OpenAI": ["openai"],
                "Anthropic": ["anthropic"],
                "Google": ["google", "deepmind"],
                "Meta": ["meta"],
                "xAI": ["xai", "grok"],
            }),
            "infrastructure": self._tech_keyword_card(notes, {
                "GPU": ["gpu", "nvidia", "accelerator"],
                "Semiconductors": ["chip", "semiconductor", "foundry"],
                "Datacenter": ["datacenter", "cloud", "inference"]
            }),
            "enterprise_adoption": self._tech_keyword_card(notes, {
                "Enterprise": ["enterprise", "rollout", "deployment", "partnership"],
                "API platforms": ["api", "platform", "integration"],
            }),
            "funding_deals": self._tech_keyword_card(notes, {
                "Funding": ["funding", "raised", "series", "investment"],
                "M&A": ["acquisition", "merger", "deal"],
            }),
            "headlines": {
                "items": [
                    {"source": n.source_name, "headline": n.headline}
                    for n in notes[:5]
                ]
            },
            "open_source": self._tech_keyword_card(notes, {
                "Open models": ["open-source", "weights", "model release", "hugging face"],
                "Tooling": ["repo", "sdk", "framework", "library"],
            }),
            "developer_tooling": self._tech_keyword_card(notes, {
                "Agents": ["agent", "autonomous", "workflow"],
                "Coding": ["code", "developer", "copilot", "cursor", "cli"],
            }),
        }, warnings

    def _tech_keyword_card(self, notes: List[Any], groups: Dict[str, List[str]]) -> Dict[str, Any]:
        items = []
        for name, keys in groups.items():
            count = 0
            for note in notes:
                blob = f"{note.headline} {note.note} {note.excerpt}".lower()
                if any(key in blob for key in keys):
                    count += 1
            if count > 0:
                items.append({"name": name, "value": f"{count} signals"})
        return {"items": items}

    def _fred_latest(self, series: str) -> Tuple[Optional[float], Optional[str]]:
        try:
            response = self.session.get(
                f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}",
                timeout=self.config.fetch_timeout,
            )
            response.raise_for_status()
            rows = [line.strip() for line in response.text.splitlines() if line.strip()]
            values: List[float] = []
            for row in rows[1:]:
                _date, value = row.split(",", 1)
                if value != ".":
                    values.append(float(value))
            if not values:
                return None, "no numeric values"
            return values[-1], None
        except Exception as exc:
            return None, str(exc)

    def _fear_label(self, score: int) -> str:
        if score <= 24:
            return "Extreme Fear"
        if score <= 44:
            return "Fear"
        if score <= 55:
            return "Neutral"
        if score <= 74:
            return "Greed"
        return "Extreme Greed"

    def _human_dollars(self, value: float) -> str:
        if value >= 1_000_000_000_000:
            return f"${value / 1_000_000_000_000:.2f}T"
        if value >= 1_000_000_000:
            return f"${value / 1_000_000_000:.2f}B"
        return f"${value:,.0f}"

    def _ms_to_iso(self, value: Any) -> Optional[str]:
        try:
            if value is None:
                return None
            return datetime.fromtimestamp(float(value) / 1000.0, tz=timezone.utc).isoformat()
        except Exception:
            return None
