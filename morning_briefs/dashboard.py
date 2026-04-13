from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

from .config import AppConfig
from .models import ScriptPackage, SignalPackage, WeatherReport
from .paths import WEB_DIR
from .utils import save_json
from .utils import word_count


class DashboardRenderer:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def render(
        self,
        *,
        signals: SignalPackage,
        script: ScriptPackage,
        weather: WeatherReport,
        intel: Dict[str, object],
        generated_at: datetime,
        audio_path: Optional[Path],
        output_path: Path,
    ) -> Tuple[Path, Path]:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        assets_dir = output_path.parent / "assets"
        assets_dir.mkdir(parents=True, exist_ok=True)
        for asset_name in ("dashboard.css", "dashboard.js"):
            shutil.copyfile(WEB_DIR / "static" / asset_name, assets_dir / asset_name)
        if self.config.music_enabled and self.config.music_source_path.exists():
            music_asset_path = assets_dir / self.config.music_source_path.name
            if (
                not music_asset_path.exists()
                or music_asset_path.stat().st_size
                != self.config.music_source_path.stat().st_size
            ):
                shutil.copyfile(self.config.music_source_path, music_asset_path)

        data = self._dashboard_data(signals, script, weather, intel, generated_at, audio_path)
        data_path = output_path.with_suffix(".json")
        save_json(data_path, data)

        template = (WEB_DIR / "templates" / "dashboard.html").read_text(
            encoding="utf-8"
        )
        inline_json = json.dumps(data, ensure_ascii=False).replace("<", "\\u003c")
        html = (
            template.replace("__BRIEFING_DATA__", inline_json)
            .replace("__AUDIO_SRC__", data.get("audio_src") or "")
            .replace("__GENERATED_AT__", generated_at.strftime("%B %-d, %Y, %-I:%M %p"))
        )
        output_path.write_text(html, encoding="utf-8")
        return output_path, data_path

    def _dashboard_data(
        self,
        signals: SignalPackage,
        script: ScriptPackage,
        weather: WeatherReport,
        intel: Dict[str, object],
        generated_at: datetime,
        audio_path: Optional[Path],
    ) -> Dict[str, object]:
        audio_src = None
        if audio_path and audio_path.exists():
            audio_src = "../audio/latest.mp3"
        music_src = None
        if self.config.music_enabled and self.config.music_source_path.exists():
            music_src = f"assets/{self.config.music_source_path.name}"
        sections = {
            category: [note.to_dict() for note in notes]
            for category, notes in signals.sections.items()
        }
        return {
            "generated_at": generated_at.isoformat(),
            "generated_label": generated_at.strftime("%A, %B %-d, %Y at %-I:%M %p"),
            "timezone": self.config.timezone_name,
            "user_name": self.config.user_name,
            "what_matters_today": signals.what_matters_today,
            "weather": weather.to_dict(),
            "intel": intel,
            "sections": sections,
            "market_movers": signals.market_movers,
            "script_markdown": script.markdown,
            "script_sections": script.sections,
            "narration_plan": script.narration_plan,
            "word_count": script.word_count,
            "presentation_timeline": self._presentation_timeline(script, signals),
            "music_enabled": self.config.music_enabled,
            "browser_music_enabled": self.config.browser_music_enabled,
            "music_volume": self.config.music_volume,
            "followup_timeout_seconds": self.config.followup_timeout_seconds,
            "audio_driver": self.config.audio_driver,
            "music_src": music_src,
            "music_duration_seconds": self.config.music_max_duration_seconds,
            "model_used": {
                "signals": signals.model_used,
                "script": script.model_used,
            },
            "warnings": [*signals.warnings, *script.warnings],
            "audio_src": audio_src,
        }

    def _presentation_timeline(
        self, script: ScriptPackage, signals: SignalPackage
    ) -> Dict[str, object]:
        order = [
            ("greeting", "Greeting", 8),
            ("weather", "Weather", 10),
            ("geopolitics", "Geopolitics", 18),
            ("technology_ai", "Technology and AI", 18),
            ("markets", "Stock market", 18),
            ("closing_question", "Closing question", 5),
        ]
        wpm = 145
        cursor = 0.0
        section_cues = []
        topic_cues = []
        for key, label, minimum in order:
            text = script.sections.get(key, "")
            estimated = max(float(minimum), word_count(text) / wpm * 60.0)
            start = cursor
            end = cursor + estimated
            section_cues.append(
                {
                    "key": key,
                    "label": label,
                    "start": round(start, 2),
                    "end": round(end, 2),
                    "duration": round(estimated, 2),
                }
            )
            notes = signals.sections.get(key, [])
            if notes:
                weights = [
                    max(12, word_count(f"{note.headline} {note.note} {note.why_it_matters}"))
                    for note in notes
                ]
                total_weight = sum(weights) or len(notes)
                topic_cursor = start
                for index, note in enumerate(notes):
                    slice_size = estimated * (weights[index] / total_weight)
                    topic_start = topic_cursor
                    topic_end = min(topic_start + slice_size, end)
                    topic_cues.append(
                        {
                            "key": f"{key}-{index}",
                            "section": key,
                            "label": label,
                            "index": index,
                            "headline": note.headline,
                            "start": round(topic_start, 2),
                            "end": round(topic_end, 2),
                            "target_id": f"topic-{key}-{index}",
                        }
                    )
                    topic_cursor = topic_end
            cursor = end
        return {
            "total_seconds": round(cursor, 2),
            "sections": section_cues,
            "topics": topic_cues,
        }
