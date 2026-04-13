from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import load_config


def main(argv=None) -> None:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0].startswith("-"):
        argv.insert(0, "run")

    parser = argparse.ArgumentParser(
        prog="morning-briefs",
        description="Generate and view a local work morning briefing.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Collect, write, narrate, and render.")
    run_parser.add_argument("--skip-tts", action="store_true", help="Do not generate MP3.")
    run_parser.add_argument("--play", action="store_true", help="Play the MP3 after generation.")
    run_parser.add_argument("--serve", action="store_true", help="Start the local dashboard.")
    run_parser.add_argument(
        "--no-open",
        action="store_true",
        help="Do not open the browser after generating the dashboard.",
    )
    run_parser.add_argument("--host", default="127.0.0.1")
    run_parser.add_argument("--port", type=int, default=8765)

    dash_parser = subparsers.add_parser("dashboard", help="Serve the latest dashboard.")
    dash_parser.add_argument("--host", default="127.0.0.1")
    dash_parser.add_argument("--port", type=int, default=8765)

    play_parser = subparsers.add_parser("play", help="Play the latest MP3.")
    play_parser.add_argument("--path", default=None, help="Optional MP3 path.")

    args = parser.parse_args(argv)
    config = load_config()

    if args.command == "run":
        try:
            from .pipeline import run_once
        except ModuleNotFoundError as exc:
            print(
                f"Missing Python dependency `{exc.name}`. Run `make setup` first.",
                file=sys.stderr,
            )
            sys.exit(2)

        result = run_once(
            config,
            skip_tts=args.skip_tts,
            play=args.play,
            open_browser=not args.no_open,
        )
        print(f"Raw sources: {result.latest_raw_path}")
        print(f"Extracted notes: {result.latest_notes_path}")
        print(f"Weather: {result.latest_weather_path}")
        print(f"Script: {result.latest_script_path}")
        print(f"Dashboard: {result.latest_dashboard_path}")
        if result.latest_audio_path:
            print(f"Audio: {result.latest_audio_path}")
        for warning in result.warnings:
            print(f"Warning: {warning}")
        if args.serve:
            try:
                from .server import serve
            except ModuleNotFoundError as exc:
                print(
                    f"Missing Python dependency `{exc.name}`. Run `make setup` first.",
                    file=sys.stderr,
                )
                sys.exit(2)

            print(f"Dashboard URL: http://{args.host}:{args.port}")
            serve(config, host=args.host, port=args.port)
        return

    if args.command == "dashboard":
        try:
            from .server import serve
        except ModuleNotFoundError as exc:
            print(
                f"Missing Python dependency `{exc.name}`. Run `make setup` first.",
                file=sys.stderr,
            )
            sys.exit(2)

        print(f"Dashboard URL: http://{args.host}:{args.port}")
        serve(config, host=args.host, port=args.port)
        return

    if args.command == "play":
        from .tts import AudioPlayer

        audio_path = Path(args.path) if args.path else config.audio_dir / "latest.mp3"
        warnings = AudioPlayer(config).play(audio_path)
        for warning in warnings:
            print(f"Warning: {warning}")


if __name__ == "__main__":
    main()
