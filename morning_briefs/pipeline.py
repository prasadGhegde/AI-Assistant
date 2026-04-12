from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import List

from .collector import NewsCollector
from .config import AppConfig
from .dashboard import DashboardRenderer
from .extractor import SignalExtractor
from .models import PipelineResult
from .tts import AudioPlayer, SpeechSynthesizer
from .utils import copy_latest, ensure_dirs, save_json, save_text
from .writer import ScriptWriter


def run_once(
    config: AppConfig,
    *,
    skip_tts: bool = False,
    play: bool = False,
) -> PipelineResult:
    ensure_dirs(
        [
            config.raw_dir,
            config.processed_dir,
            config.audio_dir,
            config.scripts_dir,
            config.dashboard_dir,
            config.log_dir,
        ]
    )
    generated_at = datetime.now(config.timezone)
    stamp = generated_at.strftime("%Y-%m-%d_%H%M%S")
    warnings: List[str] = []

    raw_items, collect_warnings = NewsCollector(config).collect()
    warnings.extend(collect_warnings)
    raw_payload = {
        "generated_at": generated_at.isoformat(),
        "lookback_hours": config.last_hours,
        "count": len(raw_items),
        "items": [item.to_dict() for item in raw_items],
        "warnings": collect_warnings,
    }
    raw_path = config.raw_dir / f"sources_{stamp}.json"
    latest_raw_path = config.raw_dir / "latest_sources.json"
    save_json(raw_path, raw_payload)
    save_json(latest_raw_path, raw_payload)

    signals, signal_warnings = SignalExtractor(config).extract(raw_items, generated_at)
    warnings.extend(signal_warnings)
    notes_path = config.processed_dir / f"notes_{stamp}.json"
    latest_notes_path = config.processed_dir / "latest_notes.json"
    save_json(notes_path, signals.to_dict())
    save_json(latest_notes_path, signals.to_dict())

    script, script_warnings = ScriptWriter(config).write(signals, generated_at)
    warnings.extend(script_warnings)
    script_path = config.scripts_dir / f"briefing_{stamp}.md"
    latest_script_path = config.scripts_dir / "latest.md"
    save_text(script_path, script.markdown)
    save_text(latest_script_path, script.markdown)

    audio_path = None
    latest_audio_path = None
    if not skip_tts:
        synth_path = config.audio_dir / f"briefing_{stamp}.mp3"
        audio_path, tts_warnings = SpeechSynthesizer(config).synthesize(
            script.spoken_text, synth_path
        )
        warnings.extend(tts_warnings)
        copied = copy_latest(audio_path, config.audio_dir / "latest.mp3")
        latest_audio_path = copied if copied else None
    else:
        warnings.append("TTS skipped by command-line flag.")

    dashboard_path = config.dashboard_dir / f"briefing_{stamp}.html"
    latest_dashboard_path = config.dashboard_dir / "latest.html"
    DashboardRenderer(config).render(
        signals=signals,
        script=script,
        generated_at=generated_at,
        audio_path=latest_audio_path,
        output_path=dashboard_path,
    )
    DashboardRenderer(config).render(
        signals=signals,
        script=script,
        generated_at=generated_at,
        audio_path=latest_audio_path,
        output_path=latest_dashboard_path,
    )

    if play and latest_audio_path:
        warnings.extend(AudioPlayer(config).play(latest_audio_path))

    result = PipelineResult(
        generated_at=generated_at,
        raw_path=str(raw_path),
        latest_raw_path=str(latest_raw_path),
        notes_path=str(notes_path),
        latest_notes_path=str(latest_notes_path),
        script_path=str(script_path),
        latest_script_path=str(latest_script_path),
        dashboard_path=str(dashboard_path),
        latest_dashboard_path=str(latest_dashboard_path),
        audio_path=str(audio_path) if audio_path else None,
        latest_audio_path=str(latest_audio_path) if latest_audio_path else None,
        warnings=warnings,
    )
    save_json(config.output_dir / "latest_result.json", result.to_dict())
    return result
