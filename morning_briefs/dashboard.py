from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

from .config import AppConfig
from .models import ScriptPackage, SignalPackage
from .paths import WEB_DIR
from .utils import save_json


class DashboardRenderer:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def render(
        self,
        *,
        signals: SignalPackage,
        script: ScriptPackage,
        generated_at: datetime,
        audio_path: Optional[Path],
        output_path: Path,
    ) -> Tuple[Path, Path]:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        assets_dir = output_path.parent / "assets"
        assets_dir.mkdir(parents=True, exist_ok=True)
        for asset_name in ("dashboard.css", "dashboard.js"):
            shutil.copyfile(WEB_DIR / "static" / asset_name, assets_dir / asset_name)

        data = self._dashboard_data(signals, script, generated_at, audio_path)
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
        generated_at: datetime,
        audio_path: Optional[Path],
    ) -> Dict[str, object]:
        audio_src = None
        if audio_path and audio_path.exists():
            audio_src = "../audio/latest.mp3"
        sections = {
            category: [note.to_dict() for note in notes]
            for category, notes in signals.sections.items()
        }
        return {
            "generated_at": generated_at.isoformat(),
            "generated_label": generated_at.strftime("%A, %B %-d, %Y at %-I:%M %p"),
            "timezone": self.config.timezone_name,
            "what_matters_today": signals.what_matters_today,
            "sections": sections,
            "market_movers": signals.market_movers,
            "watchlist": signals.watchlist,
            "script_markdown": script.markdown,
            "word_count": script.word_count,
            "model_used": {
                "signals": signals.model_used,
                "script": script.model_used,
            },
            "warnings": [*signals.warnings, *script.warnings],
            "audio_src": audio_src,
        }
