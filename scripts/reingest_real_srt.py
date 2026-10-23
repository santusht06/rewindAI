#!/usr/bin/env python3
"""
Rewind AI — Real SRT Ingestion Script
Clears mock subtitle chunks and re-indexes the real Interstellar SRT
using actual Gemini embeddings so the AI can answer properly.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from services.api.config import settings
from services.api.infrastructure.database import engine
from services.api.ingestion.embeddings import get_embedding_provider
from services.api.ingestion.pipeline import IngestionPipeline


SRT_PATH = Path(__file__).resolve().parent.parent / "media" / "interstellar.srt"
MOVIE_ID = "interstellar-epic"


async def clear_old_data(session: AsyncSession) -> None:
    """Delete all existing content versions and chunks for this movie."""
    print("🗑️  Clearing old mock data...")
    # Delete subtitle chunks first (FK)
    r = await session.execute(
        text("""
            DELETE FROM subtitle_chunks
            WHERE content_version_id IN (
                SELECT id FROM content_versions WHERE movie_id = :mid
            )
        """),
        {"mid": MOVIE_ID},
    )
    print(f"   Deleted {r.rowcount} old chunks")

    # Delete subtitle cues
    r2 = await session.execute(
        text("""
            DELETE FROM subtitle_cues
            WHERE content_version_id IN (
                SELECT id FROM content_versions WHERE movie_id = :mid
            )
        """),
        {"mid": MOVIE_ID},
    )
    print(f"   Deleted {r2.rowcount} old cues")

    # Delete content versions
    r3 = await session.execute(
        text("DELETE FROM content_versions WHERE movie_id = :mid"),
        {"mid": MOVIE_ID},
    )
    print(f"   Deleted {r3.rowcount} old content versions")

    await session.commit()


async def main() -> None:
    print("=" * 60)
    print("Rewind AI — Real SRT Ingestion")
    print("=" * 60)

    # Verify SRT exists
    if not SRT_PATH.exists():
        print(f"❌ SRT file not found: {SRT_PATH}")
        sys.exit(1)

    srt_content = SRT_PATH.read_text(encoding="utf-8", errors="replace")
    print(f"📄 SRT loaded: {SRT_PATH.name} ({len(srt_content):,} chars)")

    # Check embedding provider
    provider = get_embedding_provider()
    print(f"🤖 Embedding provider: {provider.model_name}")

    if "mock" in provider.model_name:
        print("⚠️  WARNING: Using mock embeddings — Gemini API key may be invalid or missing.")
        print(f"   GEMINI_API_KEY configured: {bool(settings.gemini_api_key)}")
        if settings.gemini_api_key:
            key_val = settings.gemini_api_key.get_secret_value()
            print(f"   Key prefix: {key_val[:8]}...")
    else:
        print(f"✅ Using real Gemini embeddings (dimension={provider.dimension})")

    async with AsyncSession(engine) as session:
        # Clear old mock data
        await clear_old_data(session)

        # Re-ingest with real embeddings
        print("\n🚀 Starting ingestion pipeline...")
        print("   This will take 2-5 minutes for a full movie SRT...")

        pipeline = IngestionPipeline(db_session=session, embedding_provider=provider)

        result = await pipeline.ingest_asset(
            movie_id=MOVIE_ID,
            raw_content=srt_content,
            source_type="srt",
            auto_publish=True,
            actor="cli-ingestion",
        )
        # Pipeline uses flush() designed for FastAPI sessions — must commit explicitly here
        await session.commit()
        print("   ✅ Ingestion committed to database.")

    print("\n" + "=" * 60)
    print("✅ Ingestion complete!")
    print(f"   Content Version ID : {result.content_version_id}")
    print(f"   Version Number     : {result.version_number}")
    print(f"   Subtitle Cues      : {result.cue_count:,}")
    print(f"   Semantic Chunks    : {result.chunk_count:,}")
    print(f"   Duration           : {result.duration_seconds:.0f}s ({result.duration_seconds/60:.1f} min)")
    print(f"   Processing Status  : {result.processing_status}")
    print(f"   Active/Published   : {result.is_active}")
    print(f"   Time Elapsed       : {result.elapsed_milliseconds:.0f}ms")
    print("=" * 60)
    print("\n🎬 AI companion is ready. Restart the FastAPI server to reload config.")


if __name__ == "__main__":
    asyncio.run(main())
