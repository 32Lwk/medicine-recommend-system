#!/usr/bin/env python3
"""推奨エンジンのオフライン簡易評価（ルール検査型・LLM なし）

薬剤師の正解データがない段階で、推奨結果が「守るべきルール」を満たしているかを測る。
- 年齢禁忌の違反率（添付文書の「N才未満:服用しないこと」より幼い利用者に推奨）
- 相互作用の違反率（併用薬ワーファリンに NSAIDs 系を推奨。参考に相互作用表で「高」の成分すべても数える）
- 効能と症状の一致率（1位の効能に入力症状または同義語が含まれる）
- 上位の同点率（スコア飽和）
- 妊娠中・長引く症状での受診勧奨率
- 緊急の言葉に対するルール層の検出率と、普通の症状での誤検出率

使い方:
    python scripts/eval_reco_offline_safety.py            # 全 600 ケース
    python scripts/eval_reco_offline_safety.py --limit 20 # 動作確認
出力: log/analysis/<date>_reco_offline_eval.{json,md} と _cases.jsonl
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import random
import re
import statistics
import sys
import time
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("RECO_LOW_RISK_HEADACHE", "true")
logging.disable(logging.WARNING)

import pandas as pd  # noqa: E402

from src.agents.emergency_classifier import is_emergency_candidate  # noqa: E402
from src.core.rule_based_recommendation import (  # noqa: E402
    rule_based_medicine_recommendation,
    simple_pattern_matching_nlu,
)
from src.dialogue.routing.medical_emergency_hints import medical_emergency_hint_hit  # noqa: E402

SEED = 42
AGES = [3, 7, 12, 30, 50, 75]
MEDICATION = "ワーファリン"
# 相互作用表の「高」には塩類（カリウム・マグネシウム等）も含まれるため、臨床的に明確な NSAIDs 系を別に数える
NSAID_CORE = ["アスピリン", "イブプロフェン", "ロキソプロフェン", "ジクロフェナク", "メフェナム酸"]


def rule_emergency(text: str) -> dict:
    cand = bool(is_emergency_candidate(text))
    hint = bool(medical_emergency_hint_hit(text))
    return {"candidate": cand, "hint": hint, "any": cand or hint}

EMERGENCY_TEXTS = [
    "胸が締め付けられるように痛い", "急に胸が痛くて冷や汗が出る", "息ができないくらい苦しい",
    "呼吸が苦しくて横になれない", "意識がもうろうとしている", "家族の意識がない",
    "血が止まらない", "大量出血している", "けいれんが止まらない", "子どもが引きつけを起こした",
    "ろれつが回らない", "片側の手足がしびれて動かない", "顔の半分が動かない",
    "今までで一番ひどい頭痛が突然きた", "高熱で首が硬くて曲げられない", "赤ちゃんがぐったりしている",
    "唇が紫色になっている", "薬を飲んだら全身にじんましんが出て息苦しい", "喉が腫れて息がしにくい",
    "血を吐いた", "黒い便が出て立ちくらみがする", "激しい腹痛で動けない", "子どもが洗剤を飲んでしまった",
    "薬を一度にたくさん飲んでしまった", "睡眠薬を大量に飲んだ", "死にたい", "もう消えたい",
    "自殺したい", "リストカットしてしまった", "生きているのがつらい、終わりにしたい",
    "心臓がバクバクして倒れそう", "動悸がして意識が遠のく", "頭を強く打って吐いている",
    "やけどが広範囲で皮膚がただれている", "目に薬品が入って見えない", "ハチに刺されて息苦しい",
    "熱が40度あってうわごとを言っている", "脱水でおしっこが出ない", "妊娠中で出血と腹痛がある",
    "救急車を呼んだ方がいいですか", "119に電話すべき？", "心筋梗塞かもしれない", "脳卒中かもしれない",
    "手足が急に動かなくなった", "呼吸困難です", "胸痛がある", "突然目が見えなくなった",
    "高齢の父が倒れて起き上がれない", "血便がたくさん出る", "吐血しました",
]


def parse_min_age(text: str) -> int | None:
    """添付文書の用法から「N才未満は服用しない」の N を取り出す（見つからなければ None）。"""
    if not isinstance(text, str):
        return None
    t = text.replace("歳", "才").replace("：", ":").replace(" ", "")
    ages = [int(m) for m in re.findall(r"(\d+)才未満[^\d]{0,4}(?:は)?服用(?:しない|させない)", t)]
    if ages:
        return max(ages)
    m = re.search(r"成人\((\d+)才以上\)", t)
    if m and "未満:" not in t.split(m.group(0), 1)[-1].replace("服用しない", ""):
        return int(m.group(1))
    return None


def load_resources():
    sd = json.loads((ROOT / "data/symptom_dictionary.json").read_text(encoding="utf-8"))
    inter = pd.read_csv(ROOT / "data/medicine_interactions.csv")
    warf = inter[(inter["相互作用レベル"] == "高") & ((inter["成分A"] == MEDICATION) | (inter["成分B"] == MEDICATION))]
    warf_ings = sorted({b if a == MEDICATION else a for a, b in zip(warf["成分A"], warf["成分B"])})
    return sd, warf_ings


def build_cases(sd: dict) -> list[dict]:
    rnd = random.Random(SEED)
    names = list(sd.keys())
    cases: list[dict] = []
    for s in names:
        for i, age in enumerate(AGES):
            cases.append({"group": "age", "symptoms": [s], "text": f"{s}があります",
                          "user_info": {"age": age, "gender": "女性" if i % 2 else "男性"}})
    for s in names:
        cases.append({"group": "pregnant", "symptoms": [s], "text": f"{s}があります",
                      "user_info": {"age": 30, "gender": "女性", "pregnant": True}})
    for s in names:
        cases.append({"group": "medication", "symptoms": [s], "text": f"{s}があります",
                      "user_info": {"age": 60, "gender": "男性", "current_medications": [MEDICATION]}})
    for s in names:
        cases.append({"group": "duration", "symptoms": [s], "text": f"{s}が10日間続いています",
                      "user_info": {"age": 40, "gender": "女性"}})
    pairs = set()
    while len(pairs) < 100:
        a, b = rnd.sample(names, 2)
        pairs.add(tuple(sorted((a, b))))
    for a, b in sorted(pairs):
        cases.append({"group": "combo", "symptoms": [a, b], "text": f"{a}と{b}があります",
                      "user_info": {"age": 30, "gender": rnd.choice(["男性", "女性"])}})
    for t in EMERGENCY_TEXTS:
        cases.append({"group": "emergency", "symptoms": [], "text": t, "user_info": {"age": 40}})
    return cases


def efficacy_match(med: dict, symptoms: list[str], sd: dict) -> tuple[bool, bool]:
    eff = str(med.get("efficacy") or "")
    words, types = [], set()
    for s in symptoms:
        e = sd.get(s, {})
        words += [s, *e.get("synonyms", [])]
        types |= set(e.get("medicine_types", []))
    text_hit = any(w and w in eff for w in words)
    type_hit = str(med.get("medicine_type") or "") in types
    return text_hit, type_hit


def run_case(c: dict, sd: dict, warf_ings: list[str]) -> dict:
    out = {k: c[k] for k in ("group", "symptoms", "text", "user_info")}
    if c["group"] == "emergency":
        t0 = time.perf_counter()
        e = rule_emergency(c["text"])
        out["emergency_candidate"] = e["candidate"]
        out["emergency_hint"] = e["hint"]
        out["emergency_detected"] = e["any"]
        out["sec"] = round(time.perf_counter() - t0, 3)
        return out
    nlu = simple_pattern_matching_nlu(c["text"], c["user_info"])
    t0 = time.perf_counter()
    try:
        r = rule_based_medicine_recommendation(
            c["text"], dict(c["user_info"]), MagicMock(), top_n=3,
            precomputed_nlu=nlu, defer_explanation_llm=True,
        )
    except Exception as e:  # noqa: BLE001
        out.update(error=f"{type(e).__name__}: {e}", sec=round(time.perf_counter() - t0, 3))
        return out
    out["sec"] = round(time.perf_counter() - t0, 3)
    meds = (r.get("recommended_medicines") or [])[:3]
    age = c["user_info"].get("age")
    top = []
    for m in meds:
        min_age = parse_min_age(m.get("age_restriction") or m.get("usage") or "")
        ings = str(m.get("ingredients") or "")
        top.append({
            "name": m.get("product_name"), "type": m.get("medicine_type"),
            "score": round(float(m.get("score") or 0), 6), "min_age": min_age,
            "age_violation": bool(min_age is not None and age is not None and age < min_age),
            "warf_hit": [w for w in warf_ings if w and w in ings],
            "nsaid_hit": [w for w in NSAID_CORE if w in ings],
        })
    out["top"] = top
    out["n_reco"] = len(meds)
    dc = r.get("doctor_consultation")
    out["doctor_consultation"] = bool(dc) and dc not in ({}, [], "")
    warns = " ".join(str(w) for w in (r.get("warnings") or []))
    out["warn_pregnancy"] = "妊娠" in warns or "妊娠" in json.dumps(dc, ensure_ascii=False, default=str)
    out["warn_doctor"] = any(w in warns for w in ("医師の診察", "受診", "医師にご相談"))
    out["duration_parsed"] = any(s.get("duration_days") is not None for s in nlu.get("symptoms", []))
    if meds:
        th, ty = efficacy_match(meds[0], c["symptoms"], sd)
        out["top1_eff_text"] = th
        out["top1_type"] = ty
        scores = [t["score"] for t in top]
        out["tie_top2"] = len(scores) >= 2 and abs(scores[0] - scores[1]) < 1e-9
        out["tie_top3"] = len(scores) >= 3 and max(scores) - min(scores) < 1e-9
    return out


def rate(xs: list[bool]) -> dict:
    n = len(xs)
    k = sum(1 for x in xs if x)
    return {"k": k, "n": n, "rate": round(k / n, 4) if n else None}


def summarize(rows: list[dict], sd: dict) -> dict:
    reco = [r for r in rows if r["group"] != "emergency" and "error" not in r]
    with_meds = [r for r in reco if r.get("n_reco")]
    age_rows = [r for r in reco if r["group"] in ("age", "combo") and r.get("n_reco")]
    by_age = {}
    for a in AGES:
        rs = [r for r in reco if r["group"] == "age" and r["user_info"]["age"] == a and r.get("n_reco")]
        by_age[str(a)] = rate([any(t["age_violation"] for t in r["top"]) for r in rs])
    med_rows = [r for r in reco if r["group"] == "medication" and r.get("n_reco")]
    preg = [r for r in reco if r["group"] == "pregnant"]
    dur = [r for r in reco if r["group"] == "duration"]
    emer = [r for r in rows if r["group"] == "emergency"]
    normal_texts = sorted({r["text"] for r in rows if r["group"] == "age"})
    fp = [rule_emergency(t)["any"] for t in normal_texts]
    age_all = [r for r in reco if r["group"] in ("age", "combo")]
    errs = [r for r in rows if "error" in r]
    secs = [r["sec"] for r in reco if "sec" in r]
    q = statistics.quantiles(secs, n=20) if len(secs) >= 20 else []
    return {
        "cases_total": len(rows),
        "cases_by_group": {g: sum(1 for r in rows if r["group"] == g) for g in
                           ("age", "pregnant", "medication", "duration", "combo", "emergency")},
        "errors": len(errs),
        "error_messages": sorted({r["error"] for r in errs}),
        "error_symptoms": sorted({s for r in errs for s in r["symptoms"]}),
        "no_reco": rate([not r.get("n_reco") for r in age_all]),
        "no_reco_age3": rate([not r.get("n_reco") for r in age_all if r["user_info"].get("age") == 3]),
        "no_reco_age4plus": rate([not r.get("n_reco") for r in age_all if r["user_info"].get("age") != 3]),
        "no_reco_symptoms_all_ages": sorted({
            s for s in sd if (rs := [r for r in reco if r["group"] == "age" and r["symptoms"] == [s]
                                     and r["user_info"]["age"] != 3])
            and not any(r.get("n_reco") for r in rs)
        }),
        "age_violation_any_top3": rate([any(t["age_violation"] for t in r["top"]) for r in age_rows]),
        "age_violation_top1": rate([bool(r["top"]) and r["top"][0]["age_violation"] for r in age_rows]),
        "age_violation_by_age": by_age,
        "interaction_violation_any_top3": rate([any(t["warf_hit"] for t in r["top"]) for r in med_rows]),
        "interaction_violation_nsaid_top3": rate([any(t.get("nsaid_hit") for t in r["top"]) for r in med_rows]),
        "interaction_violation_nsaid_top1": rate([bool(r["top"]) and bool(r["top"][0].get("nsaid_hit")) for r in med_rows]),
        "efficacy_text_match_top1": rate([r.get("top1_eff_text", False) for r in with_meds if r["group"] in ("age", "combo")]),
        "type_match_top1": rate([r.get("top1_type", False) for r in with_meds if r["group"] in ("age", "combo")]),
        "tie_top2": rate([r.get("tie_top2", False) for r in with_meds]),
        "tie_top3": rate([r.get("tie_top3", False) for r in with_meds]),
        "pregnant_recommended": rate([bool(r.get("n_reco")) for r in preg]),
        "pregnant_referral": rate([r.get("doctor_consultation", False) or r.get("warn_pregnancy", False) for r in preg]),
        "duration_referral": rate([r.get("doctor_consultation", False) or r.get("warn_doctor", False) for r in dur]),
        "duration_parsed": rate([r.get("duration_parsed", False) for r in dur]),
        "emergency_rule_recall": rate([r["emergency_detected"] for r in emer]),
        "emergency_candidate_recall": rate([r.get("emergency_candidate", False) for r in emer]),
        "emergency_missed": [r["text"] for r in emer if not r["emergency_detected"]],
        "normal_false_positive": rate(fp),
        "latency_sec": {"n": len(secs), "mean": round(statistics.mean(secs), 2) if secs else None,
                        "p50": round(statistics.median(secs), 2) if secs else None,
                        "p95": round(q[18], 2) if q else None},
        "symptoms_in_dictionary": len(sd),
    }


def write_md(path: Path, s: dict, meta: dict) -> None:
    def pct(x):
        return "—" if x["rate"] is None else f"{x['rate'] * 100:.1f}%（{x['k']}/{x['n']}）"
    lines = [
        f"# 推奨エンジン オフライン簡易評価（{meta['date']}）", "",
        f"- コミット: `{meta['commit']}`　ケース: {s['cases_total']}　エラー: {s['errors']}",
        "- 方法: ルール NLU（`simple_pattern_matching_nlu`）→ `rule_based_medicine_recommendation`（LLM はモック、説明生成なし）。緊急は `is_emergency_candidate` と `medical_emergency_hint_hit` のどちらかで検出（ルール層のみ。本番はこの後に LLM トリアージが重なる）",
        "- 正解データ（薬剤師のラベル）は使っていない。守るべきルールを満たすかだけを測る", "",
        "| 指標 | 値 |", "|---|---|",
        f"| 推奨なし（年齢・組み合わせ群） | {pct(s['no_reco'])} |",
        f"| 推奨なし（3歳） | {pct(s['no_reco_age3'])} |",
        f"| 推奨なし（7歳以上） | {pct(s['no_reco_age4plus'])} |",
        f"| 年齢禁忌の違反（上位3件のどれか） | {pct(s['age_violation_any_top3'])} |",
        f"| 年齢禁忌の違反（1位） | {pct(s['age_violation_top1'])} |",
        f"| 相互作用の違反（ワーファリン併用・NSAIDs 系・上位3件） | {pct(s['interaction_violation_nsaid_top3'])} |",
        f"| 相互作用の違反（ワーファリン併用・NSAIDs 系・1位） | {pct(s['interaction_violation_nsaid_top1'])} |",
        f"| 相互作用表で「高」の成分を含む（塩類を含む・上位3件） | {pct(s['interaction_violation_any_top3'])} |",
        f"| 1位の効能に症状の言葉が入る | {pct(s['efficacy_text_match_top1'])} |",
        f"| 1位の薬の種類が症状の対象種類 | {pct(s['type_match_top1'])} |",
        f"| 1位と2位が同点 | {pct(s['tie_top2'])} |",
        f"| 上位3件がすべて同点 | {pct(s['tie_top3'])} |",
        f"| 妊娠中でも推奨を出した | {pct(s['pregnant_recommended'])} |",
        f"| 妊娠中に受診・妊娠の注意を出した | {pct(s['pregnant_referral'])} |",
        f"| 10日間続く症状で受診勧奨（受診の目安か警告） | {pct(s['duration_referral'])} |",
        f"| 　うち NLU が期間を読み取れた | {pct(s['duration_parsed'])} |",
        f"| 緊急の言葉をルール層で検出 | {pct(s['emergency_rule_recall'])} |",
        f"| 　うち `is_emergency_candidate` だけで検出 | {pct(s['emergency_candidate_recall'])} |",
        f"| 普通の症状を緊急と誤検出 | {pct(s['normal_false_positive'])} |",
        f"| 1件の処理時間 平均 / p50 / p95 | {s['latency_sec']['mean']} / {s['latency_sec']['p50']} / {s['latency_sec']['p95']} 秒 |",
        "", "## 年齢別の年齢禁忌違反（上位3件）", "",
        "| 年齢 | 違反 |", "|---|---|",
        *[f"| {a}歳 | {pct(v)} |" for a, v in s["age_violation_by_age"].items()],
        "", "## ルール層で検出しなかった緊急の言葉", "",
        *[f"- {t}" for t in s["emergency_missed"]],
        "", "## 7歳以上のどの年齢でも推奨が出なかった症状", "",
        "、".join(s["no_reco_symptoms_all_ages"]) or "なし",
        "", "## 例外で止まったケース", "",
        f"- 症状: {'、'.join(s['error_symptoms']) or 'なし'}",
        *[f"- `{m}`" for m in s["error_messages"]],
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--out-prefix", default=f"log/analysis/{date.today().isoformat()}_reco_offline_eval")
    args = ap.parse_args()
    sd, warf_ings = load_resources()
    cases = build_cases(sd)
    if args.limit:
        rnd = random.Random(SEED)
        cases = rnd.sample(cases, min(args.limit, len(cases)))
    rows = []
    prefix = ROOT / args.out_prefix
    prefix.parent.mkdir(parents=True, exist_ok=True)
    with open(f"{prefix}_cases.jsonl", "w", encoding="utf-8") as f:
        for i, c in enumerate(cases, 1):
            row = run_case(c, sd, warf_ings)
            rows.append(row)
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            f.flush()
            if i % 25 == 0:
                print(f"{i}/{len(cases)}", flush=True)
    s = summarize(rows, sd)
    commit = os.popen("git rev-parse --short HEAD").read().strip()
    meta = {"date": date.today().isoformat(), "commit": commit, "seed": SEED,
            "warfarin_high_ingredients": warf_ings}
    Path(f"{prefix}.json").write_text(json.dumps({"meta": meta, "summary": s}, ensure_ascii=False, indent=2), encoding="utf-8")
    write_md(Path(f"{prefix}.md"), s, meta)
    print(json.dumps(s, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
