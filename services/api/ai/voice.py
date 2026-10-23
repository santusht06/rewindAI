"""Voice interaction adapters: Speech-To-Text (STT) and Text-To-Speech (TTS).

Adheres to:
- REWIND-REQ-018 (FR-09: Voice interaction, push-to-talk, fallback to text)
- REWIND-REQ-020 (Section 4: Voice behavior)
- AT-11, AT-12

TTS backends (in order of priority):
1. Google Cloud Text-to-Speech REST API  (if GEMINI_API_KEY / GOOGLE_TTS_API_KEY is set)
2. MockTextToSpeechProvider              (returns sentinel; browser falls back to Web Speech API)

The browser-side JS (app.js) detects the sentinel and falls back to
window.speechSynthesis when the TTS audio payload is absent.
"""

from __future__ import annotations

import base64
import logging
from typing import Protocol

import httpx

from services.api.config import settings

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Protocol definitions
# ──────────────────────────────────────────────────────────────────────────────

class SpeechToTextProvider(Protocol):
    """Abstract interface for audio transcription."""

    async def transcribe(self, audio_bytes: bytes, language: str = "en") -> str:
        """Convert input speech audio bytes to text string."""
        ...


class TextToSpeechProvider(Protocol):
    """Abstract interface for speech audio synthesis."""

    async def synthesize(self, text: str, voice: str | None = None) -> bytes:
        """Convert answer text into playable audio bytes (MP3 or WAV).
        
        Returns empty bytes if synthesis is unavailable — client falls back
        to browser Web Speech API.
        """
        ...


# ──────────────────────────────────────────────────────────────────────────────
# STT: Mock (deterministic offline)
# ──────────────────────────────────────────────────────────────────────────────

class MockSpeechToTextProvider:
    """Deterministic STT provider for tests and offline/edge development."""

    def __init__(self, default_transcription: str = "Who is this character and what is their role?") -> None:
        self.default_transcription = default_transcription

    async def transcribe(self, audio_bytes: bytes, language: str = "en") -> str:
        if not audio_bytes:
            return ""
        # Check if text is encoded in audio header for deterministic test fixtures
        if audio_bytes.startswith(b"MOCK_STT:"):
            return audio_bytes[9:].decode("utf-8", errors="replace").strip()
        return self.default_transcription


# ──────────────────────────────────────────────────────────────────────────────
# TTS: Mock (silent — triggers browser Web Speech API fallback)
# ──────────────────────────────────────────────────────────────────────────────

class MockTextToSpeechProvider:
    """Mock TTS provider returning simulated audio bytes for tests, or empty bytes for browser Web Speech API."""

    def __init__(self, audio_bytes: bytes = b"RIFF-MOCK-TTS-SYNTHESIZED-AUDIO") -> None:
        self.audio_bytes = audio_bytes

    async def synthesize(self, text: str, voice: str | None = None) -> bytes:
        return self.audio_bytes


# ──────────────────────────────────────────────────────────────────────────────
# TTS: Google Cloud Text-to-Speech REST
# ──────────────────────────────────────────────────────────────────────────────

class GoogleCloudTTSProvider:
    """Google Cloud Text-to-Speech via REST API.

    Uses the same API key as Gemini (AIza…) since both belong to Google Cloud.
    Returns MP3 audio bytes or empty bytes on failure (browser fallback).
    """

    TTS_URL = "https://texttospeech.googleapis.com/v1/text:synthesize"

    # Warm, natural voice for TV companion
    DEFAULT_VOICE = "en-US-Neural2-D"   # Male, natural Neural2
    FALLBACK_VOICE = "en-US-Standard-D" # Fallback Standard voice

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key or (
            settings.gemini_api_key.get_secret_value() if settings.gemini_api_key else ""
        )

    async def synthesize(self, text: str, voice: str | None = None) -> bytes:
        """Synthesize text to MP3 audio. Returns empty bytes on failure."""
        if not self._api_key:
            logger.warning("Google TTS: No API key configured, returning empty bytes.")
            return b""

        # Truncate very long answers to keep TTS snappy (TV UX)
        if len(text) > 500:
            text = text[:497] + "..."

        chosen_voice = voice or self.DEFAULT_VOICE

        payload = {
            "input": {"text": text},
            "voice": {
                "languageCode": "en-US",
                "name": chosen_voice,
                "ssmlGender": "MALE",
            },
            "audioConfig": {
                "audioEncoding": "MP3",
                "speakingRate": 1.0,
                "pitch": 0.0,
                "volumeGainDb": 0.0,
            },
        }

        url = f"{self.TTS_URL}?key={self._api_key}"

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.post(url, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    audio_b64 = data.get("audioContent", "")
                    if audio_b64:
                        return base64.b64decode(audio_b64)
                    logger.warning("Google TTS: Response had no audioContent.")
                    return b""
                elif resp.status_code == 400 and chosen_voice != self.FALLBACK_VOICE:
                    # Neural2 voice may not be available in all regions — retry with Standard
                    logger.warning(
                        "Google TTS: Neural2 voice unavailable (%s), retrying with Standard voice.",
                        resp.status_code,
                    )
                    payload["voice"]["name"] = self.FALLBACK_VOICE
                    resp2 = await client.post(url, json=payload)
                    if resp2.status_code == 200:
                        data2 = resp2.json()
                        audio_b64 = data2.get("audioContent", "")
                        return base64.b64decode(audio_b64) if audio_b64 else b""
                    logger.warning("Google TTS: Fallback voice also failed: %s", resp2.status_code)
                    return b""
                else:
                    logger.warning(
                        "Google TTS: API error %s — %s",
                        resp.status_code,
                        resp.text[:200],
                    )
                    return b""
            except httpx.TimeoutException:
                logger.warning("Google TTS: Request timed out.")
                return b""
            except Exception as exc:
                logger.warning("Google TTS: Unexpected error: %s", exc)
                return b""


# ──────────────────────────────────────────────────────────────────────────────
# Registry / Factory
# ──────────────────────────────────────────────────────────────────────────────

_stt_provider: SpeechToTextProvider | None = None
_tts_provider: TextToSpeechProvider | None = None


def get_stt_provider() -> SpeechToTextProvider:
    global _stt_provider
    if _stt_provider is None:
        _stt_provider = MockSpeechToTextProvider()
    return _stt_provider


def set_stt_provider(provider: SpeechToTextProvider) -> None:
    global _stt_provider
    _stt_provider = provider


def get_tts_provider() -> TextToSpeechProvider:
    global _tts_provider
    if _tts_provider is None:
        if settings.has_gemini_provider():
            # Reuse Gemini/Google API key for Google Cloud TTS
            _tts_provider = GoogleCloudTTSProvider()
            logger.info("TTS: Using Google Cloud Text-to-Speech.")
        else:
            _tts_provider = MockTextToSpeechProvider()
            logger.info("TTS: No API key — using Mock TTS (browser Web Speech API fallback).")
    return _tts_provider


def set_tts_provider(provider: TextToSpeechProvider) -> None:
    global _tts_provider
    _tts_provider = provider
