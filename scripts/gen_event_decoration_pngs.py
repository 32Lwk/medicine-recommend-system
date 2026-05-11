#!/usr/bin/env python3
"""開発用: 行事装飾の淡色 PNG（8x8）を static/img/events/ に生成する。本番では API を呼ばない。"""
from __future__ import annotations

import struct
import zlib
from pathlib import Path


def write_rgba_png(path: Path, width: int, height: int, rgba: tuple[int, int, int, int]) -> None:
    r, g, b, a = rgba
    sig = b"\x89PNG\r\n\x1a\n"

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    row = bytes([0]) + bytes([r, g, b, a] * width)
    raw = row * height
    idat = zlib.compress(raw, 9)
    data = sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def main() -> None:
    root = Path(__file__).resolve().parents[1] / "static" / "img" / "events"
    specs = [
        ("tanabata", "tanabata-bamboo.png", (180, 230, 200, 255)),
        ("tanabata", "tanabata-streamer.png", (220, 210, 255, 255)),
        ("keiro", "keiro-carnation-soft.png", (255, 200, 210, 255)),
        ("keiro", "keiro-gift-soft.png", (255, 235, 220, 255)),
        ("halloween", "halloween-moon-soft.png", (255, 230, 200, 255)),
        ("halloween", "halloween-star-soft.png", (240, 220, 255, 255)),
        ("shichigosan", "shichigosan-chouchin-soft.png", (255, 220, 200, 255)),
        ("shichigosan", "shichigosan-motif-soft.png", (255, 245, 230, 255)),
    ]
    for sub, name, rgba in specs:
        write_rgba_png(root / sub / name, 8, 8, rgba)
    print("wrote", len(specs), "files under", root)


if __name__ == "__main__":
    main()
