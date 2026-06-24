"""
session_id 単位の会話再構成・意図紐づけ・ヒューリスティック評価。
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple

GREETING_INPUT_RE = re.compile(
    r"^(やあ|やっ|おい|こんにちは|こんばんは|おはよう|hello|hi|hey|👋|🙋)[\s!！.。?？]*$",
    re.I,
)
CONFUSION_INPUT_RE = re.compile(r"^(えっ|え\?|は\?|意味|わから|なに\?|何\?|huh|\?+)$", re.I)
OFFENSIVE_INPUT_RE = re.compile(r"[🖕💩👹]|クソ|死ね|ふざけ|バカ|馬鹿|殺", re.I)
IMAGE_GEN_RE = re.compile(r"画像|生成して|draw|generate.*image|作って", re.I)
OFF_TOPIC_RE = re.compile(r"マチュピチュ|迷子|観光|遺失|在庫|トイレ|駐車")
ABOUT_APP_RE = re.compile(
    r"について|教えて$|あなた|おまえ|君は|だれ|誰|どこ|病院|クリニック|otcって|OTCって|できること",
    re.I,
)
PHYSICAL_SYMPTOM_RE = re.compile(
    r"痛|熱|咳|鼻|頭|腹痛|吐|下痢|痒|腫|寒|倦怠|不眠|発熱|風邪|症状|headache|pain|fever|cough",
    re.I,
)
GREETING_RESPONSE_RE = re.compile(
    r"こんにちは|お気軽に|何かお困り|お待ちして|ご相談|お聞かせください|feel free|hello",
    re.I,
)
MEDICAL_REFERRAL_RE = re.compile(r"医療機関|受診|病院|診察|医師に相談")
ABOUT_CARD_RE = re.compile(r"このツールについて|chat-status-card--notice")

ISSUE_DEFS: Tuple[Tuple[str, str], ...] = (
    ("greeting_to_non_greeting", "挨拶以外の入力に挨拶テンプレート応答"),
    ("offensive_input_ignored", "攻撃的・不適切入力への適切な境界設定なし"),
    ("confusion_not_addressed", "困惑・疑問符入力への文脈ない応答"),
    ("image_gen_medical_referral", "画像生成依頼に受診勧告など不適切ルーティング"),
    ("about_question_mishandled", "アプリ説明・能力質問への不適切応答"),
    ("symptom_ignored", "症状入力に一般挨拶のみ"),
    ("intent_routing_gap", "検出 intent / triage と応答内容の乖離"),
    ("duplicate_turn", "同一入力への重複応答"),
    ("concierge_not_handled", "Concierge handled=false のまま不自然応答"),
    ("off_topic_pivoted", "店舗・施設外の質問を薬相談テンプレにすり替え"),
)


def _parse_ts(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _strip_html(text: str) -> str:
    cleaned = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", cleaned).strip()


def _seconds_between(a: Optional[str], b: Optional[str]) -> Optional[float]:
    ta, tb = _parse_ts(a), _parse_ts(b)
    if not ta or not tb:
        return None
    return abs((ta - tb).total_seconds())


def classify_user_input(user_input: str) -> List[str]:
    text = (user_input or "").strip()
    if not text:
        return ["empty"]
    labels: List[str] = []
    if GREETING_INPUT_RE.match(text):
        labels.append("greeting")
    if CONFUSION_INPUT_RE.match(text):
        labels.append("confusion")
    if OFFENSIVE_INPUT_RE.search(text):
        labels.append("offensive")
    if IMAGE_GEN_RE.search(text):
        labels.append("image_generation")
    if ABOUT_APP_RE.search(text):
        labels.append("about_or_capabilities")
    if OFF_TOPIC_RE.search(text):
        labels.append("off_topic_store")
    if PHYSICAL_SYMPTOM_RE.search(text):
        labels.append("physical_symptom")
    if len(text) <= 3 and not labels:
        labels.append("short_or_emoji")
    if not labels:
        labels.append("general")
    return labels


def _routing_from_trace(trace: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not trace:
        return {}
    handoff_target = None
    concierge_handled = None
    for step in trace.get("agent_steps") or []:
        payload = step.get("payload") or {}
        if step.get("agent") == "ChatOrchestrator" and step.get("step") == "handoff":
            handoff_target = payload.get("target")
        if step.get("agent") == "ConciergeAgent" and step.get("step") == "complete":
            concierge_handled = payload.get("handled")
    return {
        "trace_id": trace.get("trace_id"),
        "triage": trace.get("triage"),
        "concierge_intent": trace.get("concierge_intent"),
        "structural_intent": trace.get("structural_intent"),
        "meta_intent": trace.get("meta_intent"),
        "handoff_target": handoff_target,
        "concierge_handled": concierge_handled,
        "total_ms": (trace.get("pipeline_perf") or {}).get("total_ms"),
        "channel": (trace.get("pipeline_perf") or {}).get("channel"),
    }


def _match_trace_for_turn(
    traces: Sequence[Dict[str, Any]],
    *,
    session_id: str,
    timestamp: str,
    user_input: str,
    window_seconds: float = 45.0,
) -> Optional[Dict[str, Any]]:
    candidates: List[Tuple[float, Dict[str, Any]]] = []
    for trace in traces:
        if trace.get("session_id") and trace.get("session_id") != session_id:
            continue
        delta = _seconds_between(timestamp, trace.get("started_at"))
        if delta is None:
            continue
        if delta > window_seconds:
            continue
        score = delta
        trace_msg = (trace.get("user_message") or "").strip()
        if trace_msg and trace_msg == user_input.strip():
            score -= 10.0
        candidates.append((score, trace))
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0])
    return candidates[0][1]


def _answers_about_question(user_input: str, plain: str) -> bool:
    if ABOUT_CARD_RE.search(plain):
        return True
    if re.search(r"OTC|市販薬|over the counter", plain, re.I) and re.search(
        r"OTC|市販薬", user_input, re.I
    ):
        return True
    if re.search(r"チャット型|相談ツール|一般用医薬品|処方せん", plain):
        return True
    return False


def detect_turn_issues(
    *,
    user_input: str,
    response: str,
    input_labels: Sequence[str],
    routing: Dict[str, Any],
    prior_turns: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    issues: List[Dict[str, Any]] = []
    plain = _strip_html(response)
    lower_input = user_input.strip().lower()

    def add(issue_type: str, severity: str, cause: str, evidence: str) -> None:
        issues.append(
            {
                "type": issue_type,
                "severity": severity,
                "cause_hypothesis": cause,
                "evidence": evidence[:300],
            }
        )

    is_greeting_input = "greeting" in input_labels or "short_or_emoji" in input_labels
    looks_greeting_response = bool(GREETING_RESPONSE_RE.search(plain))

    if not is_greeting_input and looks_greeting_response:
        if "offensive" in input_labels:
            add(
                "offensive_input_ignored",
                "critical",
                "不適切入力が greeting / concierge テンプレに落ちた",
                f"input={user_input!r} response={plain[:120]!r}",
            )
        elif "confusion" in input_labels:
            add(
                "confusion_not_addressed",
                "warning",
                "困惑入力に対し前ターンの説明を補足せず挨拶テンプレを返した",
                f"input={user_input!r}",
            )
        elif "physical_symptom" in input_labels:
            add(
                "symptom_ignored",
                "critical",
                "症状入力なのに一般挨拶のみでトリアージ/推奨に進んでいない",
                f"input={user_input!r}",
            )
        elif "about_or_capabilities" in input_labels and not _answers_about_question(user_input, plain):
            add(
                "about_question_mishandled",
                "warning",
                "アプリ説明系の質問に about カードではなく汎用挨拶を返した",
                f"input={user_input!r}",
            )
        else:
            add(
                "greeting_to_non_greeting",
                "warning",
                "非挨拶入力に挨拶テンプレート応答",
                f"input={user_input!r} labels={list(input_labels)}",
            )

    if "off_topic_store" in input_labels and GREETING_RESPONSE_RE.search(plain) and "市販薬" in plain:
        if not re.search(r"迷子|観光|遺失|マチュピチュ", plain):
            add(
                "off_topic_pivoted",
                "warning",
                "スコープ外（店舗案内・観光等）の質問に薬相談テンプレで返した",
                f"input={user_input!r}",
            )

    if "image_generation" in input_labels and MEDICAL_REFERRAL_RE.search(plain):
        add(
            "image_gen_medical_referral",
            "critical",
            "スコープ外（画像生成）が Physical/受診フォールバックに落ちた",
            f"input={user_input!r} response={plain[:120]!r}",
        )

    if "about_or_capabilities" in input_labels:
        intent = routing.get("concierge_intent") or routing.get("meta_intent")
        if (
            intent
            and intent not in ("app_about", "capabilities", "greeting")
            and not _answers_about_question(user_input, plain)
        ):
            add(
                "about_question_mishandled",
                "warning",
                f"meta/concierge intent={intent} が about 系質問と不一致",
                f"input={user_input!r}",
            )

    triage = routing.get("triage") or {}
    triage_cat = triage.get("category")
    if triage_cat and triage_cat not in ("Other", "Ask") and looks_greeting_response and "greeting" not in input_labels:
        add(
            "intent_routing_gap",
            "warning",
            f"triage={triage_cat} なのに挨拶応答",
            f"input={user_input!r} triage={triage}",
        )

    concierge_intent = routing.get("concierge_intent")
    if concierge_intent == "greeting" and not is_greeting_input and "physical_symptom" not in input_labels:
        if "about_or_capabilities" in input_labels or "image_generation" in input_labels or "offensive" in input_labels:
            add(
                "intent_routing_gap",
                "warning",
                "concierge_intent=greeting が非挨拶入力に誤適用",
                f"input={user_input!r} intent=greeting",
            )

    if routing.get("concierge_handled") is False and looks_greeting_response:
        add(
            "concierge_not_handled",
            "info",
            "Concierge が handled=false のため下流ハンドラまたはフォールバック応答の可能性",
            f"trace_id={routing.get('trace_id')}",
        )

    for prior in prior_turns:
        if prior.get("user_input") == user_input and prior.get("response_preview") == plain[:400]:
            add(
                "duplicate_turn",
                "info",
                "同一セッション内で同一入出力が繰り返された（再送または重複処理）",
                f"input={user_input!r}",
            )
            break

    if "offensive" in input_labels and not any(i["type"] == "offensive_input_ignored" for i in issues):
        if not MEDICAL_REFERRAL_RE.search(plain) and looks_greeting_response:
            add(
                "offensive_input_ignored",
                "critical",
                "攻撃的入力に境界設定せず通常挨拶",
                f"input={user_input!r}",
            )

    # dedupe by type
    seen: set[str] = set()
    unique: List[Dict[str, Any]] = []
    for issue in issues:
        if issue["type"] in seen:
            continue
        seen.add(issue["type"])
        unique.append(issue)
    return unique


def _session_grade(issue_count: int, critical_count: int, warning_count: int, turn_count: int) -> str:
    if critical_count >= 2 or (critical_count >= 1 and turn_count >= 3):
        return "poor"
    if critical_count >= 1 or warning_count >= 3:
        return "needs_improvement"
    if warning_count >= 1:
        return "acceptable_with_issues"
    if turn_count == 0:
        return "no_data"
    return "good"


def _summarize_session_narrative(
    session_id: str,
    turns: Sequence[Dict[str, Any]],
    evaluation: Dict[str, Any],
) -> str:
    turn_count = len(turns)
    grade = evaluation.get("overall_grade", "unknown")
    issue_types = evaluation.get("issue_type_counts") or {}
    top_issues = ", ".join(f"{k}×{v}" for k, v in sorted(issue_types.items(), key=lambda x: -x[1])[:4])
    first_input = turns[0].get("user_input", "") if turns else ""
    last_input = turns[-1].get("user_input", "") if turns else ""
    return (
        f"session={session_id} turns={turn_count} grade={grade}"
        + (f" issues=[{top_issues}]" if top_issues else "")
        + f" first={first_input[:40]!r} last={last_input[:40]!r}"
    )


def dedupe_counseling_details(
    counseling_objects: Sequence[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], int]:
    """同一 session・timestamp・入出力の重複 counseling_detail を除去。"""
    seen: set[tuple[Any, ...]] = set()
    deduped: List[Dict[str, Any]] = []
    removed = 0
    for obj in sorted(counseling_objects, key=lambda x: str(x.get("timestamp") or "")):
        key = (
            obj.get("session_id"),
            obj.get("timestamp"),
            obj.get("user_input"),
            str(obj.get("response") or "")[:240],
        )
        if key in seen:
            removed += 1
            continue
        seen.add(key)
        deduped.append(obj)
    return deduped, removed


def _conversation_history_before(turns: Sequence[Dict[str, Any]]) -> List[Dict[str, str]]:
    history: List[Dict[str, str]] = []
    for turn in turns:
        history.append({"role": "user", "content": str(turn.get("user_input") or "")})
        history.append({"role": "assistant", "content": str(turn.get("response_preview") or "")})
    return history


def _full_conversation_history(turns: Sequence[Dict[str, Any]]) -> List[Dict[str, str]]:
    return _conversation_history_before(turns)


def build_session_conversations(
    counseling_details: Sequence[Dict[str, Any]],
    chat_flow: Dict[str, Any],
    *,
    max_sessions: int = 50,
    max_turns_per_session: int = 80,
) -> Dict[str, Any]:
    traces = chat_flow.get("exported_traces") or []
    traces_by_session: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for trace in traces:
        sid = trace.get("session_id")
        if sid:
            traces_by_session[str(sid)].append(trace)

    by_session: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for obj in counseling_details:
        sid = str(obj.get("session_id") or "unknown")
        by_session[sid].append(obj)

    sessions_out: List[Dict[str, Any]] = []
    all_mismatches: List[Dict[str, Any]] = []

    for session_id, turns_raw in sorted(by_session.items(), key=lambda x: x[0]):
        turns_sorted = sorted(turns_raw, key=lambda t: str(t.get("timestamp") or ""))
        if len(turns_sorted) > max_turns_per_session:
            turns_sorted = turns_sorted[-max_turns_per_session:]

        session_traces = traces_by_session.get(session_id, [])
        built_turns: List[Dict[str, Any]] = []

        for obj in turns_sorted:
            user_input = str(obj.get("user_input") or "")
            response = str(obj.get("response") or "")
            timestamp = str(obj.get("timestamp") or "")
            plain = _strip_html(response)
            input_labels = classify_user_input(user_input)
            matched_trace = _match_trace_for_turn(
                session_traces,
                session_id=session_id,
                timestamp=timestamp,
                user_input=user_input,
            )
            routing = _routing_from_trace(matched_trace)
            issues = detect_turn_issues(
                user_input=user_input,
                response=response,
                input_labels=input_labels,
                routing=routing,
                prior_turns=built_turns,
            )
            turn = {
                "timestamp": timestamp,
                "user_input": user_input,
                "response_preview": plain[:500],
                "response_html": response.strip().startswith("<"),
                "input_labels": input_labels,
                "routing": routing,
                "conversation_history": _conversation_history_before(built_turns),
                "heuristic_signals": issues,
                "issues": issues,
                "llm_review_required": True,
                "turn_grade": (
                    "critical"
                    if any(i["severity"] == "critical" for i in issues)
                    else "warning"
                    if issues
                    else "ok"
                ),
            }
            built_turns.append(turn)
            for issue in issues:
                all_mismatches.append(
                    {
                        "session_id": session_id,
                        "timestamp": timestamp,
                        "user_input": user_input[:200],
                        "issue_type": issue["type"],
                        "severity": issue["severity"],
                        "cause_hypothesis": issue["cause_hypothesis"],
                        "evidence": issue["evidence"],
                        "routing": routing,
                    }
                )

        issue_counter = Counter(i["type"] for t in built_turns for i in t.get("issues") or [])
        severity_counter = Counter(
            i["severity"] for t in built_turns for i in t.get("issues") or []
        )
        evaluation = {
            "turn_count": len(built_turns),
            "issue_count": sum(issue_counter.values()),
            "critical_count": severity_counter.get("critical", 0),
            "warning_count": severity_counter.get("warning", 0),
            "issue_type_counts": dict(issue_counter),
            "overall_grade": _session_grade(
                sum(issue_counter.values()),
                severity_counter.get("critical", 0),
                severity_counter.get("warning", 0),
                len(built_turns),
            ),
            "strengths": _session_strengths(built_turns),
            "weaknesses": _session_weaknesses(built_turns, issue_counter),
        }
        evaluation["summary"] = _summarize_session_narrative(session_id, built_turns, evaluation)

        sessions_out.append(
            {
                "session_id": session_id,
                "channel": _session_channel(session_id, built_turns),
                "time_range": {
                    "start": built_turns[0]["timestamp"] if built_turns else None,
                    "end": built_turns[-1]["timestamp"] if built_turns else None,
                },
                "conversation_history": _full_conversation_history(built_turns),
                "turns": built_turns,
                "evaluation": evaluation,
                "llm_session_review_required": True,
            }
        )

    sessions_out.sort(
        key=lambda s: (
            {"poor": 0, "needs_improvement": 1, "acceptable_with_issues": 2, "good": 3, "no_data": 4}.get(
                s["evaluation"]["overall_grade"], 5
            ),
            -s["evaluation"]["issue_count"],
        )
    )
    if len(sessions_out) > max_sessions:
        sessions_out = sessions_out[:max_sessions]

    all_mismatches.sort(
        key=lambda m: {"critical": 0, "warning": 1, "info": 2}.get(m["severity"], 3)
    )

    return {
        "session_count": len(by_session),
        "exported_session_count": len(sessions_out),
        "sessions": sessions_out,
        "intent_mismatches": all_mismatches,
        "mismatch_count": len(all_mismatches),
        "sessions_by_grade": dict(Counter(s["evaluation"]["overall_grade"] for s in sessions_out)),
    }


def _session_channel(session_id: str, turns: Sequence[Dict[str, Any]]) -> str:
    if str(session_id).startswith("line:"):
        return "line"
    for turn in turns:
        if turn.get("routing", {}).get("channel") == "line":
            return "line"
        if turn.get("routing", {}).get("channel") == "web":
            return "web"
    return "web"


def _session_strengths(turns: Sequence[Dict[str, Any]]) -> List[str]:
    strengths: List[str] = []
    if not turns:
        return strengths
    ok_turns = sum(1 for t in turns if t.get("turn_grade") == "ok")
    if ok_turns == len(turns):
        strengths.append("全ターンでヒューリスティック上の問題なし")
    elif ok_turns > 0:
        strengths.append(f"{ok_turns}/{len(turns)} ターンは応答が入力意図と整合")
    about_ok = sum(
        1
        for t in turns
        if "about_or_capabilities" in t.get("input_labels", [])
        and ABOUT_CARD_RE.search(t.get("response_preview", ""))
    )
    if about_ok:
        strengths.append("アプリ説明質問に about カードで正しく応答したターンあり")
    return strengths


def _session_weaknesses(
    turns: Sequence[Dict[str, Any]],
    issue_counter: Counter[str],
) -> List[str]:
    weaknesses: List[str] = []
    for issue_type, _label in ISSUE_DEFS:
        count = issue_counter.get(issue_type, 0)
        if count:
            weaknesses.append(f"{issue_type}: {count}件")
    greeting_loops = sum(
        1
        for t in turns
        if t.get("turn_grade") != "ok" and "greeting" in t.get("input_labels", [])
    )
    if greeting_loops and issue_counter.get("greeting_to_non_greeting", 0) == 0:
        pass
    repeat_inputs = len(turns) - len({t.get("user_input") for t in turns})
    if repeat_inputs >= 2:
        weaknesses.append(f"同一ユーザーが似た入力を繰り返し（{repeat_inputs}回）— 文脈維持が課題")
    return weaknesses
