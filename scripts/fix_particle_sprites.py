#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""開発用: 粒子 PNG のアルファ掃除・リサイズ、夏花火の再生成。

本番では API を呼ばない。実行例:
  python scripts/fix_particle_sprites.py
"""
from __future__ import annotations

import math
import struct
import zlib
from pathlib import Path

MAX_DIM = 64
ALPHA_CUTOFF = 16
DARK_RGB = 50


def read_rgba_png(path: Path) -> tuple[int, int, list[tuple[int, int, int, int]]]:
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"not a PNG: {path}")
    pos = 8
    w = h = None
    idat = b""
    while pos < len(data):
        ln = struct.unpack(">I", data[pos : pos + 4])[0]
        typ = data[pos + 4 : pos + 8]
        chunk = data[pos + 8 : pos + 8 + ln]
        if typ == b"IHDR":
            w, h = struct.unpack(">II", chunk[:8])
            bit_depth, color_type = chunk[8], chunk[9]
            if not (bit_depth == 8 and color_type == 6):
                raise ValueError(f"expected 8-bit RGBA PNG: {path}")
        elif typ == b"IDAT":
            idat += chunk
        elif typ == b"IEND":
            break
        pos += 12 + ln
    if w is None or h is None:
        raise ValueError(f"missing IHDR: {path}")

    raw = zlib.decompress(idat)
    pixels: list[tuple[int, int, int, int]] = []
    i = 0
    for _y in range(h):
        i += 1
        row = raw[i : i + w * 4]
        i += w * 4
        for j in range(0, len(row), 4):
            pixels.append(tuple(row[j : j + 4]))  # type: ignore[misc]
    return w, h, pixels


def write_rgba_png(path: Path, width: int, height: int, pixels: list[tuple[int, int, int, int]]) -> None:
    if len(pixels) != width * height:
        raise ValueError("pixel count mismatch")
    sig = b"\x89PNG\r\n\x1a\n"

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    rows = []
    for y in range(height):
        row = bytes([0])
        base = y * width
        for x in range(width):
            r, g, b, a = pixels[base + x]
            row += bytes((r, g, b, a))
        rows.append(row)
    raw = b"".join(rows)
    idat = zlib.compress(raw, 9)
    data = sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def clean_pixel(r: int, g: int, b: int, a: int) -> tuple[int, int, int, int]:
    if a < ALPHA_CUTOFF:
        return (0, 0, 0, 0)
    if r < DARK_RGB and g < DARK_RGB and b < DARK_RGB:
        return (0, 0, 0, 0)
    return (r, g, b, a)


def resize_rgba(
    w: int, h: int, pixels: list[tuple[int, int, int, int]], max_dim: int
) -> tuple[int, int, list[tuple[int, int, int, int]]]:
    if max(w, h) <= max_dim:
        return w, h, pixels
    scale = max_dim / max(w, h)
    nw = max(1, int(round(w * scale)))
    nh = max(1, int(round(h * scale)))

    def at(sx: float, sy: float) -> tuple[int, int, int, int]:
        x = min(w - 1, max(0, int(sx)))
        y = min(h - 1, max(0, int(sy)))
        return pixels[y * w + x]

    out: list[tuple[int, int, int, int]] = []
    for y in range(nh):
        sy = (y + 0.5) * h / nh - 0.5
        for x in range(nw):
            sx = (x + 0.5) * w / nw - 0.5
            r, g, b, a = at(sx, sy)
            if a < ALPHA_CUTOFF:
                out.append((0, 0, 0, 0))
                continue
            ar = ag = ab = aa = 0
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    pr, pg, pb, pa = at(sx + dx * 0.45, sy + dy * 0.45)
                    if pa < ALPHA_CUTOFF:
                        continue
                    ar += pr * pa
                    ag += pg * pa
                    ab += pb * pa
                    aa += pa
            if aa < 1:
                out.append((0, 0, 0, 0))
            else:
                out.append(
                    (
                        min(255, int(ar / aa)),
                        min(255, int(ag / aa)),
                        min(255, int(ab / aa)),
                        min(255, int(aa / 9)),
                    )
                )
    return nw, nh, out


def make_firework_rgba(size: int = 64) -> list[tuple[int, int, int, int]]:
    pixels = [(0, 0, 0, 0)] * (size * size)
    cx = cy = (size - 1) / 2.0

    def put(x: int, y: int, rgba: tuple[int, int, int, int]) -> None:
        if 0 <= x < size and 0 <= y < size:
            i = y * size + x
            old = pixels[i]
            oa = old[3] / 255.0
            na = rgba[3] / 255.0
            if na <= 0:
                return
            out_a = na + oa * (1 - na)
            if out_a <= 0:
                return
            def blend(cn: int, co: int) -> int:
                return int((cn * na + co * oa * (1 - na)) / out_a)

            pixels[i] = (
                blend(rgba[0], old[0]),
                blend(rgba[1], old[1]),
                blend(rgba[2], old[2]),
                min(255, int(out_a * 255)),
            )

    palette = [
        (255, 200, 220, 230),
        (180, 230, 255, 220),
        (255, 240, 180, 220),
        (255, 255, 255, 200),
    ]
    for deg in range(0, 360, 12):
        rad = math.radians(deg)
        for dist in (6, 10, 14, 18, 22):
            x = int(cx + math.cos(rad) * dist)
            y = int(cy + math.sin(rad) * dist)
            put(x, y, palette[(deg // 12) % len(palette)])
            put(x + 1, y, palette[(deg // 12 + 1) % len(palette)])
    for _ in range(18):
        ang = (_ * 137.5) % 360
        rad = math.radians(ang)
        d = 4 + (_ % 5)
        x = int(cx + math.cos(rad) * d)
        y = int(cy + math.sin(rad) * d)
        put(x, y, (255, 255, 255, 180))
    put(int(cx), int(cy), (255, 255, 255, 240))
    return [clean_pixel(*p) for p in pixels]


def process_file(path: Path, *, skip_resize: bool = False) -> None:
    w, h, pixels = read_rgba_png(path)
    pixels = [clean_pixel(*p) for p in pixels]
    if not skip_resize:
        w, h, pixels = resize_rgba(w, h, pixels, MAX_DIM)
    write_rgba_png(path, w, h, pixels)


def main() -> None:
    root = Path(__file__).resolve().parents[1] / "static" / "img" / "particles"
    firework = root / "summer" / "firework-soft.png"
    write_rgba_png(firework, 64, 64, make_firework_rgba(64))

    for png in sorted(root.rglob("*.png")):
        if png == firework:
            continue
        process_file(png)
        print("fixed", png.relative_to(root.parent.parent))

    print("regenerated", firework.relative_to(root.parent.parent))


if __name__ == "__main__":
    main()
