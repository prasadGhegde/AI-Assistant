from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

from .config import AppConfig


@dataclass(frozen=True)
class VoicePreset:
    number: int
    name: str
    filter_graph: str


@dataclass(frozen=True)
class VoiceRenderResult:
    clean_path: Path
    default_preset: str
    default_path: Path
    variant_paths: Dict[str, Path]
    preset_numbers: Dict[str, int]
    warnings: List[str]


VOICE_PRESETS = [
    VoicePreset(
        1,
        "clean_ai",
        "acompressor=threshold=-26dB:ratio=3.5:attack=8:release=110:makeup=3.0,"
        "equalizer=f=2500:t=q:w=1:g=2.5,"
        "equalizer=f=4500:t=q:w=1:g=1.5,"
        "volume=1.08,"
        "alimiter=limit=0.95:attack=5:release=80",
    ),
    VoicePreset(
        2,
        "subtle_assistant",
        "acompressor=threshold=-28dB:ratio=4.5:attack=6:release=105:makeup=4.0,"
        "equalizer=f=2200:t=q:w=1:g=3.0,"
        "equalizer=f=4200:t=q:w=1:g=2.0,"
        "volume=1.15,"
        "alimiter=limit=0.94:attack=4:release=80",
    ),
    VoicePreset(
        3,
        "jarvis_clean",
        "highpass=f=120,"
        "lowpass=f=7500,"
        "acompressor=threshold=-28dB:ratio=5.5:attack=5:release=100:makeup=5.0,"
        "equalizer=f=2400:t=q:w=1:g=3.5,"
        "equalizer=f=5000:t=q:w=1:g=2.5,"
        "volume=1.18,"
        "alimiter=limit=0.93:attack=3:release=80",
    ),
    VoicePreset(
        4,
        "jarvis_like",
        "highpass=f=130,"
        "lowpass=f=6800,"
        "acompressor=threshold=-30dB:ratio=6.0:attack=5:release=95:makeup=5.5,"
        "equalizer=f=2300:t=q:w=1:g=4.0,"
        "equalizer=f=4200:t=q:w=1:g=3.0,"
        "aecho=0.6:0.2:18:0.08,"
        "volume=1.18,"
        "alimiter=limit=0.92:attack=3:release=80",
    ),
    VoicePreset(
        5,
        "radio_comms",
        "highpass=f=200,"
        "lowpass=f=3500,"
        "acompressor=threshold=-24dB:ratio=8.0:attack=5:release=100:makeup=8.0,"
        "aecho=0.85:0.95:15|30:0.5|0.4,"
        "equalizer=f=1800:t=q:w=1:g=4.0,"
        "equalizer=f=4200:t=q:w=1:g=4.0,"
        "volume=1.5,"
        "alimiter=limit=0.90:attack=3:release=70",
    ),
    VoicePreset(
        6,
        "tactical_brief",
        "highpass=f=180,"
        "lowpass=f=5200,"
        "acompressor=threshold=-28dB:ratio=6.0:attack=5:release=100:makeup=4.5,"
        "equalizer=f=2500:t=q:w=1:g=3.5,"
        "equalizer=f=5200:t=q:w=1:g=1.5,"
        "volume=1.16,"
        "alimiter=limit=0.92:attack=3:release=75",
    ),
    VoicePreset(
        7,
        "hologram",
        "highpass=f=160,"
        "lowpass=f=6400,"
        "acompressor=threshold=-30dB:ratio=5.0:attack=5:release=95:makeup=4.5,"
        "equalizer=f=2600:t=q:w=1:g=4.0,"
        "equalizer=f=6000:t=q:w=1:g=2.0,"
        "aecho=0.7:0.25:22:0.07,"
        "volume=1.12,"
        "alimiter=limit=0.92:attack=3:release=75",
    ),
    VoicePreset(
        8,
        "synthetic_warm",
        "highpass=f=110,"
        "lowpass=f=7000,"
        "acompressor=threshold=-30dB:ratio=4.5:attack=7:release=110:makeup=4.0,"
        "equalizer=f=180:t=q:w=1:g=1.5,"
        "equalizer=f=2200:t=q:w=1:g=2.5,"
        "volume=1.14,"
        "alimiter=limit=0.94:attack=4:release=80",
    ),
    VoicePreset(
        9,
        "stronger_robot",
        "highpass=f=170,"
        "lowpass=f=5600,"
        "acompressor=threshold=-32dB:ratio=7.5:attack=4:release=95:makeup=6.0,"
        "equalizer=f=2600:t=q:w=1:g=4.5,"
        "aecho=0.7:0.25:24:0.06,"
        "volume=1.20,"
        "alimiter=limit=0.91:attack=3:release=70",
    ),
    VoicePreset(
        10,
        "bitcrushed_bot",
        "highpass=f=180,"
        "lowpass=f=4200,"
        "acompressor=threshold=-24dB:ratio=7.0:attack=4:release=90:makeup=3.0,"
        "acrusher=bits=10:mix=0.18,"
        "equalizer=f=2400:t=q:w=1:g=3.0,"
        "volume=1.14,"
        "alimiter=limit=0.90:attack=3:release=70",
    ),
    VoicePreset(
        11,
        "masked_vocoder_style",
        "highpass=f=210,"
        "lowpass=f=5000,"
        "acompressor=threshold=-28dB:ratio=6.0:attack=5:release=95:makeup=4.0,"
        "equalizer=f=1600:t=q:w=1:g=2.5,"
        "equalizer=f=3200:t=q:w=1:g=3.5,"
        "aecho=0.5:0.2:16:0.05,"
        "volume=1.10,"
        "alimiter=limit=0.90:attack=3:release=70",
    ),
    VoicePreset(
        12,
        "test_radio_echo_strong1",
        "acompressor=threshold=-30dB:ratio=6.0:attack=5:release=100:makeup=8.0,"
        "equalizer=f=2200:t=q:w=1:g=4.0,"
        "equalizer=f=4200:t=q:w=1:g=3.0,"
        "volume=1.85",
    ),
]

PRESETS_BY_NAME = {preset.name: preset for preset in VOICE_PRESETS}


class VoiceEffectProcessor:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def render_variants(
        self,
        *,
        clean_tts_path: Path,
        output_stem: Path,
    ) -> Tuple[VoiceRenderResult, List[str]]:
        warnings: List[str] = []
        if not clean_tts_path.exists():
            warnings.append(f"Clean TTS file not found for voice variants: {clean_tts_path}")
            result = VoiceRenderResult(
                clean_path=clean_tts_path,
                default_preset=self._default_preset_name(),
                default_path=clean_tts_path,
                variant_paths={},
                preset_numbers=self._preset_numbers(),
                warnings=warnings,
            )
            return result, warnings

        default_preset = self._default_preset_name()
        if not self.config.voice_effect_enabled:
            result = VoiceRenderResult(
                clean_path=clean_tts_path,
                default_preset="clean",
                default_path=clean_tts_path,
                variant_paths={"clean": clean_tts_path},
                preset_numbers={"clean": 0, **self._preset_numbers()},
                warnings=[],
            )
            return result, []

        ffmpeg = shutil.which(self.config.ffmpeg_path)
        if not ffmpeg:
            warnings.append(
                "Voice effect variants skipped because ffmpeg was not found. Install ffmpeg "
                "or set MORNING_BRIEFS_VOICE_EFFECT_ENABLED=false."
            )
            result = VoiceRenderResult(
                clean_path=clean_tts_path,
                default_preset="clean",
                default_path=clean_tts_path,
                variant_paths={"clean": clean_tts_path},
                preset_numbers={"clean": 0, **self._preset_numbers()},
                warnings=warnings,
            )
            return result, warnings

        output_stem.parent.mkdir(parents=True, exist_ok=True)
        if self.config.voice_effect_save_wavs:
            self._render_clean_wav(ffmpeg, clean_tts_path)

        variant_paths: Dict[str, Path] = {}
        presets = VOICE_PRESETS if self.config.voice_effect_render_all else [PRESETS_BY_NAME[default_preset]]
        for preset in presets:
            variant_path = output_stem.with_name(
                f"{output_stem.name}_voice_{preset.number:02d}_{preset.name}.mp3"
            )
            try:
                if preset.name == default_preset and self.config.voice_effect_save_wavs:
                    default_wav = self.config.audio_dir / "robotic_tts.wav"
                    self._run(
                        [
                            ffmpeg,
                            "-y",
                            "-i",
                            str(clean_tts_path),
                            "-af",
                            preset.filter_graph,
                            "-ac",
                            "1",
                            "-ar",
                            "48000",
                            str(default_wav),
                        ]
                    )
                    self._encode_mp3(ffmpeg, default_wav, variant_path)
                else:
                    self._render_preset(ffmpeg, clean_tts_path, variant_path, preset)
                variant_paths[preset.name] = variant_path
            except Exception as exc:
                warnings.append(f"Voice preset '{preset.name}' failed; skipped it: {exc}")

        default_path = variant_paths.get(default_preset, clean_tts_path)
        if default_preset not in variant_paths:
            warnings.append(
                f"Default voice preset '{default_preset}' was not rendered; using clean TTS."
            )
            variant_paths.setdefault("clean", clean_tts_path)
        result = VoiceRenderResult(
            clean_path=clean_tts_path,
            default_preset=default_preset if default_preset in variant_paths else "clean",
            default_path=default_path,
            variant_paths=variant_paths or {"clean": clean_tts_path},
            preset_numbers={"clean": 0, **self._preset_numbers()},
            warnings=warnings,
        )
        return result, warnings

    def process(self, tts_mp3_path: Path) -> Tuple[Path, List[str]]:
        result, warnings = self.render_variants(
            clean_tts_path=tts_mp3_path,
            output_stem=tts_mp3_path.with_suffix(""),
        )
        return result.default_path, warnings

    def _default_preset_name(self) -> str:
        configured = self.config.voice_effect_default_preset
        if configured in PRESETS_BY_NAME:
            return configured
        legacy = self.config.voice_effect_mode
        if legacy in PRESETS_BY_NAME:
            return legacy
        return "radio_comms"

    @staticmethod
    def _preset_numbers() -> Dict[str, int]:
        return {preset.name: preset.number for preset in VOICE_PRESETS}

    def _render_clean_wav(self, ffmpeg: str, clean_tts_path: Path) -> None:
        self._run(
            [
                ffmpeg,
                "-y",
                "-i",
                str(clean_tts_path),
                "-ac",
                "1",
                "-ar",
                "48000",
                str(self.config.audio_dir / "original_tts.wav"),
            ]
        )

    def _render_preset(
        self,
        ffmpeg: str,
        clean_tts_path: Path,
        variant_path: Path,
        preset: VoicePreset,
    ) -> None:
        self._run(
            [
                ffmpeg,
                "-y",
                "-i",
                str(clean_tts_path),
                "-af",
                preset.filter_graph,
                "-ac",
                "1",
                "-ar",
                "48000",
                "-c:a",
                "libmp3lame",
                "-q:a",
                "3",
                str(variant_path),
            ]
        )

    def _encode_mp3(self, ffmpeg: str, wav_path: Path, output_path: Path) -> None:
        self._run(
            [
                ffmpeg,
                "-y",
                "-i",
                str(wav_path),
                "-c:a",
                "libmp3lame",
                "-q:a",
                "3",
                str(output_path),
            ]
        )

    @staticmethod
    def _run(command: List[str]) -> None:
        result = subprocess.run(
            command,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,  # Capture stderr instead of discarding
            text=True,
        )
        if result.stderr:
            print(f"FFmpeg stderr: {result.stderr}")  # Print errors to terminal
