#!/usr/bin/env python3
import json, re, time, requests, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts.sync_top50_otc_images import download_as_webp_from_url, verify_image_match

OUT = Path(__file__).resolve().parent / "batch_4_discovered_urls.json"
headers = {"User-Agent": "Mozilla/5.0"}

with open(Path(__file__).resolve().parent / "results_batch_4.json") as f:
    items = [r for r in json.load(f) if r.get("status") == "not_found"]
items.sort(key=lambda x: -int(x.get("recommendation_count") or 0))

found = {}
if OUT.is_file():
    found = json.loads(OUT.read_text(encoding="utf-8"))

for i, it in enumerate(items, 1):
    name = it["product_name"]
    if name in found:
        continue
    mfr = it.get("manufacturer", "")
    q = f"{name} {mfr}".strip()
    url = "https://search.rakuten.co.jp/search/mall/" + requests.utils.quote(q) + "/"
    imgs: list[str] = []
    try:
        r = requests.get(url, headers=headers, timeout=30)
        imgs = list(
            dict.fromkeys(
                re.findall(
                    r"https://(?:shop|tshop)\.r10s\.jp/[^\"'\\]+\.(?:jpg|png|webp)",
                    r.text,
                )
            )
        )
    except Exception as exc:
        print(f"[{i}/{len(items)}] SEARCH ERR {name}: {exc}", flush=True)
        time.sleep(0.5)
        continue

    jan_imgs = [u for u in imgs if re.search(r"49\d{11}", u)]
    other_imgs = [u for u in imgs if u not in jan_imgs]
    approved_url = None
    for img in (jan_imgs + other_imgs)[:6]:
        try:
            body = download_as_webp_from_url(img)
            rev = verify_image_match(name, mfr, name, body)
            if rev.approved:
                approved_url = img
                break
        except Exception:
            continue
    print(
        f"[{i}/{len(items)}] rec={it.get('recommendation_count')} "
        f"{'OK' if approved_url else 'MISS'} {name[:40]}",
        flush=True,
    )
    if approved_url:
        found[name] = approved_url
        OUT.write_text(json.dumps(found, ensure_ascii=False, indent=2), encoding="utf-8")
    time.sleep(0.5)

print(f"FOUND {len(found)}", flush=True)
OUT.write_text(json.dumps(found, ensure_ascii=False, indent=2), encoding="utf-8")
