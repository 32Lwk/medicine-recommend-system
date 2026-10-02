#!/usr/bin/env python3
"""Render the 2.5D sprite avatar offline with the same transforms as sage_avatar_sprite.js.

Used to check seams, holes and left-behind parts at extreme poses without a browser.

  python scripts/live2d_preview_poses.py                 # contact sheet of extreme poses (cast b)
  python scripts/live2d_preview_poses.py --cast a        # another character
  python scripts/live2d_preview_poses.py --bg normal     # stage background instead of magenta
  python scripts/live2d_preview_poses.py --crop face     # zoom on the head
  python scripts/live2d_preview_poses.py --set gestures  # body variants + hand overlays

Output: %TEMP%/sage_sprite_debug/{cast}_{poses|gestures}_<bg>_<crop>.png
"""
from __future__ import annotations

import argparse
import json
import math
import tempfile
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SPRITE = ROOT / "static/live2d/sage_cast_b/sprite"


def sprite_dir(cast: str) -> Path:
    return ROOT / f"static/live2d/sage_cast_{cast}/sprite"

# keep in sync with sage_avatar_sprite.js
PARALLAX = {
    "head": (8, 6), "face": (4, 3), "features": (14, 11), "hair": (2, 2),
    "ear_l": (0, -1), "ear_r": (0, -1),
}
RIG_EXTEND = (0.025, 0.05)  # .sage-avatar__rig inset: sides -2.5%, bottom -5%
BODY_IN_END, BASE_OUT_START, BASE_OUT_END = 0.25, 0.15, 0.4  # gesture body swap by amount

POSES: list[tuple[str, str, dict]] = [
    ("neutral", "通常", {}),
    ("neutral", "左を見る", {"angleX": -25, "angleY": 2}),
    ("neutral", "右を見る", {"angleX": 25, "angleY": 2}),
    ("neutral", "深くうなずき", {"angleY": -25, "lean": 0.15}),
    ("neutral", "見上げ", {"angleY": 10, "lean": -0.25}),
    ("thinking", "首かしげ+思案", {"angleZ": 20, "angleX": 13, "angleY": 6}),
    ("confused", "困惑", {"angleZ": -11, "angleY": 3}),
    ("neutral", "首振り", {"angleX": -18}),
    ("sorry", "お辞儀", {"bow": 1, "angleY": -29, "angleZ": -3}),
    ("serious", "前のめり", {"lean": 1.3, "angleY": -6}),
    ("cheer", "弾む", {"hop": 22, "angleY": 7}),
    ("shy", "照れ", {"angleX": -14, "angleY": -7, "angleZ": 7, "bodyAngleZ": 0.6}),
]

# --set gestures: every hand overlay, plus combinations with big motions and a half-entered frame
GESTURE_POSES: list[tuple[str, str, dict]] = [
    ("smile", "手を振る", {"gesture": "wave", "sway": 9}),
    ("empathy", "手のひら差し出し", {"gesture": "explain", "angleZ": 4, "angleY": -3, "lean": 0.15}),
    ("serious", "人差し指", {"gesture": "point", "lean": 0.3}),
    ("worry", "胸に手", {"gesture": "chest", "angleZ": 5, "angleY": -3, "lean": 0.25}),
    ("thinking", "あごに手", {"gesture": "chin", "angleZ": 7, "angleX": 8, "angleY": 6}),
    ("cheer", "こぶし+弾む", {"gesture": "fist", "lift": 26, "hop": 22}),
    ("sorry", "両手+お辞儀", {"gesture": "bow_hands", "bow": 1, "angleY": -29, "angleZ": -3}),
    ("relief", "OK", {"gesture": "ok", "sway": -3}),
    ("smile", "手を振る(入り途中)", {"gesture": "wave", "amount": 0.5}),
    ("thinking", "あごに手+首かしげ", {"gesture": "chin", "angleZ": 20, "angleX": 13, "angleY": 6}),
    ("neutral", "手を振る+左を見る", {"gesture": "wave", "angleX": -25, "sway": -9}),
    ("neutral", "OK+右を見る", {"gesture": "ok", "angleX": 25}),
]


def mat(a=1.0, b=0.0, c=0.0, d=1.0, e=0.0, f=0.0) -> np.ndarray:
    return np.array([[a, c, e], [b, d, f], [0, 0, 1]], np.float64)


def translate(x: float, y: float) -> np.ndarray:
    return mat(e=x, f=y)


def rotate(deg: float) -> np.ndarray:
    r = math.radians(deg)
    return mat(math.cos(r), math.sin(r), -math.sin(r), math.cos(r))


def scale(sx: float, sy: float) -> np.ndarray:
    return mat(sx, 0, 0, sy)


def css(origin: tuple[float, float], *ops: np.ndarray) -> np.ndarray:
    m = translate(*origin)
    for op in ops:
        m = m @ op
    return m @ translate(-origin[0], -origin[1])


def load(manifest: dict, spec: dict, cw: int, ch: int, margin: int = 0) -> np.ndarray:
    """Layer on a canvas grown by ``margin`` on every side (gestures reach outside the canvas)."""
    img = np.asarray(Image.open(SPRITE / spec["src"]).convert("RGBA"), np.float32) / 255.0
    layer = np.zeros((ch + 2 * margin, cw + 2 * margin, 4), np.float32)
    x, y = spec["x"] + margin, spec["y"] + margin
    h, w = img.shape[:2]
    sx0, sy0 = max(-x, 0), max(-y, 0)
    dx0, dy0 = max(x, 0), max(y, 0)
    ww = min(w - sx0, layer.shape[1] - dx0)
    hh = min(h - sy0, layer.shape[0] - dy0)
    layer[dy0:dy0 + hh, dx0:dx0 + ww] = img[sy0:sy0 + hh, sx0:sx0 + ww]
    return layer


GESTURE_MARGIN = 300


def load_layers(manifest: dict) -> dict:
    cw, ch = manifest["canvas"]["width"], manifest["canvas"]["height"]
    layers: dict = {k: load(manifest, v, cw, ch) for k, v in manifest["parts"].items()}
    for key, spec in manifest["layers"]["expression"].items():
        layers[("expression", key)] = load(manifest, spec, cw, ch)
    for key, spec in manifest["layers"].get("gesture", {}).items():
        layers[("gesture_body", key)] = load(manifest, spec["body"], cw, ch)
        if "hand" in spec:
            layers[("gesture_hand", key)] = load(manifest, spec["hand"], cw, ch, GESTURE_MARGIN)
    return layers


def pose_matrices(p: dict, cw: int, ch: int, pivot: tuple[float, float]) -> dict:
    tx, ty = p.get("angleX", 0) / 30, p.get("angleY", 0) / 30
    bow, lean, breath = p.get("bow", 0), p.get("lean", 0), p.get("breath", 0)
    rig_scale = 1 + lean * 0.07 + bow * 0.02
    rig = css((cw / 2, ch), translate(0, bow * 70 + lean * 18 - p.get("hop", 0)),
              rotate(p.get("bodyAngleZ", 0)), scale(rig_scale, rig_scale * (1 + breath * 0.008)))
    head = css(pivot, translate(tx * PARALLAX["head"][0], -ty * PARALLAX["head"][1] - breath * 3 + bow * 10),
               rotate(p.get("angleZ", 0)), scale(1 - abs(tx) * 0.025, 1 - abs(ty) * 0.03))
    out = {"rig": rig, "head": rig @ head}
    for k in ("face", "features", "hair", "ear_l", "ear_r"):
        px, py = PARALLAX[k]
        out[k] = out["head"] @ translate(tx * px, -ty * py)
    return out


def over(dst: np.ndarray, src: np.ndarray) -> None:
    a = src[..., 3:4]
    dst[..., :3] = src[..., :3] * a + dst[..., :3] * (1 - a)
    dst[..., 3:4] = a + dst[..., 3:4] * (1 - a)


def render(manifest: dict, layers: dict, expr: str, p: dict, bg: tuple) -> np.ndarray:
    cw, ch = manifest["canvas"]["width"], manifest["canvas"]["height"]
    piv = manifest["pivot"]["neck"]
    ms = pose_matrices(p, cw, ch, (piv["x"], piv["y"]))
    out = np.zeros((ch, cw, 4), np.float32)
    out[..., :3] = np.array(bg, np.float32) / 255.0
    out[..., 3] = 1

    def put(img: np.ndarray, m: np.ndarray) -> None:
        warped = cv2.warpAffine(img, m[:2], (cw, ch), flags=cv2.INTER_LINEAR,
                                borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
        over(out, warped)

    key = p.get("gesture")
    spec = manifest["layers"].get("gesture", {}).get(key) if key else None
    amount = min(p.get("amount", 1.0), 1.0)
    clamp01 = lambda v: min(max(v, 0.0), 1.0)  # noqa: E731

    def put_faded(img: np.ndarray, m: np.ndarray, opacity: float) -> None:
        if opacity <= 0:
            return
        img = img.copy()
        img[..., 3] *= opacity
        put(img, m)

    for k in manifest["partOrder"]:
        if k == "body":
            cover = clamp01((amount - BASE_OUT_START) / (BASE_OUT_END - BASE_OUT_START))
            put_faded(layers["body"], ms["rig"], 1 - cover if spec else 1.0)
            if spec:
                put_faded(layers[("gesture_body", key)], ms["rig"], clamp01(amount / BODY_IN_END))
        elif k == "features":
            put(layers["features"], ms["features"])
            if (("expression", expr)) in layers:
                put(layers[("expression", expr)], ms["features"])
        else:
            put(layers[k], ms[k])
    if spec and ("gesture_hand", key) in layers:
        hs = spec["hand"]
        pv = (hs["pivot"]["x"], hs["pivot"]["y"])
        swing = p.get("swing", amount)
        g = css(pv, translate(0, hs.get("enterDrop", 0) * (1 - swing) - p.get("lift", 0)),
                rotate(hs.get("enterRot", 0) * (1 - swing) + p.get("sway", 0)))
        parent = ms["head"] if spec.get("attach") == "head" else ms["rig"]
        # the layer image is stored with a margin; undo it after the element transform
        m = parent @ g @ translate(-GESTURE_MARGIN, -GESTURE_MARGIN)
        warped = cv2.warpAffine(layers[("gesture_hand", key)], m[:2], (cw, ch), flags=cv2.INTER_LINEAR,
                                borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
        warped[..., 3] *= clamp01(amount / BODY_IN_END)
        over(out, warped)
    # visible box of .sage-avatar (rig extends past the root on the sides and bottom)
    vw = cw / (1 + 2 * RIG_EXTEND[0])
    x0 = int(round(vw * RIG_EXTEND[0]))
    return out[: int(round(ch / (1 + RIG_EXTEND[1]))), x0:x0 + int(round(vw))]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bg", choices=["magenta", "normal"], default="magenta")
    ap.add_argument("--crop", choices=["full", "face"], default="full")
    ap.add_argument("--cols", type=int, default=4)
    ap.add_argument("--tag", default="", help="suffix for the output file name")
    ap.add_argument("--set", choices=["poses", "gestures"], default="poses")
    ap.add_argument("--cast", default="b", choices=["a", "b", "c", "d"])
    args = ap.parse_args()

    global SPRITE
    SPRITE = sprite_dir(args.cast)
    manifest = json.loads((SPRITE / "manifest.json").read_text(encoding="utf-8"))
    layers = load_layers(manifest)

    bg = (255, 0, 255) if args.bg == "magenta" else (238, 242, 246)
    piv = manifest["pivot"]["neck"]
    tiles = []
    for expr, label, p in (GESTURE_POSES if args.set == "gestures" else POSES):
        img = render(manifest, layers, expr, p, bg)
        if args.crop == "face":
            fx, fy = int(piv["x"]), int(piv["y"])
            img = img[max(fy - 520, 0):fy + 160, max(fx - 340, 0):fx + 340]
        tile = Image.fromarray((np.clip(img[..., :3], 0, 1) * 255).astype(np.uint8))
        tile = tile.resize((tile.width // 2, tile.height // 2), Image.LANCZOS)
        draw = ImageDraw.Draw(tile)
        try:
            font = ImageFont.truetype("C:/Windows/Fonts/meiryo.ttc", 18)
        except OSError:
            font = ImageFont.load_default()
        draw.rectangle((0, 0, 170, 26), fill=(255, 255, 255))
        draw.text((4, 2), label, fill=(0, 0, 0), font=font)
        tiles.append(tile)
    cols = args.cols
    tw, th = tiles[0].size
    rows = math.ceil(len(tiles) / cols)
    sheet = Image.new("RGB", (cols * tw + (cols - 1) * 4, rows * th + (rows - 1) * 4), (255, 255, 255))
    for i, t in enumerate(tiles):
        sheet.paste(t, ((i % cols) * (tw + 4), (i // cols) * (th + 4)))
    out_dir = Path(tempfile.gettempdir()) / "sage_sprite_debug"
    out_dir.mkdir(exist_ok=True)
    name = "poses" if args.set == "poses" else "gestures"
    out = out_dir / f"{args.cast}_{name}_{args.bg}_{args.crop}{args.tag}.png"
    sheet.save(out)
    print(out)


if __name__ == "__main__":
    main()
