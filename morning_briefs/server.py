from __future__ import annotations

from pathlib import Path

from .config import AppConfig


def create_app(config: AppConfig):
    try:
        from flask import Flask, abort, send_file, send_from_directory
    except ImportError as exc:
        raise RuntimeError("Flask is not installed. Run `pip install -e .`.") from exc

    app = Flask(__name__)

    @app.get("/")
    def index():
        dashboard = config.dashboard_dir / "latest.html"
        if not dashboard.exists():
            abort(404, "No dashboard generated yet. Run `python3 -m morning_briefs run`.")
        return send_file(dashboard)

    @app.get("/assets/<path:name>")
    def assets(name: str):
        return send_from_directory(config.dashboard_dir / "assets", name)

    @app.get("/audio/latest.mp3")
    def latest_audio():
        audio = config.audio_dir / "latest.mp3"
        if not audio.exists():
            abort(404, "No MP3 generated yet.")
        return send_file(audio, mimetype="audio/mpeg")

    @app.get("/data/latest.json")
    def latest_data():
        data = config.dashboard_dir / "latest.json"
        if not data.exists():
            abort(404, "No dashboard data generated yet.")
        return send_file(data, mimetype="application/json")

    return app


def serve(config: AppConfig, host: str = "127.0.0.1", port: int = 8765) -> None:
    app = create_app(config)
    app.run(host=host, port=port)
