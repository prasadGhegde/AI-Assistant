#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from morning_briefs.audio_fx import PRESETS_BY_NAME


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Apply a voice effect preset filter to a WAV file without adding music."
    )
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Path to the input WAV file.",
    )
    parser.add_argument(
        "--preset",
        type=str,
        default="test_radio_echo_strong1",
        choices=list(PRESETS_BY_NAME.keys()),
        help="Voice effect preset to apply.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("output/audio/filtered_voice.wav"),
        help="Path for the filtered output WAV file.",
    )
    parser.add_argument(
        "--ffmpeg-path",
        type=str,
        default=os.getenv("MORNING_BRIEFS_FFMPEG_PATH", "ffmpeg"),
        help="FFmpeg executable path.",
    )
    args = parser.parse_args()

    if not args.input.exists():
        raise FileNotFoundError(f"Input WAV file not found: {args.input}")
    ffmpeg = shutil.which(args.ffmpeg_path)
    if not ffmpeg:
        raise RuntimeError(
            f"ffmpeg not found at '{args.ffmpeg_path}'. Install ffmpeg or set MORNING_BRIEFS_FFMPEG_PATH."
        )

    preset = PRESETS_BY_NAME[args.preset]
    args.output.parent.mkdir(parents=True, exist_ok=True)

    command = [
        ffmpeg,
        "-y",
        "-i",
        str(args.input),
        "-af",
        preset.filter_graph,
        "-ac",
        "1",
        "-ar",
        "48000",
        "-c:a",
        "pcm_s16le",
        str(args.output),
    ]

    print("Applying preset:", args.preset)
    print("FFmpeg command:", " ".join(shlex_quote(arg) for arg in command))
    subprocess.run(command, check=True)
    print(f"Filtered output written to: {args.output}")


def shlex_quote(value: str) -> str:
    import shlex

    return shlex.quote(value)


if __name__ == "__main__":
    main()
