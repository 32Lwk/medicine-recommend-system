"""Assemble the static site for live2d.medicine.yutok.dev (Cloudflare Worker static assets).

Copies the avatar demo and its assets from static/ into workers/live2d-demo/public/.
The chat app is not touched; the demo page becomes index.html with root-relative paths
and server TTS disabled (the site has no /api/tts).

    python scripts/build_live2d_site.py
    cd workers/live2d-demo && npx wrangler deploy
"""
from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "static"
OUT = ROOT / "workers" / "live2d-demo" / "public"

FILES = [
    "css/scrollbar.css",
    "css/avatar.css",
    "js/avatar/sage_avatar.js",
    "js/avatar/sage_avatar_sprite.js",
]
DIRS = ["live2d/sage_cast_b/sprite"]

CONFIG_SCRIPT = "<script>window.SAGE_AVATAR_CONFIG = { serverTts: false };</script>\n"

HEADERS = """/*
  X-Robots-Tag: noindex, nofollow
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin
  X-Frame-Options: DENY

/live2d/*
  Cache-Control: public, max-age=3600
"""

ROBOTS = "User-agent: *\nDisallow: /\n"


def build() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)

    for rel in FILES:
        dst = OUT / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(STATIC / rel, dst)
    for rel in DIRS:
        shutil.copytree(STATIC / rel, OUT / rel)

    html = (STATIC / "dev" / "avatar_demo.html").read_text(encoding="utf-8")
    if "../" not in html or "<script src=" not in html:
        raise RuntimeError("avatar_demo.html layout changed; update build_live2d_site.py")
    html = html.replace('"../', '"/').replace("'../", "'/")
    html = html.replace("<script src=", CONFIG_SCRIPT + "<script src=", 1)
    (OUT / "index.html").write_text(html, encoding="utf-8")
    (OUT / "_headers").write_text(HEADERS, encoding="utf-8")
    (OUT / "robots.txt").write_text(ROBOTS, encoding="utf-8")

    files = [p for p in OUT.rglob("*") if p.is_file()]
    total = sum(p.stat().st_size for p in files)
    print(f"OK → {OUT} ({len(files)} files, {total / 1024:.0f} KB)")


if __name__ == "__main__":
    build()
