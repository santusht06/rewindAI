"""Media storage provider interface and local/cloud storage adapters.

Adheres to:
- REWIND-REQ-018 (FR-02: Upload and assets, stored in object storage)
- REWIND-REQ-019 (Section 1: Processing model, MediaStorageProvider abstraction)
- ADR-008: Asynchronous Media Processing Pipeline & Storage Provider
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Protocol


class MediaStorageProvider(Protocol):
    """Abstract protocol for binary media object storage (local, MinIO, S3, Cloudinary)."""

    async def store(
        self, file_name: str, file_bytes: bytes, content_type: str = "video/mp4"
    ) -> tuple[str, str]:
        """Store binary asset and return (storage_path, access_url)."""
        ...

    async def get(self, storage_path: str) -> bytes:
        """Retrieve stored binary content."""
        ...

    async def delete(self, storage_path: str) -> bool:
        """Remove binary asset from storage."""
        ...

    def get_url(self, storage_path: str) -> str:
        """Get publicly resolvable or proxied access URL."""
        ...


class LocalStorageProvider:
    """Local filesystem storage provider with static/proxied serving."""

    def __init__(self, base_dir: str | Path | None = None, url_prefix: str = "/media") -> None:
        if base_dir is None:
            # Check environment or default to local ./media directory
            env_dir = os.getenv("REWIND_MEDIA_DIR", "./media")
            self.base_dir = Path(env_dir).resolve()
        else:
            self.base_dir = Path(base_dir).resolve()

        self.url_prefix = url_prefix.rstrip("/")
        self.base_dir.mkdir(parents=True, exist_ok=True)

    async def store(
        self, file_name: str, file_bytes: bytes, content_type: str = "video/mp4"
    ) -> tuple[str, str]:
        # Sanitize filename and prevent directory traversal
        safe_name = Path(file_name).name
        target_path = self.base_dir / safe_name
        target_path.parent.mkdir(parents=True, exist_ok=True)

        target_path.write_bytes(file_bytes)
        rel_path = str(target_path.relative_to(self.base_dir))
        url = self.get_url(rel_path)
        return str(target_path), url

    async def get(self, storage_path: str) -> bytes:
        path = Path(storage_path)
        if not path.is_absolute():
            path = self.base_dir / path
        if not path.exists():
            raise FileNotFoundError(f"Media asset not found: {storage_path}")
        return path.read_bytes()

    async def delete(self, storage_path: str) -> bool:
        path = Path(storage_path)
        if not path.is_absolute():
            path = self.base_dir / path
        if path.exists():
            path.unlink()
            return True
        return False

    def get_url(self, storage_path: str) -> str:
        safe_name = Path(storage_path).name
        return f"{self.url_prefix}/{safe_name}"


class ImageKitStorageProvider:
    """ImageKit.io cloud media storage provider supporting YouTube-style HLS and CDN byte-range delivery."""

    def __init__(
        self,
        url_endpoint: str | None = None,
        private_key: str | None = None,
        public_key: str | None = None,
        folder: str = "/movies/",
    ) -> None:
        self.url_endpoint = (
            url_endpoint
            or os.getenv("IMAGEKIT_URL_ENDPOINT")
            or "https://ik.imagekit.io/xzjrui5vv"
        ).rstrip("/")
        self.private_key = private_key or os.getenv("IMAGEKIT_PRIVATE_KEY", "")
        self.public_key = public_key or os.getenv("IMAGEKIT_PUBLIC_KEY", "")
        self.folder = folder

    def get_url(self, storage_path: str) -> str:
        safe_name = Path(storage_path).name
        return f"{self.url_endpoint}{self.folder}{safe_name}"

    def get_hls_url(self, storage_path: str, resolutions: str = "360_480_720_1080") -> str:
        """Generates YouTube-style Adaptive Bitrate Streaming (HLS) master manifest."""
        base_url = self.get_url(storage_path)
        return f"{base_url}/ik-master.m3u8?tr=sr-{resolutions}"

    async def store(
        self, file_name: str, file_bytes: bytes, content_type: str = "video/mp4"
    ) -> tuple[str, str]:
        if not self.private_key:
            raise RuntimeError("IMAGEKIT_PRIVATE_KEY is not configured.")
        try:
            from imagekitio import ImageKit
        except ImportError:
            raise RuntimeError("imagekitio library is not installed.")

        client = ImageKit(
            private_key=self.private_key,
            public_key=self.public_key,
            url_endpoint=self.url_endpoint,
        )
        safe_name = Path(file_name).name
        res = client.files.upload(
            file=file_bytes,
            file_name=safe_name,
            folder=self.folder,
            use_unique_file_name=False,
        )
        return res.file_id, res.url

    async def get(self, storage_path: str) -> bytes:
        raise NotImplementedError("Direct binary get from ImageKit not required; stream via CDN URL.")

    async def delete(self, storage_path: str) -> bool:
        return True


# Global/default factory
_default_storage: MediaStorageProvider | None = None


def get_media_storage() -> MediaStorageProvider:
    """Get configured media storage provider instance."""
    global _default_storage
    if _default_storage is None:
        provider_type = os.getenv("MEDIA_STORAGE_BACKEND", "local").lower()
        if provider_type == "imagekit":
            _default_storage = ImageKitStorageProvider()
        else:
            _default_storage = LocalStorageProvider()
    return _default_storage


def set_media_storage(provider: MediaStorageProvider) -> None:
    """Override media storage provider (useful for testing)."""
    global _default_storage
    _default_storage = provider
