#!/usr/bin/env python3
"""
上位50 OTC 品目の画像をマツキヨ / 公式URL から取得し、審査後 R2 にアップロード。

Usage:
  .venv/bin/python scripts/sync_top50_otc_images.py --plan log/analysis/otc_image_sync_top50/top50_plan.json
  .venv/bin/python scripts/sync_top50_otc_images.py --batch 1 --batch-size 12
"""
from __future__ import annotations

import argparse
import io
import json
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None  # type: ignore

from scripts.sync_otc_images_from_matsukiyo import (
    Candidate,
    MatsukiyoClient,
    download_as_webp,
    resolve_image,
    save_local_webp,
    upload_to_r2,
    _norm,
    _manufacturer_short,
    pick_search_match,
    _query_variants,
)
from src.services.medicine_image_urls import slugify_product_name

DEFAULT_PLAN = ROOT / "log" / "analysis" / "otc_image_sync_top50" / "top50_plan.json"
DEFAULT_OUT = ROOT / "log" / "analysis" / "otc_image_sync_top50"
DEFAULT_LOCAL = ROOT / "static" / "otc"
CDN_BASE = "https://images.yutok.dev/otc/"

# 公式サイト / 薬局通販のパッケージ画像（マツキヨ未掲載品は楽天薬局・メーカー公式を使用）
OFFICIAL_IMAGE_URLS: dict[str, str] = {
    "トキワイブプロエースＡ": "https://www.tokiwayakuhin.co.jp/img/goods/L/H177300.jpg",
    "イブＡ錠": "https://images.microcms-assets.io/assets/5cd0cfb38d8449fe993f92b8c6c2c085/0dde9084b54e41459a7240b169b417b9/product-evea-img_02.jpg",
    "イブＡ錠ＥＸ": "https://images.microcms-assets.io/assets/5cd0cfb38d8449fe993f92b8c6c2c085/a9f3cbb1603b4a54923b16a0c010858b/product-eveaex-img_02.jpg",
    "イブクイック頭痛薬": "https://images.microcms-assets.io/assets/5cd0cfb38d8449fe993f92b8c6c2c085/1ed0816cdb3247f5af6fa22f422ae383/product-eveq-img_02.jpg",
    "パブロンゴールドＡ＜微粒＞": "https://www.catalog-taisho.com/content/dam/selfmedication/jp/ja/pabron/images/04515/04515_Product1.png",
    "ルルアタックＴＲ": "https://www.daiichisankyo-hc.co.jp/library/content/img_library/image/lulu_attack_tr_1C290_main.jpg",
    "バファリンＡ": "https://delivery-p62220-e526456.adobeaemcloud.com/adobe/assets/urn:aaid:aem:91ee1aa2-a1b5-41d9-99b3-0bc24ebd6ebf/as/pdt_a-sp_ava_l-jg.png",
    "バファリンプレミアム": "https://delivery-p62220-e526456.adobeaemcloud.com/adobe/assets/urn:aaid:aem:9720d1f7-7117-4e49-b36f-9c1cde9bd330/as/pdt_premium-sp_ava_l-jg.png",
    "セデス・ハイ": "https://www.shionogi-hc.co.jp/content/dam/shc/jp/wellness/medicine/sh/images/sh.jpg",
    "リングルアイビー": "https://www.ringl.jp/assets/img/products/item01.png",
    "小中学生用ノーシンピュア": "https://www.arax.co.jp/norshinpure/pure_syou/assets/images/top/mv-package.png",
    "ストナのどスプレー": "https://www.stona.jp/products/images/product_img01_02.png",
    "スカイブブロンのどスプレー": "https://shop.r10s.jp/fukuei/cabinet/01/16/510-6086-001_1.jpg",
    "イブロック冷感Ｓ": "https://shop.r10s.jp/himaraya/cabinet/0000001310c/0000001310474_r1_01.jpg",
    "マキセリン「コタロー」": "https://shop.r10s.jp/pupuhima/cabinet/4987301003175.jpg",
    "新エスベナントローチ": "https://shop.r10s.jp/shiraishiyakuhin/cabinet/0103101.jpg",
    "イブプロフェンソフトカプセル２００「キョーワ」": "https://shop.r10s.jp/doremi/cabinet/new4/4987060007858.jpg",
    "トピックＧトローチ": "https://shop.r10s.jp/genki-e-shop-hanshin/cabinet/b/4975979330211.jpg",
    "デーチカ": "https://item-shopping.c.yimg.jp/i/n/satuma_4987474174160-dmc",
    "オリブ油「タイセイ」Ｐ": "https://shop.r10s.jp/kenko-joy/cabinet/kusuri_002/4987286319124.jpg",
    "クールスロート": "https://shop.r10s.jp/leaf-land/cabinet/medication/oral-medicine/4987227029013-1.jpg",
    "ザッツ錠": "https://shop.r10s.jp/drugpure/cabinet/kihon41/4987033209135.jpg",
    "角野龍雲湯": "https://shop.r10s.jp/muraiyakuhin/cabinet/10858325/26/c66-1.jpg",
    "東洋漢方の小青龍湯": "https://makeshop-multi-images.akamaized.net/5312/itemimages/000000001439_JZK4IKj.jpg",
    "富士はら薬「赤玉」": "https://shop.r10s.jp/fujiyaku/cabinet/item23/4987524080519.jpg",
    "高砂オウレン": "https://shop.r10s.jp/garou/cabinet/01204501/img57695140.jpg",
    "高砂オウレン末": "https://shop.r10s.jp/garou/cabinet/01204501/img57695141.jpg",
    "グリセリン浣腸Ａ１０": "https://shop.r10s.jp/tels/cabinet/itemrobot/26/a103hu_05.jpg",
    "スースカット浣腸１０": "https://shop.r10s.jp/koto-p/cabinet/itempic10/4987388011414x10.jpg",
    "胃健錠": "https://shop.r10s.jp/yotsubadrug/cabinet/09794708/4987306009776_1.jpg",
    "キンカンＡＬ錠": "https://shop.r10s.jp/besthbi/cabinet/goq001/45532_1.jpg",
    "デイトナＳ": "https://shop.r10s.jp/fine-kagaku/cabinet/az/medicine/500017_1.jpg",
    "ノイロンムーンＳ": "https://shop.r10s.jp/fumichan/cabinet/rakuten/rakuten3/4987299225313.jpg",
    "フストールＳ": "https://shop.r10s.jp/genki-e-shop-hanshin/cabinet/b/4987299225719.jpg",
    "ハイカゼ内服液Ｓ": "https://shop.r10s.jp/sakuraiyakuhinstore/cabinet/1/09418500/10107656/imgrc0105635235.jpg",
    "スロナースのどスプレー": "https://shop.r10s.jp/reg-kenseido/cabinet/09109438/09109528/imgrc0157079681.jpg",
}


def _load_env() -> None:
    env_path = ROOT / ".env"
    if load_dotenv and env_path.is_file():
        load_dotenv(env_path, override=False)


def _norm_name(text: str) -> str:
    return _norm(re.sub(r"[「」『』\"'（）()《》]", "", text or ""))


@dataclass
class ReviewResult:
    approved: bool
    score: int
    reasons: list[str] = field(default_factory=list)


def verify_image_match(
    product_name: str,
    manufacturer: str,
    source_label: str,
    image_bytes: bytes,
    *,
    min_bytes: int = 8000,
    min_width: int = 120,
) -> ReviewResult:
    """パッケージ画像の妥当性を簡易審査。"""
    reasons: list[str] = []
    score = 0

    if len(image_bytes) < min_bytes:
        reasons.append(f"file_too_small ({len(image_bytes)} bytes)")
    else:
        score += 20

    try:
        from PIL import Image

        img = Image.open(io.BytesIO(image_bytes))
        w, h = img.size
        if w < min_width or h < min_width:
            reasons.append(f"dimensions_too_small ({w}x{h})")
        else:
            score += 20
        if w > h * 3 or h > w * 3:
            reasons.append(f"unusual_aspect_ratio ({w}x{h})")
        else:
            score += 10
    except Exception as exc:
        reasons.append(f"pil_error: {exc}")

    label_norm = _norm_name(source_label)
    prod_norm = _norm_name(product_name)
    main = _norm_name(re.split(r"[「『]", product_name or "", maxsplit=1)[0])
    mfr = _norm(_manufacturer_short(manufacturer))

    if prod_norm and prod_norm in label_norm:
        score += 40
    elif main and len(main) >= 4 and main in label_norm:
        score += 35
    else:
        overlap = len(set(main[i : i + 2] for i in range(max(1, len(main) - 1))) & set(
            label_norm[i : i + 2] for i in range(max(1, len(label_norm) - 1))
        ))
        if overlap >= max(3, len(main) // 3):
            score += 25
        else:
            reasons.append(f"name_mismatch: product={product_name!r} source={source_label!r}")

    if mfr and mfr in label_norm:
        score += 10

    approved = score >= 55 and not any(
        r.startswith("file_too_small") or r.startswith("dimensions_too_small") or r.startswith("pil_error")
        for r in reasons
    )
    return ReviewResult(approved=approved, score=score, reasons=reasons)


def r2_exists(slug: str) -> bool:
    url = f"{CDN_BASE}{slug}.webp"
    try:
        r = requests.head(url, timeout=15)
        return r.status_code == 200
    except requests.RequestException:
        return False


def download_image_bytes(image_url: str, session: requests.Session | None = None) -> bytes:
    """画像URLからバイト列を取得（マツキヨCDNはセッション必須）。"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) medicine-recommend/1.0",
    }
    if "matsukiyococokara-online.com" in image_url:
        headers["Referer"] = "https://www.matsukiyococokara-online.com/store/"
    sess = session or requests.Session()
    r = sess.get(image_url, timeout=60, headers=headers)
    r.raise_for_status()
    return r.content


def download_as_webp_from_url(image_url: str, session: requests.Session | None = None) -> bytes:
    from PIL import Image

    content = download_image_bytes(image_url, session)
    img = Image.open(io.BytesIO(content))
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGB")
    elif img.mode == "RGBA":
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[3])
        img = bg
    buf = io.BytesIO()
    img.save(buf, format="WEBP", quality=85, method=4)
    return buf.getvalue()


def resolve_official(product_name: str) -> str | None:
    url = OFFICIAL_IMAGE_URLS.get(product_name, "").strip()
    if not url or url.endswith(".html"):
        return None
    return url


def process_item(
    item: dict[str, Any],
    client: MatsukiyoClient,
    *,
    upload: bool,
    local_dir: Path,
) -> dict[str, Any]:
    name = str(item["product_name"])
    mfr = str(item.get("manufacturer", ""))
    slug = str(item.get("slug") or slugify_product_name(name, mfr))
    result = dict(item)
    result["slug"] = slug
    result["processed_at"] = datetime.now(timezone.utc).isoformat()

    if item.get("r2_status") == "exists" or r2_exists(slug):
        result["status"] = "skipped_exists"
        result["r2_url"] = f"{CDN_BASE}{slug}.webp"
        return result

    official = str(item.get("official_url") or "") or resolve_official(name) or ""
    cand = Candidate(
        product_name=name,
        manufacturer=mfr,
        medicine_type=str(item.get("medicine_type", "")),
        recommendation_count=int(item.get("recommendation_count") or 0),
        slug=slug,
    )

    source_url = ""
    source_label = ""

    if official:
        source_url = official
        source_label = name
        result["source"] = "official_url"
        result["source_image_url"] = official
    else:
        resolve_image(client, cand)
        if cand.status != "resolved" or not cand.source_image_url:
            result["status"] = cand.status or "not_found"
            result["note"] = cand.note
            return result
        source_url = cand.source_image_url
        source_label = cand.matsukiyo_name or name
        result["source"] = "matsukiyo"
        result["matsukiyo_jan"] = cand.matsukiyo_jan
        result["matsukiyo_name"] = cand.matsukiyo_name
        result["source_image_url"] = source_url

    try:
        if result.get("source") == "matsukiyo":
            body = download_as_webp_from_url(source_url, client.session)
        else:
            body = download_as_webp_from_url(source_url)
    except Exception as exc:
        result["status"] = "download_error"
        result["note"] = str(exc)
        return result

    review = verify_image_match(name, mfr, source_label, body)
    result["review_score"] = review.score
    result["review_reasons"] = review.reasons
    if not review.approved:
        result["status"] = "review_rejected"
        result["note"] = "; ".join(review.reasons)
        review_path = local_dir.parent / "review_rejected"
        review_path.mkdir(parents=True, exist_ok=True)
        (review_path / f"{slug}.webp").write_bytes(body)
        return result

    local_path = save_local_webp(local_dir, slug, body)
    result["local_path"] = str(local_path)

    if upload:
        try:
            result["r2_url"] = upload_to_r2(slug, body)
            result["status"] = "uploaded"
        except Exception as exc:
            result["status"] = "upload_error"
            result["note"] = str(exc)
    else:
        result["status"] = "review_approved"

    return result


def load_plan(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, list) else data.get("items", [])


def write_results(out_dir: Path, results: list[dict[str, Any]], *, batch: str) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"results_{batch}.json"
    path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")


def merge_all_results(out_dir: Path) -> dict[str, Any]:
    merged: list[dict[str, Any]] = []
    for p in sorted(out_dir.glob("results_batch*.json")):
        merged.extend(json.loads(p.read_text(encoding="utf-8")))
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total": len(merged),
        "uploaded": sum(1 for r in merged if r.get("status") == "uploaded"),
        "skipped_exists": sum(1 for r in merged if r.get("status") == "skipped_exists"),
        "not_found": sum(1 for r in merged if r.get("status") == "not_found"),
        "review_rejected": sum(1 for r in merged if r.get("status") == "review_rejected"),
        "errors": sum(1 for r in merged if str(r.get("status", "")).endswith("error")),
        "items": merged,
    }
    (out_dir / "top50_results.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync top50 OTC images with review")
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--local-dir", type=Path, default=DEFAULT_LOCAL)
    parser.add_argument("--batch", type=int, default=0, help="1-based batch index")
    parser.add_argument("--batch-size", type=int, default=12)
    parser.add_argument("--upload", action="store_true", default=True)
    parser.add_argument("--no-upload", action="store_true")
    parser.add_argument("--merge-only", action="store_true")
    parser.add_argument("--delay", type=float, default=0.8)
    args = parser.parse_args()
    _load_env()

    if args.merge_only:
        s = merge_all_results(args.out_dir)
        print(json.dumps({k: s[k] for k in ("total", "uploaded", "skipped_exists", "not_found", "review_rejected", "errors")}, ensure_ascii=False))
        return 0

    plan = load_plan(args.plan)
    need = [p for p in plan if p.get("r2_status") != "exists"]

    if args.batch > 0:
        start = (args.batch - 1) * args.batch_size
        end = start + args.batch_size
        subset = need[start:end]
        batch_name = f"batch{args.batch}"
    else:
        subset = need
        batch_name = "all"

    upload = args.upload and not args.no_upload
    client = MatsukiyoClient(delay_sec=args.delay)
    results: list[dict[str, Any]] = []

    print(f"Processing {len(subset)} items ({batch_name}), upload={upload}", flush=True)
    for i, item in enumerate(subset, 1):
        print(f"[{i}/{len(subset)}] {item['product_name']}", flush=True)
        res = process_item(item, client, upload=upload, local_dir=args.local_dir)
        results.append(res)
        print(f"  -> {res.get('status')} score={res.get('review_score', 'n/a')} {res.get('note', '')}", flush=True)

    write_results(args.out_dir, results, batch=batch_name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
