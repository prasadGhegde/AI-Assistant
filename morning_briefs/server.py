from __future__ import annotations

import socket
import threading
import time
from dataclasses import dataclass
from typing import List, Optional

from .config import AppConfig
from .followup import FollowUpResponder
from .tts import SpeechSynthesizer


@dataclass
class SessionState:
    completed: threading.Event
    reason: str = ""


def create_app(config: AppConfig, session_state: Optional[SessionState] = None):
    try:
        from flask import Flask, abort, jsonify, request, send_file, send_from_directory
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

    @app.get("/audio/session/<path:name>")
    def session_audio(name: str):
        return send_from_directory(config.audio_dir / "session", name, mimetype="audio/mpeg")

    @app.get("/data/latest.json")
    def latest_data():
        data = config.dashboard_dir / "latest.json"
        if not data.exists():
            abort(404, "No dashboard data generated yet.")
        return send_file(data, mimetype="application/json")

    @app.post("/api/followup")
    def followup():
        payload = request.get_json(silent=True) or {}
        answer = FollowUpResponder(config).answer(str(payload.get("question", "")))
        return jsonify({"answer": answer, "audio_src": None, "warnings": []})

    @app.post("/api/closing")
    def closing():
        line = "Okay, no further questions on the board. I am closing the mission call now. Have a strong day, Captain."
        audio_src, warnings = _synthesize_session_clip(config, line, "closing")
        return jsonify({"answer": line, "audio_src": audio_src, "warnings": warnings})

    @app.post("/api/session/complete")
    def session_complete():
        payload = request.get_json(silent=True) or {}
        if session_state:
            session_state.reason = str(payload.get("reason", "complete"))
            session_state.completed.set()
        return jsonify({"ok": True})

    return app


def _synthesize_session_clip(
    config: AppConfig,
    text: str,
    prefix: str,
) -> tuple[Optional[str], List[str]]:
    if not text.strip():
        return None, ["No text provided for session audio."]
    session_dir = config.audio_dir / "session"
    session_dir.mkdir(parents=True, exist_ok=True)
    safe_prefix = "".join(ch for ch in prefix if ch.isalnum() or ch in {"_", "-"}).strip("_")
    output_path = session_dir / f"{safe_prefix}_{int(time.time() * 1000)}.mp3"
    audio_path, warnings = SpeechSynthesizer(config).synthesize(text, output_path)
    if not audio_path:
        return None, warnings
    return f"/audio/session/{audio_path.name}", warnings


def serve(config: AppConfig, host: str = "127.0.0.1", port: int = 8765) -> None:
    app = create_app(config)
    app.run(host=host, port=port)


@dataclass
class BackgroundDashboardServer:
    host: str
    port: int
    server: object
    thread: threading.Thread
    session_state: SessionState

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}/"

    def wait_for_completion(self, timeout: float) -> bool:
        return self.session_state.completed.wait(timeout)

    def shutdown(self) -> None:
        shutdown = getattr(self.server, "shutdown", None)
        if shutdown:
            shutdown()
        self.thread.join(timeout=2)


def start_background_server(
    config: AppConfig,
    host: str = "127.0.0.1",
    port: int = 8765,
) -> BackgroundDashboardServer:
    try:
        from werkzeug.serving import make_server
    except ImportError as exc:
        raise RuntimeError("Werkzeug is not installed. Run `pip install -e .`.") from exc

    selected_port = _available_port(host, port)
    session_state = SessionState(completed=threading.Event())
    server = make_server(host, selected_port, create_app(config, session_state))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return BackgroundDashboardServer(host, selected_port, server, thread, session_state)


def _available_port(host: str, preferred: int) -> int:
    for port in range(preferred, preferred + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.2)
            if sock.connect_ex((host, port)) != 0:
                return port
    raise RuntimeError(f"No available dashboard port found near {preferred}.")
