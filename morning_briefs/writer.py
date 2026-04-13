from __future__ import annotations

import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from .config import AppConfig
from .llm import OpenAIModelClient
from .models import ExtractedNote, ScriptPackage, SignalPackage, WeatherReport
from .narration import NarrationPlan, NarrationPlanner
from .utils import clean_text, compact_for_prompt, load_json, word_count


SECTION_TITLES = {
    "geopolitics": "Geopolitics",
    "technology_ai": "Technology and AI",
    "markets": "Stock market",
}

class ScriptWriter:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.llm = OpenAIModelClient(config)

    def write(
        self,
        signals: SignalPackage,
        generated_at: datetime,
        weather: Optional[WeatherReport] = None,
    ) -> Tuple[ScriptPackage, List[str]]:
        warnings: List[str] = []
        narration_plan = NarrationPlanner(self.config).select(generated_at)
        markdown = self._write_with_model(signals, generated_at, weather, narration_plan)
        model_used = self.config.openai_writer_model if markdown else "heuristic"
        if markdown is not None and not self._model_script_is_usable(markdown):
            markdown = None
            model_used = "heuristic"
            warnings.append(
                "OpenAI script writing produced an incomplete draft; used local fallback script."
            )
        if markdown is None:
            markdown = self._fallback_script(signals, generated_at, weather, narration_plan)
            if self.config.openai_api_key:
                if not any("incomplete draft" in warning for warning in warnings):
                    warnings.append("OpenAI script writing failed; used local fallback script.")
            else:
                warnings.append("OPENAI_API_KEY not set; used local fallback script.")

        markdown = self._reduce_repetition(markdown)
        markdown = self._append_sources(markdown, signals)
        sections = split_markdown_sections(markdown)
        spoken_text = strip_markdown_for_speech(markdown)
        count = word_count(spoken_text)
        if count < 850 or count > 1150:
            warnings.append(
                f"Script word count is {count}; target is 850 to 1150 words."
            )
        package = ScriptPackage(
            generated_at=generated_at.isoformat(),
            title=f"{narration_plan.operation_name} - {generated_at.strftime('%B %-d, %Y')}",
            markdown=markdown,
            spoken_text=spoken_text,
            word_count=count,
            sections=sections,
            narration_plan=narration_plan.to_dict(),
            model_used=model_used,
            warnings=warnings,
        )
        return package, warnings

    def _write_with_model(
        self,
        signals: SignalPackage,
        generated_at: datetime,
        weather: Optional[WeatherReport],
        narration_plan: NarrationPlan,
    ) -> Optional[str]:
        if not self.llm.available:
            return None
        profile = load_json(self.config.briefing_profile_path, default={})
        skills_text = self._skills_text()
        payload = {
            "local_generated_at": generated_at.isoformat(),
            "user_name": self.config.user_name,
            "weather": weather.to_dict() if weather else None,
            "briefing_profile": profile,
            "narration_framework": narration_plan.to_dict(),
            "signals": signals.to_dict(),
        }
        return self.llm.text_response(
            system=(
                "You are an executive morning audio briefing writer. Write natural spoken copy, "
                "not newsletter copy. Use only supplied source material. Avoid duplicate stories "
                "across categories. Follow the product rules from the provided skills.md content. "
                "Do not speak source timestamps, source-brand newsletter labels, or awkward raw "
                "headline prefixes like 'The Download' or 'Stock Market Today'. Summarize those "
                "stories in clean prose instead. Keep headings structural only and never speak them."
            ),
            user=(
                "Write a Markdown script with these headings only: # Morning Brief, ## Greeting, "
                "## Weather, ## Geopolitics, ## Technology and AI, ## Stock market, "
                "## Closing question. Use narration_framework.opening_line in Greeting, narration_framework.weather_transition at the start of Weather, "
                "narration_framework.geopolitics_transition at the start of Geopolitics, narration_framework.technology_transition at the start of Technology and AI, "
                "narration_framework.market_transition at the start of Stock market, "
                "and narration_framework.closing_line in Closing question. "
                f"Write for {self.config.user_name}. Keep the tone human, useful, and work-morning focused. "
                "Do not use bullets in spoken sections. Keep source URLs out of spoken sections. "
                "Do not say or restate source timestamps. Do not repeat awkward raw headlines when a clean paraphrase is better. "
                "Use the Weather section for a short practical read on current conditions and one useful carry or wear cue. "
                "Use the news sections for clear prose and natural implications, without labels like 'Why it matters today'. "
                "Do not repeat the same implication wording across sections; each section must add new information.\n\n"
                "skills.md context:\n"
                + compact_for_prompt(skills_text, max_chars=10000)
                + "\n\n"
                + compact_for_prompt(payload, max_chars=22000)
            ),
            model=self.config.openai_writer_model,
            max_output_tokens=3600,
        )

    def _fallback_script(
        self,
        signals: SignalPackage,
        generated_at: datetime,
        weather: Optional[WeatherReport],
        narration_plan: NarrationPlan,
    ) -> str:
        date = generated_at.strftime("%B %-d, %Y")
        parts = [
            f"# Morning Brief - {date}",
            "",
            "## Greeting",
            (
                f"{narration_plan.opening_line} {narration_plan.intro_line} It is {date}, and the "
                f"main task is to stay close to the strongest developments without drowning in filler. "
                f"{signals.what_matters_today}"
            ),
            "",
            "## Weather",
            f"{narration_plan.weather_transition} {self._fallback_weather(weather)}",
        ]
        for category in ("geopolitics", "technology_ai", "markets"):
            parts.extend(["", f"## {SECTION_TITLES[category]}"])
            parts.append(
                f"{self._transition_for_category(category, narration_plan)} "
                f"{self._fallback_section(category, signals.sections.get(category, []))}"
            )
        parts.extend(
            [
                "",
                "## Closing question",
                narration_plan.closing_line,
            ]
        )
        return "\n".join(parts).strip()

    def _transition_for_category(self, category: str, narration_plan: NarrationPlan) -> str:
        transitions = {
            "geopolitics": narration_plan.geopolitics_transition,
            "technology_ai": narration_plan.technology_transition,
            "markets": narration_plan.market_transition,
        }
        return transitions.get(category, "The next pane is ready.")

    def _fallback_weather(self, weather: Optional[WeatherReport]) -> str:
        if weather is None:
            return (
                "The weather feed is quiet for the moment, so play it smart before stepping out: "
                "glance at the sky, dress in adaptable layers, and keep the morning nimble."
            )
        temp = (
            "temperature data is unavailable"
            if weather.temperature is None
            else f"{round(weather.temperature)} degrees {weather.temperature_unit}"
        )
        feels = (
            ""
            if weather.apparent_temperature is None
            else f", feeling closer to {round(weather.apparent_temperature)}"
        )
        carry = ", ".join(weather.carry) if weather.carry else "the basics"
        wear = ", ".join(weather.wear) if weather.wear else "comfortable layers"
        return (
            f"In {weather.location_name}, it is {temp}{feels}, with {weather.conditions}. "
            f"Carry {carry}, wear {wear}, and {weather.advisory.lower()} That is enough weather for now; "
            "let us move into the main signal."
        )

    def _fallback_section(self, category: str, notes: List[ExtractedNote]) -> str:
        if not notes:
            return (
                "The feeds did not produce enough fresh, high-confidence items for this section. "
                "That is useful in its own way: do not force a narrative from thin data. The better "
                "move is to keep checking primary sources and avoid overreacting before the next update lands."
            )
        lead = notes[0]
        sentences = [
            (
                f"From {lead.source_name}, the clearest thread is this: {self._spoken_summary(lead)}"
            )
        ]
        sentences.append(self._category_context(category))
        follow_up_labels = ["Second signal", "Third signal"]
        for idx, note in enumerate(notes[1:3]):
            sentences.append(f"{follow_up_labels[idx]}: {self._spoken_summary(note)}")
        sentences.append(self._clean_implication(lead.why_it_matters))
        return " ".join(clean_text(sentence) for sentence in sentences)

    def _clean_implication(self, text: str) -> str:
        text = clean_text(text)
        text = re.sub(r"^(why (it|this) matters( today)?\s*:\s*)", "", text, flags=re.I)
        text = re.sub(r"^(this is important because\s*)", "", text, flags=re.I)
        if not text:
            return "The practical implication is to watch the follow-through, not just the headline."
        return text[0].upper() + text[1:]

    def _spoken_summary(self, note: ExtractedNote) -> str:
        preferred = clean_text(note.note or note.excerpt, 320)
        if preferred:
            return preferred
        headline = clean_text(note.headline, 220)
        headline = re.sub(r"\s*\((?:live coverage|live updates?)\)\s*$", "", headline, flags=re.I)
        headline = re.sub(r"^(the download|stock market today)\s*:\s*", "", headline, flags=re.I)
        if ":" in headline:
            prefix, suffix = headline.split(":", 1)
            if len(prefix.strip()) <= 24 and suffix.strip():
                headline = suffix.strip()
        return headline

    def _category_context(self, category: str) -> str:
        context = {
            "geopolitics": (
                "The workday read is whether this remains a contained political story or starts "
                "touching trade routes, energy prices, sanctions, or alliance posture. Listen for "
                "official confirmation, not just anonymous positioning, and watch whether regional "
                "actors respond before markets have fully settled."
            ),
            "technology_ai": (
                "The practical question is whether this changes near-term buying, product planning, "
                "security review, or compute availability. In AI, a model story can become a platform "
                "story quickly, and a policy story can become a deployment constraint before teams "
                "have adjusted their road maps."
            ),
            "markets": (
                "The market lens is whether the story affects broad risk appetite, rates expectations, "
                "or just a narrow group of names. Early headlines can move futures, but the durable "
                "signal usually comes from breadth, sector leadership, and whether the bond market "
                "confirms the stock move."
            ),
        }
        return context.get(
            category,
            "The useful read is the follow-through, not the first headline.",
        )

    def _model_script_is_usable(self, markdown: str) -> bool:
        required_headings = [
            "## Greeting",
            "## Weather",
            "## Geopolitics",
            "## Technology and AI",
            "## Stock market",
            "## Closing question",
        ]
        if any(heading not in markdown for heading in required_headings):
            return False
        spoken = strip_markdown_for_speech(markdown)
        return word_count(spoken) >= 500

    def _skills_text(self) -> str:
        skills_path = self.config.project_root / "skills.md"
        if not skills_path.exists():
            return ""
        return skills_path.read_text(encoding="utf-8")

    def _reduce_repetition(self, markdown: str) -> str:
        lines = markdown.splitlines()
        out: List[str] = []
        seen_normalized = set()
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                out.append(line)
                continue
            sentences = re.split(r"(?<=[.!?])\s+", stripped)
            kept: List[str] = []
            for sentence in sentences:
                normalized = re.sub(r"[^a-z0-9 ]+", "", sentence.lower()).strip()
                if len(normalized) < 18:
                    kept.append(sentence)
                    continue
                if normalized in seen_normalized:
                    continue
                seen_normalized.add(normalized)
                kept.append(sentence)
            reduced = " ".join(kept).strip()
            if reduced:
                out.append(reduced)
        return "\n".join(out).strip()

    def _append_sources(self, markdown: str, signals: SignalPackage) -> str:
        lines = [markdown.strip(), "", "## Source links"]
        seen = set()
        for notes in signals.sections.values():
            for note in notes:
                if note.url in seen:
                    continue
                seen.add(note.url)
                lines.append(f"- [{note.source_name}: {note.headline}]({note.url})")
        return "\n".join(lines).strip() + "\n"


def strip_markdown_for_speech(markdown: str) -> str:
    before_sources = markdown.split("## Source links", 1)[0]
    lines = []
    for line in before_sources.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            continue
        stripped = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", stripped)
        stripped = stripped.replace("**", "").replace("__", "")
        lines.append(stripped)
    return clean_text(" ".join(lines))


def split_markdown_sections(markdown: str) -> Dict[str, str]:
    sections: Dict[str, List[str]] = {}
    current_key = "title"
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            current_key = _heading_key(stripped[3:])
            sections.setdefault(current_key, [])
            continue
        if stripped.startswith("# "):
            continue
        if current_key == "source_links":
            continue
        if stripped:
            sections.setdefault(current_key, []).append(stripped)
    return {
        key: clean_text(" ".join(value))
        for key, value in sections.items()
        if key != "title"
    }


def _heading_key(value: str) -> str:
    normalized = value.strip().lower()
    mapping = {
        "greeting": "greeting",
        "weather": "weather",
        "geopolitics": "geopolitics",
        "technology and ai": "technology_ai",
        "stock market": "markets",
        "closing question": "closing_question",
        "source links": "source_links",
    }
    return mapping.get(normalized, normalized.replace(" ", "_"))


