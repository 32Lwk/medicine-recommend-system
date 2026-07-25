#!/usr/bin/env python3
"""
ログ推奨頻度上位の OTC 医薬品について、マツキヨココカラ online から画像を取得し R2 にアップロードする。

Usage:
  py -3.11 scripts/sync_otc_images_from_matsukiyo.py --dry-run --limit 20
  py -3.11 scripts/sync_otc_images_from_matsukiyo.py --limit 200 --upload
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import re
import sys
import time
import unicodedata
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from typing import Any

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None  # type: ignore

from src.services.medicine_image_urls import slugify_product_name

MATSUKIYO_BASE = "https://www.matsukiyococokara-online.com/store"
DEFAULT_OUT_DIR = ROOT / "log" / "analysis" / "otc_image_sync"
DEFAULT_CSV = ROOT / "data" / "otc_medicine_data.csv"
DEFAULT_LOCAL_DIR = ROOT / "static" / "otc"
LOG_PATHS = (
    ROOT / "log" / "recommendation_detail_log.jsonl",
    ROOT / "log" / "log" / "recommendation_log.jsonl",
    ROOT / "log" / "counseling_detail_log.jsonl",
)
IMG_RE = re.compile(r"media/catalog/product/([^\"']+\.(?:jpg|jpeg|png|webp))", re.I)
PRODUCT_JSON_RE = re.compile(
    r'"@type":"Product"[^}]*?"name":"([^"]+)"[^}]*?"image":"([^"]+)"',
    re.S,
)


@dataclass
class Candidate:
    product_name: str
    manufacturer: str = ""
    medicine_type: str = ""
    recommendation_count: int = 0
    slug: str = ""
    matsukiyo_jan: str = ""
    matsukiyo_name: str = ""
    source_image_url: str = ""
    r2_url: str = ""
    status: str = "pending"
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "product_name": self.product_name,
            "manufacturer": self.manufacturer,
            "medicine_type": self.medicine_type,
            "recommendation_count": self.recommendation_count,
            "slug": self.slug,
            "matsukiyo_jan": self.matsukiyo_jan,
            "matsukiyo_name": self.matsukiyo_name,
            "source_image_url": self.source_image_url,
            "r2_url": self.r2_url,
            "status": self.status,
            "note": self.note,
        }


def _load_env() -> None:
    env_path = ROOT / ".env"
    if load_dotenv and env_path.is_file():
        load_dotenv(env_path, override=False)


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKC", (text or "").strip()).lower()
    return re.sub(r"[\s\u3000\-ー・]", "", text)


def _manufacturer_short(name: str) -> str:
    name = (name or "").strip()
    for suffix in ("株式会社", "制薬", "製薬", "工業", "ヘルスケア", "薬品"):
        name = name.replace(suffix, "")
    return name.strip()[:8]


def count_recommendations() -> tuple[Counter[str], dict[str, str], dict[str, str]]:
    counter: Counter[str] = Counter()
    manufacturers: dict[str, str] = {}
    types: dict[str, str] = {}

    for path in LOG_PATHS:
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            meds: list[dict[str, Any]] = []
            if row.get("log_type") == "recommendation_detail":
                meds = (
                    (row.get("diagnosis_snapshot") or {}).get("recommended_medicines")
                    or row.get("recommended_medicines")
                    or []
                )
            elif "result" in row:
                meds = row.get("result", {}).get("recommended_medicines", [])
            elif row.get("log_type") == "counseling_detail":
                for turn in row.get("conversation_history", []):
                    diag = turn.get("diagnosis") or {}
                    if isinstance(diag, dict):
                        meds.extend(diag.get("recommended_medicines", []))
            for m in meds:
                name = (m.get("product_name") or m.get("name") or "").strip()
                if not name:
                    continue
                counter[name] += 1
                mfr = (m.get("manufacturer") or m.get("maker") or "").strip()
                if mfr and name not in manufacturers:
                    manufacturers[name] = mfr
                mtype = (m.get("medicine_type") or m.get("classification") or "").strip()
                if mtype and name not in types:
                    types[name] = mtype
    return counter, manufacturers, types


def load_otc_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8")
    df = df.rename(
        columns={
            "製品名": "product_name",
            "メーカー名": "manufacturer",
            "医薬品の種類": "medicine_type",
        }
    )
    return df


def build_candidates(limit: int, csv_path: Path) -> list[Candidate]:
    counter, log_mfr, log_types = count_recommendations()
    df = load_otc_csv(csv_path)
    csv_lookup = {
        str(row.product_name).strip(): row
        for row in df.itertuples(index=False)
        if getattr(row, "product_name", None)
    }

    ordered_names = [name for name, _ in counter.most_common()]
    if len(ordered_names) < limit:
        top_types = Counter(log_types.get(n, "") for n in ordered_names[:30])
        top_types.pop("", None)
        popular_types = {t for t, _ in top_types.most_common(8)}
        extras: list[str] = []
        for row in df.itertuples(index=False):
            pname = str(getattr(row, "product_name", "")).strip()
            mtype = str(getattr(row, "medicine_type", "")).strip()
            if not pname or pname in counter:
                continue
            if popular_types and mtype not in popular_types:
                continue
            extras.append(pname)
        ordered_names.extend(extras)
        seen = set()
        deduped: list[str] = []
        for name in ordered_names:
            if name in seen:
                continue
            seen.add(name)
            deduped.append(name)
        ordered_names = deduped[:limit]
    else:
        ordered_names = ordered_names[:limit]

    out: list[Candidate] = []
    for name in ordered_names:
        row = csv_lookup.get(name)
        manufacturer = log_mfr.get(name) or (str(row.manufacturer) if row is not None else "")
        medicine_type = log_types.get(name) or (
            str(row.medicine_type) if row is not None else ""
        )
        out.append(
            Candidate(
                product_name=name,
                manufacturer=manufacturer,
                medicine_type=medicine_type,
                recommendation_count=int(counter.get(name, 0)),
                slug=slugify_product_name(name, manufacturer),
            )
        )
    return out


class MatsukiyoClient:
    def __init__(self, *, delay_sec: float = 0.6) -> None:
        self.delay_sec = delay_sec
        self.session = requests.Session()
        self.session.headers.update(
            {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) medicine-recommend/1.0"}
        )
        self._warmed = False

    def _warm(self) -> None:
        if self._warmed:
            return
        self.session.get(f"{MATSUKIYO_BASE}/", timeout=30)
        self._warmed = True
        time.sleep(self.delay_sec)

    def search(self, keyword: str, *, limit: int = 8) -> list[dict[str, str]]:
        self._warm()
        r = self.session.get(
            f"{MATSUKIYO_BASE}/catalogsearch/result/",
            params={"search_keyword": keyword},
            timeout=30,
        )
        r.raise_for_status()
        time.sleep(self.delay_sec)
        items: list[dict[str, str]] = []
        for dl_raw, img in re.findall(
            r"data-datalayer='([^']+)'[\s\S]*?media/catalog/product/([^\"']+\.(?:jpg|jpeg|png|webp))",
            r.text,
            flags=re.I,
        ):
            dl = json.loads(unescape(dl_raw))
            items.append(
                {
                    "item_id": str(dl.get("item_id") or ""),
                    "item_name": str(dl.get("item_name") or ""),
                    "image_path": img,
                    "image_url": f"{MATSUKIYO_BASE}/media/catalog/product/{img}",
                }
            )
            if len(items) >= limit:
                break
        return items

    def product_image(self, jan: str) -> dict[str, str] | None:
        self._warm()
        url = f"{MATSUKIYO_BASE}/catalog/product/view/id/{jan}"
        r = self.session.get(url, timeout=30)
        time.sleep(self.delay_sec)
        if r.status_code != 200:
            return None
        m = PRODUCT_JSON_RE.search(r.text)
        if m:
            return {"item_name": m.group(1), "image_url": m.group(2), "item_id": jan}
        imgs = IMG_RE.findall(r.text)
        if not imgs:
            return None
        front = next((p for p in imgs if "_01_" in p), imgs[0])
        return {
            "item_name": "",
            "image_url": f"{MATSUKIYO_BASE}/media/catalog/product/{front}",
            "item_id": jan,
        }


def _query_variants(product_name: str, manufacturer: str) -> list[str]:
    raw = (product_name or "").strip()
    cleaned = re.sub(r"[「」『』\"'（）()]", "", raw)
    core = re.sub(r"[Ａ-ＺA-Z0-9]+$", "", cleaned).strip()
    mfr = _manufacturer_short(manufacturer)
    variants: list[str] = []
    for base in dict.fromkeys([raw, cleaned, core]):
        if not base:
            continue
        if mfr:
            variants.append(f"{base} {mfr}")
        variants.append(base)
    # 長い名称は先頭トークンでも検索
    if len(core) >= 6:
        variants.append(core[: min(12, len(core))])
    return variants[:6]


def _token_overlap(target: str, candidate: str) -> float:
    if not target or not candidate:
        return 0.0
    if target in candidate or candidate in target:
        return 1.0
    t_tokens = {target[i : i + 2] for i in range(max(1, len(target) - 1))}
    c_tokens = {candidate[i : i + 2] for i in range(max(1, len(candidate) - 1))}
    if not t_tokens:
        return 0.0
    return len(t_tokens & c_tokens) / len(t_tokens)


def pick_search_match(
    product_name: str, manufacturer: str, items: list[dict[str, str]]
) -> dict[str, str] | None:
    if not items:
        return None
    raw_name = re.sub(r"[「」『』\"'（）()]", "", product_name or "")
    target = _norm(raw_name)
    main_part = _norm(re.split(r"[「『]", product_name or "", maxsplit=1)[0])
    mfr = _norm(_manufacturer_short(manufacturer))
    scored: list[tuple[int, dict[str, str]]] = []
    for it in items:
        name = _norm(it.get("item_name", ""))
        score = 0
        if target and target in name:
            score += 120
        elif main_part and len(main_part) >= 4 and main_part in name:
            score += 100
        else:
            overlap = _token_overlap(main_part or target, name)
            score += int(overlap * 60)
            if overlap < 0.45:
                continue
        if mfr and mfr in name:
            score += 25
        if "医薬品" in it.get("item_name", ""):
            score += 5
        scored.append((score, it))
    scored.sort(key=lambda x: x[0], reverse=True)
    if not scored:
        return None
    best_score, best = scored[0]
    return best if best_score >= 55 else None


def resolve_image(client: MatsukiyoClient, cand: Candidate) -> Candidate:
    match: dict[str, str] | None = None
    used_query = ""
    for q in _query_variants(cand.product_name, cand.manufacturer):
        items = client.search(q)
        match = pick_search_match(cand.product_name, cand.manufacturer, items)
        if match:
            used_query = q
            break
    if not match:
        cand.status = "not_found"
        cand.note = "matsukiyo search: no match"
        return cand

    cand.matsukiyo_jan = match.get("item_id", "")
    cand.matsukiyo_name = match.get("item_name", "")
    detail = client.product_image(cand.matsukiyo_jan) if cand.matsukiyo_jan else None
    if detail and detail.get("image_url"):
        cand.source_image_url = detail["image_url"]
        if detail.get("item_name"):
            cand.matsukiyo_name = detail["item_name"]
    else:
        cand.source_image_url = match.get("image_url", "")
    cand.status = "resolved"
    cand.note = f"query={used_query}"
    return cand


def download_as_webp(image_url: str) -> bytes:
    r = requests.get(image_url, timeout=60, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    from PIL import Image

    img = Image.open(io.BytesIO(r.content))
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGB")
    elif img.mode == "RGBA":
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[3])
        img = bg
    buf = io.BytesIO()
    img.save(buf, format="WEBP", quality=85, method=4)
    return buf.getvalue()


def save_local_webp(local_dir: Path, slug: str, body: bytes) -> Path:
    local_dir.mkdir(parents=True, exist_ok=True)
    dest = local_dir / f"{slug}.webp"
    dest.write_bytes(body)
    return dest


def upload_to_r2(slug: str, body: bytes) -> str:
    import boto3

    from src.services.medicine_image_urls import record_otc_image_version

    bucket = os.getenv("R2_BUCKET", "medicine-recommend-otc-images")
    endpoint = os.getenv("R2_S3_ENDPOINT", "").strip()
    access_key = os.getenv("R2_ACCESS_KEY_ID", "").strip()
    secret_key = os.getenv("R2_SECRET_ACCESS_KEY", "").strip()
    if not all([endpoint, access_key, secret_key]):
        raise RuntimeError("Set R2_S3_ENDPOINT, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY")

    key = f"otc/{slug}.webp"
    client = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name="auto",
    )
    client.put_object(
        Bucket=bucket,
        Key=key,
        Body=body,
        ContentType="image/webp",
        CacheControl="public, max-age=300, must-revalidate",
    )
    record_otc_image_version(slug, body)
    _try_purge_cdn_cache(slug)
    return f"https://images.yutok.dev/{key}"


def _try_purge_cdn_cache(slug: str) -> None:
    """CLOUDFLARE_API_TOKEN / CLOUDFLARE_ZONE_ID があれば CDN キャッシュをパージ。"""
    if not os.getenv("CLOUDFLARE_API_TOKEN") or not os.getenv("CLOUDFLARE_ZONE_ID"):
        return
    try:
        from scripts.purge_otc_cdn_cache import purge_urls, _build_urls

        purge_urls(_build_urls(slug))
    except Exception as exc:
        print(f"[warn] CDN purge skipped for {slug}: {exc}", file=sys.stderr)


def write_outputs(out_dir: Path, candidates: list[Candidate], *, meta: dict[str, Any]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        **meta,
        "items": [c.to_dict() for c in candidates],
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    with (out_dir / "candidates.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "product_name",
                "manufacturer",
                "medicine_type",
                "recommendation_count",
                "slug",
                "matsukiyo_jan",
                "matsukiyo_name",
                "source_image_url",
                "r2_url",
                "status",
                "note",
            ],
        )
        writer.writeheader()
        for c in candidates:
            writer.writerow(c.to_dict())


def build_meta(candidates: list[Candidate], *, limit: int, dry_run: bool) -> dict[str, Any]:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_store": MATSUKIYO_BASE,
        "limit": limit,
        "dry_run": dry_run,
        "uploaded": sum(1 for c in candidates if c.status == "uploaded"),
        "resolved": sum(1 for c in candidates if c.status in ("resolved", "uploaded")),
        "not_found": sum(1 for c in candidates if c.status == "not_found"),
        "errors": sum(1 for c in candidates if c.status == "error"),
    }


def load_existing_manifest(out_dir: Path) -> dict[str, Candidate]:
    path = out_dir / "manifest.json"
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, Candidate] = {}
    for row in data.get("items", []):
        c = Candidate(
            product_name=str(row.get("product_name", "")),
            manufacturer=str(row.get("manufacturer", "")),
            medicine_type=str(row.get("medicine_type", "")),
            recommendation_count=int(row.get("recommendation_count") or 0),
            slug=str(row.get("slug", "")),
            matsukiyo_jan=str(row.get("matsukiyo_jan", "")),
            matsukiyo_name=str(row.get("matsukiyo_name", "")),
            source_image_url=str(row.get("source_image_url", "")),
            r2_url=str(row.get("r2_url", "")),
            status=str(row.get("status", "")),
            note=str(row.get("note", "")),
        )
        out[c.product_name] = c
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync OTC images from Matsukiyo to R2")
    parser.add_argument("--limit", type=int, default=200, help="Max products (default: 200)")
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--dry-run", action="store_true", help="List/resolve only, no download/upload")
    parser.add_argument("--upload", action="store_true", help="Download and upload resolved images to R2")
    parser.add_argument("--resume", action="store_true", help="Skip items already uploaded in manifest")
    parser.add_argument("--local-dir", type=Path, default=DEFAULT_LOCAL_DIR, help="Also save webp locally")
    parser.add_argument("--no-local", action="store_true", help="Skip local static/otc save")
    args = parser.parse_args()
    _load_env()

    candidates = build_candidates(args.limit, args.csv)
    existing = load_existing_manifest(args.out_dir) if args.resume else {}
    client = MatsukiyoClient(delay_sec=args.delay)

    print(f"Candidates: {len(candidates)} (log-prioritized, limit={args.limit})", flush=True)

    for i, cand in enumerate(candidates, 1):
        prev = existing.get(cand.product_name)
        if prev and prev.status == "uploaded" and prev.r2_url:
            cand.status = prev.status
            cand.r2_url = prev.r2_url
            cand.source_image_url = prev.source_image_url
            cand.matsukiyo_jan = prev.matsukiyo_jan
            cand.matsukiyo_name = prev.matsukiyo_name
            cand.note = "resume: skipped"
            print(f"[{i}/{len(candidates)}] skip {cand.product_name} (uploaded)", flush=True)
            continue

        print(
            f"[{i}/{len(candidates)}] resolve {cand.product_name} (rec={cand.recommendation_count})",
            flush=True,
        )
        resolve_image(client, cand)
        if cand.status != "resolved":
            print(f"  -> {cand.status}: {cand.note}", flush=True)
            write_outputs(
                args.out_dir,
                candidates,
                meta=build_meta(
                    candidates,
                    limit=args.limit,
                    dry_run=args.dry_run and not args.upload,
                ),
            )
            continue
        print(f"  -> JAN {cand.matsukiyo_jan} | {cand.matsukiyo_name[:50]}", flush=True)

        if args.dry_run and not args.upload:
            continue

        if args.upload:
            try:
                body = download_as_webp(cand.source_image_url)
                if not args.no_local:
                    save_local_webp(args.local_dir, cand.slug, body)
                cand.r2_url = upload_to_r2(cand.slug, body)
                cand.status = "uploaded"
                print(f"  -> uploaded {cand.r2_url}", flush=True)
            except Exception as exc:
                cand.status = "error"
                cand.note = str(exc)
                print(f"  -> error: {exc}", flush=True)

        write_outputs(
            args.out_dir,
            candidates,
            meta=build_meta(
                candidates,
                limit=args.limit,
                dry_run=args.dry_run and not args.upload,
            ),
        )

    meta = build_meta(
        candidates,
        limit=args.limit,
        dry_run=args.dry_run and not args.upload,
    )
    write_outputs(args.out_dir, candidates, meta=meta)
    print(
        f"Done. uploaded={meta['uploaded']} resolved={meta['resolved']} "
        f"not_found={meta['not_found']} errors={meta['errors']}",
        flush=True,
    )
    print(
        f"Outputs: {args.out_dir / 'manifest.json'} , {args.out_dir / 'candidates.csv'}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
