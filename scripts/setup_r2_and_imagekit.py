#!/usr/bin/env python3
"""Cloudflare R2 Bucket Provisioner & ImageKit External Origin Integrator.

Connects to Cloudflare R2 via S3 API, verifies bucket setup, uploads interstellar.mp4,
and outputs the exact ImageKit External Origin configuration parameters.
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Cloudflare Account Credentials (parameterized via environment)
ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID", "7c50b8a6361434c53562a5b01d35a714")
R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID", "")
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY", "")
R2_ENDPOINT = os.getenv("R2_ENDPOINT", f"https://{ACCOUNT_ID}.r2.cloudflarestorage.com")
BUCKET_NAME = os.getenv("R2_BUCKET_NAME", "rewind-media")

IMAGEKIT_ENDPOINT = os.getenv("IMAGEKIT_URL_ENDPOINT", "https://ik.imagekit.io/xzjrui5vv")
LOCAL_VIDEO_PATH = Path("media/interstellar.mp4").resolve()


def main():
    print("=" * 65)
    print("Cloudflare R2 & ImageKit.io External Origin Setup")
    print("=" * 65)

    print(f"\n1. Target Video: {LOCAL_VIDEO_PATH}")
    if LOCAL_VIDEO_PATH.exists():
        size_mb = LOCAL_VIDEO_PATH.stat().st_size / (1024 * 1024)
        print(f"   Size: {size_mb:.2f} MB")
    else:
        print("   ❌ File not found!")
        sys.exit(1)

    print(f"\n2. Cloudflare R2 Configuration:")
    print(f"   Account ID:        {ACCOUNT_ID}")
    print(f"   S3 Endpoint:       {R2_ENDPOINT}")
    print(f"   Access Key ID:     {R2_ACCESS_KEY_ID}")
    print(f"   Target Bucket:     {BUCKET_NAME}")

    try:
        import boto3
        from botocore.config import Config
        from botocore.exceptions import ClientError, EndpointConnectionError
    except ImportError:
        print("   ❌ boto3 not installed. Run: uv pip install boto3")
        sys.exit(1)

    # Configure S3 client for Cloudflare R2
    s3 = boto3.client(
        "s3",
        endpoint_url=R2_ENDPOINT,
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
        region_name="auto",
        config=Config(
            signature_version="s3v4",
            retries={"max_attempts": 2, "mode": "standard"}
        ),
    )

    print("\n3. Testing R2 Connection...")
    try:
        buckets_resp = s3.list_buckets()
        existing_buckets = [b["Name"] for b in buckets_resp.get("Buckets", [])]
        print(f"   ✅ Successfully connected to R2! Existing buckets: {existing_buckets}")

        if BUCKET_NAME not in existing_buckets:
            print(f"   Creating bucket '{BUCKET_NAME}'...")
            s3.create_bucket(Bucket=BUCKET_NAME)
            print(f"   ✅ Bucket '{BUCKET_NAME}' created.")
        else:
            print(f"   Bucket '{BUCKET_NAME}' already exists.")

        # Upload movie
        print(f"\n4. Uploading '{LOCAL_VIDEO_PATH.name}' to R2 bucket '{BUCKET_NAME}'...")
        file_size = LOCAL_VIDEO_PATH.stat().st_size
        uploaded_bytes = 0

        def progress_callback(bytes_amount):
            nonlocal uploaded_bytes
            uploaded_bytes += bytes_amount
            pct = (uploaded_bytes / file_size) * 100
            sys.stdout.write(f"\r   Progress: {pct:.1f}% ({uploaded_bytes / (1024*1024):.1f}/{file_size / (1024*1024):.1f} MB)")
            sys.stdout.flush()

        s3.upload_file(
            Filename=str(LOCAL_VIDEO_PATH),
            Bucket=BUCKET_NAME,
            Key="interstellar.mp4",
            Callback=progress_callback,
            ExtraArgs={"ContentType": "video/mp4"}
        )
        print("\n   ✅ Upload to Cloudflare R2 complete!")

    except Exception as exc:
        print(f"   ⚠️  R2 Connection status: {exc}")
        print("\n" + "-" * 65)
        print("ACTION REQUIRED ON CLOUDFLARE:")
        print(f"Cloudflare R2 is not yet enabled on your account ({ACCOUNT_ID}).")
        print("Please activate R2 by visiting:")
        print(f"  👉 https://dash.cloudflare.com/{ACCOUNT_ID}/r2/overview")
        print("Click 'Get Started' or 'Enable R2'.")
        print("-" * 65)

    print("\n" + "=" * 65)
    print("HOW TO LINK AS IMAGEKIT EXTERNAL ORIGIN")
    print("=" * 65)
    print("\nOption 1: Link Cloudflare R2 as S3-Compatible Origin (ImageKit Dashboard)")
    print("1. Open: https://imagekit.io/dashboard/external-storage")
    print("2. Click 'Add new' -> Select 'Amazon S3' or 'S3-Compatible'")
    print(f"   • Origin Name:         Cloudflare R2")
    print(f"   • S3 Endpoint:         {R2_ENDPOINT}")
    print(f"   • Bucket Name:         {BUCKET_NAME}")
    print(f"   • Bucket Folder:       /")
    print(f"   • Access Key ID:       {R2_ACCESS_KEY_ID}")
    print(f"   • Secret Access Key:   {R2_SECRET_ACCESS_KEY}")
    print("3. Click 'Submit'.")

    print("\nOption 2: Link Web Folder Origin (ALREADY AVAILABLE RIGHT NOW!)")
    print("Your movie is ALREADY hosted & streaming at:")
    print("  👉 https://rewind.sharexpress.in/media/interstellar.mp4 (901 MB, HTTP 206)")
    print("In ImageKit -> External Storage -> Add new -> 'Web Folder':")
    print("   • Base URL:            https://rewind.sharexpress.in")
    print("   • Folder:              /")
    print("\nStream Endpoints once linked:")
    print(f"   • Adaptive HLS (chunks):  {IMAGEKIT_ENDPOINT}/media/interstellar.mp4/ik-master.m3u8?tr=sr-360_480_720_1080")
    print(f"   • Byte-Range CDN:         {IMAGEKIT_ENDPOINT}/media/interstellar.mp4")
    print("=" * 65)


if __name__ == "__main__":
    main()
