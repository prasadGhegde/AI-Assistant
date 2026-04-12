from __future__ import annotations

import re
from datetime import datetime
from typing import List, Optional, Tuple

from .config import AppConfig
from .llm import OpenAIModelClient
from .models import ExtractedNote, ScriptPackage, SignalPackage
from .utils import clean_text, compact_for_prompt, load_json, parse_iso_datetime, word_count


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
        self, signals: SignalPackage, generated_at: datetime
    ) -> Tuple[ScriptPackage, List[str]]:
        warnings: List[str] = []
        markdown = self._write_with_model(signals, generated_at)
        model_used = self.config.openai_model if markdown else "heuristic"
        if markdown is None:
            markdown = self._fallback_script(signals, generated_at)
            if self.config.openai_api_key:
                warnings.append("OpenAI script writing failed; used local fallback script.")
            else:
                warnings.append("OPENAI_API_KEY not set; used local fallback script.")

        markdown = self._append_sources(markdown, signals)
        spoken_text = strip_markdown_for_speech(markdown)
        count = word_count(spoken_text)
        if count < 900 or count > 1200:
            warnings.append(f"Script word count is {count}; target is 1000 to 1100 words.")
        package = ScriptPackage(
            generated_at=generated_at.isoformat(),
            title=f"Morning Brief - {generated_at.strftime('%B %-d, %Y')}",
            markdown=markdown,
            spoken_text=spoken_text,
            word_count=count,
            model_used=model_used,
            warnings=warnings,
        )
        return package, warnings

    def _write_with_model(
        self, signals: SignalPackage, generated_at: datetime
    ) -> Optional[str]:
        if not self.llm.available:
            return None
        profile = load_json(self.config.briefing_profile_path, default={})
        payload = {
            "local_generated_at": generated_at.isoformat(),
            "briefing_profile": profile,
            "signals": signals.to_dict(),
        }
        return self.llm.text_response(
            system=(
                "You are an executive morning audio briefing writer. Write natural spoken copy, "
                "not newsletter copy. Use only supplied source material. Avoid duplicate stories "
                "across categories. Use exact dates when relevant. Keep the total script between "
                "1000 and 1100 words for roughly eight minutes of narration."
            ),
            user=(
                "Write a Markdown script with exactly these headings: # Morning Brief, ## Intro, "
                "## Geopolitics, ## Technology and AI, ## Stock market, ## Watch list for today. "
                "The intro should run about 45 seconds. Geopolitics, Technology and AI, and Stock "
                "market should each run about two minutes. Watch list should run about one minute. "
                "Do not use bullets in spoken sections. End Geopolitics, Technology and AI, Stock "
                "market, and Watch list with a conversational sentence that begins exactly: "
                "'Why it matters today:'. Keep source URLs out of the spoken sections.\n\n"
                + compact_for_prompt(payload, max_chars=22000)
            ),
            max_output_tokens=3600,
        )

    def _fallback_script(
        self, signals: SignalPackage, generated_at: datetime
    ) -> str:
        date = generated_at.strftime("%B %-d, %Y")
        parts = [
            f"# Morning Brief - {date}",
            "",
            "## Intro",
            (
                f"Good morning. It is {date}, and this is your eight-minute work briefing. "
                f"{signals.what_matters_today} We will move quickly through geopolitics, "
                "technology and AI, the stock market, and the watch list that deserves attention "
                "as the day opens. The source mix is weighted toward the last twenty-four hours, "
                "so treat this as a live orientation rather than a final verdict."
            ),
        ]
        for category in ("geopolitics", "technology_ai", "markets"):
            parts.extend(["", f"## {SECTION_TITLES[category]}"])
            parts.append(self._fallback_section(category, signals.sections.get(category, [])))
        parts.extend(["", "## Watch list for today", self._fallback_watchlist(signals)])
        return "\n".join(parts).strip()

    def _fallback_section(self, category: str, notes: List[ExtractedNote]) -> str:
        if not notes:
            return (
                "The feeds did not produce enough fresh, high-confidence items for this section. "
                "That is useful in its own way: do not force a narrative from thin data. "
                "Why it matters today: a quiet section means the better move is to keep checking "
                "primary sources and avoid overreacting before the next update lands."
            )
        lead = notes[0]
        sentences = [
            (
                f"The lead story is from {lead.source_name}: {lead.headline}. "
                f"{self._dated_context(lead)} {lead.note}"
            )
        ]
        sentences.append(self._category_context(category))
        for note in notes[1:4]:
            sentences.append(
                f"Also watch {note.headline}. {self._dated_context(note)} {note.note}"
            )
        close = lead.why_it_matters
        if not close.lower().startswith("why it matters today"):
            close = f"Why it matters today: {close}"
        sentences.append(close)
        return " ".join(clean_text(sentence) for sentence in sentences)

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

    def _fallback_watchlist(self, signals: SignalPackage) -> str:
        if not signals.watchlist:
            return (
                "For the watch list, keep an eye on source updates, market-open reaction, "
                "and whether any single story starts spilling into another category. "
                "Why it matters today: the most important move may be the second-order effect, "
                "not the headline itself."
            )
        watch = " ".join(signals.watchlist[:4])
        return (
            f"For the watch list, keep these threads open: {watch} Check whether fresh reporting "
            "confirms the early read, whether markets price it in, and whether a policy or platform "
            "response changes the story by midday. Why it matters today: the watch list turns the "
            "briefing into action, so you know what to revisit before decisions harden."
        )

    def _dated_context(self, note: ExtractedNote) -> str:
        dt = parse_iso_datetime(note.published_at)
        if dt is None:
            return "The item did not include a clean publication timestamp."
        local_dt = dt.astimezone(self.config.timezone)
        return f"The source timestamp is {local_dt.strftime('%B %-d, %Y at %-I:%M %p')}."

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
            stripped = stripped.lstrip("#").strip()
        stripped = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", stripped)
        stripped = stripped.replace("**", "").replace("__", "")
        lines.append(stripped)
    return clean_text(" ".join(lines))
