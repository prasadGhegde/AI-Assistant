from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple

from .config import AppConfig


class MusicBed:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def create_and_mix(
        self,
        *,
        narration_path: Path,
        output_path: Path,
        duration_seconds: float,
    ) -> Tuple[Path, Optional[Path], List[str]]:
        warnings: List[str] = []
        if not self.config.music_enabled:
            return narration_path, None, warnings

        source_path = self.config.music_source_path
        if not source_path.exists():
            warnings.append(
                f"Background music source was not found: {source_path}. "
                "Music was not mixed into the MP3."
            )
            return narration_path, None, warnings
        music_path = source_path

        ffmpeg = shutil.which(self.config.ffmpeg_path)
        if not ffmpeg:
            warnings.append(
                "Background music source is available, but ffmpeg was not found; "
                "the browser will play the uploaded music separately, and installing "
                "ffmpeg enables a ducked MP3 mix."
            )
            return narration_path, music_path, warnings

        mixed_path = output_path
        filter_graph = (
            f"[1:a]volume={self.config.music_volume}[music];"
            "[0:a][music]amix=inputs=2:duration=shortest:dropout_transition=2[out]"
        )
        command = [
            ffmpeg,
            "-y",
            "-i",
            str(narration_path),
            "-i",
            str(music_path),
            "-filter_complex",
            filter_graph,
            "-map",
            "[out]",
            "-c:a",
            "libmp3lame",
            "-q:a",
            "3",
            "-ac",
            "1",
            "-ar",
            "48000",
            str(mixed_path),
        ]
        try:
            subprocess.run(
                command,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception as exc:
            warnings.append(f"Background music mix failed; using narration only: {exc}")
            return narration_path, music_path, warnings

        return mixed_path, music_path, warnings
