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
    openai_tts_model: str
    openai_tts_voice: str
    last_hours: int
    max_items_per_source: int
    fetch_timeout: int
    audio_autoplay_command: str
    sources_path: Path
    briefing_profile_path: Path
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
    return AppConfig(
        project_root=PROJECT_ROOT,
        config_dir=CONFIG_DIR,
        data_dir=Path(os.getenv("MORNING_BRIEFS_DATA_DIR", str(DATA_DIR))),
        output_dir=Path(os.getenv("MORNING_BRIEFS_OUTPUT_DIR", str(OUTPUT_DIR))),
        log_dir=Path(os.getenv("MORNING_BRIEFS_LOG_DIR", str(LOG_DIR))),
        timezone=ZoneInfo(timezone_name),
        timezone_name=timezone_name,
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        openai_org_id=os.getenv("OPENAI_ORG_ID", ""),
        openai_project_id=os.getenv("OPENAI_PROJECT_ID", ""),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-5-mini"),
        openai_tts_model=os.getenv("OPENAI_TTS_MODEL", "gpt-4o-mini-tts"),
        openai_tts_voice=os.getenv("OPENAI_TTS_VOICE", "coral"),
        last_hours=_int_env("MORNING_BRIEFS_LAST_HOURS", 24),
        max_items_per_source=_int_env("MORNING_BRIEFS_MAX_ITEMS_PER_SOURCE", 10),
        fetch_timeout=_int_env("MORNING_BRIEFS_FETCH_TIMEOUT", 12),
        audio_autoplay_command=os.getenv(
            "MORNING_BRIEFS_AUDIO_AUTOPLAY_COMMAND", "afplay"
        ),
        sources_path=CONFIG_DIR / "sources.json",
        briefing_profile_path=CONFIG_DIR / "briefing_profile.json",
        skills_catalog_path=CONFIG_DIR / "skills_catalog.json",
    )
