from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WEB_DIR = PROJECT_ROOT / "morning_briefs" / "web"


def render_fixture(snapshot_path: Path, output_path: Path, *, keep_audio: bool) -> None:
    """Render the dashboard UI from a saved JSON snapshot only.

    This is intentionally API-free and audio-free by default so layout changes can
    be checked quickly without running collection, TTS, or browser playback.
    """

    data = json.loads(snapshot_path.read_text(encoding="utf-8"))
    if not keep_audio:
        data["audio_src"] = ""
        data["music_src"] = ""
        data["music_enabled"] = False
        data["browser_music_enabled"] = False

    output_path.parent.mkdir(parents=True, exist_ok=True)
    assets_dir = output_path.parent / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    for asset_name in ("dashboard.css", "dashboard.js"):
        shutil.copyfile(WEB_DIR / "static" / asset_name, assets_dir / asset_name)

    generated = data.get("generated_label") or data.get("generated_at") or "Fixture"
    template = (WEB_DIR / "templates" / "dashboard.html").read_text(encoding="utf-8")
    inline_json = json.dumps(data, ensure_ascii=False).replace("<", "\\u003c")
    html = (
        template.replace("__BRIEFING_DATA__", inline_json)
        .replace("__AUDIO_SRC__", data.get("audio_src") or "")
        .replace("__GENERATED_AT__", generated)
    )
    output_path.write_text(html, encoding="utf-8")
    print(f"Rendered fixture dashboard: {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Render dashboard HTML from a saved JSON snapshot.")
    parser.add_argument(
        "--snapshot",
        type=Path,
        default=PROJECT_ROOT / "output" / "dashboard" / "latest.json",
        help="Saved dashboard JSON snapshot to render.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=PROJECT_ROOT / "output" / "dashboard" / "fixture.html",
        help="Output HTML path.",
    )
    parser.add_argument(
        "--keep-audio",
        action="store_true",
        help="Keep audio/music references from the snapshot instead of disabling them.",
    )
    args = parser.parse_args()
    render_fixture(args.snapshot, args.out, keep_audio=args.keep_audio)


if __name__ == "__main__":
    main()
