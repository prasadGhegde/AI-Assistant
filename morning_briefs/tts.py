from __future__ import annotations

import shlex
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple

from .config import AppConfig
from .utils import clean_text


class SpeechSynthesizer:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def synthesize(self, spoken_text: str, output_path: Path) -> Tuple[Optional[Path], List[str]]:
        warnings: List[str] = []
        if not self.config.openai_api_key:
            return None, ["OPENAI_API_KEY not set; MP3 narration was not generated."]
        try:
            from openai import OpenAI
        except Exception as exc:
            return None, [f"OpenAI package import failed; MP3 narration skipped: {exc}"]

        output_path.parent.mkdir(parents=True, exist_ok=True)
        kwargs = {"api_key": self.config.openai_api_key}
        if self.config.openai_org_id:
            kwargs["organization"] = self.config.openai_org_id
        if self.config.openai_project_id:
            kwargs["project"] = self.config.openai_project_id
        client = OpenAI(**kwargs)
        voice_order = [self.config.openai_tts_voice]
        fallback = self.config.openai_tts_fallback_voice
        if (
            self.config.openai_tts_allow_fallback
            and fallback
            and fallback != self.config.openai_tts_voice
        ):
            voice_order.append(fallback)

        last_error: Optional[Exception] = None
        for voice in voice_order:
            try:
                self._synthesize_with_voice(client, spoken_text, output_path, voice)
                if voice != self.config.openai_tts_voice:
                    warnings.append(
                        f"OpenAI TTS voice '{self.config.openai_tts_voice}' was not accepted; "
                        f"used fallback voice '{voice}' for this whole audio clip."
                    )
                return output_path, warnings
            except Exception as exc:
                last_error = exc
                try:
                    output_path.unlink()
                except FileNotFoundError:
                    pass

        warnings.append(f"OpenAI speech generation failed: {last_error}")
        return None, warnings

    def _synthesize_with_voice(
        self,
        client,
        spoken_text: str,
        output_path: Path,
        voice: str,
    ) -> None:
        chunks = chunk_for_tts(spoken_text)
        part_paths = []
        try:
            for index, chunk in enumerate(chunks, start=1):
                part_path = output_path.with_suffix(f".part{index}.mp3")
                self._stream_chunk(client, chunk, part_path, voice=voice)
                part_paths.append(part_path)
            with output_path.open("wb") as output:
                for part_path in part_paths:
                    with part_path.open("rb") as part:
                        output.write(part.read())
        finally:
            for part_path in part_paths:
                try:
                    part_path.unlink()
                except FileNotFoundError:
                    pass

    def _stream_chunk(self, client, chunk: str, output_path: Path, *, voice: str) -> None:
        kwargs = {
            "model": self.config.openai_tts_model,
            "voice": voice,
            "input": chunk,
            "response_format": "mp3",
        }
        instructions = self.config.openai_tts_instructions
        try:
            with client.audio.speech.with_streaming_response.create(
                **kwargs, instructions=instructions
            ) as response:
                response.stream_to_file(output_path)
        except TypeError:
            with client.audio.speech.with_streaming_response.create(**kwargs) as response:
                response.stream_to_file(output_path)


class AudioPlayer:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def play(self, audio_path: Path) -> List[str]:
        if not audio_path.exists():
            return [f"Audio file not found: {audio_path}"]
        command = shlex.split(self.config.audio_autoplay_command) or ["afplay"]
        try:
            subprocess.run([*command, str(audio_path)], check=False)
        except FileNotFoundError:
            return [f"Audio playback command not found: {command[0]}"]
        return []


def chunk_for_tts(text: str, max_chars: int = 3600) -> List[str]:
    text = clean_text(text)
    if len(text) <= max_chars:
        return [text]
    chunks = []
    current = ""
    for sentence in split_sentences(text):
        if len(current) + len(sentence) + 1 <= max_chars:
            current = f"{current} {sentence}".strip()
            continue
        if current:
            chunks.append(current)
        current = sentence
    if current:
        chunks.append(current)
    return chunks


def split_sentences(text: str) -> List[str]:
    parts = []
    current = []
    for token in text.split(" "):
        current.append(token)
        if token.endswith((".", "?", "!")):
            parts.append(" ".join(current))
            current = []
    if current:
        parts.append(" ".join(current))
    return parts
