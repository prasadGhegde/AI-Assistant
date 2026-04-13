from __future__ import annotations

import argparse
import json
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

    replay_parser = subparsers.add_parser(
        "replay",
        help="Serve and open the latest generated dashboard/audio without fetching sources or calling APIs.",
    )
    replay_parser.add_argument("--host", default="127.0.0.1")
    replay_parser.add_argument("--port", type=int, default=8765)
    replay_parser.add_argument(
        "--timeout",
        type=float,
        default=None,
        help="Seconds to keep the replay server open before closing Chrome.",
    )
    replay_parser.add_argument(
        "--no-open",
        action="store_true",
        help="Serve the saved dashboard without opening Chrome.",
    )

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

    if args.command == "replay":
        dashboard = config.dashboard_dir / "latest.html"
        audio = config.audio_dir / "latest.mp3"
        if not dashboard.exists():
            print(
                "No saved dashboard found. Run `make briefing` once before `make replay`.",
                file=sys.stderr,
            )
            sys.exit(1)
        if not audio.exists():
            print(
                "No saved audio found. Run `make briefing` once before `make replay`.",
                file=sys.stderr,
            )
            sys.exit(1)

        try:
            from .browser import BrowserPresenter
            from .server import serve, start_background_server
        except ModuleNotFoundError as exc:
            print(
                f"Missing Python dependency `{exc.name}`. Run `make setup` first.",
                file=sys.stderr,
            )
            sys.exit(2)

        if args.no_open:
            print(f"Replay URL: http://{args.host}:{args.port}?presentation=1&autoplay=1")
            serve(config, host=args.host, port=args.port)
            return

        server = start_background_server(config, host=args.host, port=args.port)
        presenter = BrowserPresenter(config)
        opened_url = ""
        warnings = []
        try:
            warnings.extend(
                presenter.open_dashboard_url(
                    server.url,
                    presentation=config.presentation_mode,
                    external_audio=False,
                )
            )
            opened_url = presenter.last_url
            timeout = args.timeout if args.timeout is not None else _replay_timeout(config)
            completed = server.wait_for_completion(timeout)
            if not completed:
                warnings.append("Replay timed out before the dashboard reported completion.")
        finally:
            if opened_url:
                warnings.extend(presenter.close_url(opened_url))
            server.shutdown()
        for warning in warnings:
            print(f"Warning: {warning}")
        return

    if args.command == "play":
        from .tts import AudioPlayer

        audio_path = Path(args.path) if args.path else config.audio_dir / "latest.mp3"
        warnings = AudioPlayer(config).play(audio_path)
        for warning in warnings:
            print(f"Warning: {warning}")


def _replay_timeout(config) -> float:
    data_path = config.dashboard_dir / "latest.json"
    try:
        payload = json.loads(data_path.read_text(encoding="utf-8"))
        total = float(((payload.get("presentation_timeline") or {}).get("total_seconds")) or 0)
    except Exception:
        total = 0
    if total <= 0:
        total = 8 * 60
    return total + config.followup_timeout_seconds + 45


if __name__ == "__main__":
    main()
