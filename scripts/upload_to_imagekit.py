#!/usr/bin/env python3
"""Upload movie to ImageKit.io and generate YouTube-style HLS / Byte-range streaming endpoints.

Usage:
    .venv/bin/python3 scripts/upload_to_imagekit.py \
        --private-key YOUR_PRIVATE_KEY \
        --public-key YOUR_PUBLIC_KEY \
        --url-endpoint https://ik.imagekit.io/YOUR_ID \
        --file media/interstellar.mp4
"""

import argparse
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load any .env variables
load_dotenv()

try:
    from imagekitio import ImageKit
except ImportError:
    print("Error: imagekitio package not found. Run: uv pip install imagekitio")
    sys.exit(1)


def parse_args():
    parser = argparse.ArgumentParser(description="Upload movie to ImageKit.io for YouTube-style chunked streaming.")
    parser.add_argument(
        "--file",
        type=str,
        default="media/interstellar.mp4",
        help="Path to the video file to upload (default: media/interstellar.mp4)"
    )
    parser.add_argument(
        "--private-key",
        type=str,
        default=os.getenv("IMAGEKIT_PRIVATE_KEY", ""),
        help="ImageKit Private API Key"
    )
    parser.add_argument(
        "--public-key",
        type=str,
        default=os.getenv("IMAGEKIT_PUBLIC_KEY", ""),
        help="ImageKit Public API Key"
    )
    parser.add_argument(
        "--url-endpoint",
        type=str,
        default=os.getenv("IMAGEKIT_URL_ENDPOINT", "https://ik.imagekit.io/xzjrui5vv"),
        help="ImageKit URL Endpoint (default: https://ik.imagekit.io/xzjrui5vv)"
    )
    parser.add_argument(
        "--folder",
        type=str,
        default="/movies/",
        help="Destination folder on ImageKit (default: /movies/)"
    )
    return parser.parse_args()


def main():
    args = parse_args()

    file_path = Path(args.file).resolve()
    if not file_path.exists():
        # Check alternative locations
        alt_paths = [
            Path("/Users/santushtkotai/Desktop/rewindAI/media/interstellar.mp4"),
            Path("/Users/santushtkotai/Downloads/interstellar.mp4"),
        ]
        found = False
        for p in alt_paths:
            if p.exists():
                file_path = p
                found = True
                break
        if not found:
            print(f"Error: Video file not found at {args.file}")
            sys.exit(1)

    file_size_mb = file_path.stat().st_size / (1024 * 1024)
    print(f"🎬 Found movie file: {file_path}")
    print(f"📦 File size: {file_size_mb:.2f} MB")

    if not args.private_key:
        print("\n⚠️  IMAGEKIT_PRIVATE_KEY is missing!")
        print("Please provide it via --private-key argument or set IMAGEKIT_PRIVATE_KEY in .env.")
        print(f"Current URL Endpoint: {args.url_endpoint}")
        print("\nGet your API keys from: https://imagekit.io/dashboard/developer/api-keys")
        sys.exit(2)

    print("\n🚀 Initializing ImageKit client...")
    imagekit = ImageKit(
        private_key=args.private_key,
        public_key=args.public_key,
        url_endpoint=args.url_endpoint
    )

    file_name = file_path.name
    print(f"Uploading '{file_name}' to ImageKit folder '{args.folder}'...")
    print("This may take several minutes depending on network bandwidth...")

    try:
        with open(file_path, "rb") as stream:
            upload_result = imagekit.files.upload(
                file=stream,
                file_name=file_name,
                folder=args.folder,
                use_unique_file_name=False,
                tags=["movie", "interstellar", "rewindAI"]
            )

        print("\n✅ Upload succeeded!")
        cdn_url = upload_result.url
        print(f"🌐 ImageKit Raw CDN URL: {cdn_url}")

        # Construct YouTube-style Adaptive Bitrate Streaming (HLS) URL:
        # Format: {endpoint}/{folder}/{file_name}/ik-master.m3u8?tr=sr-360_480_720_1080
        hls_url = f"{cdn_url}/ik-master.m3u8?tr=sr-360_480_720_1080"
        dash_url = f"{cdn_url}/ik-master.mpd?tr=sr-360_480_720_1080"

        print("\n📺 YouTube-Style Chunked Streaming Endpoints:")
        print(f"  • HLS Adaptive Manifest (chunks):  {hls_url}")
        print(f"  • MPEG-DASH Manifest (chunks):     {dash_url}")
        print(f"  • Byte-Range CDN (HTTP 206):       {cdn_url}")

        # Update environment file or local settings
        env_path = Path(".env")
        lines = []
        if env_path.exists():
            lines = env_path.read_text().splitlines()
        
        # Upsert keys
        def upsert_var(var_name, val):
            nonlocal lines
            found = False
            for i, line in enumerate(lines):
                if line.startswith(f"{var_name}="):
                    lines[i] = f"{var_name}={val}"
                    found = True
                    break
            if not found:
                lines.append(f"{var_name}={val}")

        upsert_var("IMAGEKIT_PRIVATE_KEY", args.private_key)
        upsert_var("IMAGEKIT_PUBLIC_KEY", args.public_key)
        upsert_var("IMAGEKIT_URL_ENDPOINT", args.url_endpoint)
        upsert_var("REWIND_STREAM_URL", hls_url)
        upsert_var("REWIND_STREAM_RAW_URL", cdn_url)

        env_path.write_text("\n".join(lines) + "\n")
        print(f"\n💾 Saved stream configuration to {env_path.resolve()}")

    except Exception as exc:
        print(f"\n❌ Upload failed: {exc}")
        print("\nNote: On ImageKit Free accounts, the maximum single video file size is 100MB.")
        print("For files > 100MB, an ImageKit Lite (300MB) or Pro/Enterprise plan (2GB+) is required,")
        print("or link an external S3/R2 storage bucket in your ImageKit Origin settings.")
        sys.exit(1)


if __name__ == "__main__":
    main()
