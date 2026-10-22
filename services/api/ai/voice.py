"""Voice interaction adapters: Speech-To-Text (STT) and Text-To-Speech (TTS).

Adheres to:
- REWIND-REQ-018 (FR-09: Voice interaction, push-to-talk, fallback to text)
- REWIND-REQ-020 (Section 4: Voice behavior)
- AT-11, AT-12
"""

from __future__ import annotations

import base64
import os
from typing import Protocol


class SpeechToTextProvider(Protocol):
    """Abstract interface for audio transcription."""

    async def transcribe(self, audio_bytes: bytes, language: str = "en") -> str:
        """Convert input speech audio bytes to text string."""
        ...


class TextToSpeechProvider(Protocol):
    """Abstract interface for speech audio synthesis."""

    async def synthesize(self, text: str, voice: str | None = None) -> bytes:
        """Convert answer text into playable audio bytes."""
        ...


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


class MockTextToSpeechProvider:
    """Deterministic TTS provider returning valid minimal WAV container."""

    # 44-byte minimal silent PCM WAV container
    MINIMAL_WAV_HEADER = (
        b"RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00D\xac\x00\x00"
        b"\x88X\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00"
    )

    async def synthesize(self, text: str, voice: str | None = None) -> bytes:
        # Return valid minimal WAV audio binary
        return self.MINIMAL_WAV_HEADER


# Registry / Factory
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
        _tts_provider = MockTextToSpeechProvider()
    return _tts_provider


def set_tts_provider(provider: TextToSpeechProvider) -> None:
    global _tts_provider
    _tts_provider = provider
