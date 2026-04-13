from __future__ import annotations

import time
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from .browser import BrowserPresenter
from .collector import NewsCollector
from .config import AppConfig
from .dashboard import DashboardRenderer
from .extractor import SignalExtractor
from .models import PipelineResult
from .music import MusicBed
from .server import start_background_server
from .tts import AudioPlayer, SpeechSynthesizer
from .audio_fx import VoiceEffectProcessor, VoiceRenderResult
from .utils import copy_latest, ensure_dirs, save_json, save_text
from .utils import word_count
from .weather import WeatherService
from .writer import ScriptWriter
from .intel_data import DashboardIntelCollector


def run_once(
    config: AppConfig,
    *,
    skip_tts: bool = False,
    play: bool = False,
    open_browser: bool = True,
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
    rejected_count = sum(1 for item in raw_items if not item.is_relevant)
    raw_payload = {
        "generated_at": generated_at.isoformat(),
        "lookback_hours": config.last_hours,
        "count": len(raw_items),
        "accepted_count": len(raw_items) - rejected_count,
        "rejected_count": rejected_count,
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

    weather, weather_warnings = WeatherService(config).fetch()
    warnings.extend(weather_warnings)
    weather_path = config.processed_dir / f"weather_{stamp}.json"
    latest_weather_path = config.processed_dir / "latest_weather.json"
    save_json(weather_path, weather.to_dict())
    save_json(latest_weather_path, weather.to_dict())

    intel_modules, intel_warnings = DashboardIntelCollector(config).collect(signals)
    warnings.extend(intel_warnings)

    script, script_warnings = ScriptWriter(config).write(
        signals,
        generated_at,
        weather,
        market_snapshot=intel_modules.get("markets", {}),
    )
    warnings.extend(script_warnings)
    script_path = config.scripts_dir / f"briefing_{stamp}.md"
    latest_script_path = config.scripts_dir / "latest.md"
    save_text(script_path, script.markdown)
    save_text(latest_script_path, script.markdown)

    audio_path = None
    latest_audio_path = None
    timeout_closing_audio_path = None
    voice_result: Optional[VoiceRenderResult] = None
    voice_final_paths: Dict[str, str] = {}
    if not skip_tts:
        synth_path = config.audio_dir / f"briefing_{stamp}.mp3"
        narration_path = config.audio_dir / f"briefing_{stamp}_clean.mp3"
        audio_path, tts_warnings = SpeechSynthesizer(config).synthesize(
            script.spoken_text, narration_path
        )
        warnings.extend(tts_warnings)
        if audio_path:
            voice_result, voice_warnings = VoiceEffectProcessor(config).render_variants(
                clean_tts_path=audio_path,
                output_stem=config.audio_dir / f"briefing_{stamp}",
            )
            warnings.extend(voice_warnings)
            audio_path = voice_result.default_path
            warnings.extend(_copy_voice_aliases(config, voice_result))

        if voice_result and config.music_enabled:
            estimated_duration = max(script.word_count / 145 * 60, 45)
            if estimated_duration > config.music_max_duration_seconds:
                warnings.append(
                    "Estimated narration duration exceeds the configured music bed limit; "
                    "shorten the script target or provide a longer music file."
                )
            for preset_name, variant_path in voice_result.variant_paths.items():
                final_path = variant_path.with_name(f"{variant_path.stem}_final.mp3")
                mixed_path, _music_path, music_warnings = MusicBed(config).create_and_mix(
                    narration_path=variant_path,
                    output_path=final_path,
                    duration_seconds=estimated_duration,
                )
                voice_final_paths[preset_name] = str(mixed_path)
                warnings.extend(music_warnings)
            default_final = voice_final_paths.get(voice_result.default_preset)
            if default_final:
                audio_path = Path(default_final)
                copy_latest(audio_path, synth_path)
            warnings.extend(_copy_voice_final_aliases(config, voice_result, voice_final_paths))

        copied = copy_latest(audio_path, config.audio_dir / "latest.mp3")
        latest_audio_path = copied if copied else None
        timeout_line = str(script.narration_plan.get("timeout_closing_line", "")).strip()
        if timeout_line:
            timeout_closing_audio_path, closing_warnings = _render_timeout_closing_audio(
                config=config,
                line=timeout_line,
                stamp=stamp,
            )
            warnings.extend(closing_warnings)
    else:
        warnings.append("TTS skipped by command-line flag.")

    dashboard_path = config.dashboard_dir / f"briefing_{stamp}.html"
    latest_dashboard_path = config.dashboard_dir / "latest.html"
    DashboardRenderer(config).render(
        signals=signals,
        script=script,
        weather=weather,
        intel=intel_modules,
        generated_at=generated_at,
        audio_path=latest_audio_path,
        timeout_closing_audio_path=timeout_closing_audio_path,
        output_path=dashboard_path,
    )
    DashboardRenderer(config).render(
        signals=signals,
        script=script,
        weather=weather,
        intel=intel_modules,
        generated_at=generated_at,
        audio_path=latest_audio_path,
        timeout_closing_audio_path=timeout_closing_audio_path,
        output_path=latest_dashboard_path,
    )

    dashboard_server = None
    presenter = None
    browser_audio_session = False
    opened_url = ""
    if open_browser and config.open_browser:
        presenter = BrowserPresenter(config)
        browser_audio_session = (
            play
            and latest_audio_path is not None
            and config.audio_driver == "browser"
            and config.serve_dashboard_for_runs
        )
        if config.serve_dashboard_for_runs:
            try:
                dashboard_server = start_background_server(
                    config,
                    host=config.dashboard_host,
                    port=config.dashboard_port,
                )
                warnings.extend(
                    presenter.open_dashboard_url(
                        dashboard_server.url,
                        presentation=config.presentation_mode,
                        external_audio=play
                        and latest_audio_path is not None
                        and not browser_audio_session,
                    )
                )
                opened_url = presenter.last_url
            except Exception as exc:
                warnings.append(
                    f"Could not start local dashboard server; opened file dashboard instead: {exc}"
                )
                warnings.extend(
                    presenter.open_dashboard(
                        latest_dashboard_path,
                        presentation=config.presentation_mode,
                        external_audio=play and latest_audio_path is not None,
                    )
                )
                opened_url = presenter.last_url
        else:
            warnings.extend(
                presenter.open_dashboard(
                    latest_dashboard_path,
                    presentation=config.presentation_mode,
                    external_audio=play and latest_audio_path is not None,
                )
            )
            opened_url = presenter.last_url

    if browser_audio_session and dashboard_server:
        timeout = _browser_session_timeout(script.word_count, config)
        completed = dashboard_server.wait_for_completion(timeout)
        if not completed:
            warnings.append(
                "Browser presentation did not report completion before timeout; closing the tab."
            )
        if presenter:
            warnings.extend(presenter.close_url(opened_url))
    elif play and latest_audio_path:
        warnings.extend(AudioPlayer(config).play(latest_audio_path))
        if dashboard_server:
            time.sleep(config.followup_timeout_seconds + 2)
        if presenter:
            warnings.extend(presenter.close_url(opened_url))

    if dashboard_server:
        dashboard_server.shutdown()

    diagnostics = _write_run_diagnostics(
        config=config,
        stamp=stamp,
        generated_at=generated_at,
        raw_items=raw_items,
        signals=signals,
        script=script,
        warnings=warnings,
        voice_result=voice_result,
        voice_final_paths=voice_final_paths,
        timeout_closing_audio_path=timeout_closing_audio_path,
    )
    warnings.append(f"Diagnostics written to {diagnostics}")

    result = PipelineResult(
        generated_at=generated_at,
        raw_path=str(raw_path),
        latest_raw_path=str(latest_raw_path),
        notes_path=str(notes_path),
        latest_notes_path=str(latest_notes_path),
        weather_path=str(weather_path),
        latest_weather_path=str(latest_weather_path),
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


def _render_timeout_closing_audio(
    *,
    config: AppConfig,
    line: str,
    stamp: str,
) -> tuple[Optional[Path], List[str]]:
    warnings: List[str] = []
    session_dir = config.audio_dir / "session"
    ensure_dirs([session_dir])
    clean_path = session_dir / f"closing_timeout_{stamp}_clean.mp3"
    audio_path, tts_warnings = SpeechSynthesizer(config).synthesize(line, clean_path)
    warnings.extend(tts_warnings)
    if not audio_path:
        return None, warnings

    final_path = audio_path
    if config.voice_effect_enabled:
        effect_config = replace(
            config,
            voice_effect_render_all=False,
            voice_effect_save_wavs=False,
        )
        voice_result, voice_warnings = VoiceEffectProcessor(effect_config).render_variants(
            clean_tts_path=audio_path,
            output_stem=session_dir / f"closing_timeout_{stamp}",
        )
        warnings.extend(voice_warnings)
        final_path = voice_result.default_path

    latest_path = copy_latest(final_path, session_dir / "closing_timeout_latest.mp3")
    warnings.append(f"Timeout closing audio saved: {latest_path or final_path}")
    return latest_path or final_path, warnings


def _browser_session_timeout(word_count: int, config: AppConfig) -> float:
    estimated_narration = max(word_count / 125 * 60, 90)
    return estimated_narration + config.followup_timeout_seconds + 90


def _copy_voice_aliases(config: AppConfig, voice_result: VoiceRenderResult) -> List[str]:
    warnings: List[str] = []
    copy_latest(voice_result.clean_path, config.audio_dir / "briefing_clean.mp3")
    for preset_name, path in voice_result.variant_paths.items():
        alias = config.audio_dir / f"briefing_voice_{voice_result.preset_numbers[preset_name]:02d}_{preset_name}.mp3"
        copy_latest(path, alias)
    warnings.append(
        "Voice variants saved: "
        + ", ".join(str(path) for path in voice_result.variant_paths.values())
    )
    return warnings


def _copy_voice_final_aliases(
    config: AppConfig,
    voice_result: VoiceRenderResult,
    voice_final_paths: Dict[str, str],
) -> List[str]:
    warnings: List[str] = []
    for preset_name, path_text in voice_final_paths.items():
        path = Path(path_text)
        alias = config.audio_dir / f"briefing_voice_{voice_result.preset_numbers[preset_name]:02d}_{preset_name}_final.mp3"
        copy_latest(path, alias)
    if voice_final_paths:
        warnings.append(
            "Final mixed voice variants saved: "
            + ", ".join(voice_final_paths.values())
        )
    return warnings


def _write_run_diagnostics(
    *,
    config: AppConfig,
    stamp: str,
    generated_at: datetime,
    raw_items,
    signals,
    script,
    warnings: List[str],
    voice_result: Optional[VoiceRenderResult],
    voice_final_paths: Dict[str, str],
    timeout_closing_audio_path: Optional[Path],
) -> str:
    categories = ("geopolitics", "technology_ai", "markets")
    raw_counts = {
        category: sum(1 for item in raw_items if item.category == category)
        for category in categories
    }
    accepted_counts = {
        category: sum(
            1 for item in raw_items if item.category == category and item.is_relevant
        )
        for category in categories
    }
    rejected_counts = {
        category: raw_counts[category] - accepted_counts[category]
        for category in categories
    }
    payload = {
        "generated_at": generated_at.isoformat(),
        "raw_article_counts": raw_counts,
        "accepted_article_counts": accepted_counts,
        "rejected_article_counts": rejected_counts,
        "extracted_note_counts": {
            category: len(signals.sections.get(category, []))
            for category in categories
        },
        "final_script_section_words": {
            key: word_count(value)
            for key, value in script.sections.items()
            if key != "source_links"
        },
        "final_script_word_count": script.word_count,
        "narration_plan": script.narration_plan,
        "voice_default_preset": voice_result.default_preset if voice_result else None,
        "voice_variant_paths": {
            key: str(path)
            for key, path in (voice_result.variant_paths if voice_result else {}).items()
        },
        "voice_final_paths": voice_final_paths,
        "timeout_closing_audio_path": (
            str(timeout_closing_audio_path) if timeout_closing_audio_path else None
        ),
        "warnings": warnings,
    }
    diagnostics_path = config.log_dir / f"briefing_{stamp}_diagnostics.json"
    latest_path = config.log_dir / "latest_diagnostics.json"
    save_json(diagnostics_path, payload)
    save_json(latest_path, payload)
    return str(latest_path)
