from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo

from .paths import CONFIG_DIR, DATA_DIR, LOG_DIR, OUTPUT_DIR, PROJECT_ROOT


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(PROJECT_ROOT / ".env")


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _float_env(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class AppConfig:
    project_root: Path
    config_dir: Path
    data_dir: Path
    output_dir: Path
    log_dir: Path
    timezone: ZoneInfo
    timezone_name: str
    openai_api_key: str
    openai_org_id: str
    openai_project_id: str
    openai_model: str
    openai_signal_model: str
    openai_writer_model: str
    openai_tts_model: str
    openai_tts_voice: str
    openai_tts_fallback_voice: str
    openai_tts_allow_fallback: bool
    force_ryan_voice: bool
    openai_tts_instructions: str
    last_hours: int
    good_news_only: bool
    max_items_per_source: int
    fetch_timeout: int
    audio_autoplay_command: str
    audio_driver: str
    user_name: str
    weather_location_name: str
    weather_latitude: float
    weather_longitude: float
    weather_temperature_unit: str
    weather_wind_speed_unit: str
    open_browser: bool
    browser_app: str
    browser_close_on_end: bool
    browser_launch_with_autoplay_policy: bool
    browser_fullscreen: bool
    browser_kiosk_mode: bool
    browser_hide_toolbar_in_fullscreen: bool
    browser_restore_toolbar_on_close: bool
    chrome_user_data_dir: Path
    presentation_mode: bool
    presentation_start_delay_seconds: float
    dashboard_host: str
    dashboard_port: int
    serve_dashboard_for_runs: bool
    followup_timeout_seconds: int
    music_enabled: bool
    music_volume: float
    music_ducking_enabled: bool
    browser_music_enabled: bool
    music_source_path: Path
    music_max_duration_seconds: float
    ffmpeg_path: str
    voice_effect_enabled: bool
    voice_effect_mode: str
    voice_effect_default_preset: str
    voice_effect_render_all: bool
    voice_effect_save_wavs: bool
    use_fake_data_when_empty: bool
    narration_recent_limit: int
    sources_path: Path
    news_quality_path: Path
    briefing_profile_path: Path
    narration_phrases_path: Path
    narration_history_path: Path
    skills_catalog_path: Path

    @property
    def raw_dir(self) -> Path:
        return self.data_dir / "raw"

    @property
    def processed_dir(self) -> Path:
        return self.data_dir / "processed"

    @property
    def audio_dir(self) -> Path:
        return self.output_dir / "audio"

    @property
    def scripts_dir(self) -> Path:
        return self.output_dir / "scripts"

    @property
    def dashboard_dir(self) -> Path:
        return self.output_dir / "dashboard"


def load_config() -> AppConfig:
    _load_dotenv()
    timezone_name = os.getenv("MORNING_BRIEFS_TIMEZONE", "Europe/Berlin")
    data_dir = Path(os.getenv("MORNING_BRIEFS_DATA_DIR", str(DATA_DIR)))
    output_dir = Path(os.getenv("MORNING_BRIEFS_OUTPUT_DIR", str(OUTPUT_DIR)))
    force_ryan_voice = _bool_env("MORNING_BRIEFS_FORCE_RYAN", True)
    tts_instructions = os.getenv(
        "OPENAI_TTS_INSTRUCTIONS",
        (
            "Use the Ryan system voice when available. Speak as a premium morning "
            "assistant: warm, crisp, composed, energetic without rushing, polished "
            "like a high-end British-leaning news presenter. Never imitate or "
            "reference any copyrighted character."
        ),
    )
    if force_ryan_voice and "ryan" not in tts_instructions.lower():
        tts_instructions = (
            "Use the Ryan system voice when available. Keep Ryan consistent for "
            "greeting, weather, news, and the spoken closing question. "
            + tts_instructions
        )
    return AppConfig(
        project_root=PROJECT_ROOT,
        config_dir=CONFIG_DIR,
        data_dir=data_dir,
        output_dir=output_dir,
        log_dir=Path(os.getenv("MORNING_BRIEFS_LOG_DIR", str(LOG_DIR))),
        timezone=ZoneInfo(timezone_name),
        timezone_name=timezone_name,
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        openai_org_id=os.getenv("OPENAI_ORG_ID", ""),
        openai_project_id=os.getenv("OPENAI_PROJECT_ID", ""),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-5.4-mini"),
        openai_signal_model=os.getenv(
            "OPENAI_SIGNAL_MODEL", os.getenv("OPENAI_MODEL", "gpt-5.4-mini")
        ),
        openai_writer_model=os.getenv(
            "OPENAI_WRITER_MODEL", os.getenv("OPENAI_MODEL", "gpt-5.4")
        ),
        openai_tts_model=os.getenv("OPENAI_TTS_MODEL", "gpt-4o-mini-tts"),
        openai_tts_voice=(
            "ryan" if force_ryan_voice else os.getenv("OPENAI_TTS_VOICE", "ryan")
        ),
        openai_tts_fallback_voice=os.getenv("OPENAI_TTS_FALLBACK_VOICE", "cedar"),
        openai_tts_allow_fallback=_bool_env("OPENAI_TTS_ALLOW_FALLBACK", True),
        force_ryan_voice=force_ryan_voice,
        openai_tts_instructions=tts_instructions,
        last_hours=_int_env("MORNING_BRIEFS_LAST_HOURS", 24),
        good_news_only=_bool_env("MORNING_BRIEFS_GOOD_NEWS_ONLY", True),
        max_items_per_source=_int_env("MORNING_BRIEFS_MAX_ITEMS_PER_SOURCE", 10),
        fetch_timeout=_int_env("MORNING_BRIEFS_FETCH_TIMEOUT", 12),
        audio_autoplay_command=os.getenv(
            "MORNING_BRIEFS_AUDIO_AUTOPLAY_COMMAND", "afplay"
        ),
        audio_driver=os.getenv("MORNING_BRIEFS_AUDIO_DRIVER", "browser").lower(),
        user_name=os.getenv("MORNING_BRIEFS_USER_NAME", "Prasad"),
        weather_location_name=os.getenv("MORNING_BRIEFS_WEATHER_LOCATION", "Berlin"),
        weather_latitude=_float_env("MORNING_BRIEFS_WEATHER_LAT", 52.52),
        weather_longitude=_float_env("MORNING_BRIEFS_WEATHER_LON", 13.405),
        weather_temperature_unit=os.getenv(
            "MORNING_BRIEFS_WEATHER_TEMPERATURE_UNIT", "celsius"
        ),
        weather_wind_speed_unit=os.getenv(
            "MORNING_BRIEFS_WEATHER_WIND_UNIT", "kmh"
        ),
        open_browser=_bool_env("MORNING_BRIEFS_OPEN_BROWSER", True),
        browser_app=os.getenv("MORNING_BRIEFS_BROWSER_APP", "Google Chrome"),
        browser_close_on_end=_bool_env("MORNING_BRIEFS_BROWSER_CLOSE_ON_END", True),
        browser_launch_with_autoplay_policy=_bool_env(
            "MORNING_BRIEFS_BROWSER_AUTOPLAY_POLICY", True
        ),
        browser_fullscreen=_bool_env("MORNING_BRIEFS_BROWSER_FULLSCREEN", True),
        browser_kiosk_mode=_bool_env("MORNING_BRIEFS_BROWSER_KIOSK", True),
        browser_hide_toolbar_in_fullscreen=_bool_env(
            "MORNING_BRIEFS_BROWSER_HIDE_FULLSCREEN_TOOLBAR", True
        ),
        browser_restore_toolbar_on_close=_bool_env(
            "MORNING_BRIEFS_BROWSER_RESTORE_FULLSCREEN_TOOLBAR", True
        ),
        chrome_user_data_dir=Path(
            os.getenv(
                "MORNING_BRIEFS_CHROME_USER_DATA_DIR",
                "/tmp/morning-briefs-chrome-profile",
            )
        ),
        presentation_mode=_bool_env("MORNING_BRIEFS_PRESENTATION_MODE", True),
        presentation_start_delay_seconds=_float_env(
            "MORNING_BRIEFS_PRESENTATION_START_DELAY_SECONDS", 1.8
        ),
        dashboard_host=os.getenv("MORNING_BRIEFS_DASHBOARD_HOST", "127.0.0.1"),
        dashboard_port=_int_env("MORNING_BRIEFS_DASHBOARD_PORT", 8765),
        serve_dashboard_for_runs=_bool_env(
            "MORNING_BRIEFS_SERVE_DASHBOARD_FOR_RUNS", True
        ),
        followup_timeout_seconds=_int_env(
            "MORNING_BRIEFS_FOLLOWUP_TIMEOUT_SECONDS", 10
        ),
        music_enabled=_bool_env("MORNING_BRIEFS_MUSIC_ENABLED", True),
        music_volume=_float_env("MORNING_BRIEFS_MUSIC_VOLUME", 0.3),
        music_ducking_enabled=_bool_env(
            "MORNING_BRIEFS_MUSIC_DUCKING_ENABLED", False
        ),
        browser_music_enabled=_bool_env("MORNING_BRIEFS_BROWSER_MUSIC_ENABLED", True),
        music_source_path=Path(
            os.getenv(
                "MORNING_BRIEFS_MUSIC_SOURCE",
                str(PROJECT_ROOT / "assets/audio/jarvis_proper_8min.wav"),
            )
        ),
        music_max_duration_seconds=_float_env(
            "MORNING_BRIEFS_MUSIC_MAX_DURATION_SECONDS", 380
        ),
        ffmpeg_path=os.getenv("MORNING_BRIEFS_FFMPEG_PATH", "ffmpeg"),
        voice_effect_enabled=_bool_env("MORNING_BRIEFS_VOICE_EFFECT_ENABLED", True),
        voice_effect_mode=os.getenv(
            "MORNING_BRIEFS_VOICE_EFFECT_MODE", "radio_comms"
        ),
        voice_effect_default_preset=os.getenv(
            "MORNING_BRIEFS_VOICE_EFFECT_DEFAULT_PRESET",
            os.getenv("MORNING_BRIEFS_VOICE_EFFECT_MODE", "radio_comms"),
        ),
        voice_effect_render_all=_bool_env(
            "MORNING_BRIEFS_VOICE_EFFECT_RENDER_ALL", False
        ),
        voice_effect_save_wavs=_bool_env(
            "MORNING_BRIEFS_VOICE_EFFECT_SAVE_WAVS", True
        ),
        use_fake_data_when_empty=_bool_env(
            "MORNING_BRIEFS_USE_FAKE_DATA_WHEN_EMPTY", True
        ),
        narration_recent_limit=_int_env("MORNING_BRIEFS_NARRATION_RECENT_LIMIT", 5),
        sources_path=CONFIG_DIR / "sources.json",
        news_quality_path=CONFIG_DIR / "news_quality.json",
        briefing_profile_path=CONFIG_DIR / "briefing_profile.json",
        narration_phrases_path=CONFIG_DIR / "narration_phrases.json",
        narration_history_path=data_dir / "narration_history.json",
        skills_catalog_path=CONFIG_DIR / "skills_catalog.json",
    )
