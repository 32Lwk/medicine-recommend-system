#!/usr/bin/env python3
"""Cloudflare CDN キャッシュをパージ（R2 カスタムドメイン images.yutok.dev）。"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from urllib.parse import quote

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None  # type: ignore

DEFAULT_HOST = "https://images.yutok.dev"


def _load_env() -> None:
    env_path = ROOT / ".env"
    if load_dotenv and env_path.is_file():
        load_dotenv(env_path, override=False)


def _build_urls(slug: str, *, ext: str = "webp") -> list[str]:
    raw = f"{DEFAULT_HOST}/otc/{slug}.{ext}"
    encoded = f"{DEFAULT_HOST}/otc/{quote(slug, safe='')}.{ext}"
    return list(dict.fromkeys([raw, encoded]))


def purge_urls(urls: list[str]) -> dict:
    token = os.getenv("CLOUDFLARE_API_TOKEN", "").strip()
    zone_id = os.getenv("CLOUDFLARE_ZONE_ID", "").strip()
    if not token or not zone_id:
        raise RuntimeError(
            "Set CLOUDFLARE_API_TOKEN and CLOUDFLARE_ZONE_ID in .env to purge CDN cache"
        )

    resp = requests.post(
        f"https://api.cloudflare.com/client/v4/zones/{zone_id}/purge_cache",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json={"files": urls},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    if not data.get("success"):
        raise RuntimeError(f"Cloudflare purge failed: {data}")
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description="Purge OTC image URLs from Cloudflare CDN")
    parser.add_argument("slug", help="product slug (e.g. スカイブブロンのどスプレー)")
    parser.add_argument("--ext", default="webp")
    args = parser.parse_args()
    _load_env()

    urls = _build_urls(args.slug, ext=args.ext)
    try:
        result = purge_urls(urls)
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc), "urls": urls}, ensure_ascii=False), file=sys.stderr)
        return 1

    print(json.dumps({"ok": True, "urls": urls, "result": result}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
