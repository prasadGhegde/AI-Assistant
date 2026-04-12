from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class RawItem:
    id: str
    category: str
    source_name: str
    source_url: str
    headline: str
    url: str
    excerpt: str
    published_at: Optional[str]
    collected_at: str
    tags: List[str] = field(default_factory=list)
    source_weight: float = 1.0
    freshness_hours: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ExtractedNote:
    category: str
    headline: str
    source_name: str
    url: str
    published_at: Optional[str]
    excerpt: str
    note: str
    score: float
    subskills: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    why_it_matters: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SignalPackage:
    generated_at: str
    lookback_hours: int
    what_matters_today: str
    sections: Dict[str, List[ExtractedNote]]
    market_movers: List[Dict[str, Any]] = field(default_factory=list)
    watchlist: List[str] = field(default_factory=list)
    model_used: str = "heuristic"
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "lookback_hours": self.lookback_hours,
            "what_matters_today": self.what_matters_today,
            "sections": {
                name: [note.to_dict() for note in notes]
                for name, notes in self.sections.items()
            },
            "market_movers": self.market_movers,
            "watchlist": self.watchlist,
            "model_used": self.model_used,
            "warnings": self.warnings,
        }


@dataclass
class ScriptPackage:
    generated_at: str
    title: str
    markdown: str
    spoken_text: str
    word_count: int
    model_used: str = "heuristic"
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PipelineResult:
    generated_at: datetime
    raw_path: str
    latest_raw_path: str
    notes_path: str
    latest_notes_path: str
    script_path: str
    latest_script_path: str
    dashboard_path: str
    latest_dashboard_path: str
    audio_path: Optional[str]
    latest_audio_path: Optional[str]
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["generated_at"] = self.generated_at.isoformat()
        return payload
