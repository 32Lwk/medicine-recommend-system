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
    "のどスッキリスプレーＡＣ": "https://tshop.r10s.jp/fortress/cabinet/products/06713660/4987286318271medeal.jpg",
    "はらはら薬「翁丸」": "https://tshop.r10s.jp/benkyo/cabinet/okihai01/4989719100101teikei.jpg",
    "やまと丸": "https://item-shopping.c.yimg.jp/i/j/sakuraiyakuhin-store_iya1637?resolution=2x",
    "イスロンＧⅡ": "https://tshop.r10s.jp/protoolshop/cabinet/703/4992873046703.jpg",
    "イスロ胃腸ドリンクＳ": "https://tshop.r10s.jp/mprice-shop/cabinet/l/20260525fk/4962720202132.jpg",
    "ウチダの大黄牡丹皮湯": "https://tshop.r10s.jp/k-benkyo/cabinet/shohin204/4987359200199.jpg",
    "ウチダの麻黄附子細辛湯": "https://tshop.r10s.jp/phmikawa2/cabinet/kihon7/498735901072910.jpg",
    "エイクレス": "https://tshop.r10s.jp/kyorindo/cabinet/item11/4987475118491.jpg",
    "エスタックイブファインＥＸ": "https://tshop.r10s.jp/koyamadrug/cabinet/12217305//p05/4987300069011-1.jpg",
    "オウレンいけだや": "https://tshop.r10s.jp/mikawaph/cabinet/kihon6/4987466109040.jpg",
    "オウレンダイコー": "https://tshop.r10s.jp/drugpure/cabinet/kihon45/4979654026741.jpg",
    "オウレン末いけだや": "https://tshop.r10s.jp/drugpure/cabinet/kihon40/4936246100784.jpg",
    "オウレン末ダイコー": "https://tshop.r10s.jp/drugpure/cabinet/kihon40/4936246100821.jpg",
    "オムニンエース": "https://tshop.r10s.jp/koubetanpopo/cabinet/take01/pake201902/y4987299222626.jpg",
    "カコナールせき止め液Ｗ": "https://tshop.r10s.jp/drugaozora/cabinet/gazou23/4987040051024.jpg",
    "ガロール健芯液": "https://tshop.r10s.jp/fortress/cabinet/products/12374699/4987103052449mede.jpg",
    "クミアイ解熱鎮痛錠": "https://tshop.r10s.jp/benkyo/cabinet/shohin14/4987847021442.jpg",
    "クールワンせき止めＧＸプラス": "https://tshop.r10s.jp/drugpure/cabinet/kihon53/te_4987060009616.jpg",
    "グロンサンゴールド錠Ａ": "https://tshop.r10s.jp/ads01/cabinet/p05/4987306045132.jpg",
    "コトブキ浣腸３０パステル": "https://tshop.r10s.jp/hanaxhanadrug/cabinet/default/itemrobot_iyakuhin1/4987388015016.jpg",
    "コトブキ浣腸４０": "https://tshop.r10s.jp/drugpure/cabinet/kihon21/4987388014019.jpg",
    "コトブキ浣腸４０パステル": "https://tshop.r10s.jp/beisia/cabinet/drug/set3/4987388034208-5_00.jpg",
    "コリイス浣腸３０": "https://tshop.r10s.jp/hanaxhanadrug/cabinet/default/itemrobot_iyakuhin1/4987388013012.jpg",
    "コリクリアーＳローション": "https://tshop.r10s.jp/koyamadrug/cabinet/12217305//p05/4987973113837-1.jpg",
    "ササイサン": "https://tshop.r10s.jp/ds-kotobukiya/cabinet/10548348/4987301780533.jpg",
    "サンワ白虎加人参湯エキス細粒": "https://tshop.r10s.jp/y-koto/cabinet/itempic11/4987327047146.jpg",
    "ザッツ": "https://tshop.r10s.jp/drug-sakura/cabinet/item06/4987316011097.jpg",
    "ストナデイタイム": "https://tshop.r10s.jp/drugpure/cabinet/kihon26/4987316012827m.jpg",
    "ストーゼ胃腸内服液": "https://tshop.r10s.jp/fuseyakuten/cabinet/202503/4987239127516.jpg",
    "ソルマックＥＸ２": "https://tshop.r10s.jp/jism/cabinet/0429/4987117396201.jpg",
    "タブローンＭⅡ": "https://tshop.r10s.jp/sakuraiyakuhinstore/cabinet/1/09418500/12734325/imgrc0121259788.jpg",
    "トチモトのオウレン末Ｐ": "https://tshop.r10s.jp/phmikawa2/cabinet/kihon6/4987466109040.jpg",
    "トチモトのオウレンＰ": "https://tshop.r10s.jp/kusurinoaoki/cabinet/tochimoto/4987466751829.jpg",
    "ナカジマオウレン": "https://tshop.r10s.jp/kobe-menken/cabinet/dw11/4936246100777.jpg",
    "ナカジマオウレン末": "https://tshop.r10s.jp/drugpure/cabinet/kihon40/4936246100784.jpg",
    "ナカジマキキョウ末": "https://tshop.r10s.jp/drugpure/cabinet/kihon40/4936246100753.jpg",
    "ニタンダ麻杏甘石湯エキス顆粒": "https://tshop.r10s.jp/akibaoo-r/cabinet/gi1049/4930342520057.jpg",
    "ニチイ胃腸内服液": "https://tshop.r10s.jp/sakuraiyakuhinstore/cabinet/1/09418500/12242331/imgrc0117263790.jpg",
    "ハイウルソグリーンＳ": "https://tshop.r10s.jp/benkyo/cabinet/shohin126/4987316093116.jpg",
    "バファリンかぜＥＸ錠《瓶》": "https://tshop.r10s.jp/n-yakuhin/cabinet/syouhin11/4903301010982.jpg",
    "パンジアス顆粒": "https://tshop.r10s.jp/jetdrug/cabinet/p05/4987241139460-01.jpg",
    "ヒストミンせき止め液ＮＸ": "https://tshop.r10s.jp/welpark/cabinet/202508shouhin05/4987336771513a.jpg",
    "フジコールＩＰ錠": "https://tshop.r10s.jp/genki-e-shop-hanshin/cabinet/b/4968250903112.jpg",
    "フラーリンＪ粒": "https://tshop.r10s.jp/leaf-land/cabinet/medication/herbal-medicine/4987474377141-1.jpg",
    "フラーリンＪ錠": "https://tshop.r10s.jp/doremi/cabinet/new4/4987474000070.jpg",
    "ミカサ浣腸Ｎ４０": "https://tshop.r10s.jp/drugpure/cabinet/kihon17/4987203001439.jpg",
    "ヤマサンオウレン": "https://tshop.r10s.jp/kusurinoaoki/cabinet/kojima/ouren.jpg",
    "ヤマサンオウレン末": "https://tshop.r10s.jp/doremi/cabinet/new4/4979654026673.jpg",
    "ヤマサンシャゼンソウ": "https://tshop.r10s.jp/gold/ds-kotobukiya/img2/item/4993512243231.jpg",
    "ワクナガ生薬胃腸薬": "https://tshop.r10s.jp/leaf-land/cabinet/medication/gastrointestinal/4968250169310.jpg",
    "仁壽": "https://tshop.r10s.jp/kyorindo/cabinet/item7/4987126202722.jpg",
    "再春痛散湯エキス顆粒": "https://tshop.r10s.jp/kobe-menken/cabinet/kihon03/4987174729011.jpg",
    "増田胃腸薬": "https://tshop.r10s.jp/sakuraiyakuhinstore/cabinet/1/09418500/imgrc0098001657.jpg",
    "大光丸": "https://tshop.r10s.jp/k-benkyo/cabinet/shohin14/4987110001737.jpg",
    "大草胃腸薬内服液３０": "https://tshop.r10s.jp/kenkoumate/cabinet/4976084021308.jpg",
    "御百草丸Ｕ": "https://tshop.r10s.jp/benkyo/cabinet/okihai01/4987352002813mail.jpg",
    "恵命我神散Ｓ＜細粒＞": "https://tshop.r10s.jp/kiraramagic/cabinet/03744007/07367706/11225517/4955982030117.jpg",
    "救胆": "https://tshop.r10s.jp/fortress/cabinet/products/12374699/4987061015791mede.jpg",
    "新グリーン胃腸薬ＤＸ": "https://tshop.r10s.jp/jetdrug/cabinet/p05-04/4987107170675-02.jpg",
    "新スキントールＳ": "https://tshop.r10s.jp/drug-sakura/cabinet/item04/4979949000777-5.jpg",
    "新セキリック液": "https://tshop.r10s.jp/nissin-yk/cabinet/04191107/10056731/12732928/4975979202327.jpg",
    "新バック液": "https://tshop.r10s.jp/fortress/cabinet/products/06713660/4976652016255medeal.jpg",
    "新マルコターンソフト": "https://tshop.r10s.jp/oxjap/cabinet/00220480/img59814673.jpg",
    "新リバヘルスゴールド": "https://tshop.r10s.jp/hb-eshop/cabinet/shouhin/05998122/4987306008007.jpg",
    "新新胃腸薬Ｓ": "https://tshop.r10s.jp/drugpure/cabinet/kihon70/4987074301553.jpg",
    "日野百草丸": "https://tshop.r10s.jp/drugpure/cabinet/kihon35/4987364004010.jpg",
    "暖中錠": "https://tshop.r10s.jp/koto-p/cabinet/itempic11/4987304041013.jpg",
    "本草センナ錠": "https://tshop.r10s.jp/sundrug/cabinet/68/4987334201081.jpg",
    "東洋漢方のセンナ顆粒Ｓ（分包）": "https://tshop.r10s.jp/ladydrugplus/cabinet/pic808/4979654021968_1.jpg",
    "清痛顆粒": "https://tshop.r10s.jp/genki-e-shop-hanshin/cabinet/j/4987305116819.jpg",
    "清風散": "https://tshop.r10s.jp/welpark/cabinet/10686711/4987045109287a.jpg",
    "熊膽圓Ｓ": "https://tshop.r10s.jp/ettyutoyama-genkidou/cabinet/shohin_01/syouhin202206/megumi_200.jpg",
    "百草丸プラス": "https://tshop.r10s.jp/supplement-is/cabinet/biiino/item/main-image/20260323185243_1.jpg",
    "竹参かぜまる": "https://tshop.r10s.jp/pmone/cabinet/4987045054556s3.jpg",
    "胃腸薬エースプラス": "https://tshop.r10s.jp/jetdrug/cabinet/p05-04/4987107627162-01.jpg",
    "薬草健胃薬Ｆ": "https://tshop.r10s.jp/fujiyaku/cabinet/item23/4987524071326.jpg",
    "複方熊胆丸": "https://tshop.r10s.jp/sakuraiyakuhinstore/cabinet/1/09418500/imgrc0097076858.jpg",
    "複方熊胆円": "https://tshop.r10s.jp/sakuraiyakuhinstore/cabinet/1/09418500/10107656/imgrc0106181408.jpg",
    "イブクイック頭痛薬": "https://images.microcms-assets.io/assets/5cd0cfb38d8449fe993f92b8c6c2c085/1ed0816cdb3247f5af6fa22f422ae383/product-eveq-img_02.jpg",
    "イブプロフェンソフトカプセル２００「キョーワ」": "https://shop.r10s.jp/doremi/cabinet/new4/4987060007858.jpg",
    "イブプロフェン錠２００Ｓ": "https://shop.r10s.jp/mprice-shop/cabinet/l/m2d1/4987037862411.jpg",
    "イブロック冷感Ｓ": "https://shop.r10s.jp/himaraya/cabinet/0000001310c/0000001310474_r1_01.jpg",
    "イブＡ錠": "https://images.microcms-assets.io/assets/5cd0cfb38d8449fe993f92b8c6c2c085/0dde9084b54e41459a7240b169b417b9/product-evea-img_02.jpg",
    "イブＡ錠ＥＸ": "https://images.microcms-assets.io/assets/5cd0cfb38d8449fe993f92b8c6c2c085/a9f3cbb1603b4a54923b16a0c010858b/product-eveaex-img_02.jpg",
    "オリブ油「タイセイ」Ｐ": "https://shop.r10s.jp/kenko-joy/cabinet/kusuri_002/4987286319124.jpg",
    "カイゲンＡＺのどスプレー": "https://shop.r10s.jp/sundrug/cabinet/2/4987040059822.jpg",
    "カゼンエース": "https://shop.r10s.jp/sugiyaku/cabinet/item/05145944/imgrc0091838248.jpg",
    "キンカンＡＬ錠": "https://shop.r10s.jp/besthbi/cabinet/goq001/45532_1.jpg",
    "クミアイ新頭痛錠": "https://shop.r10s.jp/drugpure/cabinet/01294619/4987343081568.jpg",
    "クールスロート": "https://shop.r10s.jp/leaf-land/cabinet/medication/oral-medicine/4987227029013-1.jpg",
    "グットエイドＥＸ": "https://shop.r10s.jp/jetdrug/cabinet/p05-04/4589788400012-04.jpg",
    "グリセリン浣腸Ａ１０": "https://shop.r10s.jp/tels/cabinet/itemrobot/26/a103hu_05.jpg",
    "コーフパウダー": "https://shop.r10s.jp/drugpure/cabinet/kihon24/4987441191879.jpg",
    "ザッツ錠": "https://shop.r10s.jp/drugpure/cabinet/kihon41/4987033209135.jpg",
    "ジキニン鼻炎ＡＧ顆粒": "https://shop.r10s.jp/kenko-joy/cabinet/item_019/4987305131324.jpg",
    "スカイブブロンのどスプレー": "https://shop.r10s.jp/fukuei/cabinet/01/16/510-6086-001_1.jpg",
    "スカイブブロンストレート": "https://shop.r10s.jp/fines-f/cabinet/20/4987076606021.jpg",
    "スカイブブロンＮＡスプレー": "https://shop.r10s.jp/fines-f/cabinet/17/4975979306001-10.jpg",
    "ストナのどスプレー": "https://www.stona.jp/products/images/product_img01_02.png",
    "スロナースのどスプレー": "https://shop.r10s.jp/reg-kenseido/cabinet/09109438/09109528/imgrc0157079681.jpg",
    "スースカット浣腸１０": "https://shop.r10s.jp/koto-p/cabinet/itempic10/4987388011414x10.jpg",
    "セイヨン総合かぜ薬": "https://shop.r10s.jp/genki-e-shop-hanshin/cabinet/b/4987307020688.jpg",
    "セデス・ハイ": "https://www.shionogi-hc.co.jp/content/dam/shc/jp/wellness/medicine/sh/images/sh.jpg",
    "デイトナＳ": "https://shop.r10s.jp/fine-kagaku/cabinet/az/medicine/500017_1.jpg",
    "デーチカ": "https://item-shopping.c.yimg.jp/i/n/satuma_4987474174160-dmc",
    "トキワイブプロエースＡ": "https://www.tokiwayakuhin.co.jp/img/goods/L/H177300.jpg",
    "トピックＧトローチ": "https://shop.r10s.jp/genki-e-shop-hanshin/cabinet/b/4975979330211.jpg",
    "ノイロンムーンＳ": "https://shop.r10s.jp/fumichan/cabinet/rakuten/rakuten3/4987299225313.jpg",
    "ハイカゼ内服液Ｓ": "https://shop.r10s.jp/sakuraiyakuhinstore/cabinet/1/09418500/10107656/imgrc0105635235.jpg",
    "バファリンプレミアム": "https://delivery-p62220-e526456.adobeaemcloud.com/adobe/assets/urn:aaid:aem:9720d1f7-7117-4e49-b36f-9c1cde9bd330/as/pdt_premium-sp_ava_l-jg.png",
    "バファリンＡ": "https://delivery-p62220-e526456.adobeaemcloud.com/adobe/assets/urn:aaid:aem:91ee1aa2-a1b5-41d9-99b3-0bc24ebd6ebf/as/pdt_a-sp_ava_l-jg.png",
    "パブロンゴールドＡ＜微粒＞": "https://www.catalog-taisho.com/content/dam/selfmedication/jp/ja/pabron/images/04515/04515_Product1.png",
    "フストールＳ": "https://shop.r10s.jp/genki-e-shop-hanshin/cabinet/b/4987299225719.jpg",
    "マキセリン「コタロー」": "https://shop.r10s.jp/pupuhima/cabinet/4987301003175.jpg",
    "リングルアイビー": "https://www.ringl.jp/assets/img/products/item01.png",
    "ルルアタックＴＲ": "https://www.daiichisankyo-hc.co.jp/library/content/img_library/image/lulu_attack_tr_1C290_main.jpg",
    "健栄のどフレッシュ": "https://shop.r10s.jp/sundrug/cabinet/21/4987286318264.jpg",
    "富士はら薬「赤玉」": "https://shop.r10s.jp/fujiyaku/cabinet/item23/4987524080519.jpg",
    "小中学生用ノーシンピュア": "https://www.arax.co.jp/norshinpure/pure_syou/assets/images/top/mv-package.png",
    "救風": "https://shop.r10s.jp/doremi/cabinet/new3/4987438076035.jpg",
    "新エスタックイブエースカプセル": "https://shop.r10s.jp/koyamadrug/cabinet/12217305//p05/4987300069011-1.jpg",
    "新エスベナントローチ": "https://shop.r10s.jp/shiraishiyakuhin/cabinet/0103101.jpg",
    "新スカイブブロンゴールド微粒": "https://shop.r10s.jp/fines-f/cabinet/20/4954391105270.jpg",
    "スカイブブロンEX": "https://shop.r10s.jp/doremi/cabinet/new3/4987299227829.jpg",
    "新スカイブブロンゴールド錠": "https://shop.r10s.jp/bloomgreen/cabinet/bz09436449/4987299227713.jpg",
    "新ストナエースＧ": "https://shop.r10s.jp/mprice-shop/cabinet/l/m2d/4987316014722.jpg",
    "東洋漢方の小青龍湯": "https://makeshop-multi-images.akamaized.net/5312/itemimages/000000001439_JZK4IKj.jpg",
    "第一三共胃腸薬コアブロック散剤": "https://shop.r10s.jp/aoki-industry/cabinet/05366027/item/imgrc0130541489.jpg",
    "胃健錠": "https://shop.r10s.jp/yotsubadrug/cabinet/09794708/4987306009776_1.jpg",
    "角野龍雲湯": "https://shop.r10s.jp/muraiyakuhin/cabinet/10858325/26/c66-1.jpg",
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
