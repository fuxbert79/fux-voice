"""Transkribiert Audio via OpenAI Whisper API (deutsch)."""
from __future__ import annotations

import io
import logging
import wave
from typing import Optional

import numpy as np
from openai import OpenAI

logger = logging.getLogger(__name__)


class WhisperTranscriber:
    """Duenner Wrapper um die OpenAI Whisper API."""

    def __init__(
        self,
        api_key: str,
        model: str = "whisper-1",
        language: str = "de",
        prompt: Optional[str] = None,
    ) -> None:
        self._client = OpenAI(api_key=api_key)
        self.model = model
        self.language = language
        self.prompt = prompt

    @staticmethod
    def _audio_to_wav_bytes(audio: np.ndarray, sample_rate: int) -> bytes:
        """Konvertiert float32-Array (-1..1) zu 16-bit WAV-Bytes."""
        if audio.ndim > 1:
            audio = audio.mean(axis=1)

        audio = np.clip(audio, -1.0, 1.0)
        pcm = (audio * 32767.0).astype(np.int16)

        buf = io.BytesIO()
        with wave.open(buf, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)
            wav.writeframes(pcm.tobytes())
        return buf.getvalue()

    def transcribe(self, audio: np.ndarray, sample_rate: int) -> str:
        """Transkribiert Audio-Array zu deutschem Text."""
        duration_s = len(audio) / sample_rate
        if duration_s < 0.3:
            logger.info("Audio zu kurz (%.2fs), uebersprungen", duration_s)
            return ""

        wav_bytes = self._audio_to_wav_bytes(audio, sample_rate)
        logger.info("Sende %.2fs Audio an Whisper (%d KB)", duration_s, len(wav_bytes) // 1024)

        kwargs = {
            "model": self.model,
            "file": ("audio.wav", wav_bytes, "audio/wav"),
            "language": self.language,
            "response_format": "text",
        }
        if self.prompt:
            kwargs["prompt"] = self.prompt

        response = self._client.audio.transcriptions.create(**kwargs)
        text = response if isinstance(response, str) else getattr(response, "text", "")
        text = text.strip()
        logger.info("Transkription: %r", text[:80])
        return text
