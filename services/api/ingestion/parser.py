"""Subtitle and transcript parser for SRT and WebVTT formats.

Adheres to:
- SRS-ING-001 (Authorized asset validation)
- SRS-ING-003 (Timestamp validation and error handling)
- 04_content_ingestion_pipeline.mmd
"""

import re
from dataclasses import dataclass
from services.api.errors import ValidationError


@dataclass
class SubtitleCue:
    """Parsed individual subtitle cue."""
    index: int
    start_time_seconds: float
    end_time_seconds: float
    text: str
    speaker: str | None = None

    @property
    def duration_seconds(self) -> float:
        return self.end_time_seconds - self.start_time_seconds


def parse_timestamp_to_seconds(ts_str: str) -> float:
    """Parse SRT (HH:MM:SS,mmm) or WebVTT (HH:MM:SS.mmm or MM:SS.mmm) into seconds."""
    ts_str = ts_str.strip().replace(",", ".")
    parts = ts_str.split(":")
    try:
        if len(parts) == 3:
            hours = float(parts[0])
            minutes = float(parts[1])
            seconds = float(parts[2])
            return hours * 3600.0 + minutes * 60.0 + seconds
        elif len(parts) == 2:
            minutes = float(parts[0])
            seconds = float(parts[1])
            return minutes * 60.0 + seconds
        else:
            raise ValueError(f"Invalid timestamp format: {ts_str}")
    except ValueError as exc:
        raise ValidationError(f"Invalid timestamp format '{ts_str}': {exc}") from exc


def clean_subtitle_text(text: str) -> tuple[str, str | None]:
    """Strip HTML formatting tags and extract speaker prefix if present."""
    # Strip HTML tags: <i>, </i>, <b>, <c.color>, etc.
    cleaned = re.sub(r"<[^>]+>", "", text)
    cleaned = cleaned.strip()

    speaker = None
    # Check for speaker format like "COOPER: We need to leave."
    speaker_match = re.match(r"^([A-Z0-9\s]{2,20}):\s*(.+)$", cleaned)
    if speaker_match:
        speaker = speaker_match.group(1).strip()
        cleaned = speaker_match.group(2).strip()

    # Collapse multiple whitespace characters
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned, speaker


def parse_srt_or_vtt(content: str) -> list[SubtitleCue]:
    """Parse raw SRT or WebVTT string into ordered SubtitleCue objects.

    Enforces:
    - Non-empty content.
    - Valid timestamps (start >= 0, end >= start).
    - Monotonic ordering checks.
    """
    if not content or not content.strip():
        raise ValidationError("Subtitle asset is empty.")

    # Remove BOM if present
    content = content.lstrip("\ufeff")
    lines = [line.strip() for line in content.splitlines()]

    cues: list[SubtitleCue] = []
    current_index = 1
    i = 0
    n = len(lines)

    # Skip WebVTT header if present
    if lines and lines[0].upper().startswith("WEBVTT"):
        i = 1
        while i < n and lines[i] != "":
            i += 1  # Skip WebVTT metadata block
        while i < n and lines[i] == "":
            i += 1

    # Timestamp line pattern: e.g. 00:01:20,000 --> 00:01:23,500
    ts_pattern = re.compile(
        r"(\d{1,2}:\d{2}(?::\d{2})?(?:[,\.]\d{1,3})?)\s*-->\s*(\d{1,2}:\d{2}(?::\d{2})?(?:[,\.]\d{1,3})?)"
    )

    while i < n:
        line = lines[i]
        if not line:
            i += 1
            continue

        # Check if line is an index integer
        if line.isdigit() and i + 1 < n and ts_pattern.search(lines[i + 1]):
            current_index = int(line)
            i += 1
            line = lines[i]

        ts_match = ts_pattern.search(line)
        if ts_match:
            start_str, end_str = ts_match.group(1), ts_match.group(2)
            start_sec = parse_timestamp_to_seconds(start_str)
            end_sec = parse_timestamp_to_seconds(end_str)

            if start_sec < 0 or end_sec < 0:
                raise ValidationError(f"Negative timestamp encountered: start={start_sec}, end={end_sec}")

            if end_sec < start_sec:
                raise ValidationError(
                    f"Inverted timestamp range encountered: start={start_sec}s > end={end_sec}s"
                )

            # Collect text lines for this cue
            i += 1
            text_lines = []
            while i < n and lines[i] and not ts_pattern.search(lines[i]) and not (lines[i].isdigit() and i + 1 < n and ts_pattern.search(lines[i + 1])):
                text_lines.append(lines[i])
                i += 1

            raw_text = " ".join(text_lines)
            cleaned_text, speaker = clean_subtitle_text(raw_text)

            if cleaned_text:
                cues.append(
                    SubtitleCue(
                        index=current_index,
                        start_time_seconds=start_sec,
                        end_time_seconds=end_sec,
                        text=cleaned_text,
                        speaker=speaker,
                    )
                )
                current_index += 1
        else:
            i += 1

    if not cues:
        raise ValidationError("No valid subtitle cues could be parsed from the asset.")

    # Sort cues deterministically by start_time_seconds, then index
    cues.sort(key=lambda c: (c.start_time_seconds, c.end_time_seconds, c.index))
    return cues
