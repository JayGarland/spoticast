"""Audio assembly — convert Gemini TTS PCM output to MP3 for each commentary block."""

from __future__ import annotations

import logging
from pathlib import Path
import subprocess
import tempfile

from pydub import AudioSegment

# Silence appended after each commentary block, before music resumes
TRAIL_SILENCE_MS = 800
TARGET_I_LUFS = -14
TARGET_TP_DB = -1
TARGET_LRA = 11

_GENERATED_DIR = Path("generated")
logger = logging.getLogger(__name__)


def _export_loudness_normalized_mp3(audio: AudioSegment, output_path: Path) -> None:
    """Export commentary through ffmpeg loudnorm for consistent perceived volume."""
    with tempfile.TemporaryDirectory(prefix="resonova-audio-") as tmp_dir:
        tmp_wav = Path(tmp_dir) / "commentary.wav"
        audio.export(str(tmp_wav), format="wav")

        loudnorm = f"loudnorm=I={TARGET_I_LUFS}:TP={TARGET_TP_DB}:LRA={TARGET_LRA}"
        cmd = [
            AudioSegment.converter,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(tmp_wav),
            "-af",
            loudnorm,
            "-codec:a",
            "libmp3lame",
            "-q:a",
            "2",
            str(output_path),
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
        except (OSError, subprocess.CalledProcessError) as exc:
            stderr = getattr(exc, "stderr", "") or str(exc)
            logger.warning(
                "ffmpeg loudness normalization failed; exporting unnormalized commentary: %s",
                stderr.strip(),
            )
            audio.export(str(output_path), format="mp3")


def assemble_commentary(pcm_bytes: bytes, filename: str) -> Path:
    """
    Convert raw PCM dialogue audio to MP3 and write to generated/.

    Input is the raw PCM output from Gemini TTS: 16-bit signed, 24kHz, mono.
    The model already handles natural pacing between speakers, so no inter-speaker
    silence is inserted here — only a short trail before the next music track.
    """
    audio = AudioSegment(data=pcm_bytes, sample_width=2, frame_rate=24000, channels=1)
    audio += AudioSegment.silent(duration=TRAIL_SILENCE_MS)

    output_path = _GENERATED_DIR / filename
    output_path.parent.mkdir(parents=True, exist_ok=True)
    _export_loudness_normalized_mp3(audio, output_path)
    return output_path
