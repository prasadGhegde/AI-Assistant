#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shlex
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def build_voice_filter(
    highpass_freq: float,
    lowpass_freq: float,
    compressor_threshold: float,
    compressor_ratio: float,
    compressor_attack: float,
    compressor_release: float,
    compressor_makeup: float,
    eq_presence_freq: float,
    eq_presence_gain: float,
    eq_high_freq: float,
    eq_high_gain: float,
    echo_in_gain: float,
    echo_out_gain: float,
    echo_delays: str,
    echo_decays: str,
    voice_volume: float,
) -> str:
    filters = [
        f"highpass=f={highpass_freq}",
        f"lowpass=f={lowpass_freq}",
        f"acompressor=threshold={compressor_threshold}dB:ratio={compressor_ratio}:attack={compressor_attack}:release={compressor_release}:makeup={compressor_makeup}",
        f"aecho={echo_in_gain}:{echo_out_gain}:{echo_delays}:{echo_decays}",
        f"equalizer=f={eq_presence_freq}:t=q:w=1:g={eq_presence_gain}",
        f"equalizer=f={eq_high_freq}:t=q:w=1:g={eq_high_gain}",
        f"volume={voice_volume}",
        "alimiter=limit=0.92:attack=3:release=80",
    ]
    return ",".join(filters)


def run_ffmpeg(command: list[str]) -> None:
    print("Running:")
    print(" ".join(shlex.quote(arg) for arg in command))
    subprocess.run(command, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a local audio test mix from narration and music.")
    parser.add_argument("--voice-input", type=Path, default=Path("output/audio/test_radio_echo_strong1.mp3"))
    parser.add_argument("--music-input", type=Path, default=Path("assets/audio/jarvis_proper_8min.wav"))
    parser.add_argument("--output", type=Path, default=Path("output/audio/test_radio_comms_test_one.mp3"))
    parser.add_argument("--voice-volume", type=float, default=1.5)
    parser.add_argument("--music-volume", type=float, default=0.3)
    parser.add_argument("--highpass-freq", type=float, default=200.0)
    parser.add_argument("--lowpass-freq", type=float, default=3500.0)
    parser.add_argument("--compressor-threshold", type=float, default=-24.0)
    parser.add_argument("--compressor-ratio", type=float, default=8.0)
    parser.add_argument("--compressor-attack", type=float, default=5.0)
    parser.add_argument("--compressor-release", type=float, default=100.0)
    parser.add_argument("--compressor-makeup", type=float, default=8.0)
    parser.add_argument("--eq-presence-freq", type=float, default=2200.0)
    parser.add_argument("--eq-presence-gain", type=float, default=4.0)
    parser.add_argument("--eq-high-freq", type=float, default=4200.0)
    parser.add_argument("--eq-high-gain", type=float, default=4.0)
    parser.add_argument("--echo-in-gain", type=float, default=0.85)
    parser.add_argument("--echo-out-gain", type=float, default=0.95)
    parser.add_argument("--echo-delays", type=str, default="15|30")
    parser.add_argument("--echo-decays", type=str, default="0.5|0.4")
    parser.add_argument("--ffmpeg-path", type=str, default=os.getenv("MORNING_BRIEFS_FFMPEG_PATH", "ffmpeg"))
    parser.add_argument("--dry-run", action="store_true", help="Print the command without executing it.")

    args = parser.parse_args()

    if not args.voice_input.exists():
        raise FileNotFoundError(f"Voice input not found: {args.voice_input}")
    if not args.music_input.exists():
        raise FileNotFoundError(f"Music input not found: {args.music_input}")

    voice_filter = build_voice_filter(
        highpass_freq=args.highpass_freq,
        lowpass_freq=args.lowpass_freq,
        compressor_threshold=args.compressor_threshold,
        compressor_ratio=args.compressor_ratio,
        compressor_attack=args.compressor_attack,
        compressor_release=args.compressor_release,
        compressor_makeup=args.compressor_makeup,
        eq_presence_freq=args.eq_presence_freq,
        eq_presence_gain=args.eq_presence_gain,
        eq_high_freq=args.eq_high_freq,
        eq_high_gain=args.eq_high_gain,
        echo_in_gain=args.echo_in_gain,
        echo_out_gain=args.echo_out_gain,
        echo_delays=args.echo_delays,
        echo_decays=args.echo_decays,
        voice_volume=args.voice_volume,
    )

    filter_complex = (
        f"[0:a]{voice_filter}[a0];"
        f"[1:a]volume={args.music_volume}[a1];"
        "[a0][a1]amix=inputs=2:duration=shortest:dropout_transition=2"
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)

    command = [
        args.ffmpeg_path,
        "-y",
        "-i",
        str(args.voice_input),
        "-i",
        str(args.music_input),
        "-filter_complex",
        filter_complex,
        "-ac",
        "1",
        "-ar",
        "48000",
        "-c:a",
        "libmp3lame",
        "-q:a",
        "3",
        str(args.output),
    ]

    if args.dry_run:
        print("Dry run completed.")
        return

    run_ffmpeg(command)
    print(f"Generated: {args.output}")


if __name__ == "__main__":
    main()
