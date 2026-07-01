#!/usr/bin/env python3
"""Merge Wave A/B drafts into final dev log analysis report."""
from __future__ import annotations

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BASE = PROJECT_ROOT / "log" / "analysis" / "2026-06-30-dev-9-11"
OUT = PROJECT_ROOT / "log" / "analysis" / "2026-07-01_2026-06-30-dev-9-11.md"

WAVE_A = [
    ("インフラ・エラー", "draft_infra_errors.md"),
    ("性能・コスト", "draft_performance_cost.md"),
    ("会話品質（横断）", "draft_conversation_quality.md"),
    ("連携・その他", "draft_integrations.md"),
]

GRADE_ORDER = {"poor": 0, "needs_improvement": 1, "acceptable_with_issues": 2, "good": 3, "excellent": 4}


def main() -> None:
    meta = json.loads((BASE / "metadata.json").read_text(encoding="utf-8"))
    qm = json.loads((BASE / "quality_metrics.json").read_text(encoding="utf-8"))
    us = json.loads((BASE / "sections/user_sessions.json").read_text(encoding="utf-8"))
    sessions = us["session_conversations"]["sessions"]
    ranked = sorted(
        sessions,
        key=lambda s: (
            GRADE_ORDER.get(s.get("evaluation", {}).get("overall_grade", "good"), 9),
            -s.get("evaluation", {}).get("issue_count", 0),
        ),
    )
    top20 = ranked[:20]

    parts: list[str] = []
    parts.append("# GCP / Local Dev Log Analysis Report\n")
    parts.append("## メタデータ\n")
    parts.append("| 項目 | 値 |")
    parts.append("|------|-----|")
    parts.append("| ソース | `log/log/2026-06-30-9.md`, `-10.md`, `-11.md` |")
    parts.append("| 環境 | **local-dev**（ローカル v2 チャットテスト） |")
    parts.append(f"| 期間 | {meta['time_range']['start']} .. {meta['time_range']['end']} |")
    parts.append(
        f"| エントリ数 | {meta['entry_count']} "
        f"(ERROR {meta['severity_counts'].get('ERROR', 0)} / "
        f"WARNING {meta['severity_counts'].get('WARNING', 0)}) |"
    )
    c = qm["conversation"]
    parts.append(
        f"| セッション | 全体 {c['session_count']} / エクスポート {c['exported_session_count']} "
        f"(counseling {c['counseling_session_count']} / trace-only {c['trace_only_session_count']}) |"
    )
    parts.append("| 抽出 | `log/analysis/2026-06-30-dev-9-11/` |")
    parts.append("")

    parts.append("## エグゼクティブサマリー\n")
    parts.append(
        "2026-06-30 午後の local v2 統合テスト（3 ログファイル・約 3.4 時間）では、"
        "**OpenAI `insufficient_quota`（429）** が 14:15 頃から約 1 時間継続し、トリアージが `Other/error` に落ちる "
        "Clarification ループを誘発した。quota 復旧後も **`is_llm_triage_infrastructure_error` の NameError** が "
        "16:12〜17:22 に 78 件の HTTP 500 / SSE 失敗を引き起こし、インフラ障害時の graceful degradation が機能しなかった。\n"
    )
    parts.append(
        "会話品質はエクスポート 50 セッション中 **good 54%** だが **acceptable_with_issues 38%**。"
        "挨拶フォールバック（`greeting_to_non_greeting` 12 件）と店舗問い合わせの Store ルート未反映が横断的課題。"
        "性能面では推奨フルパスが **中央値 9.9s / p95 60.6s / 最大 78.6s**、LLM コスト **143 JPY / 1,261 calls**。"
        "Neon 接続は安定、LINE Webhook は本ウィンドウ未カバー。医療緊急キーワード経路は quota 後も正常。\n"
    )

    for title, fname in WAVE_A:
        path = BASE / fname
        if path.is_file():
            body = path.read_text(encoding="utf-8")
            # strip top h1 to avoid duplicate
            lines = body.splitlines()
            if lines and lines[0].startswith("# "):
                lines = lines[1:]
            parts.append(f"## {title}\n")
            parts.append("\n".join(lines).strip())
            parts.append("")

    parts.append("## 意図ずれ・品質問題（intent_mismatches）\n")
    parts.append("| 時刻 | session_id | ユーザー入力 | issue_type | 深刻度 |")
    parts.append("|------|------------|--------------|------------|--------|")
    for m in us.get("intent_mismatches", []):
        sev = m.get("severity", "")
        icon = "🔴" if sev == "critical" else "🟡" if sev == "warning" else "🟢"
        inp = (m.get("user_input") or "").replace("|", "\\|")[:60]
        parts.append(
            f"| {str(m.get('timestamp', ''))[:19]} | `{m.get('session_id', '')}` | {inp} | "
            f"`{m.get('issue_type', '')}` | {icon} {sev} |"
        )
    parts.append("")

    parts.append("## セッション評価（Wave B — 問題度上位 20 件）\n")
    parts.append(
        "全ターン transcript は `log/analysis/2026-06-30-dev-9-11/sessions/<session_id>.md`。"
        "深掘り draft は `draft_session_<session_id>.md`。\n"
    )
    parts.append("| session_id | grade | issue | ターン | draft |")
    parts.append("|------------|-------|-------|--------|-------|")
    for s in top20:
        ev = s.get("evaluation", {})
        sid = s["session_id"]
        turns = len(s.get("turns", []))
        draft = f"`draft_session_{sid}.md`"
        parts.append(
            f"| `{sid}` | {ev.get('overall_grade', '?')} | {ev.get('issue_count', 0)} | "
            f"{turns} | {draft} |"
        )
    parts.append("")

    for s in top20:
        sid = s["session_id"]
        draft_path = BASE / f"draft_session_{sid}.md"
        transcript_path = BASE / "sessions" / f"{sid}.md"
        parts.append(f"### セッション: `{sid}`\n")
        if draft_path.is_file():
            body = draft_path.read_text(encoding="utf-8")
            if body.startswith("# "):
                body = "\n".join(body.splitlines()[1:]).strip()
            parts.append(body)
        else:
            parts.append(f"*draft 未生成。transcript: `sessions/{sid}.md`*")
        parts.append("")
        if transcript_path.is_file():
            parts.append("<details><summary>全ターン transcript（CLI 生成）</summary>\n")
            parts.append(transcript_path.read_text(encoding="utf-8"))
            parts.append("\n</details>\n")

    parts.append("## 推奨アクション（優先順）\n")
    parts.append("1. 🔴 OpenAI dev quota 復旧 / テスト用キー分離")
    parts.append("2. 🔴 `is_llm_triage_infrastructure_error` の import と degraded 短絡（`chat_post_pipeline.py`）")
    parts.append("3. 🔴 推奨パイプライン直列 LLM の並列化・explanation 後段化（50–79s E2E）")
    parts.append("4. 🟡 非挨拶入力への greeting フォールバック抑止・Store ルート応答接続")
    parts.append("5. 🟡 `cleanup_expired_sessions` の `%%` エスケープ（`database.py`）")
    parts.append("6. 🟡 Clarification ループ脱出（同一フレーズ N 回上限）")
    parts.append("7. 🟢 LINE Webhook 統合テストを別ランで実施")
    parts.append("")
    parts.append("## 付録\n")
    parts.append("- manifest: `log/analysis/2026-06-30-dev-9-11/manifest.json`")
    parts.append("- quality_metrics: `log/analysis/2026-06-30-dev-9-11/quality_metrics.json`")
    parts.append("- Wave A drafts: `draft_infra_errors.md` 他")
    parts.append("- 開発ログ解析 CLI: `scripts/analyze_dev_logs.py`（新規）")

    OUT.write_text("\n".join(parts), encoding="utf-8")
    print(f"Wrote {OUT} ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
