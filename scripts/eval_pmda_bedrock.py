#!/usr/bin/env python3
"""Bedrock による PMDA 改善・正本の独立評価（2回の Converse 呼び出し）。"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import boto3  # noqa: E402

REGION = os.environ.get("AWS_REGION", "us-east-1")
MODEL_ID = os.environ.get(
    "PMDA_BEDROCK_EVAL_MODEL",
    "us.anthropic.claude-sonnet-4-6",
)
OUT_DIR = ROOT / "log" / "analysis"


def _converse(client, prompt: str, *, max_tokens: int = 1800) -> str:
    resp = client.converse(
        modelId=MODEL_ID,
        messages=[{"role": "user", "content": [{"text": prompt}]}],
        inferenceConfig={"maxTokens": max_tokens, "temperature": 0.2},
    )
    parts = resp.get("output", {}).get("message", {}).get("content") or []
    return "".join(p.get("text") or "" for p in parts if p.get("text"))


def main() -> int:
    token = os.environ.get("AWS_BEARER_TOKEN_BEDROCK", "")
    if not token:
        print("AWS_BEARER_TOKEN_BEDROCK not set", file=sys.stderr)
        return 1

    report_path = OUT_DIR / "pmda_canonical_eval_report.json"
    samples_path = OUT_DIR / "bedrock_eval_samples.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    samples = json.loads(samples_path.read_text(encoding="utf-8"))

    client = boto3.client("bedrock-runtime", region_name=REGION)

    improvement_prompt = f"""あなたは医薬品データエンジニアリングのレビュアーです。
以下の PMDA パイプライン改善を、5段階(1-5)と短い根拠で評価してください。

評価観点:
- 技術的正しさ（根本原因への対処）
- 正本性（PMDA原文への忠実さ）
- 再現性・運用性
- リスク（mergeバグ、データ喪失、幻覚）
- KB/RAG適性

改善一覧:
{json.dumps(report.get('improvements', {}), ensure_ascii=False, indent=2)}

before/after メトリクス:
{json.dumps({'before': report.get('before_backup', {}), 'after': report.get('after_current', {}), 'staging': report.get('staging_stats', {})}, ensure_ascii=False, indent=2)}

出力形式（JSONのみ）:
{{
  "overall_score_1_to_5": number,
  "scores": {{"technical": n, "canonical_fidelity": n, "operational": n, "risk": n, "rag_readiness": n}},
  "strengths": ["..."],
  "weaknesses": ["..."],
  "verdict": "..."
}}"""

    canonical_prompt = f"""あなたは OTC 医薬品推奨システムのデータ品質監査者です。
以下 CSV 正本サンプルが「PMDA §10/§11 ベースの正本」として KB に載せてよいか評価してください。

正本メトリクス:
{json.dumps(report.get('after_current', {}), ensure_ascii=False, indent=2)}

相互作用サンプル（PMDA）:
{json.dumps(samples.get('interactions_pmda_samples', [])[:3], ensure_ascii=False, indent=2)}

副作用サンプル（PMDA）:
{json.dumps(samples.get('side_effects_pmda_samples', [])[:3], ensure_ascii=False, indent=2)}

手動curatedサンプル（参考）:
{json.dumps(samples.get('manual_interactions_samples', []), ensure_ascii=False, indent=2)}

評価観点:
- 各行が§10/§11相当か（§18/HTMLボイラープレート/別製品文書の混入）
- 1行=1ペア/1成分として RAG で使える粒度か
- 説明の切り出し品質（途中開始、他薬剤混在）
- purge→KB 前の追加フィルタ要否

出力形式（JSONのみ）:
{{
  "kb_ready_score_1_to_5": number,
  "interactions_pmda_score_1_to_5": number,
  "side_effects_pmda_score_1_to_5": number,
  "purge_ready": true/false,
  "blocking_issues": ["..."],
  "non_blocking_issues": ["..."],
  "recommended_next_steps": ["..."],
  "verdict": "..."
}}"""

    results: dict = {"model_id": MODEL_ID, "region": REGION}
    try:
        results["improvements_eval"] = _converse(client, improvement_prompt)
        results["canonical_eval"] = _converse(client, canonical_prompt)
    except Exception as exc:
        results["error"] = f"{type(exc).__name__}: {exc}"
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        out = OUT_DIR / "pmda_bedrock_eval.json"
        out.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / "pmda_bedrock_eval.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
