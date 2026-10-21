"""Provider capability registry maintaining verified streaming provider integrations."""

from services.api.assistant.contracts import (
    AssistantEntryPoint,
    AssistantPresentationMode,
    ProviderCapabilityStatus,
    StreamingProviderInfo,
)


class ProviderCapabilityRegistry:
    """Registry tracking supported streaming providers and their empirical capabilities."""

    def __init__(self) -> None:
        self._providers: dict[str, StreamingProviderInfo] = {}
        self._register_default_providers()

    def _register_default_providers(self) -> None:
        defaults = [
            StreamingProviderInfo(
                id="netflix",
                name="Netflix",
                context_sync_status=ProviderCapabilityStatus.UNAVAILABLE,
                evidence_status=ProviderCapabilityStatus.PARTIAL,
                supported_presentation_modes=[
                    AssistantPresentationMode.SIDE_PANEL_OVERLAY,
                    AssistantPresentationMode.FOREGROUND_COMPANION,
                    AssistantPresentationMode.COMPANION_DEVICE,
                ],
                supported_entry_points=[
                    AssistantEntryPoint.VOICE_COMMAND,
                    AssistantEntryPoint.COMPANION_PAIRED,
                    AssistantEntryPoint.MANUAL_LAUNCHER,
                ],
                notes="Sandboxed app on Fire OS / Vega OS. Automatic playback state inspection is blocked by OS container isolation. Requires manual timestamp confirmation or paired companion.",
            ),
            StreamingProviderInfo(
                id="prime_video",
                name="Amazon Prime Video",
                context_sync_status=ProviderCapabilityStatus.PARTIAL,
                evidence_status=ProviderCapabilityStatus.VERIFIED,
                supported_presentation_modes=[
                    AssistantPresentationMode.SIDE_PANEL_OVERLAY,
                    AssistantPresentationMode.FOREGROUND_COMPANION,
                    AssistantPresentationMode.COMPANION_DEVICE,
                ],
                supported_entry_points=[
                    AssistantEntryPoint.VOICE_COMMAND,
                    AssistantEntryPoint.REMOTE_SHORTCUT,
                    AssistantEntryPoint.COMPANION_PAIRED,
                ],
                notes="Amazon first-party application. Partial MediaSession telemetry where authorized; falls back to manual confirmation if token binding is unavailable.",
            ),
            StreamingProviderInfo(
                id="disney_plus",
                name="Disney+",
                context_sync_status=ProviderCapabilityStatus.UNAVAILABLE,
                evidence_status=ProviderCapabilityStatus.PARTIAL,
                supported_presentation_modes=[
                    AssistantPresentationMode.SIDE_PANEL_OVERLAY,
                    AssistantPresentationMode.FOREGROUND_COMPANION,
                    AssistantPresentationMode.COMPANION_DEVICE,
                ],
                supported_entry_points=[
                    AssistantEntryPoint.VOICE_COMMAND,
                    AssistantEntryPoint.COMPANION_PAIRED,
                ],
                notes="Sandboxed third-party application. Requires user timestamp selection.",
            ),
            StreamingProviderInfo(
                id="youtube",
                name="YouTube",
                context_sync_status=ProviderCapabilityStatus.UNAVAILABLE,
                evidence_status=ProviderCapabilityStatus.PARTIAL,
                supported_presentation_modes=[
                    AssistantPresentationMode.SIDE_PANEL_OVERLAY,
                    AssistantPresentationMode.FOREGROUND_COMPANION,
                    AssistantPresentationMode.COMPANION_DEVICE,
                ],
                supported_entry_points=[
                    AssistantEntryPoint.VOICE_COMMAND,
                    AssistantEntryPoint.COMPANION_PAIRED,
                ],
                notes="Web/Native sandboxed application. Requires user timestamp selection.",
            ),
            StreamingProviderInfo(
                id="simulator",
                name="Rewind TV Simulator (Demo Harness)",
                context_sync_status=ProviderCapabilityStatus.VERIFIED,
                evidence_status=ProviderCapabilityStatus.VERIFIED,
                supported_presentation_modes=[
                    AssistantPresentationMode.SIDE_PANEL_OVERLAY,
                    AssistantPresentationMode.MODAL_OVERLAY,
                    AssistantPresentationMode.FOREGROUND_COMPANION,
                    AssistantPresentationMode.COMPANION_DEVICE,
                ],
                supported_entry_points=[
                    AssistantEntryPoint.VOICE_COMMAND,
                    AssistantEntryPoint.REMOTE_SHORTCUT,
                    AssistantEntryPoint.COMPANION_PAIRED,
                    AssistantEntryPoint.MANUAL_LAUNCHER,
                ],
                notes="Local test harness and hackathon judge simulator with synchronized playback controls.",
            ),
        ]
        for p in defaults:
            self._providers[p.id] = p

    def list_providers(self) -> list[StreamingProviderInfo]:
        """Return all registered streaming providers."""
        return list(self._providers.values())

    def get_provider(self, provider_id: str) -> StreamingProviderInfo | None:
        """Lookup provider metadata by identifier."""
        return self._providers.get(provider_id.lower())

    def register_provider(self, provider: StreamingProviderInfo) -> None:
        """Register or override a provider configuration."""
        self._providers[provider.id.lower()] = provider


# Global singleton instance
provider_registry = ProviderCapabilityRegistry()
