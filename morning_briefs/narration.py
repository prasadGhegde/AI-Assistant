from __future__ import annotations

import random
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

from .config import AppConfig
from .utils import load_json, save_json


PHRASE_KEYS = [
    "greetings",
    "operation_names",
    "intro_templates",
    "intro_lines",
    "weather_transitions",
    "geopolitics_transitions",
    "technology_transitions",
    "market_transitions",
    "closings",
    "final_questions",
]


@dataclass(frozen=True)
class NarrationPlan:
    greeting: str
    operation_name: str
    intro_template: str
    intro_line: str
    weather_transition: str
    geopolitics_transition: str
    technology_transition: str
    market_transition: str
    closing: str
    final_question: str

    @property
    def opening_line(self) -> str:
        return f"{self.greeting} {self.intro_template.format(operation_name=self.operation_name)}"

    @property
    def closing_line(self) -> str:
        return f"{self.closing} {self.final_question}"

    def to_dict(self) -> Dict[str, str]:
        payload = asdict(self)
        payload["opening_line"] = self.opening_line
        payload["closing_line"] = self.closing_line
        return payload


class NarrationPlanner:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.payload = load_json(config.narration_phrases_path, default={}) or {}
        self.banks = self.payload.get("phrase_banks", {})
        repeat = self.payload.get("repeat_protection", {})
        self.recent_limit = int(repeat.get("recent_limit", config.narration_recent_limit))
        self.protected_banks = set(repeat.get("protected_banks", []))

    def select(
        self,
        generated_at: datetime,
        *,
        persist: bool = True,
        recent_selections: Optional[List[Dict[str, str]]] = None,
    ) -> NarrationPlan:
        recent = recent_selections if recent_selections is not None else self._recent_history()
        chosen: Dict[str, str] = {}
        selected_values = set()
        for key in PHRASE_KEYS:
            selected = self._select_from_bank(key, recent, selected_values)
            chosen[key] = selected
            selected_values.add(selected)

        plan = NarrationPlan(
            greeting=chosen["greetings"],
            operation_name=chosen["operation_names"],
            intro_template=chosen["intro_templates"],
            intro_line=chosen["intro_lines"],
            weather_transition=chosen["weather_transitions"],
            geopolitics_transition=chosen["geopolitics_transitions"],
            technology_transition=chosen["technology_transitions"],
            market_transition=chosen["market_transitions"],
            closing=chosen["closings"],
            final_question=chosen["final_questions"],
        )
        if persist:
            self.record(plan, generated_at)
        return plan

    def record(self, plan: NarrationPlan, generated_at: datetime) -> None:
        history = load_json(self.config.narration_history_path, default={}) or {}
        runs = history.get("runs", [])
        runs.append(
            {
                "generated_at": generated_at.isoformat(),
                "selection": plan.to_dict(),
            }
        )
        history["runs"] = runs[-max(self.recent_limit * 4, 20):]
        save_json(self.config.narration_history_path, history)

    def _select_from_bank(
        self,
        key: str,
        recent: List[Dict[str, str]],
        selected_values: Iterable[str],
    ) -> str:
        entries = self._entries(key)
        if not entries:
            raise ValueError(f"Narration phrase bank is missing entries for {key}.")

        blocked = set(selected_values)
        if key in self.protected_banks:
            blocked.update(selection.get(self._selection_field(key), "") for selection in recent)

        candidates = [entry for entry in entries if entry["text"] not in blocked]
        if not candidates:
            candidates = entries
        return self._weighted_choice(candidates)

    def _entries(self, key: str) -> List[Dict[str, Any]]:
        raw_entries = self.banks.get(key, [])
        entries: List[Dict[str, Any]] = []
        for entry in raw_entries:
            if isinstance(entry, str):
                entries.append({"text": entry, "weight": 1.0})
            elif isinstance(entry, dict) and entry.get("text"):
                entries.append(
                    {
                        "text": str(entry["text"]),
                        "weight": float(entry.get("weight", 1.0)),
                    }
                )
        return entries

    def _weighted_choice(self, entries: List[Dict[str, Any]]) -> str:
        total = sum(max(float(entry.get("weight", 1.0)), 0.0) for entry in entries)
        if total <= 0:
            return random.SystemRandom().choice(entries)["text"]
        target = random.SystemRandom().uniform(0, total)
        cursor = 0.0
        for entry in entries:
            cursor += max(float(entry.get("weight", 1.0)), 0.0)
            if cursor >= target:
                return entry["text"]
        return entries[-1]["text"]

    def _recent_history(self) -> List[Dict[str, str]]:
        history = load_json(self.config.narration_history_path, default={}) or {}
        runs = history.get("runs", [])
        selections = [run.get("selection", {}) for run in runs if run.get("selection")]
        return selections[-self.recent_limit:]

    @staticmethod
    def _selection_field(bank_key: str) -> str:
        mapping = {
            "greetings": "greeting",
            "operation_names": "operation_name",
            "intro_templates": "intro_template",
            "intro_lines": "intro_line",
            "weather_transitions": "weather_transition",
            "geopolitics_transitions": "geopolitics_transition",
            "technology_transitions": "technology_transition",
            "market_transitions": "market_transition",
            "closings": "closing",
            "final_questions": "final_question",
        }
        return mapping[bank_key]
