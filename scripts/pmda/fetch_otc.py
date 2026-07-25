"""PMDA 市販薬 live fetch → staging/otc_products.json（otcSearch + 詳細 parse）。"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.pmda.common import (  # noqa: E402
    LOG_ANALYSIS_DIR,
    OTC_CSV,
    STAGING_OTC,
    load_json,
    normalize_text,
    product_key,
    read_csv_rows,
    save_json,
    utc_now_iso,
    write_fetch_log,
)
from scripts.pmda.http_client import PmdaFetchAborted, PmdaLiveSession  # noqa: E402
from scripts.pmda.normalize import normalize_otc_product_row  # noqa: E402
from scripts.pmda.queue import (  # noqa: E402
    check_live_fetch_guards,
    compact_product_name,
    normalize_product_search_name,
    product_key_to_row,
    product_search_name_variants,
)


def load_fixture_rows(fixture_path: Path) -> List[Dict[str, Any]]:
    data = load_json(fixture_path, [])
    if isinstance(data, dict) and isinstance(data.get("rows"), list):
        return data["rows"]
    if isinstance(data, list):
        return data
    return []


def select_diff_candidates(limit: int = 100) -> List[Dict[str, str]]:
    """baseline からサンプル品目を選ぶ（GO/NO-GO / 差分 fetch）。"""
    rows = read_csv_rows(OTC_CSV)
    candidates: List[Dict[str, str]] = []
    for row in rows:
        norm = normalize_otc_product_row(row)
        if norm:
            candidates.append(norm)
        if len(candidates) >= limit:
            break
    return candidates


def score_otc_match(
    query_name: str,
    query_mfr: str,
    hit_name: str,
    hit_mfr: str = "",
) -> int:
    """完全一致 → 正規化一致 → 部分一致。score >= 50 を採用。"""
    q = compact_product_name(query_name)
    h = compact_product_name(hit_name)
    if not q or not h:
        return 0
    qn = normalize_product_search_name(query_name)
    hn = normalize_product_search_name(hit_name)
    if q == h:
        score = 100
    elif qn and hn and qn == hn:
        score = 90
    elif qn and hn and (qn in hn or hn in qn):
        shorter, longer = (qn, hn) if len(qn) <= len(hn) else (hn, qn)
        score = int(100 * len(shorter) / max(len(longer), 1))
        if score < 50:
            return 0
    elif q in h or h in q:
        shorter, longer = (q, h) if len(q) <= len(h) else (h, q)
        score = int(100 * len(shorter) / max(len(longer), 1))
        if score < 50:
            return 0
    else:
        return 0

    qm = normalize_text(query_mfr)
    hm = normalize_text(hit_mfr)
    if qm and hm:
        qm_core = qm.replace("株式会社", "").replace("(株)", "").replace("（株）", "").strip()
        hm_core = hm.replace("株式会社", "").replace("(株)", "").replace("（株）", "").strip()
        if qm_core and hm_core and (qm_core in hm_core or hm_core in qm_core):
            score = min(100, score + 5)
    return score


def pick_best_otc_hit(
    product_name: str,
    manufacturer: str,
    hits: List[Dict[str, str]],
    *,
    min_score: int = 50,
) -> Tuple[Optional[Dict[str, str]], int]:
    best: Optional[Dict[str, str]] = None
    best_score = 0
    for hit in hits:
        score = score_otc_match(
            product_name,
            manufacturer,
            hit.get("product_name") or hit.get("text") or "",
            hit.get("manufacturer") or "",
        )
        if score > best_score:
            best_score = score
            best = hit
    if best_score < min_score:
        return None, best_score
    return best, best_score


def process_otc_product(session: PmdaLiveSession, key: str) -> Dict[str, Any]:
    """1 品目: 正規化検索（フォールバック付き） → マッチ → 詳細 parse。"""
    base = product_key_to_row(key)
    product_name = base["製品名"]
    manufacturer = base.get("メーカー名") or ""
    variants = product_search_name_variants(product_name)
    search_name = variants[0] if variants else product_name
    result: Dict[str, Any] = {
        "key": key,
        "product_name": product_name,
        "manufacturer": manufacturer,
        "search_name": search_name,
        "status": "failed",
        "reason": "",
        "score": 0,
        "row": None,
        "pmda_hit": "",
    }

    best = None
    score = 0
    for variant in variants:
        if session.stats.aborted:
            break
        result["search_name"] = variant
        try:
            html = session.fetch_otc_search(variant)
        except PmdaFetchAborted as exc:
            result["status"] = "aborted"
            result["reason"] = str(exc)
            return result
        if session.stats.aborted:
            result["status"] = "aborted"
            result["reason"] = session.stats.abort_reason or "aborted"
            return result
        if not html:
            continue
        hits = PmdaLiveSession.extract_otc_result_hits(html)
        cand, cand_score = pick_best_otc_hit(product_name, manufacturer, hits)
        if cand and cand_score > score:
            best, score = cand, cand_score
        # 採用可能ヒットがあれば追加検索しない（HTTP 節約）
        if best is not None:
            break

    result["score"] = score
    if not best:
        result["reason"] = "not_found"
        return result

    result["pmda_hit"] = best.get("product_name") or ""
    try:
        detail_html = session.fetch_otc_detail_html(best.get("fname") or best.get("href") or "")
    except PmdaFetchAborted as exc:
        result["status"] = "aborted"
        result["reason"] = str(exc)
        return result
    if session.stats.aborted:
        result["status"] = "aborted"
        result["reason"] = session.stats.abort_reason or "aborted"
        return result
    if not detail_html:
        result["reason"] = "empty_detail"
        return result

    parsed = PmdaLiveSession.parse_otc_detail_html(detail_html)
    if not parsed:
        result["reason"] = "parse_empty"
        return result

    # 分類 / 医薬品の種類は社内タクソノミ（リスク区分・効能カテゴリ）を正とする。
    # PMDA の薬効分類・リスク区分で上書きしない（推奨フィルタが壊れるため）。
    row = {
        "製品名": product_name,
        "メーカー名": manufacturer,
        "効能効果": parsed.get("効能効果") or "",
        "用法用量": parsed.get("用法用量") or "",
        "年齢制限": parsed.get("年齢制限") or "",
        "成分": parsed.get("成分") or "",
    }
    norm = normalize_otc_product_row(row)
    if not norm:
        result["reason"] = "normalize_failed"
        return result
    session.stats.hits += 1
    result["status"] = "done"
    result["row"] = norm
    return result


def write_otc_orphans(orphans: List[Dict[str, Any]]) -> Path:
    LOG_ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = utc_now_iso()[:10].replace("-", "")
    path = LOG_ANALYSIS_DIR / f"pmda_otc_orphans_{stamp}.json"
    save_json(
        path,
        {
            "generated_at": utc_now_iso(),
            "count": len(orphans),
            "orphans": orphans,
        },
    )
    return path


def fetch_otc_diff(
    *,
    live: bool = False,
    limit: int = 100,
    fixture_path: Path | None = None,
    min_interval: float = 3.0,
    batch_size: int = 10,
    allow_daytime: bool = False,
    force: bool = False,
    ignore_session_gap: bool = False,
    ignore_daily_limit: bool = False,
) -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []
    stats: Dict[str, Any] = {
        "requested": 0,
        "hits": 0,
        "errors": 0,
        "mode": "live" if live else "fixture",
        "abort_reason": "",
    }
    diff_log: List[Dict[str, Any]] = []
    orphans: List[Dict[str, Any]] = []

    if fixture_path:
        rows.extend(load_fixture_rows(fixture_path))
        stats["mode"] = "fixture"

    candidates = select_diff_candidates(limit=limit)

    if live:
        ok, reason = check_live_fetch_guards(
            allow_daytime=allow_daytime,
            force=force,
            ignore_session_gap=ignore_session_gap or force,
            ignore_daily_limit=ignore_daily_limit or force,
        )
        if not ok:
            stats["abort_reason"] = reason
            payload = {
                "generated_at": utc_now_iso(),
                "source": "live",
                "stats": stats,
                "diff_log": [],
                "rows": [],
                "guard_blocked": True,
            }
            save_json(STAGING_OTC, payload)
            return payload

        # batch_size=0: limit で制御（GO/NO-GO は form GET + 検索/詳細で複数 HTTP）
        session = PmdaLiveSession(min_interval_sec=min_interval, batch_size=0)
        try:
            with session:
                for product in candidates[:limit]:
                    if session.aborted:
                        break
                    key = product_key(product["製品名"], product.get("メーカー名") or "")
                    result = process_otc_product(session, key)
                    if result["status"] == "aborted":
                        stats["abort_reason"] = result.get("reason") or session.stats.abort_reason
                        break
                    if result["status"] == "done" and result.get("row"):
                        stats["hits"] += 1
                        rows.append(result["row"])
                        diff_log.append(
                            {
                                "product_name": result["product_name"],
                                "manufacturer": result["manufacturer"],
                                "pmda_hit": result.get("pmda_hit") or "",
                                "score": result.get("score") or 0,
                                "status": "found",
                            }
                        )
                    else:
                        stats["errors"] += 1
                        orphan = {
                            "product_name": result["product_name"],
                            "manufacturer": result["manufacturer"],
                            "search_name": result.get("search_name") or "",
                            "reason": result.get("reason") or "not_found",
                            "score": result.get("score") or 0,
                        }
                        orphans.append(orphan)
                        diff_log.append({**orphan, "status": "not_found"})
            stats["requested"] = session.stats.requested
            if session.stats.aborted and not stats["abort_reason"]:
                stats["abort_reason"] = session.stats.abort_reason
        except PmdaFetchAborted as exc:
            stats["abort_reason"] = str(exc)
            stats["requested"] = session.stats.requested
    else:
        rows.extend(candidates[: min(limit, len(candidates))])

    if orphans:
        write_otc_orphans(orphans)

    normalized = [normalize_otc_product_row(r) for r in rows if normalize_otc_product_row(r)]
    payload = {
        "generated_at": utc_now_iso(),
        "source": stats["mode"],
        "stats": stats,
        "diff_log": diff_log,
        "rows": normalized,
        "orphans": orphans,
    }
    save_json(STAGING_OTC, payload)
    write_fetch_log(
        "otc_diff",
        {"stats": stats, "diff_count": len(diff_log), "staging_count": len(normalized)},
    )
    return payload


def write_otc_staging(rows: List[Dict[str, Any]], stats: Dict[str, Any]) -> None:
    normalized = [normalize_otc_product_row(r) for r in rows if normalize_otc_product_row(r)]
    save_json(
        STAGING_OTC,
        {
            "generated_at": utc_now_iso(),
            "source": "live",
            "stats": stats,
            "rows": normalized,
            "live_only": True,
        },
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch PMDA OTC diff into staging JSON")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--fixture", type=Path, default=None)
    parser.add_argument("--min-interval", type=float, default=3.0)
    parser.add_argument("--live-batch-size", type=int, default=10)
    parser.add_argument("--allow-daytime", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    fixture = args.fixture
    if fixture is None and not args.live:
        default_fixture = ROOT / "tests" / "fixtures" / "pmda" / "otc_staging.json"
        if default_fixture.is_file():
            fixture = default_fixture

    result = fetch_otc_diff(
        live=args.live,
        limit=args.limit,
        fixture_path=fixture,
        min_interval=args.min_interval,
        batch_size=args.live_batch_size,
        allow_daytime=args.allow_daytime,
        force=args.force,
    )
    print(json.dumps({"staging": str(STAGING_OTC), "stats": result["stats"]}, ensure_ascii=False, indent=2))
    hits = (result.get("stats") or {}).get("hits", 0)
    errors = (result.get("stats") or {}).get("errors", 0)
    abort = (result.get("stats") or {}).get("abort_reason") or ""
    print(f"hits={hits} errors={errors} abort={abort!r}", file=sys.stderr)
    if abort and ("HTTP 403" in abort or "HTTP 429" in abort):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
