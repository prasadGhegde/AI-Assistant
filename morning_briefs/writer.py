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
        market_snapshot: Optional[Dict[str, object]] = None,
    ) -> Tuple[ScriptPackage, List[str]]:
        warnings: List[str] = []
        narration_plan = NarrationPlanner(self.config).select(generated_at)
        markdown = self._write_with_model(
            signals,
            generated_at,
            weather,
            narration_plan,
            market_snapshot,
        )
        model_used = self.config.openai_writer_model if markdown else "heuristic"
        if markdown is not None and not self._model_script_is_usable(markdown):
            markdown = None
            model_used = "heuristic"
            warnings.append(
                "OpenAI script writing produced an incomplete draft; used local fallback script."
            )
        if markdown is None:
            markdown = self._fallback_script(
                signals,
                generated_at,
                weather,
                narration_plan,
                market_snapshot,
            )
            if self.config.openai_api_key:
                if not any("incomplete draft" in warning for warning in warnings):
                    warnings.append("OpenAI script writing failed; used local fallback script.")
            else:
                warnings.append("OPENAI_API_KEY not set; used local fallback script.")

        markdown = self._reduce_repetition(markdown)
        markdown = self._append_sources(markdown, signals)
        sections = split_markdown_sections(markdown)
        spoken_text = dedupe_spoken_sentences(strip_markdown_for_speech(markdown))
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
        market_snapshot: Optional[Dict[str, object]],
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
            "market_snapshot": market_snapshot or {},
            "signals": signals.to_dict(),
        }
        return self.llm.text_response(
            system=(
                "You are an executive morning audio briefing writer. Write natural spoken copy, "
                "not newsletter copy. Use only supplied source material. Avoid duplicate stories "
                "across categories. Follow the product rules from the provided skills.md content. "
                "Do not speak source timestamps, source-brand newsletter labels, or awkward raw "
                "headline prefixes like 'The Download' or 'Stock Market Today'. Never narrate a "
                "news item as 'BBC says', 'Reuters reports', or any source-led headline recap. "
                "Convert each article into signal, implication, and useful watch point in your own "
                "clean debriefing language. Keep headings structural only and never speak them."
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
                "The Greeting section is only the mission-style greeting and one warm opening line; do not put news, weather, the date, or what-matters content there. "
                "Use the Weather section for a short practical field-condition read and one useful carry or wear cue. "
                "Use the news sections for clear prose and natural implications, without labels like 'Why it matters today'. "
                "In news sections, do not lead with source names and do not read article titles verbatim unless the title itself is the only factual signal. "
                "In the Stock market section, if market_snapshot includes BTC and crude oil values, speak both naturally with a small expressive read such as steady, holding firm, or slightly under pressure. "
                "Sound like an intelligence officer briefing the meaning of the material, with subtle rhythm and restrained personality. "
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
        market_snapshot: Optional[Dict[str, object]] = None,
    ) -> str:
        date = generated_at.strftime("%B %-d, %Y")
        parts = [
            f"# Morning Brief - {date}",
            "",
            "## Greeting",
            f"{narration_plan.opening_line} {narration_plan.intro_line}",
            "",
            "## Weather",
            f"{narration_plan.weather_transition} {self._fallback_weather(weather)}",
        ]
        for category in ("geopolitics", "technology_ai", "markets"):
            parts.extend(["", f"## {SECTION_TITLES[category]}"])
            parts.append(
                f"{self._transition_for_category(category, narration_plan)} "
                f"{self._fallback_section(category, signals.sections.get(category, []), market_snapshot)}"
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
            f"Carry {carry} and wear {wear}.{self._weather_caution(weather)}"
        )

    def _weather_caution(self, weather: WeatherReport) -> str:
        advisory = clean_text(weather.advisory)
        if "gust" in advisory.lower():
            return " Watch the gusts; secure loose layers before you step out."
        return ""

    def _fallback_section(
        self,
        category: str,
        notes: List[ExtractedNote],
        market_snapshot: Optional[Dict[str, object]] = None,
    ) -> str:
        if not notes:
            return (
                "The feeds did not produce enough fresh, high-confidence items for this section. "
                "That is useful in its own way: do not force a narrative from thin data. The better "
                "move is to keep checking primary sources and avoid overreacting before the next update lands."
            )
        lead = notes[0]
        sentences = [
            f"The clean signal on the board is this: {self._spoken_summary(lead)}"
        ]
        lead_implication = self._clean_implication(lead.why_it_matters)
        if lead_implication:
            sentences.append(lead_implication)
        if category == "markets":
            market_line = self._market_snapshot_line(market_snapshot)
            if market_line:
                sentences.append(market_line)
        follow_up_labels = {
            "geopolitics": ["A second movement to keep in view", "The third marker"],
            "technology_ai": ["Another useful shift", "One more signal from the tech stack"],
            "markets": ["The next market tell", "The third read on the tape"],
        }.get(category, ["The next signal", "The third signal"])
        for idx, note in enumerate(notes[1:3]):
            implication = self._clean_implication(note.why_it_matters)
            detail = self._spoken_summary(note)
            if implication:
                sentences.append(f"{follow_up_labels[idx]} is {detail} {implication}")
            else:
                sentences.append(f"{follow_up_labels[idx]} is {detail}")
        sentences.append(self._category_context(category))
        return " ".join(clean_text(sentence) for sentence in sentences)

    def _market_snapshot_line(self, market_snapshot: Optional[Dict[str, object]]) -> str:
        if not market_snapshot:
            return ""
        crypto = (market_snapshot.get("crypto") or {}) if isinstance(market_snapshot, dict) else {}
        energy = (market_snapshot.get("energy") or {}) if isinstance(market_snapshot, dict) else {}
        btc = None
        if not crypto.get("mock"):
            for row in crypto.get("items") or []:
                if str(row.get("symbol", "")).upper() == "BTC":
                    btc = row
                    break
        oil = None
        if not energy.get("mock"):
            for preferred in ("Brent", "WTI"):
                oil = next(
                    (
                        row for row in (energy.get("items") or [])
                        if preferred.lower() in str(row.get("name", "")).lower()
                    ),
                    None,
                )
                if oil:
                    break
        parts = []
        if btc and btc.get("price_usd") is not None:
            price = self._spoken_market_price(float(btc["price_usd"]), round_to=100)
            tone = self._market_tone(btc.get("change_24h"))
            parts.append(f"Bitcoin is holding around {price} dollars, {tone}.")
        if oil and oil.get("value") is not None:
            value = float(oil["value"])
            name = "Brent crude" if "brent" in str(oil.get("name", "")).lower() else "WTI crude"
            tone = "still elevated" if value >= 80 else "steady" if value >= 70 else "calmer on the board"
            parts.append(f"{name} is trading near {value:.0f} dollars a barrel, {tone}.")
        return " ".join(parts)

    def _spoken_market_price(self, value: float, *, round_to: int) -> str:
        rounded = int(round(value / round_to) * round_to)
        return f"{rounded:,}"

    def _market_tone(self, change: object) -> str:
        try:
            delta = float(change)
        except (TypeError, ValueError):
            return "steady"
        if delta >= 1.0:
            return "holding firm"
        if delta <= -1.0:
            return "slightly under pressure"
        return "steady"

    def _clean_implication(self, text: str) -> str:
        text = clean_text(text)
        text = re.sub(r"^(why (it|this) matters( today)?\s*:\s*)", "", text, flags=re.I)
        text = re.sub(r"^(this is important because\s*)", "", text, flags=re.I)
        if not text:
            return ""
        return text[0].upper() + text[1:]

    def _spoken_summary(self, note: ExtractedNote) -> str:
        preferred = clean_text(note.note or note.excerpt, 320)
        if preferred:
            return self._remove_source_led_opening(preferred)
        headline = clean_text(note.headline, 220)
        headline = re.sub(r"\s*\((?:live coverage|live updates?)\)\s*$", "", headline, flags=re.I)
        headline = re.sub(r"^(the download|stock market today)\s*:\s*", "", headline, flags=re.I)
        if ":" in headline:
            prefix, suffix = headline.split(":", 1)
            if len(prefix.strip()) <= 24 and suffix.strip():
                headline = suffix.strip()
        return self._remove_source_led_opening(headline)

    def _remove_source_led_opening(self, text: str) -> str:
        text = clean_text(text)
        source_pattern = (
            r"^(?:the\s+)?(?:bbc|reuters|ap|associated press|bloomberg|cnbc|"
            r"financial times|the verge|openai|mit technology review|wall street journal|"
            r"the wall street journal)\s+"
            r"(?:says|said|reports|reported|writes|wrote|notes|noted|according to)\s+(?:that\s+)?"
        )
        text = re.sub(source_pattern, "", text, flags=re.I)
        text = re.sub(r"^(?:headline|story|report)\s*:\s*", "", text, flags=re.I)
        return text[:1].upper() + text[1:] if text else text

    def _category_context(self, category: str) -> str:
        context = {
            "geopolitics": (
                "The operational read is whether this stays contained or starts touching trade "
                "routes, energy, sanctions, or alliance posture. Watch the official moves, not the "
                "loudest commentary; that is where the map usually tells the truth."
            ),
            "technology_ai": (
                "The useful question is whether this changes buying, product planning, security "
                "review, or compute access. In AI, a lab note can become a platform shift quickly; "
                "small spark, large blast radius."
            ),
            "markets": (
                "The market read is whether this affects broad risk appetite, rates expectations, "
                "or just a narrow pocket of names. Early tape can shout; breadth and rates tell us "
                "whether the shout has legs."
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


def dedupe_spoken_sentences(text: str) -> str:
    """Remove accidental repeated spoken sentences immediately before TTS."""
    sentences = re.split(r"(?<=[.!?])\s+", clean_text(text))
    out: List[str] = []
    seen = set()
    previous = ""
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        normalized = re.sub(r"[^a-z0-9]+", " ", sentence.lower()).strip()
        if normalized and (normalized == previous or normalized in seen):
            continue
        out.append(sentence)
        if normalized:
            seen.add(normalized)
            previous = normalized
    return clean_text(" ".join(out))


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
