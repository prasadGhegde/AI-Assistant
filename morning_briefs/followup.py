from __future__ import annotations

from typing import Any, Dict, List

from .config import AppConfig
from .llm import OpenAIModelClient
from .utils import clean_text, compact_for_prompt, load_json


class FollowUpResponder:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.llm = OpenAIModelClient(config)

    def answer(self, question: str) -> str:
        question = clean_text(question, 500)
        if not question:
            return "Type the thread you want me to chase and I will keep it concise."
        context = self._context()
        if self.llm.available:
            response = self.llm.text_response(
                system=(
                    "You are the same premium morning assistant from the briefing. Answer quickly, "
                    "naturally, and concretely. Keep the tone warm, composed, and lightly British "
                    "in cadence. Use only the local briefing context unless the user asks for a "
                    "general reasoning answer. Do not imitate any copyrighted character."
                ),
                user=(
                    "Answer this follow-up in 2 to 5 concise sentences.\n\n"
                    f"Question: {question}\n\n"
                    f"Briefing context: {compact_for_prompt(context, max_chars=12000)}"
                ),
                model=self.config.openai_writer_model,
                max_output_tokens=500,
            )
            if response:
                return clean_text(response, 900)
        return self._fallback_answer(question, context)

    def _context(self) -> Dict[str, Any]:
        return {
            "weather": load_json(self.config.processed_dir / "latest_weather.json", {}),
            "notes": load_json(self.config.processed_dir / "latest_notes.json", {}),
            "script": load_json(self.config.dashboard_dir / "latest.json", {}).get(
                "script_sections", {}
            ),
        }

    def _fallback_answer(self, question: str, context: Dict[str, Any]) -> str:
        notes = context.get("notes", {}).get("sections", {})
        weather = context.get("weather", {})
        lowered = question.lower()
        if "weather" in lowered or "wear" in lowered or "carry" in lowered:
            advisory = weather.get("advisory")
            if advisory:
                return advisory
        for category in ("geopolitics", "technology_ai", "markets"):
            if category.split("_")[0] in lowered:
                items: List[Dict[str, Any]] = notes.get(category, [])
                if items:
                    headline = items[0].get("headline", "the lead item")
                    implication = items[0].get("why_it_matters") or items[0].get("note")
                    return clean_text(
                        f"I would start with {headline}. {implication} Keep an eye on whether fresh reporting confirms it before making a hard call.",
                        850,
                    )
        return (
            "I have the thread. The quick move is to check the latest source update, see whether "
            "it changes decisions today, and ignore the noise unless it creates a concrete follow-on."
        )
