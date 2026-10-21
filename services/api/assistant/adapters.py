"""Playback context adapters implementing the PlaybackContextProvider protocol."""

from services.api.assistant.contracts import (
    PlaybackContext,
    PlaybackContextProvider,
)
from services.api.errors import NotFoundError
from services.api.infrastructure.repositories import (
    MovieRepository,
    ViewingSessionRepository,
)
from services.api.infrastructure.tables import ViewingSessionTable


class StandardPlaybackContextAdapter(PlaybackContextProvider):
    """Resolves playback context from existing session and movie persistence layers."""

    def __init__(
        self,
        session_repo: ViewingSessionRepository,
        movie_repo: MovieRepository,
    ) -> None:
        self.session_repo = session_repo
        self.movie_repo = movie_repo

    async def get_current_context(self, session_id: str) -> PlaybackContext:
        """Resolve current context with honest provenance reporting."""
        session: ViewingSessionTable | None = await self.session_repo.get_by_id(session_id)
        if not session:
            raise NotFoundError(f"Viewing session '{session_id}' not found.")

        movie = await self.movie_repo.get_by_id(session.movie_id)
        if not movie:
            raise NotFoundError(f"Movie '{session.movie_id}' not found.")

        # Determine provenance note based on recorded progress source
        provenance = "Manual slider / D-pad confirmation"
        is_verified = False
        if session.progress_source == "verified_integration":
            provenance = "Cryptographically signed partner integration token"
            is_verified = True
        elif session.progress_source == "partner_sync":
            provenance = "Authorized streaming app sync channel"
            is_verified = True
        elif session.progress_source == "voice_command":
            provenance = "Voice query timestamp declaration ('At 32 minutes...')"
        elif session.progress_source == "companion_app":
            provenance = "Second-screen companion sync"

        # Safe duration fallback if movie duration is 0 or unset
        duration = movie.duration_seconds if movie.duration_seconds and movie.duration_seconds > 0 else 7200

        return PlaybackContext(
            provider_id="simulator",  # Default provider if unassigned
            title_id=movie.id,
            display_title=movie.title,
            current_position_seconds=session.current_position_seconds,
            duration_seconds=duration,
            language=movie.language or "en",
            is_verified=is_verified,
            provenance_note=provenance,
        )
