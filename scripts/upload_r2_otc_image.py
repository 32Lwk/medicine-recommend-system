#!/usr/bin/env python3
"""R2 に OTC 画像を 1 件アップロード（S3 互換 API + boto3）。"""
from __future__ import annotations

import argparse
import mimetypes
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None  # type: ignore


def _load_env() -> None:
    env_path = ROOT / ".env"
    if load_dotenv and env_path.is_file():
        load_dotenv(env_path, override=False)


def upload_file(slug: str, file_path: Path, *, content_type: str | None = None) -> str:
    import boto3

    bucket = os.getenv("R2_BUCKET", "medicine-recommend-otc-images")
    endpoint = os.getenv("R2_S3_ENDPOINT", "").strip()
    access_key = os.getenv("R2_ACCESS_KEY_ID", "").strip()
    secret_key = os.getenv("R2_SECRET_ACCESS_KEY", "").strip()
    if not all([endpoint, access_key, secret_key]):
        raise SystemExit("Set R2_S3_ENDPOINT, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY in .env")

    ext = file_path.suffix.lstrip(".") or "webp"
    key = f"otc/{slug}.{ext}"
    ctype = content_type or mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"

    client = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name="auto",
    )
    body = file_path.read_bytes()
    client.put_object(Bucket=bucket, Key=key, Body=body, ContentType=ctype)
    public_url = f"https://images.yutok.dev/{key}"
    return public_url


def _write_minimal_png(path: Path) -> None:
    """1x1 PNG（テスト用）。"""
    import base64

    raw = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    )
    path.write_bytes(raw)


def main() -> int:
    parser = argparse.ArgumentParser(description="Upload OTC image to Cloudflare R2")
    parser.add_argument("slug", help="object slug without extension (e.g. test)")
    parser.add_argument(
        "file",
        nargs="?",
        help="local file path (default: generate minimal PNG)",
    )
    args = parser.parse_args()
    _load_env()

    if args.file:
        src = Path(args.file)
        if not src.is_file():
            raise SystemExit(f"file not found: {src}")
    else:
        src = ROOT / "scripts" / ".r2-upload-tmp-test.png"
        _write_minimal_png(src)

    url = upload_file(args.slug, src)
    print(f"Uploaded: {url}")
    print(f"Verify: curl -sI {url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
