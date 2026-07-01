"""
session_id 単位の会話再構成・意図紐づけ・ヒューリスティック評価。
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple

from src.analysis.session_transcript_markdown import (
    build_turn_timing,
    enrich_routing_from_trace,
)

GREETING_INPUT_RE = re.compile(
    r"^(やあ|やっ|おい|こんにちは|こんばんは|おはよう|hello|hi|hey|👋|🙋)[\s!！.。?？]*$",
    re.I,
)
CONFUSION_INPUT_RE = re.compile(r"^(えっ|え\?|は\?|意味|わから|なに\?|何\?|huh|\?+)$", re.I)
OFFENSIVE_INPUT_RE = re.compile(r"[🖕💩👹]|クソ|死ね|ふざけ|バカ|馬鹿|殺", re.I)
IMAGE_GEN_RE = re.compile(r"画像|生成して|draw|generate.*image|作って", re.I)
OFF_TOPIC_RE = re.compile(r"マチュピチュ|迷子|観光|遺失|在庫|トイレ|駐車")
ABOUT_APP_RE = re.compile(
    r"(アプリ|サービス|サイト|このツール|このチャット).*(について|教えて|できること)"
    r"|あなた|おまえ|君は|だれ|誰"
    r"|otcって|OTCって",
    re.I,
)
PHYSICAL_SYMPTOM_RE = re.compile(
    r"痛|熱|咳|鼻|頭|腹痛|吐|下痢|痒|腫|寒|倦怠|不眠|発熱|風邪|症状|headache|pain|fever|cough",
    re.I,
)
GREETING_RESPONSE_RE = re.compile(
    r"こんにちは|何かお困り|お待ちして|お聞かせください|feel free",
    re.I,
)
_STORE_RESPONSE_MARKERS = (
    "店内のスタッフ",
    "お近くのスタッフ",
    "店舗案内",
    "在庫",
)
_SECURITY_RESPONSE_MARKERS = (
    "攻撃的な表現",
    "不審なパターン",
    "お答えできません",
)
MEDICAL_REFERRAL_RE = re.compile(r"医療機関|受診|病院|診察|医師に相談")
ABOUT_CARD_RE = re.compile(r"このツールについて|chat-status-card--notice")
META_FOLLOW_UP_INPUT_RE = re.compile(
    r"(詳しく|もっと|続き|深く|さらに|具体的に|もう少し)"
)

ISSUE_DEFS: Tuple[Tuple[str, str], ...] = (
    ("greeting_to_non_greeting", "挨拶以外の入力に挨拶テンプレート応答"),
    ("meta_follow_up_to_greeting", "メタ会話フォローアップが挨拶に化けた"),
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
    if META_FOLLOW_UP_INPUT_RE.search(text):
        labels.append("meta_follow_up")
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
    normalized_input = user_input.strip()
    if not timestamp:
        for trace in traces:
            if trace.get("session_id") and trace.get("session_id") != session_id:
                continue
            if (trace.get("user_message") or "").strip() == normalized_input:
                return trace
        return None

    candidates: List[Tuple[float, Dict[str, Any]]] = []
    for trace in traces:
        if trace.get("session_id") and trace.get("session_id") != session_id:
            continue
        started = trace.get("started_at")
        ts_resp, ts_start = _parse_ts(timestamp), _parse_ts(started)
        if not ts_resp or not ts_start:
            continue
        if ts_start > ts_resp:
            continue
        delta_sec = (ts_resp - ts_start).total_seconds()
        if delta_sec > window_seconds:
            continue
        score = delta_sec
        trace_msg = (trace.get("user_message") or "").strip()
        if trace_msg and trace_msg == normalized_input:
            score -= 10.0
        candidates.append((score, trace))
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0])
    return candidates[0][1]


def _normalize_history_role(role: str) -> str:
    value = (role or "").lower()
    if value in ("user",):
        return "user"
    if value in ("bot", "assistant"):
        return "assistant"
    if value in ("system",):
        return "system"
    return value


def extract_pairs_from_conversation_history(
    history: Optional[Sequence[Dict[str, Any]]],
) -> List[Dict[str, str]]:
    """counseling_detail.conversation_history から user/bot ペアを抽出。"""
    if not history:
        return []
    pairs: List[Dict[str, str]] = []
    pending_user: Optional[str] = None
    for item in history:
        role = _normalize_history_role(str(item.get("type") or item.get("role") or ""))
        content = str(item.get("content") or "").strip()
        if role == "system" or not content:
            continue
        if role == "user":
            pending_user = content
        elif role == "assistant" and pending_user is not None:
            pairs.append({"user_input": pending_user, "response": content})
            pending_user = None
    return pairs


def _turn_dedupe_key(user_input: str, response: str) -> Tuple[str, str]:
    return (user_input.strip(), _strip_html(response)[:240])


def _estimate_response_timestamp_from_trace(trace: Optional[Dict[str, Any]]) -> Optional[str]:
    if not trace:
        return None
    started = trace.get("started_at")
    perf = trace.get("pipeline_perf") or {}
    total_ms = perf.get("total_ms")
    t0 = _parse_ts(started)
    if t0 and total_ms is not None:
        dt = t0 + timedelta(milliseconds=float(total_ms))
        return dt.isoformat().replace("+00:00", "Z")
    return started


def _seed_sort_key(seed: Dict[str, Any]) -> datetime:
    ts = seed.get("timestamp")
    trace = seed.get("trace") or {}
    parsed = _parse_ts(ts) or _parse_ts(trace.get("started_at"))
    return parsed or datetime.min.replace(tzinfo=timezone.utc)


def _collect_session_turn_seeds(
    turns_raw: Sequence[Dict[str, Any]],
    session_traces: Sequence[Dict[str, Any]],
    *,
    include_trace_only: bool,
) -> List[Dict[str, Any]]:
    """counseling_detail / conversation_history / chat_flow からターン候補を集約。"""
    by_key: Dict[Tuple[str, str], Dict[str, Any]] = {}
    source_rank = {"counseling_detail": 0, "conversation_history": 1, "chat_flow": 2}

    def upsert(
        *,
        user_input: str,
        response: str,
        timestamp: Optional[str],
        source: str,
        trace: Optional[Dict[str, Any]] = None,
    ) -> None:
        key = _turn_dedupe_key(user_input, response)
        existing = by_key.get(key)
        if existing is None:
            by_key[key] = {
                "user_input": user_input,
                "response": response,
                "timestamp": timestamp,
                "source": source,
                "trace": trace,
            }
            return
        if source_rank.get(source, 9) < source_rank.get(existing["source"], 9):
            existing["source"] = source
        if timestamp and not existing.get("timestamp"):
            existing["timestamp"] = timestamp
        if trace and not existing.get("trace"):
            existing["trace"] = trace

    for obj in sorted(turns_raw, key=lambda x: str(x.get("timestamp") or "")):
        for pair in extract_pairs_from_conversation_history(obj.get("conversation_history")):
            upsert(
                user_input=pair["user_input"],
                response=pair["response"],
                timestamp=None,
                source="conversation_history",
            )
        upsert(
            user_input=str(obj.get("user_input") or ""),
            response=str(obj.get("response") or ""),
            timestamp=str(obj.get("timestamp") or "") or None,
            source="counseling_detail",
        )

    if include_trace_only:
        covered_inputs = {s["user_input"].strip() for s in by_key.values()}
        for trace in sorted(session_traces, key=lambda t: str(t.get("started_at") or "")):
            user_input = (trace.get("user_message") or "").strip()
            if not user_input or user_input in covered_inputs:
                continue
            covered_inputs.add(user_input)
            upsert(
                user_input=user_input,
                response="",
                timestamp=_estimate_response_timestamp_from_trace(trace),
                source="chat_flow",
                trace=trace,
            )

    seeds = list(by_key.values())
    seeds.sort(key=_seed_sort_key)
    return seeds


def _build_turn_from_seed(
    seed: Dict[str, Any],
    *,
    session_id: str,
    session_traces: Sequence[Dict[str, Any]],
    prior_turns: Sequence[Dict[str, Any]],
    prev_response_at: Optional[str],
) -> Dict[str, Any]:
    user_input = str(seed.get("user_input") or "")
    response = str(seed.get("response") or "")
    timestamp = seed.get("timestamp")
    trace = seed.get("trace")
    if not trace:
        trace = _match_trace_for_turn(
            session_traces,
            session_id=session_id,
            timestamp=str(timestamp or ""),
            user_input=user_input,
        )
    if not timestamp:
        timestamp = _estimate_response_timestamp_from_trace(trace)

    plain = _strip_html(response)
    response_missing = not plain.strip()
    response_preview = plain[:500] if not response_missing else ""
    input_labels = classify_user_input(user_input)
    routing = enrich_routing_from_trace(trace)
    timing = build_turn_timing(
        trace=trace,
        response_at=str(timestamp or ""),
        previous_response_at=prev_response_at,
    )
    issues: List[Dict[str, Any]] = []
    if not response_missing:
        issues = detect_turn_issues(
            user_input=user_input,
            response=response,
            input_labels=input_labels,
            routing=routing,
            prior_turns=prior_turns,
        )
    return {
        "timestamp": timestamp,
        "user_input": user_input,
        "response_preview": response_preview,
        "response_html": response.strip().startswith("<"),
        "response_missing": response_missing,
        "turn_source": seed.get("source"),
        "input_labels": input_labels,
        "routing": routing,
        "timing": timing,
        "conversation_history": _conversation_history_before(prior_turns),
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
    route_kind = str((routing or {}).get("kind") or "")
    if any(m in plain for m in _STORE_RESPONSE_MARKERS) or route_kind in (
        "store_facilities",
        "store_inventory",
        "store_locator",
        "aggressive_input",
        "known_attack",
    ):
        looks_greeting_response = False
    if any(m in plain for m in _SECURITY_RESPONSE_MARKERS):
        looks_greeting_response = False

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
        if "meta_follow_up" in input_labels:
            add(
                "meta_follow_up_to_greeting",
                "critical",
                "メタ会話の続き（詳しく/もっと等）が greeting に誤分類",
                f"input={user_input!r} intent=greeting",
            )
        elif "about_or_capabilities" in input_labels or "image_generation" in input_labels or "offensive" in input_labels:
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
    trace_only_session_count = 0

    def build_one_session(session_id: str, turns_raw: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
        session_traces = traces_by_session.get(session_id, [])
        seeds = _collect_session_turn_seeds(
            turns_raw,
            session_traces,
            include_trace_only=True,
        )
        if len(seeds) > max_turns_per_session:
            seeds = seeds[-max_turns_per_session:]

        built_turns: List[Dict[str, Any]] = []
        prev_response_at: Optional[str] = None
        for seed in seeds:
            turn = _build_turn_from_seed(
                seed,
                session_id=session_id,
                session_traces=session_traces,
                prior_turns=built_turns,
                prev_response_at=prev_response_at,
            )
            built_turns.append(turn)
            prev_response_at = str(turn.get("timestamp") or "") or prev_response_at
            for issue in turn.get("issues") or []:
                all_mismatches.append(
                    {
                        "session_id": session_id,
                        "timestamp": turn.get("timestamp"),
                        "user_input": str(turn.get("user_input") or "")[:200],
                        "issue_type": issue["type"],
                        "severity": issue["severity"],
                        "cause_hypothesis": issue["cause_hypothesis"],
                        "evidence": issue["evidence"],
                        "routing": turn.get("routing") or {},
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

        turn_sources = Counter(str(t.get("turn_source") or "unknown") for t in built_turns)
        return {
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
            "turn_sources": dict(turn_sources),
            "trace_only": not turns_raw,
        }

    counseling_session_ids = set(by_session.keys())
    trace_session_ids = set(traces_by_session.keys())
    all_session_ids = sorted(counseling_session_ids | trace_session_ids)

    for session_id in all_session_ids:
        turns_raw = by_session.get(session_id, [])
        if not turns_raw and session_id in trace_session_ids:
            trace_only_session_count += 1
        sessions_out.append(build_one_session(session_id, turns_raw))

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
        "session_count": len(all_session_ids),
        "exported_session_count": len(sessions_out),
        "counseling_session_count": len(counseling_session_ids),
        "trace_only_session_count": trace_only_session_count,
        "chat_flow_trace_count": chat_flow.get("trace_count", len(traces)),
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
