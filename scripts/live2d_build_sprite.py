#!/usr/bin/env python3
"""Build 2.5D sprite avatar assets for the Sage cast (stand-in until the Cubism models exist).

Per character ``x`` (a/b/c/d), sources live in ``cast-unified/expressions-x/``:

* ``sage-x-w-base.jpg``     waist-up base frame (3:4). Defines the output canvas.
* ``sage-x-mouth-closed.jpg`` square head frame. Character coordinates (``Cast``) are measured on
  it; every other square frame (expressions, mouths, closed eyes) was generated from it.
* ``sage-x-g-*.jpg``        the waist-up base with one arm pose changed (gestures).

Steps:
1. The base is scaled into the square frame's coordinates (work canvas) and split into parts:
   body (neck under the chin is filled) / ear_l / ear_r / face (features inpainted) /
   features (face interior of the square frame) / hair. The browser moves them with different
   parallax, which gives nods, tilts and head turns.
2. Square frames are aligned to the base (SIFT + RANSAC similarity on the head) and cut into
   feathered patches: expressions (face interior), mouths, closed eyes. Half-open eyes are
   synthesised per expression by sliding the upper lash line down.
3. Gesture frames are aligned the same way. The changed region becomes a full body variant
   (the old arm disappears, the new one appears; shown with a dissolve), and the parts of the new
   arm that lie over the background or the head become a separate hand overlay that can sway.

Usage:
  python scripts/live2d_build_sprite.py [--cast a|b|c|d|all] [--debug]

Dev-only dependencies: opencv-python, numpy, Pillow
Output: static/live2d/sage_cast_x/sprite/{*.webp, manifest.json}
"""

from __future__ import annotations

import argparse
import json
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
CAST_DIR = ROOT / "static/img/live2d/concept/whitecoat/cast-unified"

Pt = tuple[int, int]


@dataclass(frozen=True)
class Cast:
    """Coordinates on the character's square frame ``sage-x-mouth-closed.jpg`` (1024x1024)."""

    key: str
    label: str
    head_rect: tuple[int, int, int, int]  # keypoints used for alignment
    jaw_x: tuple[int, int]  # columns where the jaw line separates face and neck
    jaw_prior: tuple[Pt, Pt, Pt]  # left end, chin, right end
    ear_split: tuple[int, int]  # outside jaw_x (left, right side): head above, body below
    neck_pivot: Pt
    # The neck column between its two outlines: left top/bottom, right top/bottom. Where the head
    # is cut out of the body, the column is repainted as neck shadow and the outlines extended.
    neck_x: tuple[Pt, Pt, Pt, Pt]
    neck_bottom: int
    eyes: dict[str, tuple[Pt, Pt]]  # center, (rx, ry)
    mouth: tuple[Pt, Pt]
    face_center: Pt  # a skin pixel inside the face outline
    ear_y: tuple[int, int]  # ear centroids lie between these rows ...
    ear_x: tuple[int, int]  # ... left of [0] or right of [1]
    hair_lum: float  # hair (incl. highlights) is darker than this
    hair_cut: tuple[int, int]  # hair below this row (left/right half) stays with the body
    low_y: int  # outline fragments below this row join the face
    interior_top: int  # face interior (features layer) starts here; keep the hairline in the face
    hole_top: int  # the face layer's inpainted interior starts here
    ear_barriers: tuple[tuple[Pt, ...], ...] = ()  # polylines splitting an ear from the cheek
    brow_guard: tuple[tuple[Pt, Pt], ...] = ()  # ellipses (center, axes) never counted as hair
    # columns ([x0, x1)) right of jaw_x whose rows ear_split..+30 still belong to the head
    jaw_corner: tuple[int, int, int] = (0, 0, 0)  # x0, x1, rows
    max_lash: int = 16  # px; upper lash line thickness cap for synthesised eyelids
    gesture_overrides: dict = field(default_factory=dict)


CASTS: dict[str, Cast] = {
    "a": Cast(
        key="a", label="A（やわらか）",
        head_rect=(240, 110, 770, 620), jaw_x=(385, 655),
        jaw_prior=((385, 470), (530, 597), (655, 465)), ear_split=(520, 500),
        neck_pivot=(550, 650), neck_x=((440, 440), (458, 700), (656, 430), (652, 650)), neck_bottom=720,
        eyes={"l": ((432, 380), (60, 34)), "r": ((581, 357), (60, 34))}, mouth=((522, 502), (72, 40)),
        face_center=(545, 440), ear_y=(320, 500), ear_x=(400, 650),
        hair_lum=115, hair_cut=(500, 545), low_y=420, interior_top=280, hole_top=260,
        ear_barriers=(((657, 370), (659, 410), (661, 452)),), max_lash=12,
    ),
    "b": Cast(
        key="b", label="B（落ち着き）",
        head_rect=(220, 150, 840, 830), jaw_x=(336, 714),
        jaw_prior=((336, 655), (520, 806), (714, 652)), ear_split=(700, 640),
        neck_pivot=(560, 745), neck_x=((376, 560), (410, 820), (718, 560), (718, 770)), neck_bottom=860,
        eyes={"l": ((398, 460), (84, 46)), "r": ((612, 442), (84, 46))}, mouth=((518, 668), (104, 60)),
        face_center=(520, 560), ear_y=(380, 660), ear_x=(330, 715),
        hair_lum=80, hair_cut=(520, 520), low_y=480, interior_top=320, hole_top=300,
        ear_barriers=(((743, 392), (738, 520), (737, 612)),), jaw_corner=(715, 736, 30),
    ),
    "c": Cast(
        key="c", label="C（明るい）",
        head_rect=(250, 110, 770, 610), jaw_x=(385, 655),
        jaw_prior=((385, 455), (497, 590), (655, 450)), ear_split=(500, 500),
        neck_pivot=(550, 620), neck_x=((442, 440), (466, 650), (656, 420), (655, 600)), neck_bottom=680,
        eyes={"l": ((420, 366), (54, 32)), "r": ((582, 345), (54, 32))}, mouth=((512, 494), (68, 38)),
        face_center=(540, 430), ear_y=(320, 490), ear_x=(395, 655),
        hair_lum=115, hair_cut=(490, 540), low_y=410, interior_top=270, hole_top=250,
        ear_barriers=(((656, 320), (660, 380), (663, 446)),), max_lash=12,
    ),
    "d": Cast(
        key="d", label="D（かわいい）",
        head_rect=(250, 110, 860, 680), jaw_x=(360, 660),
        jaw_prior=((360, 480), (505, 625), (660, 475)), ear_split=(620, 480),
        neck_pivot=(560, 660), neck_x=((452, 470), (470, 700), (647, 460), (648, 640)), neck_bottom=720,
        eyes={"l": ((408, 412), (58, 36)), "r": ((575, 390), (60, 36))}, mouth=((505, 540), (68, 40)),
        face_center=(540, 470), ear_y=(380, 520), ear_x=(365, 655),
        hair_lum=85, hair_cut=(700, 730), low_y=450, interior_top=330, hole_top=300,
        max_lash=14,
    ),
}

INTERIOR_ERODE = 20
HAIR_BAND = 48  # work px of overlap where hair continues below hair_cut
FEATHER = 7.0


@dataclass(frozen=True)
class Frame:
    key: str
    src: str  # without the ``sage-x-`` prefix
    label: str


EXPRESSIONS: list[Frame] = [
    Frame("smile", "e1-smile.jpg", "微笑み"),
    Frame("thinking", "e2-thinking.jpg", "思案"),
    Frame("empathy", "e3-empathy.jpg", "共感"),
    Frame("surprise", "e4-surprise.jpg", "軽い驚き"),
    Frame("nod", "e5-nod.jpg", "うなずき"),
    Frame("relief", "x-relief.jpg", "安心"),
    Frame("worry", "x-worry.jpg", "心配"),
    Frame("sorry", "x-sorry.jpg", "申し訳なさ"),
    Frame("serious", "x-serious.jpg", "真剣"),
    Frame("cheer", "x-cheer.jpg", "励まし"),
    Frame("shy", "x-shy.jpg", "照れ"),
    Frame("confused", "x-confused.jpg", "困惑"),
]
MOUTHS = ("a", "i", "u", "e", "o")


@dataclass(frozen=True)
class Gesture:
    key: str
    label: str
    attach: str = "rig"  # "head": the hand touches the face and follows head turns


GESTURES: list[Gesture] = [
    Gesture("wave", "手を振る"),
    Gesture("explain", "手のひら差し出し"),
    Gesture("point", "人差し指"),
    Gesture("chest", "胸に手"),
    Gesture("chin", "あごに手", "head"),
    Gesture("fist", "こぶし"),
    Gesture("bow_hands", "両手を合わせる"),
    Gesture("ok", "OK サイン"),
]
HEAD_ZONE = 24  # px around the head where body variants keep the base (the head covers it)
CHANGE_MIN_AREA = 4000  # px; smaller differences are redraw noise
HAND_MIN_AREA = 1500
ENTER_ROT = 16.0  # deg; hand overlays swing in about the cuff by this much
ENTER_DROP = 10  # output px; more than this lifts the hand visibly off the cuff while it swings in


# ---------------------------------------------------------------- helpers

def key_green(bgr: np.ndarray) -> np.ndarray:
    """Chroma-key the green background. Green connected to the border is removed, and so are
    enclosed pockets of saturated green (gaps between arm and torso); the mint capsule pin is
    far less saturated and stays. Returns BGRA uint8."""
    b, g, r = (bgr[..., i].astype(np.int16) for i in range(3))
    greenness = g - np.maximum(r, b)
    cand = ((greenness > 20) & (g > 90)).astype(np.uint8)
    n, labels = cv2.connectedComponents(cand, connectivity=8)
    border = np.unique(np.concatenate([labels[0], labels[-1], labels[:, 0], labels[:, -1]]))
    keep = np.zeros(n, bool)
    keep[border[border != 0]] = True
    sums = np.bincount(labels.ravel(), weights=greenness.ravel(), minlength=n)
    counts = np.bincount(labels.ravel(), minlength=n)
    keep |= (counts >= 30) & (sums / np.maximum(counts, 1) > 110)
    keep[0] = False
    bg = keep[labels]

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
    cv2.ellipse(m, tuple(int(v) for v in center), tuple(int(v) for v in axes), 0, 0, 360, 1, -1)
    return m.astype(bool)


def disk(r: int) -> np.ndarray:
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))


def fill_holes(mask: np.ndarray) -> np.ndarray:
    m = np.pad(mask.astype(np.uint8), 1)
    ff = np.zeros((m.shape[0] + 2, m.shape[1] + 2), np.uint8)
    cv2.floodFill(m, ff, (0, 0), 1)
    return mask | (m[1:-1, 1:-1] == 0)


def with_alpha(bgr: np.ndarray, alpha_f: np.ndarray) -> np.ndarray:
    return np.dstack([bgr, (np.clip(alpha_f, 0, 1) * 255).round().astype(np.uint8)])


def despill_all(bgra: np.ndarray) -> np.ndarray:
    """Cap green at max(r, b) everywhere (only for parts with no legitimately green pixels)."""
    bgra = bgra.copy()
    bgra[..., 1] = np.minimum(bgra[..., 1], np.maximum(bgra[..., 0], bgra[..., 2]))
    return bgra


def blend_pm(under: np.ndarray, over: np.ndarray, w: np.ndarray) -> np.ndarray:
    """Per-pixel mix of two BGRA images (premultiplied): w=0 → under, w=1 → over."""
    w = w[..., None]
    au = under[..., 3:4].astype(np.float32) / 255
    ao = over[..., 3:4].astype(np.float32) / 255
    a = au * (1 - w) + ao * w
    pm = under[..., :3] * au * (1 - w) + over[..., :3] * ao * w
    rgb = pm / np.maximum(a, 1e-4)
    return np.dstack([np.clip(rgb, 0, 255), np.clip(a * 255, 0, 255)]).round().astype(np.uint8)


# ---------------------------------------------------------------- build context

class Builder:
    def __init__(self, cast: Cast, debug: Path | None):
        self.cast = cast
        self.expr = CAST_DIR / f"expressions-{cast.key}"
        self.out = ROOT / f"static/live2d/sage_cast_{cast.key}/sprite"
        self.debug = debug
        self.sift = cv2.SIFT_create(nfeatures=6000)
        self._setup_canvas()

    def src(self, name: str) -> Path:
        return self.expr / f"sage-{self.cast.key}-{name}"

    def read(self, name: str) -> np.ndarray:
        bgr = cv2.imread(str(self.src(name)), cv2.IMREAD_COLOR)
        if bgr is None:
            raise FileNotFoundError(self.src(name))
        return bgr

    # -- coordinates

    def _setup_canvas(self) -> None:
        """Scale the waist-up base into the square frame's coordinates (no rotation)."""
        c = self.cast
        ref = self.read("mouth-closed.jpg")
        waist = self.read("w-base.jpg")
        m, inliers = self._align(cv2.cvtColor(ref, cv2.COLOR_BGR2GRAY), c.head_rect,
                                 cv2.cvtColor(waist, cv2.COLOR_BGR2GRAY))
        k = float(np.hypot(m[0, 0], m[1, 0]))
        anchor = np.array(c.face_center, np.float64)
        a2 = np.vstack([m, [0, 0, 1]])
        w_anchor = (np.linalg.inv(a2) @ np.array([*anchor, 1.0]))[:2]
        tx, ty = anchor - k * w_anchor
        wh, ww = waist.shape[:2]
        ox = int(np.ceil(max(0.0, -tx)))
        oy = int(np.ceil(max(0.0, -ty)))
        self.off = (ox, oy)
        self.work_w = int(np.ceil(k * ww + tx + ox))
        self.work_h = int(np.ceil(k * wh + ty + oy))
        self.k = k
        self.out_w, self.out_h = int(round(self.work_w / k)), int(round(self.work_h / k))
        mw = np.float32([[k, 0, tx + ox], [0, k, ty + oy]])
        self.base_bgr = cv2.warpAffine(waist, mw, (self.work_w, self.work_h), flags=cv2.INTER_CUBIC,
                                       borderMode=cv2.BORDER_REPLICATE)
        self.base_bgra = cv2.warpAffine(key_green(waist), mw, (self.work_w, self.work_h), flags=cv2.INTER_CUBIC,
                                        borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
        self.base_gray = cv2.cvtColor(self.base_bgr, cv2.COLOR_BGR2GRAY)
        rot = float(np.degrees(np.arctan2(m[1, 0], m[0, 0])))
        print(f"[{c.key}] base: scale {k:.3f} rot {rot:+.2f} (dropped) inliers {inliers} "
              f"work {self.work_w}x{self.work_h} → out {self.out_w}x{self.out_h}")
        self.shape = (self.work_h, self.work_w)

    def p(self, pt) -> tuple[int, int]:
        return int(pt[0] + self.off[0]), int(pt[1] + self.off[1])

    def px(self, x: int) -> int:
        return int(x + self.off[0])

    def py(self, y: int) -> int:
        return int(y + self.off[1])

    def eyes(self) -> dict:
        return {s: (self.p(c), r) for s, (c, r) in self.cast.eyes.items()}

    # -- alignment

    def _align(self, base_gray: np.ndarray, rect, var_gray: np.ndarray) -> tuple[np.ndarray, int]:
        """rect: (x0, y0, x1, y1) or a boolean mask of base pixels whose keypoints count."""
        if isinstance(rect, np.ndarray):
            mask = rect.astype(np.uint8) * 255
        else:
            mask = np.zeros_like(base_gray)
            x0, y0, x1, y1 = rect
            mask[y0:y1, x0:x1] = 255
        kb, db = self.sift.detectAndCompute(base_gray, mask)
        kv, dv = self.sift.detectAndCompute(var_gray, None)
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

    def warp(self, bgr: np.ndarray, keyed: np.ndarray | None = None, region=None) -> tuple[np.ndarray, dict]:
        """Align a frame to the base on its head (default) or on ``region`` (a base pixel mask)."""
        if region is None:
            x0, y0, x1, y1 = self.cast.head_rect
            region = (self.px(x0), self.py(y0), self.px(x1), self.py(y1))
        m, inliers = self._align(self.base_gray, region, cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY))
        src = key_green(bgr) if keyed is None else keyed
        warped = cv2.warpAffine(src, m, (self.work_w, self.work_h), flags=cv2.INTER_CUBIC,
                                borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
        scale = float(np.hypot(m[0, 0], m[1, 0]))
        rot = float(np.degrees(np.arctan2(m[1, 0], m[0, 0])))
        return warped, {"inliers": inliers, "scale": round(scale, 4), "rotationDeg": round(rot, 2)}

    # -- output

    def to_out(self, bgra: np.ndarray) -> np.ndarray:
        a = bgra[..., 3].astype(np.float32) / 255
        pm = bgra[..., :3].astype(np.float32) * a[..., None]
        size = (self.out_w, self.out_h)
        pm = cv2.resize(pm, size, interpolation=cv2.INTER_AREA)
        a = cv2.resize(a, size, interpolation=cv2.INTER_AREA)
        rgb = pm / np.maximum(a[..., None], 1e-4)
        return np.dstack([np.clip(rgb, 0, 255), np.clip(a * 255, 0, 255)]).round().astype(np.uint8)

    def save(self, bgra_work: np.ndarray, name: str, quality: int = 92, despill: bool = False) -> dict:
        if despill:
            bgra_work = despill_all(bgra_work)
        bgra = self.to_out(bgra_work)
        ys, xs = np.nonzero(bgra[..., 3] > 2)
        if not len(xs):
            xs, ys = np.array([0, 1]), np.array([0, 1])
        x0, x1, y0, y1 = int(xs.min()), int(xs.max()) + 1, int(ys.min()), int(ys.max()) + 1
        Image.fromarray(cv2.cvtColor(bgra[y0:y1, x0:x1], cv2.COLOR_BGRA2RGBA), "RGBA").save(
            self.out / name, "WEBP", quality=quality, method=6)
        return {"src": name, "x": x0, "y": y0, "w": x1 - x0, "h": y1 - y0}

    def out_pt(self, pt) -> dict:
        return {"x": round(pt[0] / self.k, 1), "y": round(pt[1] / self.k, 1)}

    # ------------------------------------------------------------ base parts

    def hair_mask(self, bgr: np.ndarray, alpha: np.ndarray) -> np.ndarray:
        c = self.cast
        h, w = alpha.shape
        lum = bgr.mean(axis=2)
        dark = ((lum < c.hair_lum) & (alpha > 0)).astype(np.uint8)
        cut = np.zeros((h, w), bool)
        mid = self.px(c.face_center[0])
        cut[self.py(c.hair_cut[0]):, :mid] = True
        cut[self.py(c.hair_cut[1]):, mid:] = True
        dark[cut] = 0
        # brows are dark too; where bangs touch them they would join the hair
        for (bx, by), (brx, bry) in c.brow_guard:
            dark[ellipse((h, w), self.p((bx, by)), (brx, bry))] = 0
        core = cv2.morphologyEx(dark, cv2.MORPH_OPEN, disk(4))
        n, lab, st, _ = cv2.connectedComponentsWithStats(core)
        biggest = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
        core = (lab == biggest).astype(np.uint8)
        # grow back the thin strands that belong to the mass, but not the face outline below it
        grown = cv2.dilate(core, np.ones((5, 5), np.uint8), iterations=2) & dark
        hair = (core | grown).astype(bool)
        # thin strand tips beside the face hang over the background, cut off from the mass by
        # their lighter anti-aliasing; small dark pieces right next to the hair go with it
        loose = (lum < c.hair_lum + 50) & (alpha > 0) & ~hair & ~cut
        loose[:self.py(c.ear_y[1])] = False
        loose[self.py(c.neck_bottom):] = False
        loose[:, self.px(c.jaw_x[0]):self.px(c.jaw_x[1]) + 1] = False
        n, lab, st, _ = cv2.connectedComponentsWithStats(loose.astype(np.uint8), connectivity=8)
        near = cv2.dilate(hair.astype(np.uint8), disk(12)) > 0
        ids = np.unique(lab[near & (lab > 0)])
        ids = ids[st[ids, cv2.CC_STAT_AREA] < 2500]
        hair |= np.isin(lab, ids)
        # anti-aliased edge against the green background stays with the hair
        edge = (alpha > 0) & (alpha < 255) & (cv2.dilate(hair.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0)
        return (hair | edge) & ~cut

    def jaw_curve(self, bgr: np.ndarray) -> np.ndarray:
        """y of the jaw line for each column in jaw_x (quadratic prior refined by the dark outline)."""
        (x0, y0), (xc, yc), (x1, y1) = (self.p(q) for q in self.cast.jaw_prior)
        coef = np.polyfit([x0, xc, x1], [y0, yc, y1], 2)
        lum = cv2.GaussianBlur(bgr.mean(axis=2), (0, 0), 1.2)
        jx0, jx1 = self.px(self.cast.jaw_x[0]), self.px(self.cast.jaw_x[1])
        ys = np.zeros(jx1 - jx0 + 1, np.float32)
        for i, x in enumerate(range(jx0, jx1 + 1)):
            prior = int(round(np.polyval(coef, x)))
            lo, hi = max(prior - 24, 0), min(prior + 24, bgr.shape[0] - 1)
            col = lum[lo:hi, x]
            ys[i] = lo + int(np.argmin(col)) if col.min() < 110 else prior
        return cv2.GaussianBlur(ys.reshape(1, -1), (0, 0), 3).ravel()

    def head_mask(self, bgr: np.ndarray, alpha: np.ndarray, hair: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Head pixels, and the band just under the jaw line (outline anti-aliasing on the neck)."""
        c = self.cast
        h, w = alpha.shape
        jaw = self.jaw_curve(bgr)
        jx0, jx1 = self.px(c.jaw_x[0]), self.px(c.jaw_x[1])
        yy = np.arange(h)[:, None]
        head = np.zeros((h, w), bool)
        head[:self.py(c.ear_split[0]), :jx0] = True
        head[:self.py(c.ear_split[1]), jx1 + 1:] = True
        cols = slice(jx0, jx1 + 1)
        head[:, cols] = yy <= (jaw[None, :] + 5)  # the whole outline stays with the face
        if c.jaw_corner[2]:
            # the jaw corner's outline sits just outside jaw_x; it must turn with the head
            y0 = self.py(c.ear_split[1])
            head[y0:y0 + c.jaw_corner[2], self.px(c.jaw_corner[0]):self.px(c.jaw_corner[1])] = True
        under_jaw = np.zeros((h, w), bool)
        under_jaw[:, cols] = (yy > jaw[None, :] + 5) & (yy <= jaw[None, :] + 10)
        return (head & (alpha > 0)) | hair, under_jaw

    def split_head(self, bgr: np.ndarray, head: np.ndarray, hair: np.ndarray):
        """Split head into face / ear_l / ear_r using the dark outlines as borders.
        Anything left over (stray strands, outline between ear and hair) joins the hair."""
        c = self.cast
        lum = bgr.mean(axis=2)
        open_area = (head & ~hair & (lum >= 100)).astype(np.uint8)
        if c.ear_barriers:
            cv2.polylines(open_area, [np.array([self.p(q) for q in b], np.int32) for b in c.ear_barriers],
                          False, 0, 2)
        n, lab, st, cen = cv2.connectedComponentsWithStats(open_area, connectivity=4)
        fx, fy = self.p(c.face_center)
        face_id = lab[fy, fx]
        if face_id == 0:
            raise RuntimeError(f"face_center {c.face_center} is not on open skin")
        face_c = lab == face_id
        ear_l = np.zeros_like(head)
        ear_r = np.zeros_like(head)
        for i in range(1, n):
            if st[i, cv2.CC_STAT_AREA] < 400 or i == face_id:
                continue
            x, y = cen[i]
            if self.py(c.ear_y[0]) < y < self.py(c.ear_y[1]):
                if x < self.px(c.ear_x[0]):
                    ear_l |= lab == i
                elif x > self.px(c.ear_x[1]):
                    ear_r |= lab == i
        face_fill = fill_holes(face_c)
        k = np.ones((3, 3), np.uint8)
        face = cv2.dilate(face_fill.astype(np.uint8), k, iterations=7).astype(bool) & head & ~hair
        ears = []
        for m in (ear_l, ear_r):
            m = fill_holes(cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_CLOSE, k, iterations=3).astype(bool))
            ears.append(cv2.dilate(m.astype(np.uint8), k, iterations=4).astype(bool) & head & ~face & ~hair)
        ear_l, ear_r = ears
        leftover = head & ~face & ~ear_l & ~ear_r & ~hair
        low = np.zeros_like(head)
        low[self.py(c.low_y):] = True
        face |= leftover & low  # outline fragments along the cheeks and chin
        hair = head & ~face & ~ear_l & ~ear_r
        return face, face_fill, ear_l, ear_r, hair

    def build_parts(self) -> dict:
        c = self.cast
        base_bgr, base_bgra = self.base_bgr, self.base_bgra
        h, w = self.shape
        alpha = base_bgra[..., 3]
        hair = self.hair_mask(base_bgr, alpha)
        head, under_jaw = self.head_mask(base_bgr, alpha, hair)
        # small islands left over above the shoulders (strand tips, ear slivers) belong to the head
        rest = ((alpha > 0) & ~head).astype(np.uint8)
        n, lab, st, _ = cv2.connectedComponentsWithStats(rest, connectivity=8)
        stray = np.zeros(n, bool)
        stray[1:] = (st[1:, cv2.CC_STAT_AREA] < 3000) & \
            (st[1:, cv2.CC_STAT_TOP] + st[1:, cv2.CC_STAT_HEIGHT] < self.py(c.neck_bottom))
        stray = stray[lab]
        hair |= stray
        head |= stray
        skin = skin_mask(base_bgr)
        face, face_fill, ear_l, ear_r, hair = self.split_head(base_bgr, head, hair)
        self.head = head
        self.face_fill = face_fill

        interior = cv2.erode(face_fill.astype(np.uint8), disk(INTERIOR_ERODE)).astype(bool)
        interior[:self.py(c.interior_top)] = False  # keep the hairline in the face layer

        parts: dict = {}

        # where hair continues below hair_cut (a ponytail), the body keeps a band above the cut
        # and the hair layer fades out over it, so a head turn bends the hair instead of tearing it
        lum = base_bgr.mean(axis=2)
        dark = (lum < c.hair_lum) & (alpha > 0)
        mid = self.px(c.face_center[0])
        hair_fade = np.ones((h, w), np.float32)
        band_keep = np.zeros((h, w), bool)
        for cols, cy in ((slice(0, mid), c.hair_cut[0]), (slice(mid, w), c.hair_cut[1])):
            y1 = self.py(cy)
            if y1 >= h:
                continue
            y0 = max(y1 - HAIR_BAND, 0)
            cont = np.zeros(w, bool)
            cont[cols] = dark[y1:min(y1 + 10, h), cols].mean(axis=0) > 0.5
            band = np.zeros((h, w), bool)
            band[y0:y1, :] = cont[None, :]
            band &= hair
            band_keep |= band
            ramp = np.linspace(1.0, 0.0, y1 - y0, dtype=np.float32)[:, None]
            hair_fade[y0:y1] = np.where(band[y0:y1], ramp, hair_fade[y0:y1])

        # body: everything below the head + neck column filled with the under-chin shadow
        body = base_bgra.copy()
        body[head & ~band_keep, 3] = 0
        lt, lb, rt, rb = (self.p(q) for q in c.neck_x)
        nb = self.py(c.neck_bottom)
        neck_zone = np.zeros((h, w), np.uint8)
        # the zone reaches well below the chin; only the hidden part of it is painted
        cv2.fillPoly(neck_zone, [np.array([lt, rt, (rb[0], nb), (lb[0], nb)], np.int32)], 1)
        neck_zone = neck_zone.astype(bool)
        shadow_src = (~head) & ~under_jaw & neck_zone & skin & (alpha == 255)
        shadow = np.median(base_bgr[shadow_src], axis=0) if shadow_src.sum() > 50 else np.array([90, 130, 200])
        hidden = head | under_jaw
        fill = neck_zone & hidden
        body[fill, :3] = shadow.astype(np.uint8)
        body[fill, 3] = 255
        lines = np.zeros((h, w), np.uint8)
        cv2.line(lines, lt, lb, 1, 5)
        cv2.line(lines, rt, rb, 1, 5)
        lines = (lines > 0) & hidden
        outline_src = (~hidden) & (cv2.dilate(lines.astype(np.uint8), np.ones((3, 3), np.uint8), iterations=40) > 0) \
            & (base_bgr.mean(axis=2) < 70) & (alpha == 255)
        outline = np.median(base_bgr[outline_src], axis=0) if outline_src.sum() > 20 else np.array([40, 40, 50])
        body[lines, :3] = outline.astype(np.uint8)
        body[lines, 3] = 255
        self.body = body
        parts["body"] = self.save(body, "part_body.webp", 90)

        # colours for every visible part come from the despilled frame (no green fringe)
        clean = np.ascontiguousarray(base_bgra[..., :3])

        # ears: drawn under the face and hair, extended under both so head turns never open a gap
        k3 = np.ones((3, 3), np.uint8)
        for side, m in (("l", ear_l), ("r", ear_r)):
            ext = (cv2.dilate(m.astype(np.uint8), k3, iterations=12) > 0) & (face | hair) & ~m
            rgb = cv2.inpaint(clean, ext.astype(np.uint8) * 255, 5, cv2.INPAINT_TELEA) if m.any() else clean
            a = m.astype(np.float32) * (alpha / 255.0)
            if m.any():
                a[ext] = 1.0
            parts[f"ear_{side}"] = self.save(with_alpha(rgb, a), f"part_ear_{side}.webp", despill=True)

        # face: skin + outline with the whole interior repainted as plain skin (features layer
        # covers it); skin also continues a little under the hair so the hairline can slide
        hole_core = cv2.erode(face_fill.astype(np.uint8), disk(8)).astype(bool)
        hole_core[:self.py(c.hole_top)] = False
        under_hair = hair & (alpha == 255) & (cv2.dilate(face.astype(np.uint8), k3, iterations=14) > 0)
        hole = (hole_core | under_hair).astype(np.uint8) * 255
        face_rgb = cv2.inpaint(clean, hole, 9, cv2.INPAINT_TELEA)
        face_a = face.astype(np.float32) * (alpha / 255.0)
        face_a[under_hair] = 1.0
        parts["face"] = self.save(with_alpha(face_rgb, face_a), "part_face.webp", despill=True)

        # features: the face interior of the square frame, so every expression patch (drawn from
        # that frame) matches it; skin tone is matched to the base
        self.interior_f = feather(interior, FEATHER)
        ref, info = self.warp(self.read("mouth-closed.jpg"))
        a = self.interior_f * (ref[..., 3] / 255.0)
        self.ref_rgb = match_skin(ref[..., :3], base_bgr, a)
        parts["features"] = self.save(with_alpha(self.ref_rgb, a), "part_features.webp")
        self.meta["features"] = info

        # hair
        hair_a = hair.astype(np.float32) * (alpha / 255.0) * hair_fade
        parts["hair"] = self.save(with_alpha(clean, hair_a), "part_hair.webp", despill=True)

        if self.debug:
            vis = base_bgr.copy()
            for m, col in ((hair, (255, 0, 0)), (ear_l, (0, 200, 255)), (ear_r, (0, 200, 255)),
                           (interior, (0, 0, 255)), (fill, (255, 0, 255))):
                vis[m] = (vis[m] * 0.45 + np.array(col) * 0.55).astype(np.uint8)
            for (cx, cy), (rx, ry) in self.eyes().values():
                cv2.ellipse(vis, (cx, cy), (rx, ry), 0, 0, 360, (0, 255, 255), 2)
            (mx, my), (mrx, mry) = self.cast.mouth
            cv2.ellipse(vis, self.p((mx, my)), (mrx, mry), 0, 0, 360, (0, 255, 255), 2)
            cv2.circle(vis, self.p(c.neck_pivot), 8, (0, 0, 255), -1)
            cv2.imwrite(str(self.debug / f"{c.key}_parts_overlay.png"), vis)
        return parts

    # ------------------------------------------------------------ variants

    def eye_mask(self) -> np.ndarray:
        e = self.eyes()
        return ellipse(self.shape, *e["l"]) | ellipse(self.shape, *e["r"])

    def build_variants(self) -> dict:
        base_bgr = self.base_bgr
        h, w = self.shape
        e = self.eyes()
        layers: dict = {"expression": {}, "eyes": {}, "mouth": {}}
        eyes_f = feather(self.eye_mask(), 5.0)
        # synth_eyelid edits reach the ellipse edge, so its patch must be opaque a bit beyond it
        half_f = feather(ellipse((h, w), e["l"][0], (e["l"][1][0] + 14, e["l"][1][1] + 10))
                         | ellipse((h, w), e["r"][0], (e["r"][1][0] + 14, e["r"][1][1] + 10)), 5.0)
        (mc, mr) = self.cast.mouth
        mouth_f = feather(ellipse((h, w), self.p(mc), mr), FEATHER)

        # neutral half-open eyes from the features frame
        half = synth_eyelid(self.ref_rgb, 0.55, e, self.cast.max_lash)
        layers["eyes"]["half"] = self.save(with_alpha(half, half_f), "eyes_half.webp")

        warped, info = self.warp(self.read("eye-closed.jpg"))
        a = eyes_f * (warped[..., 3] / 255.0)
        rgb = match_skin(warped[..., :3], base_bgr, a)
        layers["eyes"]["closed"] = self.save(with_alpha(rgb, a), "eyes_closed.webp")
        self.meta["eyes.closed"] = info

        for fr in EXPRESSIONS:
            if not self.src(fr.src).exists():
                print(f"  expr {fr.key:9s} (missing {self.src(fr.src).name})")
                continue
            warped, info = self.warp(self.read(fr.src))
            a = self.interior_f * (warped[..., 3] / 255.0)
            rgb = match_skin(warped[..., :3], base_bgr, a)
            spec = self.save(with_alpha(rgb, a), f"expr_{fr.key}.webp")
            spec["label"] = fr.label
            layers["expression"][fr.key] = spec
            self.meta[f"expression.{fr.key}"] = info
            # per-expression half-open eyes so blinks keep the expression's eye shape
            half = synth_eyelid(rgb, 0.55, e, self.cast.max_lash)
            layers["eyes"][f"half@{fr.key}"] = self.save(with_alpha(half, half_f * (warped[..., 3] / 255.0)),
                                                          f"eyes_half_{fr.key}.webp")
            print(f"  expr {fr.key:9s} inliers={info['inliers']:4d} scale={info['scale']:.3f} "
                  f"rot={info['rotationDeg']:+.2f}")

        for key in MOUTHS:
            warped, info = self.warp(self.read(f"mouth-{key}.jpg"))
            a = mouth_f * (warped[..., 3] / 255.0)
            rgb = match_skin(warped[..., :3], base_bgr, a)
            layers["mouth"][key] = self.save(with_alpha(rgb, a), f"mouth_{key}.webp")
            self.meta[f"mouth.{key}"] = info
        return layers

    # ------------------------------------------------------------ gestures

    def build_gestures(self) -> dict:
        h, w = self.shape
        base_rgb = self.base_bgra[..., :3]
        base_a = self.base_bgra[..., 3]
        bfg = base_a >= 128
        head_zone = cv2.dilate(self.head.astype(np.uint8), disk(HEAD_ZONE)) > 0
        blur_b = cv2.GaussianBlur(base_rgb, (5, 5), 0).astype(np.int16)
        # keypoints on the torso and neck (RANSAC drops the ones on the moved arm)
        torso = bfg & ~(cv2.dilate(self.head.astype(np.uint8), disk(8)) > 0)
        out: dict = {}
        for g in GESTURES:
            path = self.src(f"g-{g.key}.jpg")
            if not path.exists():
                print(f"  gesture {g.key:9s} (missing {path.name})")
                continue
            bgr = cv2.imread(str(path), cv2.IMREAD_COLOR)
            keyed = key_green(bgr)
            # enclosed background (e.g. the ring of the OK sign) is not connected to the border
            b, gr, r = (bgr[..., i].astype(np.int16) for i in range(3))
            keyed[((gr - np.maximum(r, b)) > 20) & (gr > 90), 3] = 0
            # the body variant must line up with the base body; a hand on the face with the face
            G, info = self.warp(bgr, keyed, None if g.attach == "head" else torso)
            g_rgb, g_a = G[..., :3], G[..., 3]
            gfg = g_a >= 128

            diff = np.abs(cv2.GaussianBlur(g_rgb, (5, 5), 0).astype(np.int16) - blur_b).max(axis=2) > 45
            raw = ((diff & (gfg | bfg)) | (gfg != bfg)).astype(np.uint8)
            raw = cv2.morphologyEx(raw, cv2.MORPH_OPEN, disk(3))
            raw = cv2.morphologyEx(raw, cv2.MORPH_CLOSE, disk(7))
            n, lab, st, _ = cv2.connectedComponentsWithStats(raw, connectivity=8)
            change = np.isin(lab, [i for i in range(1, n) if st[i, cv2.CC_STAT_AREA] >= CHANGE_MIN_AREA])
            change = fill_holes(cv2.dilate(change.astype(np.uint8), disk(4)) > 0)

            # the arm: changed foreground pieces that reach outside the head (expression redraws
            # inside the head zone are dropped)
            n, lab, st, _ = cv2.connectedComponentsWithStats((change & gfg).astype(np.uint8), connectivity=8)
            outside = np.bincount(lab[change & gfg & ~head_zone].ravel(), minlength=n)
            arm = np.isin(lab, [i for i in range(1, n) if outside[i] >= 2000])

            sb, sg, sr = (cv2.GaussianBlur(g_rgb, (3, 3), 0)[..., i].astype(np.int16) for i in range(3))
            skin_g = (sr > 150) & (sr > sg) & (sg > sb) & (sr - sb > 40)
            if g.attach == "head":
                near = cv2.dilate(head_zone.astype(np.uint8), disk(60)) > 0
                hand = self._hand_regions(g_rgb, gfg, skin_g, arm, near, blur_b)
                free = np.zeros((h, w), bool)
            else:
                # the hand itself (behind it the base shows the torso or background; it swings at
                # the cuff) and the arm where it lies over the head
                near = cv2.dilate(arm.astype(np.uint8), disk(6)) > 0
                free = self._hand_regions(g_rgb, gfg, skin_g, arm, near, blur_b) | (arm & head_zone)
                n, lab, st, _ = cv2.connectedComponentsWithStats(free.astype(np.uint8), connectivity=8)
                # pieces without a hand in them (an elbow sticking out) stay in the body variant
                skin_n = np.bincount(lab[free & skin_g].ravel(), minlength=n)
                free = np.isin(lab, [i for i in range(1, n)
                                     if st[i, cv2.CC_STAT_AREA] >= HAND_MIN_AREA and skin_n[i] >= 800])
                hand = np.zeros((h, w), bool)

            overlay = free | hand
            body_change = change & ~head_zone & ~overlay
            wgt = feather(body_change, 2.0)
            wgt[overlay | head_zone] = 0
            variant = blend_pm(self.body, G, wgt)
            spec = {"label": g.label, "attach": g.attach,
                    "body": self.save(variant, f"gesture_{g.key}_body.webp", 88)}

            if overlay.any():
                # overlap the body variant by a couple of px so no seam opens
                grown_in = cv2.dilate(overlay.astype(np.uint8), disk(2)) > 0
                draw = (grown_in & gfg) | overlay
                soft_out = draw | ((g_a == 0) & (cv2.dilate(draw.astype(np.uint8), disk(3)) > 0))
                a = cv2.GaussianBlur(soft_out.astype(np.float32), (0, 0), 1.0) \
                    * (cv2.dilate(draw.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0) * (g_a / 255.0)
                hand_bgra = despill_all(with_alpha(g_rgb, a))
                hspec = self.save(hand_bgra, f"gesture_{g.key}_hand.webp", 90)
                seam = (cv2.dilate(overlay.astype(np.uint8), disk(5)) > 0) & body_change & gfg & ~overlay
                ys, xs = np.nonzero(overlay)
                cx, cy = xs.mean(), ys.mean()
                if seam.sum() > 20:
                    sy, sx = np.nonzero(seam)
                    pv = (float(sx.mean()), float(sy.mean()))
                else:
                    pv = (float(cx), float(ys.max()))
                dx = cx - pv[0]
                hspec["pivot"] = self.out_pt(pv)
                hspec["enterRot"] = 0.0 if g.attach == "head" or abs(dx) < 10 else round(
                    ENTER_ROT * float(np.sign(dx)), 1)
                hspec["enterDrop"] = 0 if g.attach == "head" else ENTER_DROP
                spec["hand"] = hspec
            out[g.key] = spec
            self.meta[f"gesture.{g.key}"] = info
            print(f"  gesture {g.key:9s} inliers={info['inliers']:4d} scale={info['scale']:.3f} "
                  f"change={int(change.sum() / self.k ** 2):6d}px hand={int(overlay.sum() / self.k ** 2):5d}px")
            if self.debug:
                self._debug_gesture(g.key, G, variant, overlay, change, head_zone)
        return out

    def _hand_regions(self, g_rgb, gfg, skin_g, arm, near, blur_b) -> np.ndarray:
        """Hand pixels within ``near``. Skin on skin (a hand on the face) barely differs in colour,
        so judge whole regions enclosed by line art: skin regions that belong to the arm or changed."""
        lum_g = cv2.cvtColor(g_rgb, cv2.COLOR_BGR2GRAY)
        dark_g = lum_g < 95
        base_dark = cv2.cvtColor(self.base_bgra[..., :3], cv2.COLOR_BGR2GRAY) < 95
        diff_lo = np.abs(cv2.GaussianBlur(g_rgb, (5, 5), 0).astype(np.int16) - blur_b).max(axis=2) > 22
        changed = diff_lo | (base_dark != dark_g)
        n, lab, st, _ = cv2.connectedComponentsWithStats((~dark_g & gfg & near).astype(np.uint8),
                                                         connectivity=4)
        face_cap = 0.3 * self.face_fill.sum()

        def count(m):
            return np.bincount(lab[m].ravel(), minlength=n)

        area_n, arm_n, ch_n = st[:, cv2.CC_STAT_AREA], count(arm), count(changed)
        skin_n, skin_arm_n, skin_ch_n = count(skin_g), count(skin_g & arm), count(skin_g & changed)
        on_face = count(self.face_fill)
        whole, skin_only = [], []
        for i in range(1, n):
            if skin_n[i] < 60:
                continue
            if skin_n[i] >= 0.5 * area_n[i]:
                cand, a_n, c_n, ids = area_n[i], arm_n[i], ch_n[i], whole
            else:
                # a gap in the outline merged the hand with the clothes: keep its skin pixels only
                cand, a_n, c_n, ids = skin_n[i], skin_arm_n[i], skin_ch_n[i], skin_only
            if cand > face_cap and on_face[i] > 0.5 * area_n[i]:
                continue  # the face itself
            if a_n > 0.3 * cand or c_n > 0.45 * cand:
                ids.append(i)
        part = np.isin(lab, skin_only) & skin_g
        part = cv2.morphologyEx(part.astype(np.uint8), cv2.MORPH_OPEN, disk(2)) > 0
        keep = np.isin(lab, whole) | part
        n, lab, st, _ = cv2.connectedComponentsWithStats(
            (cv2.dilate(keep.astype(np.uint8), disk(3)) > 0).astype(np.uint8), connectivity=8)
        if n > 1:
            big = st[1:, cv2.CC_STAT_AREA].max()
            keep &= np.isin(lab, [i for i in range(1, n) if st[i, cv2.CC_STAT_AREA] > 0.1 * big])
        ring = (cv2.dilate(keep.astype(np.uint8), disk(4)) > 0) & dark_g & gfg
        hand = cv2.morphologyEx((keep | ring).astype(np.uint8), cv2.MORPH_CLOSE, disk(3)) > 0
        return fill_holes(hand) & gfg

    def _debug_gesture(self, key: str, G, variant, overlay, change, head_zone) -> None:
        h, w = self.shape
        gray = np.full((h, w, 3), 128, np.float32)

        def over(dst, bgra):
            a = bgra[..., 3:4].astype(np.float32) / 255
            return dst * (1 - a) + bgra[..., :3] * a

        head_rgba = self.base_bgra.copy()
        head_rgba[~self.head, 3] = 0
        comp = over(over(gray, variant), head_rgba)
        hand = G.copy()
        hand[~overlay, 3] = 0
        comp = over(comp, hand)
        masks = self.base_bgr.astype(np.float32).copy()
        for m, col in ((change, (0, 0, 255)), (overlay, (255, 128, 0)), (head_zone & ~change, (0, 200, 0))):
            masks[m] = masks[m] * 0.5 + np.array(col) * 0.5
        g_vis = over(gray, G)
        pair = np.hstack([g_vis, comp, masks]).astype(np.uint8)
        pair = cv2.resize(pair, None, fx=0.4, fy=0.4, interpolation=cv2.INTER_AREA)
        cv2.imwrite(str(self.debug / f"{self.cast.key}_gesture_{key}.png"), pair)

    # ------------------------------------------------------------ main

    def build_gestures_only(self) -> None:
        """Rebuild the parts and gesture layers and patch them into the existing manifest."""
        path = self.out / "manifest.json"
        manifest = json.loads(path.read_text(encoding="utf-8"))
        for f in self.out.glob("gesture_*.webp"):
            f.unlink()
        self.meta = manifest.get("alignment", {})
        manifest["parts"] = self.build_parts()
        manifest["layers"]["gesture"] = self.build_gestures()
        manifest["alignment"] = self.meta
        path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"[{self.cast.key}] gestures patched → {path.relative_to(ROOT)}")

    def build(self) -> None:
        if self.out.exists():
            for f in self.out.glob("*.webp"):
                f.unlink()
        self.out.mkdir(parents=True, exist_ok=True)
        self.meta: dict = {}
        parts = self.build_parts()
        layers = self.build_variants()
        layers["gesture"] = self.build_gestures()
        manifest = {
            "version": 3,
            "character": f"sage_cast_{self.cast.key}",
            "label": self.cast.label,
            "canvas": {"width": self.out_w, "height": self.out_h},
            "pivot": {"neck": self.out_pt(self.p(self.cast.neck_pivot))},
            "parts": parts,
            "partOrder": ["body", "ear_l", "ear_r", "face", "features", "hair"],
            "layers": layers,
            "alignment": self.meta,
        }
        (self.out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                                                encoding="utf-8")
        total = sum(f.stat().st_size for f in self.out.glob("*.webp"))
        print(f"[{self.cast.key}] OK → {self.out.relative_to(ROOT)} "
              f"({len(list(self.out.glob('*.webp')))} files, {total / 1024:.0f} KB)")
        if self.debug:
            for name in ("body", "face", "features", "hair", "ear_l", "ear_r"):
                shutil.copy(self.out / parts[name]["src"], self.debug / f"{self.cast.key}_{parts[name]['src']}")


def match_skin(patch_bgr: np.ndarray, base_bgr: np.ndarray, mask: np.ndarray) -> np.ndarray:
    lum_p, lum_b = patch_bgr.mean(axis=2), base_bgr.mean(axis=2)
    sel = (mask > 0.05) & (mask < 0.7) & (lum_p > 150) & (lum_b > 150)
    if sel.sum() < 200:
        return patch_bgr
    shift = base_bgr[sel].astype(np.float32).mean(0) - patch_bgr[sel].astype(np.float32).mean(0)
    return np.clip(patch_bgr.astype(np.float32) + np.clip(shift, -25, 25), 0, 255).astype(np.uint8)


def synth_eyelid(bgr: np.ndarray, closeness: float, eyes: dict, max_lash: int) -> np.ndarray:
    """Slide the upper lash line down by ``closeness`` (0=open, 1=closed) and cover the
    uncovered eye with skin. Works on any frame aligned to the base."""
    out = bgr.copy()
    skin = skin_mask(bgr)
    lum = bgr.mean(axis=2)
    h, w = lum.shape
    for (cx, cy), (rx, ry) in eyes.values():
        roi = ellipse((h, w), (cx, cy), (rx - 6, ry - 8))
        opening = (roi & ~skin).astype(np.uint8)
        opening = cv2.morphologyEx(opening, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
        # drop the thin double-eyelid crease that touches the lash line in places
        opening = cv2.morphologyEx(opening, cv2.MORPH_OPEN, disk(2))
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
            while top + t <= bot and t < max_lash and lum[top + t, x] < 110:
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
        lash_t = np.clip(np.round(thick_s), 3, max_lash).astype(int)
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


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--cast", default="all", choices=[*CASTS, "all"])
    ap.add_argument("--debug", action="store_true", help="write part / gesture overlays to a temp dir")
    ap.add_argument("--gestures-only", action="store_true", help="rebuild parts and gestures only")
    args = ap.parse_args()
    debug_dir = None
    if args.debug:
        debug_dir = Path(tempfile.gettempdir()) / "sage_sprite_debug"
        debug_dir.mkdir(parents=True, exist_ok=True)
    for key in (CASTS if args.cast == "all" else [args.cast]):
        b = Builder(CASTS[key], debug_dir)
        b.build_gestures_only() if args.gestures_only else b.build()
    if debug_dir:
        print(f"debug → {debug_dir}")


if __name__ == "__main__":
    main()
