#!/usr/bin/env python3
"""Build consolidated session transcript report from local v2 chat test JSON."""

from __future__ import annotations

import json
import re
from html import unescape
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = PROJECT_ROOT / "log" / "analysis"
OUTPUT = ANALYSIS / "2026-06-30_local_v2_session_transcripts_post-fix.md"
YAML_SCENARIOS = PROJECT_ROOT / "tests" / "fixtures" / "v2_local_chat_scenarios.yaml"
GPT_PERSONAS = PROJECT_ROOT / "tests" / "fixtures" / "v2_gpt_personas.yaml"
COUNSELING_LOG = PROJECT_ROOT / "log" / "counseling_detail_log.jsonl"
INTENT_REVIEW = ANALYSIS / "2026-06-30_local_v2_intent_review_post-fix.md"
TRUNCATE_AT = 1500


def strip_html(text: str) -> str:
    if not text:
        return ""
    t = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL | re.IGNORECASE)
    t = re.sub(r"<style[^>]*>.*?</style>", "", t, flags=re.DOTALL | re.IGNORECASE)
    t = re.sub(r"<br\s*/?>", "\n", t, flags=re.IGNORECASE)
    t = re.sub(r"</p>", "\n", t, flags=re.IGNORECASE)
    t = re.sub(r"</div>", "\n", t, flags=re.IGNORECASE)
    t = re.sub(r"</h[1-6]>", "\n", t, flags=re.IGNORECASE)
    t = re.sub(r"<[^>]+>", "", t)
    t = unescape(t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def maybe_truncate(text: str) -> str:
    if len(text) <= TRUNCATE_AT:
        return text
    return text[:500].rstrip() + "…（省略）"


def slugify(scenario_id: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]", "-", scenario_id).lower()


def load_yaml_descriptions() -> dict[str, str]:
    out: dict[str, str] = {}
    if YAML_SCENARIOS.exists():
        raw = yaml.safe_load(YAML_SCENARIOS.read_text(encoding="utf-8")) or {}
        items = raw if isinstance(raw, list) else (raw.get("scenarios") or [])
        for item in items:
            sid = item.get("id", "")
            if not sid:
                continue
            desc = (item.get("description") or "").strip()
            setup = item.get("setup") or []
            inp = (item.get("input") or "").strip()
            if desc:
                out[sid] = desc
            elif setup or inp:
                parts = []
                if setup:
                    parts.append("setup: " + " → ".join(str(s) for s in setup))
                if inp:
                    parts.append(f"input: {inp}")
                out[sid] = "; ".join(parts)
            elif inp:
                out[sid] = inp
    return out


def load_persona_labels() -> dict[str, str]:
    out: dict[str, str] = {}
    if GPT_PERSONAS.exists():
        data = yaml.safe_load(GPT_PERSONAS.read_text(encoding="utf-8")) or {}
        for p in data.get("personas") or []:
            pid = p.get("id", "")
            label = (p.get("label") or "").strip()
            goal = (p.get("goal") or "").strip()
            if pid:
                out[pid] = label or goal or pid
    return out


def parse_intent_review(path: Path) -> dict[str, dict[str, str]]:
    """scenario_id -> {intent, route, auto, notes}"""
    by_scenario: dict[str, dict[str, str]] = {}
    by_session: dict[str, dict[str, str]] = {}
    if not path.exists():
        return by_scenario

    in_table = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("| session_id | scenario | intent |"):
            in_table = True
            continue
        if in_table:
            if not line.startswith("|"):
                in_table = False
                continue
            if line.startswith("|------------"):
                continue
            cols = [c.strip() for c in line.strip("|").split("|")]
            if len(cols) < 7:
                continue
            session_id = cols[0].strip("`").strip()
            scenario = cols[1].strip()
            intent = cols[2].strip()
            route = cols[3].strip()
            notes = cols[5].strip() if len(cols) > 5 else ""
            auto = cols[6].strip() if len(cols) > 6 else ""
            row = {
                "intent": intent,
                "route": route if route != "—" else "",
                "notes": notes,
                "auto": auto,
            }
            by_scenario[scenario] = row
            if session_id:
                by_session[session_id] = row
    return by_scenario


def load_counseling_index(session_ids: set[str]) -> dict[tuple[str, str], dict[str, str]]:
    """(session_id, user_input) -> {timestamp, response}"""
    index: dict[tuple[str, str], dict[str, str]] = {}
    if not COUNSELING_LOG.exists():
        return index
    with COUNSELING_LOG.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            sid = str(row.get("session_id", ""))
            if sid not in session_ids:
                continue
            user_input = (row.get("user_input") or "").strip()
            response = row.get("response") or ""
            ts = row.get("timestamp") or ""
            key = (sid, user_input)
            # keep latest timestamp for duplicate keys
            prev = index.get(key)
            if prev is None or (ts and ts >= prev.get("timestamp", "")):
                index[key] = {
                    "timestamp": ts,
                    "response": strip_html(str(response)),
                }
    return index


def load_json_results(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("meta") or {}, data.get("results") or []


def session_description(
    result: dict[str, Any],
    yaml_desc: dict[str, str],
    persona_labels: dict[str, str],
) -> str:
    sid = result.get("scenario_id", "")
    desc = (result.get("description") or "").strip()
    if desc:
        return desc
    if sid in yaml_desc:
        return yaml_desc[sid]
    pid = (result.get("persona_id") or "").strip()
    if pid and pid in persona_labels:
        return persona_labels[pid]
    return ""


def format_bot_meta(route: str, kind: str | None, elapsed_ms: int | None) -> str:
    parts = []
    if route:
        parts.append(route)
    if kind:
        parts.append(kind)
    meta = "/".join(parts) if parts else "unknown"
    if elapsed_ms is not None:
        return f"`{meta}`, {elapsed_ms}ms"
    return f"`{meta}`"


def build_report() -> str:
    yaml_meta, yaml_results = load_json_results(
        ANALYSIS / "2026-06-30_local_v2_chat_test_post-fix.json"
    )
    gpt_meta, gpt_results = load_json_results(
        ANALYSIS / "2026-06-30_local_v2_chat_test_post-fix-gpt.json"
    )

    all_results = yaml_results + gpt_results
    yaml_desc = load_yaml_descriptions()
    persona_labels = load_persona_labels()
    intent_by_scenario = parse_intent_review(INTENT_REVIEW)

    session_ids = {str(r.get("session_id", "")) for r in all_results if r.get("session_id")}
    counseling_index = load_counseling_index(session_ids)

    total_sessions = len(all_results)
    total_turns = sum(len(r.get("turns") or []) for r in all_results)

    lines: list[str] = [
        "# Local v2 セッション別チャットトランスクリプト — post-fix (2026-06-30)",
        "",
        "## メタデータ",
        "",
        f"- **日付**: 2026-06-30",
        f"- **サフィックス**: post-fix",
        f"- **YAML 実行**: {yaml_meta.get('started_at', '')}（{yaml_meta.get('scenario_count', 100)} シナリオ / {yaml_meta.get('total_turns', 128)} ターン）",
        f"- **GPT 実行**: {gpt_meta.get('started_at', '')}（{gpt_meta.get('scenario_count', 4)} シナリオ / {gpt_meta.get('total_turns', 80)} ターン）",
        f"- **合計セッション数**: {total_sessions}",
        f"- **合計ターン数**: {total_turns}",
        f"- **参照**: [post-fix テストレポート](./2026-06-30_local_v2_chat_test_post-fix.md) / [GPT](./2026-06-30_local_v2_chat_test_post-fix-gpt.md) / [意図レビュー](./2026-06-30_local_v2_intent_review_post-fix.md)",
        "",
        "## 目次",
        "",
        "| # | シナリオ | session_id | カテゴリ | ターン | リンク |",
        "|---|----------|------------|----------|--------|--------|",
    ]

    for i, result in enumerate(all_results, 1):
        scenario_id = result.get("scenario_id", "")
        session_id = result.get("session_id") or "—"
        category = result.get("category", "")
        turns = len(result.get("turns") or [])
        anchor = slugify(scenario_id)
        sid_disp = f"`{session_id}`" if session_id else "—"
        lines.append(
            f"| {i} | {scenario_id} | {sid_disp} | {category} | {turns} | [→](#session-{anchor}) |"
        )

    lines.extend(["", "---", "", "## セッション別トランスクリプト", ""])

    for result in all_results:
        scenario_id = result.get("scenario_id", "")
        session_id = result.get("session_id") or ""
        category = result.get("category", "")
        wave = result.get("wave", "")
        turns = result.get("turns") or []
        auto_pass = result.get("auto_pass", False)
        auto_status = "PASS" if auto_pass else "REVIEW"
        persona_id = result.get("persona_id") or ""
        failures = result.get("auto_failures") or []

        intent_row = intent_by_scenario.get(scenario_id, {})
        wave_b_intent = intent_row.get("intent", "")
        wave_b_route = intent_row.get("route", "")
        wave_b_notes = intent_row.get("notes", "")
        wave_b_auto = intent_row.get("auto", "")

        anchor = slugify(scenario_id)
        lines.append(f'<a id="session-{anchor}"></a>')
        lines.append("")
        lines.append(f"## Session: {scenario_id} (`{session_id or '—'}`)")
        lines.append("")
        lines.append(f"- **カテゴリ**: {category}")
        if wave:
            lines.append(f"- **Wave**: {wave}")
        if persona_id:
            lines.append(f"- **ペルソナ**: {persona_id}")
        lines.append(f"- **自動合格**: {auto_status}")
        if wave_b_intent:
            wb = f"Wave B 意図: {wave_b_intent}"
            if wave_b_route:
                wb += f" / route: {wave_b_route}"
            if wave_b_auto:
                wb += f" / 手動: {wave_b_auto}"
            lines.append(f"- **{wb}**")
        if wave_b_notes:
            lines.append(f"- **意図レビュー備考**: {wave_b_notes}")

        desc = session_description(result, yaml_desc, persona_labels)
        if desc:
            lines.append(f"- **シナリオ説明**: {desc}")

        if failures:
            for fail in failures:
                lines.append(f"- **エラー**: {fail}")

        lines.append("")

        if not turns:
            lines.append("**セッション未完了（0ターン）**")
            if desc:
                lines.append(f"")
                lines.append(f"想定シナリオ: {desc}")
            lines.append("")
            lines.append("---")
            lines.append("")
            continue

        route_default = wave_b_route
        for n, turn in enumerate(turns, 1):
            user_msg = (turn.get("user_message") or "").strip()
            kind = turn.get("diagnosis_kind")
            elapsed = turn.get("elapsed_ms")
            http_status = turn.get("http_status")
            error = (turn.get("error") or "").strip()

            ts = ""
            json_text = strip_html(
                (turn.get("response_full") or turn.get("response_snippet") or "").strip()
            )
            bot_text = json_text

            if session_id:
                ckey = (session_id, user_msg)
                if ckey in counseling_index:
                    crec = counseling_index[ckey]
                    if crec.get("timestamp"):
                        ts = crec["timestamp"]
                    counsel_text = crec.get("response") or ""
                    if not bot_text and counsel_text:
                        bot_text = counsel_text
                    elif counsel_text and len(counsel_text) > len(bot_text) + 80:
                        # counseling_detail_log の方が明らかに長い場合のみ採用
                        bot_text = counsel_text

            bot_text = maybe_truncate(bot_text)

            turn_header = f"### Turn {n}"
            if ts:
                turn_header += f" ({ts})"
            lines.append(turn_header)
            lines.append("")
            lines.append(f"**User**: {user_msg}")
            lines.append("")

            meta = format_bot_meta(route_default, kind, elapsed)
            err_note = ""
            if http_status and http_status >= 400:
                err_note = f"HTTP {http_status}"
            elif error and str(error).strip().lower() not in ("", "false", "none"):
                err_note = str(error).strip()

            if bot_text:
                if err_note:
                    lines.append(f"**Bot** ({meta}, {err_note}):")
                else:
                    lines.append(f"**Bot** ({meta}):")
                lines.append("")
                lines.append(bot_text)
            else:
                lines.append(f"**Bot** ({meta}): *{err_note or '応答なし'}*")

            lines.append("")

        lines.append("---")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    report = build_report()
    OUTPUT.write_text(report, encoding="utf-8")
    line_count = len(report.splitlines())
    session_count = report.count("## Session:")
    print(f"Wrote {OUTPUT}")
    print(f"Lines: {line_count}")
    print(f"Sessions: {session_count}")


if __name__ == "__main__":
    main()
