"""チャット型医薬品相談ツールの紹介資料に出す数字を集め、data.json に書く。

    python docs/slides/medicine-recommend-overview/data/calc.py
    node .cursor/skills/html-slides/scripts/inject-data.mjs slides.html pitch.html data/data.json

リポジトリの中のデータ（data/）・git の履歴・オフライン評価（log/analysis/）から数える。
調べた値（外部の統計・運用ドキュメントの値）は定数に出典を書く。
運用の月額は開発者の申告（合計のみ）。
"""
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
EVAL_JSON = ROOT / "log/analysis/2026-09-30_reco_offline_eval.json"

# ---- 調べた値 ----
MARKET_OTC_OKU = 9331          # 一般用医薬品の生産金額（億円）。厚生労働省「令和6年 薬事工業生産動態統計」
MARKET_YEAR = "2024"
MARKET_GROWTH = 6.0            # 同 前年比（%）
AGING_RATE = 29.3              # 65歳以上人口の割合（%）。総務省統計局「人口推計」2024年10月1日
VISITORS_MAN = 3687            # 訪日外客数（万人）。日本政府観光局（JNTO）2024年
AWS = {                        # docs/ops/AWS_COST_PLAN.md（2026-08-07 更新）
    "budget": 30,              # 月の予算（USD）
    "actual_week": 1.28,       # 2026-08-01〜08-07 の実績（新アカウント、USD）
    "stopped_lo": 6, "stopped_hi": 7,   # 停止が既定のときの月額の見込み（USD）
    "always_lo": 31, "always_hi": 32,   # 常に 1 タスク動かすときの月額の見込み（USD）
    "per_hour": 0.036,         # 起動中の 1 時間あたり（USD）
    "idle_min": 30,            # 使われない時間がこれだけ続くと止める（分）
    "wake_lo": 3, "wake_hi": 6,         # 止まった状態から開くまで（分）
}
JEV = {                        # docs/planning/codex-parallel-jev-20260921/jev_intent_router_eval_cost_latency_20260921.md
    "cur_avg": 1456.28, "jev_avg": 536.78,
    "cur_p95": 3216.91, "jev_p95": 594.15,
    "n": 30, "acc_cur": 30, "acc_jev": 30,
}
WEIGHTS = {                    # src/security/enhanced_safety_checker.py ENHANCED_SCORING_WEIGHTS
    "症状適合度": 0.30, "効能特異性": 0.20, "年齢適合性": 0.12, "副作用リスク": 0.10,
    "安全性スコア": 0.08, "相互作用リスク": 0.05, "用法簡便性": 0.03,
}
DEV_SINCE = "2025-10-01"
COST_MONTHLY_YEN = 3000       # 運用の月額の合計（円）。開発者の申告（2026-09-30）、内訳は未集計
EVAL_BEFORE_JSON = ROOT / "log/analysis/2026-09-30_reco_offline_eval_before_fix.json"


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True,
                          encoding="utf-8").stdout


def db_stats() -> dict:
    otc = pd.read_csv(ROOT / "data/otc_medicine_data.csv")
    cls = otc["分類"].fillna("不明").value_counts()
    order = ["第1類", "指定第2類", "第2類", "第3類"]
    cls_vals = [int(cls.get(k, 0)) + (int(cls.get("指定第1類", 0)) if k == "第1類" else 0) for k in order]
    inter = pd.read_csv(ROOT / "data/medicine_interactions.csv")
    lv = inter["相互作用レベル"].value_counts()
    se = pd.read_csv(ROOT / "data/medicine_side_effects.csv")
    eff = pd.read_csv(ROOT / "data/summarized_efficacy_data.csv")
    sd = json.loads((ROOT / "data/symptom_dictionary.json").read_text(encoding="utf-8"))
    ing = json.loads((ROOT / "data/ingredient_dictionary.json").read_text(encoding="utf-8"))
    img = json.loads((ROOT / "data/otc_image_versions.json").read_text(encoding="utf-8"))
    doping = otc["禁止物質あり"].astype(str).str.strip() == "禁止物質あり"
    self_select = cls_vals[1] + cls_vals[2] + cls_vals[3]
    return {
        "self_share": round(self_select / sum(cls_vals) * 100, 1),
        "products": int(len(otc)),
        "unique": int(otc["製品名"].nunique()),
        "makers": int(otc["メーカー名"].nunique()),
        "cls_labels": ["第1類", "指定第2類", "第2類", "第3類"],
        "cls_values": cls_vals,
        "doping": int(doping.sum()),
        "inter": int(len(inter)),
        "inter_hi": int(lv.get("高", 0)), "inter_mid": int(lv.get("中", 0)), "inter_lo": int(lv.get("低", 0)),
        "side": int(len(se)),
        "eff": int(len(eff)),
        "symptoms": len(sd),
        "synonyms": sum(len(v.get("synonyms", [])) for v in sd.values()),
        "ingredients": len(ing),
        "images": len(img),
    }


def dev_stats() -> dict:
    dates = git("log", f"--since={DEV_SINCE}", "--format=%ad", "--date=short").split()
    months = Counter(d[:7] for d in dates)
    labels = sorted(months)
    src = [p for p in git("ls-files", "src").splitlines() if p.endswith(".py")]
    lines = sum(len((ROOT / p).read_text(encoding="utf-8", errors="ignore").splitlines()) for p in src)
    tests = [p for p in git("ls-files", "tests").splitlines() if p.endswith(".py")]
    test_funcs = sum(len(re.findall(r"^\s*(?:async\s+)?def test_", (ROOT / p).read_text(encoding="utf-8", errors="ignore"), re.M))
                     for p in tests)
    docs_md = [p for p in git("ls-files", "docs").splitlines() if p.endswith(".md")]
    return {
        "commits": len(dates),
        "first": min(dates), "last": max(dates),
        "month_labels": [f"{int(m[5:])}月" for m in labels],
        "month_values": [months[m] for m in labels],
        "src_files": len(src),
        "src_klines": round(lines / 1000, 1),
        "test_funcs": test_funcs,
        "docs_md": len(docs_md),
    }


def eval_stats(path: Path = EVAL_JSON) -> dict:
    s = json.loads(path.read_text(encoding="utf-8"))["summary"]
    pct = lambda k: None if s[k]["rate"] is None else round(s[k]["rate"] * 100, 1)
    by_age = s["age_violation_by_age"]
    ages = [a for a in by_age if by_age[a]["n"]]
    return {
        "total": s["cases_total"],
        "groups": s["cases_by_group"],
        "errors": s["errors"],
        "error_symptoms": "・".join(s.get("error_symptoms", [])),
        "no_reco_age3": pct("no_reco_age3"),
        "no_reco_4plus": pct("no_reco_age4plus"),
        "no_reco_symptoms": len(s.get("no_reco_symptoms_all_ages", [])),
        "age_any": pct("age_violation_any_top3"), "age_any_k": s["age_violation_any_top3"]["k"],
        "age_any_n": s["age_violation_any_top3"]["n"],
        "age_top1": pct("age_violation_top1"),
        "age_labels": [f"{a}歳" for a in ages],
        "age_values": [round(by_age[a]["rate"] * 100, 1) for a in ages],
        "nsaid_any": pct("interaction_violation_nsaid_top3"),
        "nsaid_top1": pct("interaction_violation_nsaid_top1"),
        "datahigh_any": pct("interaction_violation_any_top3"),
        "eff_top1": pct("efficacy_text_match_top1"),
        "type_top1": pct("type_match_top1"),
        "tie2": pct("tie_top2"), "tie3": pct("tie_top3"),
        "preg_reco": pct("pregnant_recommended"),
        "preg_ref": pct("pregnant_referral"),
        "dur_ref": pct("duration_referral"),
        "dur_parsed": pct("duration_parsed") if "duration_parsed" in s else None,
        "emer_rule": pct("emergency_rule_recall"),
        "emer_cand": pct("emergency_candidate_recall"),
        "emer_missed": len(s["emergency_missed"]),
        "emer_hit": s["cases_by_group"]["emergency"] - len(s["emergency_missed"]),
        "fp": pct("normal_false_positive"),
        "lat_p50": s["latency_sec"]["p50"], "lat_p95": s["latency_sec"]["p95"],
    }


def main() -> int:
    db = db_stats()
    dev = dev_stats()
    ev = eval_stats()
    before = eval_stats(EVAL_BEFORE_JSON)
    ev["before"] = {k: before[k] for k in ("errors", "no_reco_4plus", "age_any", "tie2")}
    jev = dict(JEV)
    jev["speedup"] = round(JEV["cur_avg"] / JEV["jev_avg"], 2)
    jev["p95_cut"] = round((1 - JEV["jev_p95"] / JEV["cur_p95"]) * 100, 1)
    data = {
        "db": db, "dev": dev, "eval": ev, "jev": jev, "aws": AWS,
        "market": {"otc_oku": MARKET_OTC_OKU, "year": MARKET_YEAR, "growth": MARKET_GROWTH,
                   "aging": AGING_RATE, "visitors": VISITORS_MAN},
        "weights": {"labels": list(WEIGHTS), "values": list(WEIGHTS.values())},
        "cost": {"monthly_yen": COST_MONTHLY_YEN},
    }
    (HERE / "data.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: data[k] for k in ("db", "dev", "eval")}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
