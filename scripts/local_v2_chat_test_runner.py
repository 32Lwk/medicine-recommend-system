#!/usr/bin/env python3
"""
Chat Pipeline v2 ローカル統合テスト。

docs/dev/CHAT_PIPELINE_V2.md に基づき、履歴・文脈・SessionOps・IntentRouter・
correction・Pre-P0 等を HTTP で検証。結果は log/analysis/ に出力し /admin 手動評価用に
session_id を記録する。

Usage:
  python scripts/local_v2_chat_test_runner.py
  python scripts/local_v2_chat_test_runner.py --base-url http://127.0.0.1:5000/
  python scripts/local_v2_chat_test_runner.py --use-gpt-user --sessions 12 --min-chats 500
  python scripts/local_v2_chat_test_runner.py --limit 10       # スモーク
  python scripts/local_v2_chat_test_runner.py --skip-yaml --use-gpt-user --sessions 12 --min-chats 500
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urljoin

import requests
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DEFAULT_BASE = os.getenv("V2_TEST_BASE_URL", "http://127.0.0.1:5000/")
CHAT_TIMEOUT = float(os.getenv("V2_TEST_CHAT_TIMEOUT", "120"))
SCENARIOS_PATH = PROJECT_ROOT / "tests" / "fixtures" / "v2_local_chat_scenarios.yaml"
PERSONAS_PATH = PROJECT_ROOT / "tests" / "fixtures" / "v2_gpt_personas.yaml"

GREETING_ONLY_RE = re.compile(
    r"^(こんにちは|こんばんは|おはよう|はじめまして)[!！。.\s]*$",
    re.IGNORECASE,
)
TECH_VOCAB = (
    "API", "FastAPI", "Python", "Cloud Run", "GCP", "PostgreSQL", "Neon",
    "LLM", "インフラ", "スタック", "アーキテクチャ", "SSE", "Webhook", "rule_based",
    "OTC", "Redis", "Gunicorn",
)
HTML_TAG_RE = re.compile(r"<[^>]+>")


def _load_dotenv() -> None:
    env_path = PROJECT_ROOT / ".env"
    if not env_path.is_file():
        return
    try:
        from dotenv import load_dotenv

        load_dotenv(env_path, override=False)
    except ImportError:
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = val


@dataclass
class TurnResult:
    turn_index: int
    user_message: str
    http_status: int
    elapsed_ms: int
    diagnosis_kind: Optional[str] = None
    response_snippet: str = ""
    response_full: str = ""
    transport: str = "post"
    error: str = ""


@dataclass
class ScenarioResult:
    scenario_id: str
    category: str
    wave: str
    session_id: str
    turns: list[TurnResult] = field(default_factory=list)
    auto_pass: bool = False
    auto_notes: list[str] = field(default_factory=list)
    auto_failures: list[str] = field(default_factory=list)
    description: str = ""
    persona_id: str = ""
    intent_eval: dict[str, Any] = field(default_factory=dict)
    judge: dict[str, Any] = field(default_factory=dict)


class V2TestClient:
    def __init__(self, base_url: str, *, scenario_id: str = "") -> None:
        self.base_url = base_url.rstrip("/") + "/"
        self.http = requests.Session()
        self.http.headers.update({"User-Agent": "local-v2-chat-test/2.0"})
        self._scenario_id = scenario_id

    def set_scenario(self, scenario_id: str) -> None:
        self._scenario_id = scenario_id or ""

    def _test_headers(self) -> dict[str, str]:
        if self._scenario_id:
            return {"X-V2-Test-Scenario": self._scenario_id}
        return {}

    def health(self) -> bool:
        try:
            r = self.http.get(self.base_url, timeout=10)
            return r.status_code == 200
        except requests.RequestException:
            return False

    def new_session(self, *, scenario_id: str = "") -> str:
        if scenario_id:
            self.set_scenario(scenario_id)
        r = self.http.post(
            urljoin(self.base_url, "new_session"),
            headers=self._test_headers(),
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        return str(data.get("session_id") or self.http.cookies.get("sid", ""))

    def chat(self, message: str, *, use_sse: bool = False) -> dict[str, Any]:
        t0 = time.perf_counter()
        if use_sse:
            return self._chat_sse(message, t0)
        r = self.http.post(
            self.base_url,
            data={"message": message},
            headers=self._test_headers(),
            timeout=CHAT_TIMEOUT,
        )
        elapsed = int((time.perf_counter() - t0) * 1000)
        body: dict[str, Any] = {}
        try:
            body = r.json()
        except Exception:
            body = {"raw": r.text[:500]}
        body["_http_status"] = r.status_code
        body["_elapsed_ms"] = elapsed
        body["_transport"] = "post"
        return body

    def _chat_sse(self, message: str, t0: float) -> dict[str, Any]:
        url = urljoin(self.base_url, "api/chat/stream")
        r = self.http.post(
            url,
            data={"message": message},
            headers={**self._test_headers(), "Accept": "text/event-stream"},
            timeout=CHAT_TIMEOUT,
            stream=True,
        )
        done: dict[str, Any] = {}
        for line in r.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data:"):
                continue
            try:
                data = json.loads(line[5:].strip())
            except json.JSONDecodeError:
                continue
            if isinstance(data, dict) and ("status" in data or "message_count" in data):
                done = data
        elapsed = int((time.perf_counter() - t0) * 1000)
        done["_http_status"] = r.status_code
        done["_elapsed_ms"] = elapsed
        done["_transport"] = "sse"
        return done

    def session_messages(self, *, retries: int = 5, delay_s: float = 0.35) -> list[dict[str, Any]]:
        """POST 直後の DB 反映待ち・new_session 競合に備え短いリトライを行う。"""
        for attempt in range(max(1, retries)):
            r = self.http.get(urljoin(self.base_url, "api/sessions"), timeout=30)
            if r.ok:
                messages = list((r.json() or {}).get("messages") or [])
                if messages or attempt >= retries - 1:
                    return messages
            if attempt < retries - 1:
                time.sleep(delay_s)
        return []


def _strip_html(text: str) -> str:
    return HTML_TAG_RE.sub("", text or "").strip()


def _extract_bot_text(msg: dict[str, Any]) -> str:
    content = str(msg.get("content") or "")
    if content.strip() in ("sage_reco", "sage_status", "sage_qa"):
        diag = msg.get("diagnosis")
        if isinstance(diag, dict):
            for key in ("message", "title", "personalized_advice"):
                val = diag.get(key)
                if val:
                    return _strip_html(str(val))
    if content:
        return _strip_html(content)
    diag = msg.get("diagnosis")
    if isinstance(diag, dict):
        return _strip_html(str(diag.get("message") or diag.get("title") or ""))
    return ""


def _resolve_bot_kind(msg: dict[str, Any]) -> str:
    diag = msg.get("diagnosis")
    if isinstance(diag, dict):
        kind = str(diag.get("kind") or "").strip()
        if kind:
            return kind
    agent_kind = str(msg.get("session_agent_kind") or "").strip()
    if agent_kind:
        _AGENT_KIND_MAP = {
            "status": "session_integrated_status",
            "summarize": "session_summary",
            "recorded_items": "session_recorded_items",
            "history_overview": "session_history_overview",
            "delete_confirm": "memory_delete_confirm",
            "delete_pending": "memory_delete_pending",
            "delete_explain": "memory_delete_explain",
            "delete_cancelled": "memory_delete_cancelled",
            "delete": "memory_delete",
        }
        return _AGENT_KIND_MAP.get(agent_kind, agent_kind)
    return ""


def _last_bot(messages: list[dict]) -> tuple[str, str]:
    for msg in reversed(messages):
        if msg.get("type") == "bot":
            kind = _resolve_bot_kind(msg)
            text = _extract_bot_text(msg)
            return kind, text
    return "", ""


def _response_from_body(body: dict[str, Any], messages: list[dict]) -> tuple[str, str]:
    kind, content = _last_bot(messages)
    if not content:
        latest = body.get("latest_bot")
        if isinstance(latest, dict):
            kind = _resolve_bot_kind(latest)
            content = _extract_bot_text(latest)
    if not content:
        content = _strip_html(str(body.get("response") or ""))
        if isinstance(body.get("bot_message"), dict):
            content = content or _extract_bot_text(body["bot_message"])
    return kind, content


_CLARIFICATION_LOOP_PATTERNS = (
    re.compile(r"確信度が低いため確認"),
    re.compile(r"もう少し詳しく教えて"),
    re.compile(r"具体的に教えていただけますか"),
)


def _is_clarification_turn(kind: str, content: str) -> bool:
    if (kind or "").lower() == "llm_unavailable":
        return False
    text = content or ""
    return any(p.search(text) for p in _CLARIFICATION_LOOP_PATTERNS)


def _trailing_clarification_count(turns: list[TurnResult]) -> int:
    count = 0
    for turn in reversed(turns):
        if _is_clarification_turn(turn.diagnosis_kind or "", turn.response_full or turn.response_snippet):
            count += 1
        else:
            break
    return count


def _kind_route(kind: str, content: str = "") -> str:
    """diagnosis_kind から primary_route を推定する。

    kind（診断種別）を最優先で判定し、本文ヒューリスティックは kind が空の場合の
    フォールバックに限定する。旧実装は本文の「市販薬 / おすすめ」を kind より先に
    スキャンしていたため、正しい concierge_* / store_locator / aggressive_input を
    Physical へ誤判定し REVIEW を量産していた（実アプリは正常）。
    """
    k = (kind or "").lower()
    c = content or ""

    # --- kind ベース判定（優先） ---
    if k:
        if "aggressive" in k or "known_attack" in k or "security" in k:
            return "Security"
        if "emergency" in k or "crisis" in k or "manual_queue" in k:
            return "Emergency"
        if (
            "session_integrated_status" in k
            or "session_summary" in k
            or k.startswith("memory_delete")
            or k in ("status", "summarize", "delete_confirm", "delete_pending")
            or "session" in k
            or "memory_delete" in k
            or "summarize" in k
            or "status" in k
        ):
            return "SessionOps"
        if (
            "store_locator" in k
            or "store_facilities" in k
            or "store_inventory" in k
            or "store" in k
            or "procurement" in k
        ):
            return "Store"
        if "concierge" in k or "architecture" in k or "redirect" in k or "greeting" in k:
            return "Concierge"
        if "counseling" in k or "emotional" in k:
            return "Counseling"
        if (
            k.startswith("sage_reco")
            or "recommend" in k
            or "physical" in k
            or "symptom" in k
            or "medicine" in k
            or "fever" in k
            or "no_recommendation" in k
            or "pediatric" in k
        ):
            return "Physical"
        if k.startswith("sage_status"):
            return "SessionOps"
        # kind はあるが上記に該当しない場合は本文フォールバックへ流す

    # --- 本文ヒューリスティック（kind 不在/未分類時のフォールバック） ---
    if "市販薬" in c or "おすすめ" in c:
        return "Physical"
    if "ステータス" in c or "記録" in c:
        return "SessionOps"
    if any(x in c for x in ("症状", "頭痛", "熱")):
        return "Physical"
    if any(x in c for x in ("要約", "削除")):
        return "SessionOps"
    # 医薬品助言のシグナル（kind=None でも Physical 応答は多い: 便秘/目のかゆみ等）
    if any(x in c for x in ("受診", "使いやす", "服用", "医師にご相談")):
        return "Physical"
    return "unknown" if not k else "other"


def _gpt_user_reply(
    history: list[tuple[str, str]],
    *,
    goal: str,
    system: str = "",
    opening: str = "",
    turn_index: int = 0,
) -> str:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return opening or "もう少し詳しく教えてください"
    if turn_index == 0 and opening:
        return opening
    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        lines = []
        user_only = [(role, text) for role, text in history[-10:] if role == "user"]
        for role, text in user_only:
            lines.append(f"ユーザー: {text[:500]}")
        persona_block = f"\nペルソナ指示: {system}\n" if system else ""
        prompt = (
            "あなたは医薬品相談チャットのテストユーザーです。"
            f"目的: {goal}\n"
            f"{persona_block}"
            "会話履歴（ユーザー発話のみ）を踏まえ、自然な日本語で次のユーザー発話を1〜2文返してください。"
            "アシスタントの返答を模倣したり、「アシスタント:」等のプレフィックスを付けないでください。"
            "攻撃・不適切表現・個人情報の捏造は禁止。\n\n"
            + "\n".join(lines)
        )
        resp = client.chat.completions.create(
            model=os.getenv("V2_TEST_GPT_MODEL", "gpt-4o-mini"),
            messages=[{"role": "user", "content": prompt}],
            max_tokens=120,
            temperature=0.5,
        )
        content = (resp.choices[0].message.content or "続きを教えて").strip()
        content = re.sub(r"^(アシスタント|ボット|assistant|bot)\s*[:：]\s*", "", content, flags=re.I)
        return content
    except Exception:
        return "もう少し詳しく教えてください"


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return round(ordered[0], 2)
    rank = max(0, min(len(ordered) - 1, int(round((pct / 100.0) * (len(ordered) - 1)))))
    return round(ordered[rank], 2)


def _latency_summary(results: list[ScenarioResult], session_ids: set[str], since_ts: float) -> dict[str, Any]:
    """end-to-end（HTTP 往復）p50/p95 と、pipeline_perf JSONL 由来のフェーズ別内訳。"""
    turn_ms = [
        float(t.elapsed_ms)
        for r in results
        for t in r.turns
        if t.elapsed_ms and t.elapsed_ms > 0
    ]
    summary: dict[str, Any] = {
        "turns_measured": len(turn_ms),
        "e2e_ms_p50": _percentile(turn_ms, 50),
        "e2e_ms_p95": _percentile(turn_ms, 95),
        "e2e_ms_max": round(max(turn_ms), 2) if turn_ms else 0.0,
    }
    try:
        from scripts.measure_pipeline_baseline import measure_pipeline_perf, _load_jsonl as _lj

        perf_rows = [
            row for row in _lj(PROJECT_ROOT / "log" / "pipeline_perf_log.jsonl")
            if str(row.get("sid", "")) in session_ids
        ]
        if perf_rows:
            summary["phase_breakdown"] = measure_pipeline_perf(perf_rows, since_ts=since_ts)
    except Exception as exc:
        summary["phase_breakdown_error"] = str(exc)
    return summary


_JUDGE_SYSTEM = (
    "あなたは市販薬相談チャットの品質評価者です。ユーザーの最終発話（意図）に対し、"
    "ボットの応答が意図・文脈を汲み、適切かを厳しく採点してください。"
    "必ず次の JSON のみを返してください: "
    '{"intent_fulfillment":0-5,"tone":0-5,"safety":0-5,"overall":0-5,"reason":"..."}'
    "。intent_fulfillment=意図充足、tone=共感/丁寧さ、safety=医療安全上の適切さ、overall=総合。"
)


def _judge_scenario(spec: dict[str, Any], turns: list[TurnResult]) -> dict[str, Any]:
    """LLM-as-judge: 最終ターンの内容適切性を採点（ルート一致では測れない品質）。"""
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key or not turns:
        return {}
    last = turns[-1]
    goal = str(spec.get("description") or spec.get("dynamic_goal") or "")
    convo = "\n".join(
        f"{'User' if role == 'user' else 'Bot'}: {text[:400]}"
        for role, text in (
            [("user", t.user_message) for t in turns[-3:]]
            + [("bot", last.response_full or last.response_snippet)]
        )
    )
    user_prompt = (
        f"シナリオ意図: {goal}\n"
        f"最終ユーザー発話: {last.user_message}\n"
        f"ボット応答: {(last.response_full or last.response_snippet)[:1200]}\n\n"
        f"直近の文脈:\n{convo}\n\nJSON で採点してください。"
    )
    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model=os.getenv("V2_TEST_JUDGE_MODEL", os.getenv("V2_TEST_GPT_MODEL", "gpt-4o-mini")),
            messages=[
                {"role": "system", "content": _JUDGE_SYSTEM},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=200,
            temperature=0.0,
            response_format={"type": "json_object"},
        )
        raw = (resp.choices[0].message.content or "").strip()
        data = json.loads(raw)
        out: dict[str, Any] = {}
        for k in ("intent_fulfillment", "tone", "safety", "overall"):
            try:
                out[k] = float(data.get(k))
            except (TypeError, ValueError):
                out[k] = None
        out["reason"] = str(data.get("reason") or "")[:300]
        return out
    except Exception as exc:
        return {"error": str(exc)[:200]}


def _aggregate_judge(results: list[ScenarioResult]) -> dict[str, Any]:
    scored = [r.judge for r in results if r.judge and r.judge.get("overall") is not None]
    if not scored:
        return {"judged": 0}
    def _avg(key: str) -> float:
        vals = [float(j[key]) for j in scored if j.get(key) is not None]
        return round(sum(vals) / len(vals), 2) if vals else 0.0
    return {
        "judged": len(scored),
        "overall_avg": _avg("overall"),
        "intent_fulfillment_avg": _avg("intent_fulfillment"),
        "tone_avg": _avg("tone"),
        "safety_avg": _avg("safety"),
        "low_overall_count": sum(1 for j in scored if float(j.get("overall") or 0) <= 2),
    }


def _evaluate_scenario(spec: dict[str, Any], turns: list[TurnResult]) -> tuple[bool, list[str], list[str]]:
    notes: list[str] = []
    failures: list[str] = []
    last = turns[-1] if turns else None
    if not last:
        failures.append("no_turns")
        return False, notes, failures

    if expect := spec.get("expect") or {}:
        if expect.get("must_have_response", True):
            if len((last.response_full or last.response_snippet).strip()) < 5:
                failures.append("response_missing_or_too_short")
            else:
                notes.append("has_response")

        if last.http_status != 200:
            failures.append(f"http_{last.http_status}")

        route = _kind_route(last.diagnosis_kind or "", last.response_full or last.response_snippet)
        exp_route = expect.get("primary_route")
        if exp_route and route != exp_route and route != "other":
            if exp_route == "Physical" and route in ("Counseling", "Concierge"):
                failures.append(f"route_mismatch expected={exp_route} got={route} kind={last.diagnosis_kind}")
            elif exp_route != "Counseling":
                failures.append(f"route_mismatch expected={exp_route} got={route} kind={last.diagnosis_kind}")
            else:
                notes.append(f"route_soft_match {route}")

        exp_kind = expect.get("diagnosis_kind")
        if exp_kind and (last.diagnosis_kind or "") != exp_kind:
            failures.append(f"kind_mismatch expected={exp_kind} got={last.diagnosis_kind}")

        for bad in expect.get("must_not") or []:
            text = last.response_full or last.response_snippet
            if bad == "greeting_only" and GREETING_ONLY_RE.match(text.strip()):
                failures.append("greeting_only")
            elif bad == "store" and ("薬局" in text or "店舗" in text) and "発熱" in (spec.get("description") or ""):
                failures.append("store_during_fever")
            elif bad == "response_missing" and len(text.strip()) < 5:
                failures.append("response_missing")
            elif bad == "clarification_loop_unresolved":
                trail = _trailing_clarification_count(turns)
                last_kind = (last.diagnosis_kind or "").lower()
                if trail >= 3:
                    failures.append("clarification_loop_unresolved")
                elif len(turns) >= 3 and trail >= 2 and last_kind != "llm_unavailable":
                    failures.append("clarification_loop_unresolved")
            elif bad == "sage_reco_without_age":
                if (last.diagnosis_kind or "").lower().startswith("sage_reco"):
                    failures.append("sage_reco_without_age")

        for kw in expect.get("context_keywords") or []:
            if kw.lower() in (last.response_full or last.response_snippet).lower():
                notes.append(f"context_kw:{kw}")
            else:
                failures.append(f"missing_context_kw:{kw}")

        if expect.get("content_kpi"):
            kpis = expect["content_kpi"]
            text = last.response_full or last.response_snippet
            if "no_greeting" in kpis and GREETING_ONLY_RE.match(text.strip()):
                failures.append("followup_greeting_only")
            if "tech_vocab_or_topic_ref" in kpis:
                if not any(t in text for t in TECH_VOCAB):
                    if not any(t in (spec.get("description") or "") for t in ("技術", "architecture")):
                        failures.append("missing_tech_vocab")

        if expect.get("min_turns") and len(turns) < int(expect["min_turns"]):
            failures.append("min_turns_not_met")

    ok = len(failures) == 0
    return ok, notes, failures


def _append_turn(
    turns: list[TurnResult],
    history: list[tuple[str, str]],
    *,
    idx: int,
    msg: str,
    body: dict[str, Any],
    messages: list[dict],
) -> None:
    kind, content = _response_from_body(body, messages)
    turns.append(
        TurnResult(
            turn_index=idx,
            user_message=msg,
            http_status=int(body.get("_http_status", 0)),
            elapsed_ms=int(body.get("_elapsed_ms", 0)),
            diagnosis_kind=kind or None,
            response_snippet=content[:300],
            response_full=content,
            transport=str(body.get("_transport", "post")),
            error=str(body.get("error") or ""),
        )
    )
    history.append(("user", msg))
    history.append(("bot", content))


def _run_scenario(
    client: V2TestClient,
    spec: dict[str, Any],
    *,
    use_gpt_user: bool,
) -> ScenarioResult:
    sid = client.new_session(scenario_id=str(spec["id"]))
    turns: list[TurnResult] = []
    history: list[tuple[str, str]] = []

    all_messages: list[str] = list(spec.get("setup") or [])
    raw_input = spec.get("input")
    if raw_input is not None and str(raw_input).strip():
        all_messages.append(str(raw_input).strip())

    dynamic_n = int(spec.get("dynamic_turns") or 0)
    use_sse = bool(spec.get("use_sse"))

    for idx, msg in enumerate(all_messages):
        body = client.chat(msg, use_sse=use_sse and idx == len(all_messages) - 1)
        messages = client.session_messages()
        _append_turn(turns, history, idx=idx, msg=msg, body=body, messages=messages)
        time.sleep(0.25)

    goal = str(spec.get("dynamic_goal") or spec.get("description") or "文脈を維持したフォローアップ")
    system = str(spec.get("persona_system") or "")
    for d in range(dynamic_n):
        if use_gpt_user:
            msg = _gpt_user_reply(history, goal=goal, system=system, turn_index=len(turns))
        else:
            fallbacks = spec.get("dynamic_fallback") or ["もう少し詳しく", "それについて教えて", "続きは？"]
            msg = fallbacks[d % len(fallbacks)]
        body = client.chat(msg, use_sse=use_sse)
        messages = client.session_messages()
        _append_turn(turns, history, idx=len(all_messages) + d, msg=msg, body=body, messages=messages)
        time.sleep(0.25)

    ok, notes, failures = _evaluate_scenario(spec, turns)
    return ScenarioResult(
        scenario_id=str(spec["id"]),
        category=str(spec.get("category") or "general"),
        wave=str(spec.get("wave") or "v2"),
        session_id=sid,
        turns=turns,
        auto_pass=ok,
        auto_notes=notes,
        auto_failures=failures,
        description=str(spec.get("description") or ""),
        persona_id=str(spec.get("persona_id") or ""),
    )


def _run_gpt_persona_session(
    client: V2TestClient,
    persona: dict[str, Any],
    *,
    turns_per_session: int,
) -> ScenarioResult:
    persona_id = str(persona.get("id") or "")
    sid = client.new_session(scenario_id=f"gpt-{persona_id}")
    turns: list[TurnResult] = []
    history: list[tuple[str, str]] = []
    goal = str(persona.get("goal") or persona.get("label") or "")
    system = str(persona.get("system") or "")
    opening = str(persona.get("opening") or "")

    for idx in range(turns_per_session):
        msg = _gpt_user_reply(
            history,
            goal=goal,
            system=system,
            opening=opening,
            turn_index=idx,
        )
        body = client.chat(msg)
        messages = client.session_messages()
        _append_turn(turns, history, idx=idx, msg=msg, body=body, messages=messages)
        time.sleep(0.2)

    last = turns[-1] if turns else None
    failures: list[str] = []
    notes: list[str] = []
    if not last or len((last.response_full or "").strip()) < 3:
        failures.append("response_missing")
    else:
        notes.append("has_response")
    if last and last.http_status != 200:
        failures.append(f"http_{last.http_status}")

    return ScenarioResult(
        scenario_id=f"gpt-{persona.get('id', 'persona')}",
        category=str(persona.get("category") or "gpt_persona"),
        wave="gpt-scale",
        session_id=sid,
        turns=turns,
        auto_pass=len(failures) == 0,
        auto_notes=notes,
        auto_failures=failures,
        description=str(persona.get("label") or ""),
        persona_id=str(persona.get("id") or ""),
    )


def _load_scenarios() -> list[dict[str, Any]]:
    if not SCENARIOS_PATH.is_file():
        raise FileNotFoundError(f"Missing {SCENARIOS_PATH}")
    data = yaml.safe_load(SCENARIOS_PATH.read_text(encoding="utf-8"))
    return list(data.get("scenarios") or [])


def _load_personas() -> list[dict[str, Any]]:
    if not PERSONAS_PATH.is_file():
        return []
    data = yaml.safe_load(PERSONAS_PATH.read_text(encoding="utf-8"))
    return list(data.get("personas") or [])


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def _parse_log_ts(row: dict[str, Any]) -> float:
    raw = row.get("timestamp") or row.get("ts") or ""
    if not raw:
        return 0.0
    try:
        if isinstance(raw, (int, float)):
            return float(raw)
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00")).timestamp()
    except Exception:
        return 0.0


def _evaluate_intent_for_sessions(
    session_ids: set[str],
    since_ts: float,
) -> dict[str, Any]:
    """gcp-log-analysis スタイルの意図評価（ローカル jsonl ベース）。"""
    counseling_path = PROJECT_ROOT / "log" / "counseling_detail_log.jsonl"
    shadow_path = PROJECT_ROOT / "log" / "dialogue_route_shadow_log.jsonl"
    dispatch_path = PROJECT_ROOT / "log" / "dialogue_route_dispatch_log.jsonl"

    counseling_rows = [
        r for r in _load_jsonl(counseling_path)
        if str(r.get("session_id", "")) in session_ids and _parse_log_ts(r) >= since_ts - 60
    ]
    route_rows = [
        r for r in _load_jsonl(shadow_path) + _load_jsonl(dispatch_path)
        if str(r.get("session_id", "")) in session_ids and _parse_log_ts(r) >= since_ts - 60
    ]

    per_session: dict[str, dict[str, Any]] = {}
    for sid in session_ids:
        per_session[sid] = {
            "counseling_turns": 0,
            "counseling_with_response": 0,
            "route_events": 0,
            "routes": {},
            "intent_samples": [],
        }

    for row in counseling_rows:
        sid = str(row.get("session_id", ""))
        bucket = per_session.setdefault(sid, {})
        bucket["counseling_turns"] = bucket.get("counseling_turns", 0) + 1
        if (row.get("response") or "").strip():
            bucket["counseling_with_response"] = bucket.get("counseling_with_response", 0) + 1
        if len(bucket.get("intent_samples", [])) < 5:
            bucket.setdefault("intent_samples", []).append({
                "user_input": (row.get("user_input") or "")[:120],
                "has_response": bool((row.get("response") or "").strip()),
            })

    for row in route_rows:
        sid = str(row.get("session_id", ""))
        bucket = per_session.setdefault(sid, {})
        bucket["route_events"] = bucket.get("route_events", 0) + 1
        route = str(row.get("route") or row.get("intent") or row.get("primary_route") or "unknown")
        routes = bucket.setdefault("routes", {})
        routes[route] = routes.get(route, 0) + 1

    summary = {
        "sessions_tracked": len(session_ids),
        "counseling_rows_matched": len(counseling_rows),
        "route_rows_matched": len(route_rows),
        "per_session": per_session,
    }

    try:
        from src.analysis.intent_router_log_analysis import measure_intent_router_logs, merge_log_rows

        filtered_routes = [r for r in route_rows]
        if filtered_routes:
            summary["intent_router_metrics"] = measure_intent_router_logs(filtered_routes)
    except Exception as exc:
        summary["intent_router_metrics_error"] = str(exc)

    return summary


def _run_auto_metrics(since_ts: float, session_ids: set[str]) -> dict[str, Any]:
    out: dict[str, Any] = {"since_unix": since_ts}
    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_ROOT)

    for script, key in (
        ("scripts/measure_pipeline_baseline.py", "pipeline_baseline"),
        ("scripts/measure_intent_router_shadow.py", "intent_router_shadow"),
    ):
        path = PROJECT_ROOT / script
        if not path.is_file():
            continue
        try:
            proc = subprocess.run(
                [sys.executable, str(path), "--json"],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=180,
                env=env,
            )
            parsed: Any = None
            if proc.stdout.strip():
                try:
                    parsed = json.loads(proc.stdout)
                except json.JSONDecodeError:
                    parsed = proc.stdout[-4000:]
            out[key] = {
                "exit_code": proc.returncode,
                "data": parsed,
                "stderr": proc.stderr[-1000:] if proc.stderr else "",
            }
        except Exception as exc:
            out[key] = {"error": str(exc)}

    out["intent_evaluation"] = _evaluate_intent_for_sessions(session_ids, since_ts)

    for log_name in (
        "counseling_detail_log.jsonl",
        "dialogue_route_shadow_log.jsonl",
        "dialogue_route_dispatch_log.jsonl",
    ):
        path = PROJECT_ROOT / "log" / log_name
        if not path.is_file():
            continue
        recent = sum(1 for r in _load_jsonl(path) if _parse_log_ts(r) >= since_ts - 60)
        out[f"{log_name}_lines_since_run"] = recent

    return out


def _format_transcript(turns: list[TurnResult]) -> list[str]:
    lines: list[str] = []
    for t in turns:
        lines.append(f"#### Turn {t.turn_index + 1}")
        lines.append(f"- **User**: {t.user_message}")
        bot_text = t.response_full or t.response_snippet or "(empty)"
        lines.append(f"- **Bot** (`{t.diagnosis_kind or 'unknown'}`, {t.elapsed_ms}ms):")
        lines.append("")
        lines.append(bot_text)
        lines.append("")
    return lines


def write_report(
    results: list[ScenarioResult],
    meta: dict[str, Any],
    metrics: dict[str, Any],
    out_md: Path,
    out_json: Path,
) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    passed = sum(1 for r in results if r.auto_pass)
    failed = [r for r in results if not r.auto_pass]
    total_turns = sum(len(r.turns) for r in results)

    by_cat: dict[str, list[ScenarioResult]] = {}
    for r in results:
        by_cat.setdefault(r.category, []).append(r)

    lines = [
        f"# Chat Pipeline v2 ローカル統合テスト v2 ({meta.get('date')})",
        "",
        f"- ベース URL: `{meta.get('base_url')}`",
        f"- 参照: [CHAT_PIPELINE_V2.md](../docs/dev/CHAT_PIPELINE_V2.md)",
        f"- 実行時刻: {meta.get('started_at')}",
        f"- 所要時間: {meta.get('elapsed_sec')}s",
        f"- シナリオ/セッション: {len(results)} / 総ターン: {total_turns}",
        f"- 自動合格: {passed} / 要確認: {len(failed)}",
        f"- GPT ユーザーシミュレータ: {meta.get('use_gpt_user')}",
        f"- GPT スケールモード: {meta.get('gpt_scale')}",
        "",
        "> **手動評価**: [http://127.0.0.1:5000/admin](http://127.0.0.1:5000/admin) で各 `session_id` の会話を確認してください。",
        "",
        "## エグゼクティブサマリ",
        "",
    ]
    for cat, rows in sorted(by_cat.items()):
        ok = sum(1 for r in rows if r.auto_pass)
        turns = sum(len(r.turns) for r in rows)
        lines.append(f"- **{cat}**: {ok}/{len(rows)} 自動合格 / {turns} ターン")

    lines.extend(["", "## カテゴリ別", "", "| カテゴリ | セッション | ターン | 合格 | 要確認 |", "|----------|------------|--------|------|--------|"])
    for cat, rows in sorted(by_cat.items()):
        ok = sum(1 for r in rows if r.auto_pass)
        turns = sum(len(r.turns) for r in rows)
        lines.append(f"| {cat} | {len(rows)} | {turns} | {ok} | {len(rows) - ok} |")

    latency = metrics.get("latency_this_run") or {}
    if latency:
        lines.extend(["", "## レイテンシ（KPI: p95 < 5s）", ""])
        lines.append(f"- 計測ターン数: {latency.get('turns_measured', 0)}")
        lines.append(
            f"- end-to-end: p50 {latency.get('e2e_ms_p50', 0)}ms / "
            f"**p95 {latency.get('e2e_ms_p95', 0)}ms** / max {latency.get('e2e_ms_max', 0)}ms"
        )
        phase = latency.get("phase_breakdown") or {}
        if phase:
            lines.append(
                f"- pipeline total: p50 {phase.get('total_ms_p50', 0)}ms / "
                f"p95 {phase.get('total_ms_p95', 0)}ms / max {phase.get('total_ms_max', 0)}ms"
            )
            lines.append(
                f"- LLM 呼び出し: 合計 {phase.get('llm_calls_total', 0)} / "
                f"リクエストあたり平均 {phase.get('llm_calls_per_request_avg', 0)}"
            )
            by_path = phase.get("llm_by_path") or {}
            if by_path:
                lines.append("")
                lines.append("| フェーズ(path) | 呼び出し | latency合計ms | p50 | p95 |")
                lines.append("|----------------|----------|---------------|-----|-----|")
                for path, stat in by_path.items():
                    lines.append(
                        f"| {path} | {stat.get('count', 0)} | {stat.get('latency_ms_sum', 0)} | "
                        f"{stat.get('latency_ms_p50', 0)} | {stat.get('latency_ms_p95', 0)} |"
                    )
        elif latency.get("phase_breakdown_error"):
            lines.append(f"- フェーズ別内訳: 取得不可（{latency['phase_breakdown_error']}）")
        else:
            lines.append("- フェーズ別内訳: pipeline_perf_log.jsonl に該当セッションの記録なし")

    judge = metrics.get("content_quality_judge") or {}
    if judge:
        lines.extend(["", "## 内容品質（LLM-as-judge, 0-5）", ""])
        if judge.get("judged"):
            lines.append(f"- 採点シナリオ数: {judge.get('judged', 0)}")
            lines.append(f"- **総合平均: {judge.get('overall_avg', 0)}**")
            lines.append(
                f"- 意図充足 {judge.get('intent_fulfillment_avg', 0)} / "
                f"トーン {judge.get('tone_avg', 0)} / 安全 {judge.get('safety_avg', 0)}"
            )
            lines.append(f"- 総合 ≤2 の低評価: {judge.get('low_overall_count', 0)} 件")
        else:
            lines.append("- 採点なし（--judge 未指定 または OPENAI_API_KEY 未設定）")

    lines.extend(["", "## 意図評価（intent evaluation）", ""])
    intent_eval = metrics.get("intent_evaluation") or {}
    lines.append(f"- 追跡セッション: {intent_eval.get('sessions_tracked', 0)}")
    lines.append(f"- counseling_detail マッチ: {intent_eval.get('counseling_rows_matched', 0)}")
    lines.append(f"- route ログマッチ: {intent_eval.get('route_rows_matched', 0)}")
    if intent_eval.get("intent_router_metrics"):
        lines.append(f"- IntentRouter metrics: `{json.dumps(intent_eval['intent_router_metrics'], ensure_ascii=False)[:500]}`")

    lines.extend(["", "### セッション別意図サマリ", ""])
    per_sess = intent_eval.get("per_session") or {}
    lines.append("| session_id | scenario | turns | counseling | route_events | top_routes |")
    lines.append("|------------|----------|-------|------------|--------------|------------|")
    for r in results:
        ev = per_sess.get(r.session_id, {})
        routes = ev.get("routes") or {}
        top_routes = ", ".join(f"{k}:{v}" for k, v in sorted(routes.items(), key=lambda x: -x[1])[:3])
        lines.append(
            f"| `{r.session_id}` | {r.scenario_id} | {len(r.turns)} | "
            f"{ev.get('counseling_with_response', 0)}/{ev.get('counseling_turns', 0)} | "
            f"{ev.get('route_events', 0)} | {top_routes or '—'} |"
        )

    lines.extend(["", "## 自動メトリクス（gcp-log-analysis 系）", "", "```json", json.dumps(metrics, ensure_ascii=False, indent=2)[:12000], "```", ""])

    lines.extend(["", "## 要確認シナリオ", ""])
    if not failed:
        lines.append("_自動評価で不一致なし（手動確認推奨）_")
    else:
        lines.append("| id | category | session_id | failures | last_kind |")
        lines.append("|----|----------|------------|----------|-----------|")
        for r in failed[:80]:
            last = r.turns[-1] if r.turns else None
            fails = "; ".join(r.auto_failures)[:100]
            kind = last.diagnosis_kind if last else ""
            lines.append(f"| {r.scenario_id} | {r.category} | `{r.session_id}` | {fails} | {kind} |")

    lines.extend(["", "## 全セッション — 完全トランスクリプト", ""])
    for r in results:
        lines.append(f"### {r.scenario_id} — {r.category} ({'PASS' if r.auto_pass else 'REVIEW'})")
        lines.append(f"- session_id: `{r.session_id}`")
        lines.append(f"- wave: {r.wave}")
        if r.judge and r.judge.get("overall") is not None:
            lines.append(
                f"- judge: overall {r.judge.get('overall')} "
                f"(意図 {r.judge.get('intent_fulfillment')} / トーン {r.judge.get('tone')} / "
                f"安全 {r.judge.get('safety')}) — {r.judge.get('reason', '')}"
            )
        if r.persona_id:
            lines.append(f"- persona: {r.persona_id}")
        if r.description:
            lines.append(f"- {r.description}")
        lines.extend(_format_transcript(r.turns))

    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    json_results = []
    for r in results:
        d = asdict(r)
        json_results.append(d)
    out_json.write_text(
        json.dumps(
            {"meta": meta, "metrics": metrics, "results": json_results},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def write_simulation_eval_report(
    results: list[ScenarioResult],
    meta: dict[str, Any],
    metrics: dict[str, Any],
    out_md: Path,
) -> None:
    """gcp-log-analysis スタイルの意図整合評価レポート（別ファイル）。"""
    out_md.parent.mkdir(parents=True, exist_ok=True)
    intent_eval = metrics.get("intent_evaluation") or {}
    per_sess = intent_eval.get("per_session") or {}
    total_turns = sum(len(r.turns) for r in results)
    passed = sum(1 for r in results if r.auto_pass)

    lines = [
        f"# Chat Pipeline v2 シミュレーション意図評価 ({meta.get('date')})",
        "",
        "gcp-log-analysis スタイルのローカル評価。`counseling_detail_log.jsonl` と",
        "`dialogue_route_*_log.jsonl` をセッション ID で突合し、応答の有無とルート分布を確認する。",
        "",
        f"- 実行時刻: {meta.get('started_at')}",
        f"- セッション数: {len(results)} / 総ターン: {total_turns}",
        f"- 自動合格: {passed} / 要確認: {len(results) - passed}",
        f"- GPT シミュレーション: {meta.get('gpt_scale')}",
        "",
        "## ログ突合サマリ",
        "",
        f"- 追跡セッション: {intent_eval.get('sessions_tracked', 0)}",
        f"- counseling_detail マッチ行: {intent_eval.get('counseling_rows_matched', 0)}",
        f"- route ログマッチ行: {intent_eval.get('route_rows_matched', 0)}",
        "",
        "## セッション別評価",
        "",
        "| session_id | scenario | turns | auto | counseling応答 | route_events | top_routes | intent_samples |",
        "|------------|----------|-------|------|----------------|--------------|------------|----------------|",
    ]

    for r in results:
        ev = per_sess.get(r.session_id, {})
        routes = ev.get("routes") or {}
        top_routes = ", ".join(f"{k}:{v}" for k, v in sorted(routes.items(), key=lambda x: -x[1])[:3])
        samples = ev.get("intent_samples") or []
        sample_txt = "; ".join(
            f"{s.get('user_input', '')[:40]}→{'OK' if s.get('has_response') else '—'}"
            for s in samples[:2]
        )
        lines.append(
            f"| `{r.session_id}` | {r.scenario_id} | {len(r.turns)} | "
            f"{'PASS' if r.auto_pass else 'REVIEW'} | "
            f"{ev.get('counseling_with_response', 0)}/{ev.get('counseling_turns', 0)} | "
            f"{ev.get('route_events', 0)} | {top_routes or '—'} | {sample_txt or '—'} |"
        )

    lines.extend(["", "## 要確認 — ターン別トランスクリプト", ""])
    failed = [r for r in results if not r.auto_pass]
    for r in failed[:30]:
        lines.append(f"### {r.scenario_id} (`{r.session_id}`)")
        if r.auto_failures:
            lines.append(f"- failures: {', '.join(r.auto_failures)}")
        lines.extend(_format_transcript(r.turns))

    if intent_eval.get("intent_router_metrics"):
        lines.extend([
            "",
            "## IntentRouter メトリクス",
            "",
            "```json",
            json.dumps(intent_eval["intent_router_metrics"], ensure_ascii=False, indent=2)[:8000],
            "```",
        ])

    lines.extend([
        "",
        "## Admin 確認",
        "",
        "- [http://127.0.0.1:5000/admin](http://127.0.0.1:5000/admin) → サイドバー「**v2テストのみ**」を ON",
        "- 検索: `v2-test` または `session_id`（下表）",
        "",
        "| scenario_id | session_id |",
        "|-------------|------------|",
    ])
    for r in results:
        lines.append(f"| {r.scenario_id} | `{r.session_id}` |")

    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_session_index(results: list[ScenarioResult], meta: dict[str, Any], out_path: Path) -> None:
    """Admin 参照用 session_id 一覧。"""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    rows = [
        {
            "scenario_id": r.scenario_id,
            "session_id": r.session_id,
            "category": r.category,
            "persona_id": r.persona_id,
            "turns": len(r.turns),
            "auto_pass": r.auto_pass,
            "admin_url": f"http://127.0.0.1:5000/admin",
        }
        for r in results
        if r.session_id
    ]
    out_path.write_text(
        json.dumps({"meta": meta, "sessions": rows}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main() -> int:
    _load_dotenv()
    parser = argparse.ArgumentParser(description="Chat Pipeline v2 local integration tests")
    parser.add_argument("--base-url", default=DEFAULT_BASE)
    parser.add_argument("--limit", type=int, default=0, help="Limit YAML scenarios (smoke)")
    parser.add_argument("--use-gpt-user", action="store_true")
    parser.add_argument(
        "--judge",
        action="store_true",
        help="LLM-as-judge で内容適切性を採点（OPENAI_API_KEY 必須）",
    )
    parser.add_argument("--skip-metrics", action="store_true")
    parser.add_argument("--skip-yaml", action="store_true", help="Skip static YAML scenarios")
    parser.add_argument("--sessions", type=int, default=0, help="GPT persona session count (gpt-scale)")
    parser.add_argument("--min-chats", type=int, default=0, help="Minimum total chat turns for gpt-scale")
    parser.add_argument("--report-suffix", default="v2", help="Report filename suffix")
    parser.add_argument(
        "--categories",
        default="",
        help="Comma-separated YAML category filter (e.g. session_ops,emergency)",
    )
    args = parser.parse_args()

    gpt_scale = args.sessions > 0 or args.min_chats > 0
    if gpt_scale and not args.use_gpt_user:
        print("WARN: gpt-scale requires --use-gpt-user; enabling.", file=sys.stderr)
        args.use_gpt_user = True

    if args.use_gpt_user and not os.getenv("OPENAI_API_KEY", "").strip():
        print("ERROR: OPENAI_API_KEY not set (.env or environment).", file=sys.stderr)
        return 2

    client = V2TestClient(args.base_url)
    if not client.health():
        print(f"ERROR: {args.base_url} に接続できません。app.py を起動してください。", file=sys.stderr)
        return 2

    from config.llm_flags import is_chat_pipeline_v2_enabled

    if not is_chat_pipeline_v2_enabled():
        print("WARN: CHAT_PIPELINE_V2 が OFF です。APP_ENV=development を確認してください。", file=sys.stderr)

    started = time.time()
    started_at = datetime.now(timezone.utc).isoformat()
    date_slug = datetime.now().strftime("%Y-%m-%d")
    results: list[ScenarioResult] = []

    if not args.skip_yaml:
        scenarios = _load_scenarios()
        if args.categories.strip():
            cats = {c.strip() for c in args.categories.split(",") if c.strip()}
            scenarios = [s for s in scenarios if str(s.get("category") or "") in cats]
        if args.limit > 0:
            scenarios = scenarios[: args.limit]
        print(f"Running {len(scenarios)} YAML scenarios against {args.base_url} ...")
        for i, spec in enumerate(scenarios, 1):
            print(f"  [yaml {i}/{len(scenarios)}] {spec.get('id')} ...", flush=True)
            try:
                results.append(_run_scenario(client, spec, use_gpt_user=args.use_gpt_user))
            except Exception as exc:
                results.append(
                    ScenarioResult(
                        scenario_id=str(spec.get("id", f"error_{i}")),
                        category=str(spec.get("category", "error")),
                        wave=str(spec.get("wave", "")),
                        session_id="",
                        auto_pass=False,
                        auto_failures=[f"exception:{exc}"],
                    )
                )

    if gpt_scale:
        personas = _load_personas()
        n_sessions = args.sessions or max(10, len(personas) or 12)
        personas = personas[:n_sessions] if personas else []
        if not personas:
            print("ERROR: No personas in tests/fixtures/v2_gpt_personas.yaml", file=sys.stderr)
            return 2

        min_chats = args.min_chats or 500
        turns_each = max(40, (min_chats + len(personas) - 1) // len(personas))
        print(f"Running GPT scale: {len(personas)} sessions × ~{turns_each} turns (target {min_chats}+ chats) ...")
        for i, persona in enumerate(personas, 1):
            print(f"  [gpt {i}/{len(personas)}] {persona.get('id')} ({turns_each} turns) ...", flush=True)
            try:
                results.append(_run_gpt_persona_session(client, persona, turns_per_session=turns_each))
            except Exception as exc:
                results.append(
                    ScenarioResult(
                        scenario_id=f"gpt-{persona.get('id', i)}",
                        category=str(persona.get("category", "gpt")),
                        wave="gpt-scale",
                        session_id="",
                        auto_pass=False,
                        auto_failures=[f"exception:{exc}"],
                        persona_id=str(persona.get("id") or ""),
                    )
                )

    if not results:
        print("ERROR: No scenarios to run.", file=sys.stderr)
        return 2

    if args.judge:
        if not os.getenv("OPENAI_API_KEY", "").strip():
            print("WARN: --judge 指定だが OPENAI_API_KEY 未設定のためスキップ。", file=sys.stderr)
        else:
            print(f"Judging {len(results)} scenarios (LLM-as-judge) ...", flush=True)
            for r in results:
                try:
                    r.judge = _judge_scenario({"description": r.description}, r.turns)
                except Exception as exc:
                    r.judge = {"error": str(exc)[:200]}

    elapsed = round(time.time() - started, 1)
    session_ids = {r.session_id for r in results if r.session_id}
    metrics = {} if args.skip_metrics else _run_auto_metrics(started, session_ids)
    metrics["latency_this_run"] = _latency_summary(results, session_ids, started)
    if args.judge:
        metrics["content_quality_judge"] = _aggregate_judge(results)

    suffix = args.report_suffix.strip() or "v2"
    out_dir = PROJECT_ROOT / "log" / "analysis"
    out_md = out_dir / f"{date_slug}_local_v2_chat_test_{suffix}.md"
    out_json = out_dir / f"{date_slug}_local_v2_chat_test_{suffix}.json"
    total_turns = sum(len(r.turns) for r in results)
    meta = {
        "date": date_slug,
        "base_url": args.base_url,
        "started_at": started_at,
        "elapsed_sec": elapsed,
        "scenario_count": len(results),
        "total_turns": total_turns,
        "auto_pass": sum(1 for r in results if r.auto_pass),
        "use_gpt_user": args.use_gpt_user,
        "gpt_scale": gpt_scale,
        "v2_enabled": is_chat_pipeline_v2_enabled(),
    }
    write_report(results, meta, metrics, out_md, out_json)
    eval_md = out_dir / f"{date_slug}_local_v2_simulation_eval_{suffix}.md"
    write_simulation_eval_report(results, meta, metrics, eval_md)
    session_index = out_dir / f"{date_slug}_local_v2_session_ids_{suffix}.json"
    write_session_index(results, meta, session_index)

    passed = meta["auto_pass"]
    print(f"\nDone: {passed}/{len(results)} auto-pass, {total_turns} turns.")
    print(f"Report: {out_md}")
    print(f"Eval:   {eval_md}")
    print(f"IDs:    {session_index}")
    print("Admin review: http://127.0.0.1:5000/admin")
    print("Server left running (do not stop).")
    return 0 if passed >= len(results) * 0.5 else 1


if __name__ == "__main__":
    raise SystemExit(main())
