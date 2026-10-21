"""Rewind Cross-App AI Viewing Assistant Package.

Implements provider-neutral abstractions, registry, and playback context adapters.
"""

from services.api.assistant.contracts import (
    AssistantEntryPoint,
    AssistantPresentationAdapter,
    AssistantPresentationMode,
    ContentEvidenceProvider,
    PlaybackContext,
    PlaybackContextProvider,
    ProviderCapabilityStatus,
    StreamingProviderInfo,
)
from services.api.assistant.registry import (
    ProviderCapabilityRegistry,
    provider_registry,
)
from services.api.assistant.adapters import StandardPlaybackContextAdapter

__all__ = [
    "AssistantEntryPoint",
    "AssistantPresentationAdapter",
    "AssistantPresentationMode",
    "ContentEvidenceProvider",
    "PlaybackContext",
    "PlaybackContextProvider",
    "ProviderCapabilityRegistry",
    "ProviderCapabilityStatus",
    "StandardPlaybackContextAdapter",
    "StreamingProviderInfo",
    "provider_registry",
]
