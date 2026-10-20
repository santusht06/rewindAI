"""Deterministic subtitle chunker for grounding and vector index staging.

Adheres to:
- BE-INGEST-005 (Deterministic tested chunking with title & timestamp metadata)
- 04_content_ingestion_pipeline.mmd
"""

from typing import Any

from services.api.ingestion.parser import SubtitleCue


def chunk_subtitle_cues(
    cues: list[SubtitleCue],
    max_duration_seconds: float = 45.0,
    max_words: int = 120,
    min_duration_seconds: float = 10.0,
) -> list[dict[str, Any]]:
    """Group subtitle cues into coherent scene chunks suitable for RAG retrieval.

    Invariants:
    - Guaranteed non-negative, non-decreasing timestamps.
    - Preserves exact boundary of cues (start of first cue, end of last cue).
    - Preserves speakers if single speaker or summarizes speaker transitions.
    """
    if not cues:
        return []

    chunks: list[dict[str, Any]] = []
    current_cues: list[SubtitleCue] = []
    current_words = 0

    for cue in cues:
        cue_words = len(cue.text.split())

        # If adding this cue exceeds max duration or word count, and we already have cues
        if current_cues:
            potential_duration = cue.end_time_seconds - current_cues[0].start_time_seconds
            potential_words = current_words + cue_words

            # Check if current chunk is long enough to finalize
            chunk_duration = current_cues[-1].end_time_seconds - current_cues[0].start_time_seconds
            if (potential_duration > max_duration_seconds or potential_words > max_words) and chunk_duration >= min_duration_seconds:
                # Finalize current chunk
                chunks.append(_build_chunk_dict(len(chunks), current_cues))
                current_cues = []
                current_words = 0

        current_cues.append(cue)
        current_words += cue_words

    if current_cues:
        chunks.append(_build_chunk_dict(len(chunks), current_cues))

    return chunks


def _build_chunk_dict(ordinal: int, cues: list[SubtitleCue]) -> dict[str, Any]:
    """Helper formatting a list of cues into a chunk dictionary."""
    start_time = cues[0].start_time_seconds
    end_time = cues[-1].end_time_seconds

    # If end_time is somehow earlier than start_time due to overlapping cues, clamp to start_time
    end_time = max(end_time, start_time)

    # Combine text with speaker attribution if present
    text_parts = []
    speakers = set()
    for c in cues:
        if c.speaker:
            speakers.add(c.speaker)
            text_parts.append(f"[{c.speaker}] {c.text}")
        else:
            text_parts.append(c.text)

    full_text = " ".join(text_parts)
    speaker_summary = ", ".join(sorted(speakers)) if speakers else None

    return {
        "ordinal": ordinal,
        "start_time_seconds": round(start_time, 2),
        "end_time_seconds": round(end_time, 2),
        "start_time_formatted": f"{int(start_time // 60):02d}:{int(start_time % 60):02d}",
        "end_time_formatted": f"{int(end_time // 60):02d}:{int(end_time % 60):02d}",
        "text": full_text,
        "speaker": speaker_summary,
        "cue_count": len(cues),
    }
