#!/usr/bin/env python3
"""Build 2.5D sprite avatar assets for Character B (stand-in until the Cubism model exists).

1. Base frame ``sage-b-mouth-closed.jpg`` is split into parts:
   body (neck under the chin is filled) / ear_l / ear_r / face (features inpainted) /
   features (face interior) / hair. The browser moves them with different parallax,
   which gives nods, tilts and head turns.
2. Every other concept frame is aligned to the base (SIFT + RANSAC similarity on the head)
   and cut into feathered patches: expressions (face interior), mouths, closed eyes.
3. Half-open eyes are synthesised per expression by sliding the upper lash line down
   (the image model does not close eyes far enough).

Usage:
  python scripts/live2d_build_sprite_b.py [--debug]

Dev-only dependencies: opencv-python, numpy, Pillow
Output: static/live2d/sage_cast_b/sprite/{*.webp, manifest.json}
"""

from __future__ import annotations

import argparse
import json
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
EXPR = ROOT / "static/img/live2d/concept/whitecoat/cast-unified/expressions-b"
OUT = ROOT / "static/live2d/sage_cast_b/sprite"

BASE_SRC = "sage-b-mouth-closed.jpg"

# Base-frame pixel coordinates (1024x1024).
HEAD_RECT = (220, 150, 840, 830)  # keypoints used for alignment
JAW_X = (336, 714)  # columns where the jaw line separates face and neck
JAW_PRIOR = ((336, 612), (520, 806), (714, 652))  # left end, chin, right end
EAR_SPLIT_Y = 640  # outside JAW_X: head above, body below
# The right ear joins the cheek without an outline; this polyline separates them.
EAR_BARRIERS = [np.array([(743, 392), (738, 520), (737, 612)], np.int32)]
NECK_PIVOT = (560, 745)
# Where the head is cut out of the body, this zone is repainted as neck shadow so that the
# face sliding sideways never reveals a hole (both jaw corners included).
NECK_FILL = np.array([(330, 560), (738, 560), (738, 690), (718, 840), (400, 840), (330, 700)], np.int32)
EYES = {"l": ((398, 460), (84, 46)), "r": ((612, 442), (84, 46))}  # center, (rx, ry)
MOUTH = ((518, 668), (104, 60))
MAX_LASH = 16  # px; upper lash line thickness cap for synthesised eyelids
INTERIOR_ERODE = 20
FEATHER = 7.0


@dataclass(frozen=True)
class Frame:
    key: str
    src: str
    label: str
    own_eyes: bool = True  # False: expression keeps base eyes (only brows/mouth change)


EXPRESSIONS: list[Frame] = [
    Frame("smile", "sage-b-e1-smile.jpg", "微笑み"),
    Frame("thinking", "sage-b-e2-thinking.jpg", "思案"),
    Frame("empathy", "sage-b-e3-empathy.jpg", "共感"),
    Frame("surprise", "sage-b-e4-surprise.jpg", "軽い驚き"),
    Frame("nod", "sage-b-e5-nod.jpg", "うなずき"),
    Frame("relief", "sage-b-x-relief.jpg", "安心"),
    Frame("worry", "sage-b-x-worry.jpg", "心配"),
    Frame("sorry", "sage-b-x-sorry.jpg", "申し訳なさ"),
    Frame("serious", "sage-b-x-serious.jpg", "真剣"),
    Frame("cheer", "sage-b-x-cheer.jpg", "励まし"),
    Frame("shy", "sage-b-x-shy.jpg", "照れ"),
    Frame("confused", "sage-b-x-confused.jpg", "困惑"),
]
MOUTHS = {k: f"sage-b-mouth-{k}.jpg" for k in ("a", "i", "u", "e", "o")}
EYES_CLOSED_SRC = "sage-b-eye-closed.jpg"


# ---------------------------------------------------------------- helpers

def key_green(bgr: np.ndarray) -> np.ndarray:
    """Chroma-key the green background. Only green connected to the border is removed
    (keeps the mint capsule pin). Returns BGRA uint8."""
    b, g, r = (bgr[..., i].astype(np.int16) for i in range(3))
    greenness = g - np.maximum(r, b)
    cand = ((greenness > 20) & (g > 90)).astype(np.uint8)
    _, labels = cv2.connectedComponents(cand, connectivity=8)
    border = np.unique(np.concatenate([labels[0], labels[-1], labels[:, 0], labels[:, -1]]))
    bg = np.isin(labels, border[border != 0])

    alpha = np.full(bgr.shape[:2], 255, np.uint8)
    ramp = np.clip(255 - (greenness - 20) * (255 / 40), 0, 255).astype(np.uint8)
    alpha[bg] = ramp[bg]

    near_bg = cv2.dilate(bg.astype(np.uint8), np.ones((7, 7), np.uint8)) > 0
    out = bgr.copy()
    despill = near_bg & (alpha > 0)
    g_cap = np.maximum(r, b).clip(0, 255).astype(np.uint8)
    out[..., 1][despill] = np.minimum(out[..., 1][despill], g_cap[despill])
    return np.dstack([out, alpha])


def skin_mask(bgr: np.ndarray) -> np.ndarray:
    b, g, r = (bgr[..., i].astype(np.int16) for i in range(3))
    return (r > 170) & (g > 120) & (b > 80) & (r > g) & (g > b) & (r - b > 40)


def feather(mask: np.ndarray, sigma: float = FEATHER) -> np.ndarray:
    return cv2.GaussianBlur(mask.astype(np.float32), (0, 0), sigma)


def ellipse(shape: tuple[int, int], center, axes) -> np.ndarray:
    m = np.zeros(shape, np.uint8)
    cv2.ellipse(m, tuple(center), tuple(axes), 0, 0, 360, 1, -1)
    return m.astype(bool)


def save_webp(bgra: np.ndarray, path: Path, quality: int = 92) -> None:
    Image.fromarray(cv2.cvtColor(bgra, cv2.COLOR_BGRA2RGBA), "RGBA").save(
        path, "WEBP", quality=quality, method=6
    )


def crop_save(bgra: np.ndarray, name: str, quality: int = 92) -> dict:
    ys, xs = np.nonzero(bgra[..., 3] > 2)
    x0, x1, y0, y1 = int(xs.min()), int(xs.max()) + 1, int(ys.min()), int(ys.max()) + 1
    save_webp(bgra[y0:y1, x0:x1], OUT / name, quality)
    return {"src": name, "x": x0, "y": y0, "w": x1 - x0, "h": y1 - y0}


def with_alpha(bgr: np.ndarray, alpha_f: np.ndarray) -> np.ndarray:
    return np.dstack([bgr, (np.clip(alpha_f, 0, 1) * 255).round().astype(np.uint8)])


# ---------------------------------------------------------------- base parts

def hair_mask(bgr: np.ndarray, alpha: np.ndarray) -> np.ndarray:
    lum = bgr.mean(axis=2)
    dark = ((lum < 80) & (alpha > 0)).astype(np.uint8)
    core = cv2.morphologyEx(dark, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)))
    n, lab, st, _ = cv2.connectedComponentsWithStats(core)
    biggest = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    core = (lab == biggest).astype(np.uint8)
    # grow back the thin strands that belong to the mass, but not the face outline below it
    grown = cv2.dilate(core, np.ones((5, 5), np.uint8), iterations=2) & dark
    hair = (core | grown).astype(bool)
    hair[EAR_SPLIT_Y - 120:, :] = False
    # anti-aliased edge against the green background stays with the hair
    edge = (alpha > 0) & (alpha < 255) & (cv2.dilate(hair.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0)
    return hair | edge


def jaw_curve(bgr: np.ndarray) -> np.ndarray:
    """y of the jaw line for each column in JAW_X (quadratic prior refined by the dark outline)."""
    (x0, y0), (xc, yc), (x1, y1) = JAW_PRIOR
    coef = np.polyfit([x0, xc, x1], [y0, yc, y1], 2)
    lum = cv2.GaussianBlur(bgr.mean(axis=2), (0, 0), 1.2)
    ys = np.zeros(JAW_X[1] - JAW_X[0] + 1, np.float32)
    for i, x in enumerate(range(JAW_X[0], JAW_X[1] + 1)):
        prior = int(round(np.polyval(coef, x)))
        lo, hi = max(prior - 24, 0), min(prior + 24, bgr.shape[0] - 1)
        col = lum[lo:hi, x]
        ys[i] = lo + int(np.argmin(col)) if col.min() < 110 else prior
    return cv2.GaussianBlur(ys.reshape(1, -1), (0, 0), 3).ravel()


def head_mask(bgr: np.ndarray, alpha: np.ndarray, hair: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Head pixels, and the band just under the jaw line (outline anti-aliasing on the neck)."""
    h, w = alpha.shape
    jaw = jaw_curve(bgr)
    yy = np.arange(h)[:, None]
    head = np.zeros((h, w), bool)
    head[:EAR_SPLIT_Y, :JAW_X[0]] = True
    head[:EAR_SPLIT_Y, JAW_X[1] + 1:] = True
    cols = slice(JAW_X[0], JAW_X[1] + 1)
    head[:, cols] = yy <= (jaw[None, :] + 5)  # the whole outline stays with the face
    # the right jaw corner's outline sits just outside JAW_X; it must turn with the head
    head[EAR_SPLIT_Y:EAR_SPLIT_Y + 30, JAW_X[1] + 1:JAW_X[1] + 22] = True
    under_jaw = np.zeros((h, w), bool)
    under_jaw[:, cols] = (yy > jaw[None, :] + 5) & (yy <= jaw[None, :] + 10)
    return (head & (alpha > 0)) | hair, under_jaw


def fill_holes(mask: np.ndarray) -> np.ndarray:
    m = mask.astype(np.uint8)
    flood = m.copy()
    ff = np.zeros((m.shape[0] + 2, m.shape[1] + 2), np.uint8)
    cv2.floodFill(flood, ff, (0, 0), 1)
    return mask | (flood == 0)


def split_head(bgr: np.ndarray, head: np.ndarray, hair: np.ndarray):
    """Split head into face / ear_l / ear_r using the dark outlines as borders.
    Anything left over (stray strands, outline between ear and hair) joins the hair."""
    lum = bgr.mean(axis=2)
    open_area = (head & ~hair & (lum >= 100)).astype(np.uint8)
    cv2.polylines(open_area, EAR_BARRIERS, False, 0, 2)
    n, lab, st, cen = cv2.connectedComponentsWithStats(open_area, connectivity=4)
    cx, cy = 520, 560
    face_c = lab == lab[cy, cx]
    ear_l = np.zeros_like(head)
    ear_r = np.zeros_like(head)
    for i in range(1, n):
        if st[i, cv2.CC_STAT_AREA] < 400 or i == lab[cy, cx]:
            continue
        x, y = cen[i]
        if 380 < y < 660:
            if x < 330:
                ear_l |= lab == i
            elif x > 715:
                ear_r |= lab == i
    face_fill = fill_holes(face_c)
    k = np.ones((3, 3), np.uint8)
    face = cv2.dilate(face_fill.astype(np.uint8), k, iterations=7).astype(bool) & head & ~hair
    ear_l = fill_holes(cv2.morphologyEx(ear_l.astype(np.uint8), cv2.MORPH_CLOSE, k, iterations=3).astype(bool))
    ear_r = fill_holes(cv2.morphologyEx(ear_r.astype(np.uint8), cv2.MORPH_CLOSE, k, iterations=3).astype(bool))
    ear_l = cv2.dilate(ear_l.astype(np.uint8), k, iterations=4).astype(bool) & head & ~face & ~hair
    ear_r = cv2.dilate(ear_r.astype(np.uint8), k, iterations=4).astype(bool) & head & ~face & ~hair
    leftover = head & ~face & ~ear_l & ~ear_r & ~hair
    low = np.zeros_like(head)
    low[480:] = True
    face |= leftover & low  # outline fragments along the cheeks and chin
    hair = head & ~face & ~ear_l & ~ear_r
    return face, face_fill, ear_l, ear_r, hair


def build_parts(base_bgr: np.ndarray, base_bgra: np.ndarray, debug: Path | None) -> tuple[dict, np.ndarray]:
    h, w = base_bgr.shape[:2]
    alpha = base_bgra[..., 3]
    hair = hair_mask(base_bgr, alpha)
    head, under_jaw = head_mask(base_bgr, alpha, hair)
    skin = skin_mask(base_bgr)
    face, face_fill, ear_l, ear_r, hair = split_head(base_bgr, head, hair)

    interior = cv2.erode(face_fill.astype(np.uint8), cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE, (2 * INTERIOR_ERODE + 1, 2 * INTERIOR_ERODE + 1))).astype(bool)
    interior[:320] = False  # keep the hairline in the face layer

    parts: dict = {}

    # body: everything below the head + neck column filled with the under-chin shadow
    body = base_bgra.copy()
    body[head, 3] = 0
    neck_zone = np.zeros((h, w), np.uint8)
    cv2.fillPoly(neck_zone, [NECK_FILL], 1)
    neck_zone = neck_zone.astype(bool)
    shadow_src = (~head) & ~under_jaw & neck_zone & skin & (alpha == 255)
    shadow = np.median(base_bgr[shadow_src], axis=0) if shadow_src.sum() > 50 else np.array([90, 130, 200])
    fill = neck_zone & (head | under_jaw)
    body[fill, :3] = shadow.astype(np.uint8)
    body[fill, 3] = 255
    parts["body"] = crop_save(body, "part_body.webp", 90)

    # ears: drawn under the face and hair, extended under both so head turns never open a gap
    k3 = np.ones((3, 3), np.uint8)
    for side, m in (("l", ear_l), ("r", ear_r)):
        ext = (cv2.dilate(m.astype(np.uint8), k3, iterations=12) > 0) & (face | hair) & ~m
        src = base_bgr.copy()
        rgb = cv2.inpaint(src, ext.astype(np.uint8) * 255, 5, cv2.INPAINT_TELEA)
        a = m.astype(np.float32) * (alpha / 255.0)
        a[ext] = 1.0
        parts[f"ear_{side}"] = crop_save(with_alpha(rgb, a), f"part_ear_{side}.webp")

    # face: skin + outline with the whole interior repainted as plain skin (features layer
    # covers it); skin also continues a little under the hair so the hairline can slide
    hole_core = cv2.erode(face_fill.astype(np.uint8), cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE, (17, 17))).astype(bool)
    hole_core[:300] = False
    under_hair = hair & (alpha == 255) & (cv2.dilate(face.astype(np.uint8), k3, iterations=14) > 0)
    hole = (hole_core | under_hair).astype(np.uint8) * 255
    face_rgb = cv2.inpaint(base_bgr, hole, 9, cv2.INPAINT_TELEA)
    face_a = face.astype(np.float32) * (alpha / 255.0)
    face_a[under_hair] = 1.0
    parts["face"] = crop_save(with_alpha(face_rgb, face_a), "part_face.webp")

    # features: the face interior of the base frame (slides over the face for head turns)
    interior_f = feather(interior, FEATHER)
    parts["features"] = crop_save(with_alpha(base_bgr, interior_f), "part_features.webp")

    # hair
    hair_a = hair.astype(np.float32) * (alpha / 255.0)
    parts["hair"] = crop_save(with_alpha(base_bgr, hair_a), "part_hair.webp")

    if debug:
        vis = base_bgr.copy()
        for m, col in ((hair, (255, 0, 0)), (ear_l, (0, 200, 255)), (ear_r, (0, 200, 255)),
                       (interior, (0, 0, 255)), (fill, (255, 0, 255))):
            vis[m] = (vis[m] * 0.45 + np.array(col) * 0.55).astype(np.uint8)
        cv2.imwrite(str(debug / "parts_overlay.png"), vis)
        for name in ("body", "face", "features", "hair", "ear_l", "ear_r"):
            shutil.copy(OUT / parts[name]["src"], debug / parts[name]["src"])
    return parts, interior_f


# ---------------------------------------------------------------- variants

def align(base_gray: np.ndarray, var_gray: np.ndarray, sift) -> tuple[np.ndarray, int]:
    head_mask_img = np.zeros_like(base_gray)
    x0, y0, x1, y1 = HEAD_RECT
    head_mask_img[y0:y1, x0:x1] = 255
    kb, db = sift.detectAndCompute(base_gray, head_mask_img)
    kv, dv = sift.detectAndCompute(var_gray, None)
    matches = cv2.BFMatcher(cv2.NORM_L2).knnMatch(dv, db, k=2)
    good = [m for m, n in (p for p in matches if len(p) == 2) if m.distance < 0.75 * n.distance]
    if len(good) < 12:
        raise RuntimeError(f"too few matches ({len(good)})")
    src = np.float32([kv[m.queryIdx].pt for m in good])
    dst = np.float32([kb[m.trainIdx].pt for m in good])
    m, inliers = cv2.estimateAffinePartial2D(src, dst, method=cv2.RANSAC, ransacReprojThreshold=3.0,
                                             maxIters=5000, confidence=0.999)
    if m is None:
        raise RuntimeError("RANSAC failed")
    return m, int(inliers.sum())


def warp_to_base(path: Path, base_gray: np.ndarray, sift, size: tuple[int, int]) -> tuple[np.ndarray, dict]:
    bgr = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if bgr is None:
        raise FileNotFoundError(path)
    m, inliers = align(base_gray, cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY), sift)
    warped = cv2.warpAffine(key_green(bgr), m, size, flags=cv2.INTER_CUBIC,
                            borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
    scale = float(np.hypot(m[0, 0], m[1, 0]))
    rot = float(np.degrees(np.arctan2(m[1, 0], m[0, 0])))
    return warped, {"inliers": inliers, "scale": round(scale, 4), "rotationDeg": round(rot, 2)}


def match_skin(patch_bgr: np.ndarray, base_bgr: np.ndarray, mask: np.ndarray) -> np.ndarray:
    lum_p, lum_b = patch_bgr.mean(axis=2), base_bgr.mean(axis=2)
    sel = (mask > 0.05) & (mask < 0.7) & (lum_p > 150) & (lum_b > 150)
    if sel.sum() < 200:
        return patch_bgr
    shift = base_bgr[sel].astype(np.float32).mean(0) - patch_bgr[sel].astype(np.float32).mean(0)
    return np.clip(patch_bgr.astype(np.float32) + np.clip(shift, -25, 25), 0, 255).astype(np.uint8)


def eye_mask(shape: tuple[int, int]) -> np.ndarray:
    return ellipse(shape, *EYES["l"]) | ellipse(shape, *EYES["r"])


def synth_eyelid(bgr: np.ndarray, closeness: float) -> np.ndarray:
    """Slide the upper lash line down by ``closeness`` (0=open, 1=closed) and cover the
    uncovered eye with skin. Works on any frame aligned to the base."""
    out = bgr.copy()
    skin = skin_mask(bgr)
    lum = bgr.mean(axis=2)
    h, w = lum.shape
    for (cx, cy), (rx, ry) in EYES.values():
        roi = ellipse((h, w), (cx, cy), (rx - 6, ry - 8))
        opening = (roi & ~skin).astype(np.uint8)
        opening = cv2.morphologyEx(opening, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
        # drop the thin double-eyelid crease that touches the lash line in places
        opening = cv2.morphologyEx(opening, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
        n, lab, st, _ = cv2.connectedComponentsWithStats(opening)
        if n < 2:
            continue
        opening = lab == (1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA])))
        above = roi & skin
        lid = np.median(bgr[above & (np.arange(h)[:, None] < cy)], axis=0) if above.any() else bgr[cy, cx]
        xs = np.arange(cx - rx, cx + rx + 1)
        tops = np.full(xs.size, np.nan)
        bots = np.full(xs.size, np.nan)
        for i, x in enumerate(xs):
            ys = np.nonzero(opening[:, x])[0]
            if ys.size >= 3:
                tops[i], bots[i] = ys[0], ys[-1]
        valid = ~np.isnan(tops)
        if valid.sum() < 5:
            continue
        # smooth the eyelid contour; the iris below the lash must not count as lash
        tops_s = tops.copy()
        tops_s[valid] = cv2.GaussianBlur(tops[valid].reshape(1, -1).astype(np.float32), (0, 0), 2).ravel()
        bots_s = bots.copy()
        bots_s[valid] = cv2.GaussianBlur(bots[valid].reshape(1, -1).astype(np.float32), (0, 0), 2).ravel()
        # lash thickness is only trustworthy where the white of the eye sits right under it;
        # over the iris the dark run continues, so interpolate from the clean columns
        thick = np.full(xs.size, np.nan)
        for i, x in enumerate(xs):
            if not valid[i]:
                continue
            top, bot = int(tops[i]), int(bots[i])
            t = 0
            while top + t <= bot and t < MAX_LASH and lum[top + t, x] < 110:
                t += 1
            if top + t <= bot and lum[top + t:top + t + 3, x].min() > 170:
                thick[i] = t
        clean = ~np.isnan(thick)
        vi = np.nonzero(valid)[0]
        if clean.sum() >= 3:
            ci = np.nonzero(clean)[0]
            thick_s = np.interp(np.arange(xs.size), ci, cv2.GaussianBlur(
                thick[ci].reshape(1, -1).astype(np.float32), (0, 0), 1.5).ravel())
        else:
            thick_s = np.full(xs.size, 6.0)
        lash_t = np.clip(np.round(thick_s), 3, MAX_LASH).astype(int)
        shift = np.zeros(xs.size, np.float32)
        for i in np.nonzero(valid)[0]:
            shift[i] = closeness * max(bots_s[i] - tops_s[i] - lash_t[i], 0)
        # taper to 0 towards the corners so lash tips outside the opening move with the line
        shift = cv2.GaussianBlur(shift.reshape(1, -1), (0, 0), 3).ravel()
        lash_px = []
        fill = np.zeros((h, w), np.uint8)
        for i in vi:
            x = int(xs[i])
            top = int(round(min(tops[i], tops_s[i])))
            # keep the anti-aliased edge (darker than skin) so the moved line is not ragged
            for y in range(top - 1, min(top + lash_t[i] + 1, h)):
                if lum[y, x] < 170:
                    lash_px.append((x, y, i))
                    fill[y, x] = 1
            fill[top - 1:int(round(tops_s[i] + shift[i])), x] = 1
        # sample the lid colour just above the lash, where the lid is shaded
        near = np.zeros((h, w), bool)
        for i in vi:
            t = int(round(tops_s[i]))
            near[max(t - 12, 0):max(t - 4, 0), int(xs[i])] = True
        near &= skin
        if near.sum() > 50:
            lid = np.median(bgr[near], axis=0)
        out[fill > 0] = lid
        for x, y, i in lash_px:
            ny = y + int(round(shift[i]))
            if ny < h:
                out[ny, x] = bgr[y, x]
    # soften the column-wise edits
    edited = np.any(out != bgr, axis=2).astype(np.uint8)
    blur = cv2.GaussianBlur(out, (3, 3), 0)
    out[edited > 0] = blur[edited > 0]
    return out


def build_variants(base_bgr: np.ndarray, interior_f: np.ndarray) -> tuple[dict, dict]:
    h, w = base_bgr.shape[:2]
    base_gray = cv2.cvtColor(base_bgr, cv2.COLOR_BGR2GRAY)
    sift = cv2.SIFT_create(nfeatures=4000)
    layers: dict = {"expression": {}, "eyes": {}, "mouth": {}}
    meta: dict = {}
    eyes_f = feather(eye_mask((h, w)), 5.0)
    # synth_eyelid edits reach the ellipse edge, so its patch must be opaque a bit beyond it
    half_f = feather(ellipse((h, w), EYES["l"][0], (EYES["l"][1][0] + 14, EYES["l"][1][1] + 10))
                     | ellipse((h, w), EYES["r"][0], (EYES["r"][1][0] + 14, EYES["r"][1][1] + 10)), 5.0)
    mouth_f = feather(ellipse((h, w), *MOUTH), FEATHER)

    # neutral half-open eyes from the base itself
    half = synth_eyelid(base_bgr, 0.55)
    layers["eyes"]["half"] = crop_save(with_alpha(half, half_f), "eyes_half.webp")

    warped, info = warp_to_base(EXPR / EYES_CLOSED_SRC, base_gray, sift, (w, h))
    a = eyes_f * (warped[..., 3] / 255.0)
    rgb = match_skin(warped[..., :3], base_bgr, a)
    layers["eyes"]["closed"] = crop_save(with_alpha(rgb, a), "eyes_closed.webp")
    meta["eyes.closed"] = info

    for fr in EXPRESSIONS:
        warped, info = warp_to_base(EXPR / fr.src, base_gray, sift, (w, h))
        a = interior_f * (warped[..., 3] / 255.0)
        rgb = match_skin(warped[..., :3], base_bgr, a)
        spec = crop_save(with_alpha(rgb, a), f"expr_{fr.key}.webp")
        spec["label"] = fr.label
        layers["expression"][fr.key] = spec
        meta[f"expression.{fr.key}"] = info
        # per-expression half-open eyes so blinks keep the expression's eye shape
        half = synth_eyelid(rgb, 0.55)
        layers["eyes"][f"half@{fr.key}"] = crop_save(with_alpha(half, half_f * (warped[..., 3] / 255.0)),
                                                       f"eyes_half_{fr.key}.webp")
        print(f"expr {fr.key:9s} inliers={info['inliers']:4d} scale={info['scale']:.3f} rot={info['rotationDeg']:+.2f}")

    for key, src in MOUTHS.items():
        warped, info = warp_to_base(EXPR / src, base_gray, sift, (w, h))
        a = mouth_f * (warped[..., 3] / 255.0)
        rgb = match_skin(warped[..., :3], base_bgr, a)
        layers["mouth"][key] = crop_save(with_alpha(rgb, a), f"mouth_{key}.webp")
        meta[f"mouth.{key}"] = info
    return layers, meta


def build(debug_dir: Path | None) -> None:
    if OUT.exists():
        for f in OUT.glob("*.webp"):
            f.unlink()
    OUT.mkdir(parents=True, exist_ok=True)
    base_bgr = cv2.imread(str(EXPR / BASE_SRC), cv2.IMREAD_COLOR)
    if base_bgr is None:
        raise FileNotFoundError(EXPR / BASE_SRC)
    h, w = base_bgr.shape[:2]
    base_bgra = key_green(base_bgr)

    parts, interior_f = build_parts(base_bgr, base_bgra, debug_dir)
    layers, meta = build_variants(base_bgr, interior_f)

    manifest = {
        "version": 2,
        "character": "sage_cast_b",
        "canvas": {"width": w, "height": h},
        "pivot": {"neck": {"x": NECK_PIVOT[0], "y": NECK_PIVOT[1]}},
        "parts": parts,
        "partOrder": ["body", "ear_l", "ear_r", "face", "features", "hair"],
        "layers": layers,
        "alignment": meta,
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    total = sum(f.stat().st_size for f in OUT.glob("*.webp"))
    print(f"OK → {OUT} ({len(list(OUT.glob('*.webp')))} files, {total / 1024:.0f} KB)")
    if debug_dir:
        print(f"debug → {debug_dir}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--debug", action="store_true", help="write part overlays to a temp dir")
    args = ap.parse_args()
    debug_dir = None
    if args.debug:
        debug_dir = Path(tempfile.gettempdir()) / "sage_sprite_debug"
        debug_dir.mkdir(parents=True, exist_ok=True)
    build(debug_dir)


if __name__ == "__main__":
    main()
