#!/usr/bin/env python3
"""Prepare Character B DIY workspace for Live2D Cubism Editor.

- Chroma-key concept JPGs → transparent PNG references
- Create named empty layer PNGs (2048 canvas) for PSD assembly
- Emit parts.csv / parameters.csv / LAYER_ORDER.txt

Usage:
  python scripts/live2d_prepare_cast_b.py
"""

from __future__ import annotations

import csv
import shutil
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
CONCEPT = ROOT / "static/img/live2d/concept/whitecoat/cast-unified"
EXPR = CONCEPT / "expressions-b"
OUT = ROOT / "static/live2d/sage_cast_b"
CANVAS = 2048
# Slightly above center (brow area) — documented in LIVE2D_CUBISM_PSD_SPEC.md
ORIGIN_Y_FRAC = 0.42

PARTS: list[tuple[str, str, str]] = [
    # group, layer_id, note
    ("body", "body", "首・肩・胸の肌（白衣の下）"),
    ("inner", "inner_torso", "シャツ胴"),
    ("inner", "inner_collar", "シャツ襟"),
    ("inner", "inner_accessory", "ネクタイ"),
    ("coat_back", "coat_back", "白衣後ろ襟・肩"),
    ("coat_body", "coat_body", "白衣本体・袖"),
    ("coat_lapel_R", "coat_lapel_R", "右襟（画面左）"),
    ("coat_lapel_L", "coat_lapel_L", "左襟（画面右）"),
    ("coat_pocket", "coat_pocket", "左胸四角パッチ"),
    ("pin_capsule", "pin_capsule", "ミント×白カプセルピン"),
    ("hair_back", "hair_back", "後ろ髪"),
    ("hair_side_L", "hair_side_L", "左横髪"),
    ("hair_side_R", "hair_side_R", "右横髪"),
    ("hair_front", "hair_front", "前髪"),
    ("hair_extra", "hair_extra", "Bは空で可（将来用）"),
    ("face_base", "face_base", "顔輪郭・頬・耳"),
    ("nose", "nose", "鼻"),
    ("mouth", "mouth_base", "閉口ベース"),
    ("mouth", "mouth_open_a", "口形あ"),
    ("mouth", "mouth_open_i", "口形い（横広げ）"),
    ("mouth", "mouth_open_u", "口形う"),
    ("mouth", "mouth_open_e", "口形え（開口）"),
    ("mouth", "mouth_open_o", "口形お"),
    ("eye_L", "eye_white_L", "左白目"),
    ("eye_L", "eye_iris_L", "左虹彩"),
    ("eye_L", "eye_highlight_L", "左ハイライト"),
    ("eye_L", "eye_lash_L", "左まつ毛・まぶた"),
    ("eye_R", "eye_white_R", "右白目"),
    ("eye_R", "eye_iris_R", "右虹彩"),
    ("eye_R", "eye_highlight_R", "右ハイライト"),
    ("eye_R", "eye_lash_R", "右まつ毛・まぶた"),
    ("brow_L", "brow_L", "左眉"),
    ("brow_R", "brow_R", "右眉"),
    ("expression_overlay", "expr_e1_smile", "任意・E1差分"),
    ("expression_overlay", "expr_e2_thinking", "任意・E2差分"),
    ("expression_overlay", "expr_e3_empathy", "任意・E3差分"),
    ("expression_overlay", "expr_e4_surprise", "任意・E4差分"),
    ("expression_overlay", "expr_e5_nod", "任意・E5差分"),
]

# Bottom → top draw order for LAYER_ORDER.txt / PSD stack
LAYER_ORDER_BOTTOM_TO_TOP = [p[1] for p in PARTS]

PARAMETERS: list[tuple[str, float, float, float, str]] = [
    # id, min, default, max, note
    ("ParamAngleX", -30, 0, 30, "首 Yaw"),
    ("ParamAngleY", -30, 0, 30, "首 Pitch / E5 うなずき"),
    ("ParamAngleZ", -30, 0, 30, "首 Roll"),
    ("ParamBodyAngleX", -10, 0, 10, "上半身（小さめ）"),
    ("ParamBreath", 0, 0, 1, "呼吸 idle"),
    ("ParamEyeLOpen", 0, 1, 1, "左目 0=閉 1=開"),
    ("ParamEyeROpen", 0, 1, 1, "右目"),
    ("ParamEyeBallX", -1, 0, 1, "視線 X"),
    ("ParamEyeBallY", -1, 0, 1, "視線 Y"),
    ("ParamMouthOpenY", 0, 0, 1, "口開き"),
    ("ParamMouthForm", -1, 0, 1, "口形 い(+1)↔え寄り"),
    ("ParamExpression", 0, 0, 5, "0–5 = E0–E5 スナップ"),
]


def chroma_key_green(im: Image.Image, soft: int = 55) -> Image.Image:
    """Remove green-screen-ish backgrounds. Returns RGBA."""
    arr = np.asarray(im.convert("RGBA")).copy()
    # int16: uint8 の r + 40 は明るい肌（R>215）でラップし、肌が緑判定される
    r, g, b = (arr[..., i].astype(np.int16) for i in range(3))
    hard = (g > 140) & (g > r + 40) & (g > b + 40)
    soft_m = (g > 110) & (g > r + 25) & (g > b + 25) & ~hard
    excess = np.minimum(g - r, g - b)
    soft_alpha = np.clip(255 - (excess - 25) * (255 / soft), 0, 255).astype(np.uint8)
    a = arr[..., 3].copy()
    a[hard] = 0
    a[soft_m] = np.minimum(a[soft_m], soft_alpha[soft_m])
    arr[..., 3] = a
    return Image.fromarray(arr, "RGBA")


def fit_to_canvas(im: Image.Image, canvas: int = CANVAS) -> Image.Image:
    """Place character on transparent canvas, roughly centered on brow origin."""
    im = im.convert("RGBA")
    # Trim transparent
    bbox = im.getbbox()
    if bbox:
        im = im.crop(bbox)
    # Scale to ~78% of canvas height
    target_h = int(canvas * 0.78)
    scale = target_h / im.height
    new_w = max(1, int(im.width * scale))
    new_h = max(1, int(im.height * scale))
    im = im.resize((new_w, new_h), Image.Resampling.LANCZOS)
    canvas_im = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
    # Place so character center-x is canvas center; top third ≈ brow at ORIGIN_Y_FRAC
    x = (canvas - new_w) // 2
    # Put top of head near 8% from top so brow ~ ORIGIN_Y_FRAC
    y = int(canvas * 0.08)
    canvas_im.paste(im, (x, y), im)
    return canvas_im


def empty_layer(canvas: int = CANVAS) -> Image.Image:
    return Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))


def write_csvs(diy: Path) -> None:
    with (diy / "parts.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["draw_order", "group", "layer_id", "filename", "note"])
        for i, (group, layer_id, note) in enumerate(PARTS):
            w.writerow([i, group, layer_id, f"layers/{layer_id}.png", note])
    with (diy / "parameters.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["param_id", "min", "default", "max", "note"])
        for row in PARAMETERS:
            w.writerow(row)
    with (diy / "LAYER_ORDER.txt").open("w", encoding="utf-8") as f:
        f.write("# Bottom → Top (Cubism / Photoshop layer stack)\n")
        for name in LAYER_ORDER_BOTTOM_TO_TOP:
            f.write(f"{name}\n")
    with (diy / "mouth_param_keys.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["viseme", "ref_file", "ParamMouthOpenY", "ParamMouthForm"])
        w.writerows(
            [
                ("closed", "reference/mouth-closed.png", 0.0, 0.0),
                ("a", "reference/mouth-a.png", 1.0, 0.0),
                ("i", "reference/mouth-i.png", 0.2, 1.0),
                ("u", "reference/mouth-u.png", 0.3, -0.3),
                ("e", "reference/mouth-e.png", 0.55, 0.2),
                ("o", "reference/mouth-o.png", 0.85, -0.2),
            ]
        )
    with (diy / "expression_param_keys.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ParamExpression", "id", "ref_file"])
        mapping = [
            (0, "E0", "reference/e0-neutral.png"),
            (1, "E1", "reference/e1-smile.png"),
            (2, "E2", "reference/e2-thinking.png"),
            (3, "E3", "reference/e3-empathy.png"),
            (4, "E4", "reference/e4-surprise.png"),
            (5, "E5", "reference/e5-nod.png"),
        ]
        for v, eid, path in mapping:
            w.writerow([v, eid, path])


def prepare_references(ref: Path) -> None:
    ref.mkdir(parents=True, exist_ok=True)
    sources = {
        "base-unified": CONCEPT / "sage-cast-b-unified-coat.jpg",
        "e0-neutral": EXPR / "sage-b-e0-neutral.jpg",
        "e1-smile": EXPR / "sage-b-e1-smile.jpg",
        "e2-thinking": EXPR / "sage-b-e2-thinking.jpg",
        "e3-empathy": EXPR / "sage-b-e3-empathy.jpg",
        "e4-surprise": EXPR / "sage-b-e4-surprise.jpg",
        "e5-nod": EXPR / "sage-b-e5-nod.jpg",
        "mouth-closed": EXPR / "sage-b-mouth-closed.jpg",
        "mouth-a": EXPR / "sage-b-mouth-a.jpg",
        "mouth-i": EXPR / "sage-b-mouth-i.jpg",
        "mouth-u": EXPR / "sage-b-mouth-u.jpg",
        "mouth-e": EXPR / "sage-b-mouth-e.jpg",
        "mouth-o": EXPR / "sage-b-mouth-o.jpg",
        "eye-half": EXPR / "sage-b-eye-half.jpg",
        "eye-closed": EXPR / "sage-b-eye-closed.jpg",
    }
    for name, path in sources.items():
        if not path.exists():
            print(f"WARN missing {path}")
            continue
        cut = chroma_key_green(Image.open(path))
        fitted = fit_to_canvas(cut)
        fitted.save(ref / f"{name}.png")
        print(f"ref {name}.png")


def prepare_layers(layers: Path) -> None:
    layers.mkdir(parents=True, exist_ok=True)
    guide = Image.open(OUT / "diy/reference/e0-neutral.png").convert("RGBA")
    # Guide at ~12% opacity under a marker file (not imported to Cubism)
    guide_faint = guide.copy()
    guide_faint.putalpha(guide_faint.getchannel("A").point(lambda a: int(a * 0.18) if a else 0))
    guide_faint.save(OUT / "diy/GUIDE_e0_faint.png")

    for _group, layer_id, _note in PARTS:
        empty_layer().save(layers / f"{layer_id}.png")
    print(f"wrote {len(PARTS)} empty layer PNGs")


def write_photoshop_jsx(diy: Path) -> None:
    """JSX: load named PNGs into a PSD in LAYER_ORDER (bottom→top)."""
    jsx = diy / "assemble_psd.jsx"
    lines = [
        "// Adobe Photoshop — open in ExtendScript Toolkit or File > Scripts > Browse",
        "// Assembles layers/*.png into sage_cast_b_layers.psd (2048x2048)",
        "(function () {",
        f'  var root = new File($.fileName).parent;',
        '  var layersDir = new Folder(root + "/layers");',
        f"  var doc = app.documents.add({CANVAS}, {CANVAS}, 72, 'sage_cast_b', NewDocumentMode.RGB, DocumentFill.TRANSPARENT);",
        "  var names = [",
    ]
    for name in LAYER_ORDER_BOTTOM_TO_TOP:
        lines.append(f'    "{name}",')
    lines += [
        "  ];",
        "  for (var i = 0; i < names.length; i++) {",
        '    var f = new File(layersDir + "/" + names[i] + ".png");',
        "    if (!f.exists) { $.writeln('missing ' + f); continue; }",
        "    app.open(f);",
        "    app.activeDocument.selection.selectAll();",
        "    app.activeDocument.selection.copy();",
        "    app.activeDocument.close(SaveOptions.DONOTSAVECHANGES);",
        "    app.activeDocument = doc;",
        "    doc.paste();",
        "    doc.activeLayer.name = names[i];",
        "  }",
        '  var out = new File(root + "/sage_cast_b_layers.psd");',
        "  var psd = new PhotoshopSaveOptions();",
        "  doc.saveAs(out, psd, true);",
        '  $.writeln("saved " + out);',
        "})();",
        "",
    ]
    jsx.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    if OUT.exists():
        # keep moc3 etc. if any; refresh diy/
        diy = OUT / "diy"
        if diy.exists():
            shutil.rmtree(diy)
    diy = OUT / "diy"
    diy.mkdir(parents=True, exist_ok=True)
    (OUT / "textures").mkdir(exist_ok=True)
    (OUT / "motions").mkdir(exist_ok=True)
    (OUT / "source").mkdir(exist_ok=True)

    write_csvs(diy)
    prepare_references(diy / "reference")
    prepare_layers(diy / "layers")
    write_photoshop_jsx(diy)

    # Convenience: copy best base into source/
    src = diy / "reference/e0-neutral.png"
    if src.exists():
        shutil.copy2(src, OUT / "source/sage_cast_b_e0_cutout.png")
        shutil.copy2(diy / "reference/base-unified.png", OUT / "source/sage_cast_b_unified_cutout.png")

    print(f"OK → {diy}")


if __name__ == "__main__":
    main()
