"""Provider-neutral assistant contracts and domain definitions.

Implements requirements from 17_REWIND_CROSS_APP_ASSISTANT_PRODUCT_REQUIREMENT.md:
- Cross-provider flexibility
- Provider-neutral playback context acquisition
- Presentation adapters and invocation entry points
"""

from enum import StrEnum
from typing import Protocol, runtime_checkable
from pydantic import BaseModel, Field


class ProviderCapabilityStatus(StrEnum):
    """Empirical status of a specific provider capability on target OS."""

    VERIFIED = "VERIFIED"          # Tested and verified working with real integration
    PARTIAL = "PARTIAL"            # Works with limitations (e.g., requires manual confirmation)
    UNAVAILABLE = "UNAVAILABLE"    # Prohibited by OS sandbox, DRM, or security boundaries
    NOT_TESTED = "NOT_TESTED"      # Under evaluation or unverified


class AssistantPresentationMode(StrEnum):
    """Supported ways the assistant UI can be presented to the viewer."""

    SIDE_PANEL_OVERLAY = "SIDE_PANEL_OVERLAY"      # Right-hand 35% drawer over playback
    MODAL_OVERLAY = "MODAL_OVERLAY"                # Centered dialog over playback
    FOREGROUND_COMPANION = "FOREGROUND_COMPANION"  # Foreground app with instant back-to-app return
    COMPANION_DEVICE = "COMPANION_DEVICE"          # Second-screen phone/tablet web UI


class AssistantEntryPoint(StrEnum):
    """Supported invocation channels for invoking the assistant."""

    VOICE_COMMAND = "VOICE_COMMAND"        # "Alexa, open Rewind"
    REMOTE_SHORTCUT = "REMOTE_SHORTCUT"    # Dedicated button or long-press
    COMPANION_PAIRED = "COMPANION_PAIRED"  # Paired phone/tablet session
    MANUAL_LAUNCHER = "MANUAL_LAUNCHER"    # In-app launcher / simulator


class StreamingProviderInfo(BaseModel):
    """Metadata and verified capabilities for a third-party streaming service."""

    id: str = Field(..., description="Unique slug for the provider (e.g. netflix, prime_video)")
    name: str = Field(..., description="Human-readable display name")
    context_sync_status: ProviderCapabilityStatus = Field(
        ...,
        description="Ability to automatically read playback position without manual input",
    )
    evidence_status: ProviderCapabilityStatus = Field(
        ...,
        description="Availability of authorized transcripts and metadata",
    )
    supported_presentation_modes: list[AssistantPresentationMode] = Field(
        default_factory=list,
        description="Presentation surfaces compatible with this provider",
    )
    supported_entry_points: list[AssistantEntryPoint] = Field(
        default_factory=list,
        description="Invocation mechanisms supported on target devices",
    )
    notes: str = Field(default="", description="Platform sandbox or limitation notes")


class PlaybackContext(BaseModel):
    """Normalized playback context supplied to the AI orchestrator."""

    provider_id: str = Field(..., description="Active streaming provider (e.g. netflix, prime_video)")
    title_id: str = Field(..., description="Canonical title identifier")
    display_title: str = Field(..., description="Title display name")
    current_position_seconds: int = Field(..., ge=0, description="Playback timestamp in seconds")
    duration_seconds: int = Field(..., ge=0, description="Total movie/episode duration")
    language: str = Field(default="en", description="Spoken dialogue language")
    is_verified: bool = Field(
        default=False,
        description="True only if cryptographically verified or partner-authenticated",
    )
    provenance_note: str = Field(
        default="Manual timestamp confirmation",
        description="Auditable explanation of how timestamp was established",
    )


@runtime_checkable
class PlaybackContextProvider(Protocol):
    """Protocol for obtaining title identity and playback position."""

    async def get_current_context(self, session_id: str) -> PlaybackContext:
        """Resolve current playback context for an active viewing session."""
        ...


@runtime_checkable
class ContentEvidenceProvider(Protocol):
    """Protocol for supplying authorized transcripts, subtitles, and scene facts."""

    async def has_evidence_for_title(self, title_id: str) -> bool:
        """Check if authorized subtitle evidence exists for a title."""
        ...


@runtime_checkable
class AssistantPresentationAdapter(Protocol):
    """Protocol for presenting the assistant surface on a target device."""

    def get_supported_modes(self) -> list[AssistantPresentationMode]:
        """Return available presentation modes on the host device."""
        ...

    def get_default_mode(self) -> AssistantPresentationMode:
        """Return primary recommended presentation mode."""
        ...
