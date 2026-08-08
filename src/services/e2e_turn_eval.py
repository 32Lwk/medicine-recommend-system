"""E2E ターン別ルール評価 — local_v2_chat_test_runner / golden PR ゲート用。"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any, Callable, Optional

GREETING_ONLY_RE = re.compile(
    r"^(こんにちは|こんばんは|おはよう|はじめまして)[!！。.\s]*$",
    re.IGNORECASE,
)

REJECT_NO_RECO = "推奨医薬品の情報では回答できません"
REJECT_NO_RECO_ALT = "推奨医薬品の情報では回答不可"

ASSISTANT_ECHO_PATTERNS = (
    "お近くの登録販売者に",
    "症状を教えてください",
    "もう少し詳しく教えてください",
    "具体的に教えていただけますか",
)

QUESTION_MARKERS = ("？", "?", "何", "どう", "どっち", "どちら", "いつ", "なぜ", "どれ", "教えて", "ですか", "でしょうか")

_ANAPHORA_RE = re.compile(r"それ|この|あの|さっき|言われた|おすすめ(?:の|さ)?(?:やつ|薬)?|前の")


def _user_has_anaphora(text: str) -> bool:
    return bool(_ANAPHORA_RE.search(text or ""))

# user 発話トピック → bot 応答に含まれうる同義語
_QUESTION_TOPIC_SYNS: tuple[tuple[re.Pattern[str], tuple[str, ...]], ...] = (
    (re.compile(r"お酒|飲酒|アルコール"), ("お酒", "飲酒", "アルコール", "酒")),
    (re.compile(r"どっち|どちら|どれが|比較|どう違|何が違"), ("イブ", "バファリン", "カロナール", "ロキソニン", "違い", "選", "おすすめ", "湿布", "飲み", "外用", "内服")),
    (re.compile(r"(?:何|なに)が(?:いい|ええ|よい)|市販薬.*(?:いい|ええ|よい)"), ("風邪", "市販", "薬", "おすすめ", "選", "候補", "感冒", "症状")),
    (re.compile(r"一緒|併用|飲み合わせ|それと"), ("併用", "一緒", "飲み合わせ", "重ね", "同時")),
    (re.compile(r"平気|大丈夫"), ("大丈夫", "平気", "避け", "安全", "注意", "控え", "負担", "使いやす")),
    (re.compile(r"胃|胃弱|胃もたれ"), ("胃", "刺激", "負担", "外用", "内服", "注意", "控え", "NSAID")),
    (re.compile(r"副作用|眠く|眠気"), ("副作用", "眠", "だる", "注意")),
    (re.compile(r"犬|ペット|猫|動物"), ("犬", "ペット", "猫", "獣医", "動物", "人間")),
    (re.compile(r"妊娠|つわり|授乳"), ("妊娠", "つわり", "産婦", "受診", "禁忌", "成分")),
    (re.compile(r"膝|関節|筋肉|肩"), ("膝", "関節", "筋", "肩", "痛", "湿布", "NSAID")),
    (re.compile(r"花粉|くしゃみ|鼻炎|アレルギ"), ("花粉", "アレルギ", "鼻炎", "抗")),
    (re.compile(r"日焼け|真っ赤"), ("日焼け", "冷却", "外用", "炎症")),
    (re.compile(r"声|のど|喉|声枯|イガイガ"), ("のど", "喉", "声", "うるさ", "イガ")),
    (re.compile(r"なんか|調子|だる"), ("調子", "症状", "だる", "休息", "受診")),
    (re.compile(r"助けて|たすけて"), ("頭痛", "症状", "市販", "休息", "受診")),
    (re.compile(r"孫|小児|子供|子ども|熱"), ("小児", "子供", "孫", "解熱", "熱", "お子", "年齢", "何歳", "市販")),
    (re.compile(r"登山|高山|吐き気"), ("高山", "受診", "頭痛", "酸素", "脱水")),
    (re.compile(r"インスリン|糖尿病|血糖"), ("インスリン", "糖尿病", "血糖", "糖")),
    (re.compile(r"空港|持ち込|旅行|タイ"), ("持ち込", "旅行", "規制", "注意", "成分")),
    (re.compile(r"便通|便秘"), ("便秘", "便", "下剤", "腸")),
    (re.compile(r"ゲーム|目|バキバキ|疲れ目"), ("目", "疲れ", "眼", "休息")),
    (re.compile(r"夜勤|眠気|寝れ"), ("眠", "睡眠", "休息", "カフェイン")),
    (re.compile(r"コーヒー|動悸|カフェイン"), ("カフェイン", "動悸", "休息", "控え")),
)

CLARIFY_HINTS = (
    "どのお薬",
    "どちらの",
    "教えていただけ",
    "教えていただければ",
    "教えてください",
    "お聞かせ",
    "もう少し詳しく",
    "具体的に",
    "品目",
    "お薬名",
    "お薬の名前",
    "薬の名前",
    "一緒に確認",
    "飲んでいるお薬",
    "飲んでいる薬",
    "市販薬名",
)

GLOBAL_RULE_IDS = (
    "reject_no_reco",
    "comparison_loop",
    "greeting_reset",
    "assistant_echo",
    "raw_kind_leak",
)


@dataclass
class TurnEvalContext:
    """1 ターン分の評価入力。"""

    turn_index: int
    user_message: str
    bot_text: str
    diagnosis_kind: str = ""
    http_status: int = 200
    prior_user_message: str = ""
    prior_bot_text: str = ""
    is_follow_up: bool = False


@dataclass
class TurnEvalResult:
    turn_index: int
    passed: bool
    notes: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)
    rule_ids: list[str] = field(default_factory=list)
    status: str = "pass"  # pass | fail | review


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", "", (text or "").strip())


def text_similarity(a: str, b: str) -> float:
    na, nb = _normalize_text(a), _normalize_text(b)
    if not na or not nb:
        return 0.0
    return SequenceMatcher(None, na, nb).ratio()


def _extract_reference_tokens(text: str, *, min_len: int = 2) -> list[str]:
    """直前発話から参照すべき語を抽出（簡易）。"""
    t = text or ""
    tokens: list[str] = []
    try:
        from src.dialogue.routing.context_signals import extract_drug_entities

        for ent in extract_drug_entities(t):
            if ent and ent not in tokens:
                tokens.append(ent)
    except Exception:
        pass
    for part in re.split(r"[\s、。．！？!?]+", t):
        part = part.strip()
        if len(part) >= min_len and part not in tokens:
            if part in ("あります", "ください", "教えて", "見せて", "写真", "飲んで", "ます"):
                continue
            tokens.append(part)
    return tokens[:8]


def _is_question(text: str) -> bool:
    t = text or ""
    return any(m in t for m in QUESTION_MARKERS)


def _is_clarify_response(text: str) -> bool:
    return any(h in (text or "") for h in CLARIFY_HINTS)


def apply_global_rules(ctx: TurnEvalContext) -> tuple[list[str], list[str], list[str]]:
    """全ターンに適用する拒否テンプレ・ループ等。returns (notes, failures, rule_ids)."""
    notes: list[str] = []
    failures: list[str] = []
    rule_ids: list[str] = []
    text = ctx.bot_text or ""

    if REJECT_NO_RECO in text or REJECT_NO_RECO_ALT in text:
        failures.append("reject_no_reco")
        rule_ids.append("reject_no_reco")

    if ctx.prior_bot_text and text_similarity(text, ctx.prior_bot_text) >= 0.85:
        failures.append("comparison_loop")
        rule_ids.append("comparison_loop")

    if ctx.is_follow_up and GREETING_ONLY_RE.match(text.strip()):
        failures.append("greeting_reset")
        rule_ids.append("greeting_reset")

    if ctx.user_message.strip() in ASSISTANT_ECHO_PATTERNS or any(
        ctx.user_message.strip() == p for p in ASSISTANT_ECHO_PATTERNS
    ):
        failures.append("assistant_echo")
        rule_ids.append("assistant_echo")

    if text.strip() in ("sage_reco", "sage_status", "sage_qa") or text.strip().startswith('{"'):
        failures.append("raw_kind_leak")
        rule_ids.append("raw_kind_leak")

    if not failures:
        notes.append("global_rules_ok")
    return notes, failures, rule_ids


def _check_must_reference_prior(
    ctx: TurnEvalContext,
    expect: dict[str, Any],
) -> tuple[list[str], list[str]]:
    notes: list[str] = []
    failures: list[str] = []
    spec = expect.get("must_reference_prior")
    if not spec:
        return notes, failures

    bot = (ctx.bot_text or "").lower()
    keywords: list[str] = []
    if spec is True:
        keywords = _extract_reference_tokens(ctx.prior_user_message or ctx.user_message)
        if ctx.prior_bot_text:
            keywords.extend(_extract_reference_tokens(ctx.prior_bot_text)[:3])
            for frag in re.findall(r"[ァ-ヶーA-Za-z0-9]{4,}", ctx.prior_bot_text):
                if frag not in keywords:
                    keywords.append(frag)
        keywords = list(dict.fromkeys(keywords))
    elif isinstance(spec, list):
        keywords = [str(k) for k in spec]
    else:
        keywords = _extract_reference_tokens(str(spec))

    if not keywords:
        notes.append("must_reference_prior:skip_no_tokens")
        return notes, failures

    if any(kw.lower() in bot for kw in keywords if kw):
        notes.append("must_reference_prior:ok")
    else:
        matched_partial = False
        for kw in keywords:
            if not kw:
                continue
            for part in re.split(r"[や、,/]", kw):
                part = part.strip()
                if len(part) >= 3 and part.lower() in bot:
                    matched_partial = True
                    break
            if matched_partial:
                break
            # 前ターンの品目名（カタカナ連続）が bot に引き継がれているか
            for frag in re.findall(r"[ァ-ヶー]{4,}", kw):
                if frag.lower() in bot:
                    matched_partial = True
                    break
            if matched_partial:
                break
        if matched_partial:
            notes.append("must_reference_prior:partial_ok")
        elif _user_has_anaphora(ctx.user_message or "") and ctx.prior_bot_text:
            prior = ctx.prior_bot_text
            bot_raw = ctx.bot_text or ""
            modality_prior = any(w in prior for w in ("外用", "塗", "湿布", "貼", "ゲル", "スプレー"))
            modality_bot = any(w in bot_raw for w in ("外用", "塗", "湿布", "貼", "ゲル", "胃"))
            topic_prior = any(w in prior for w in ("肩", "頭", "風邪", "痛", "こり", "熱"))
            topic_bot = any(w in bot_raw for w in ("肩", "頭", "風邪", "痛", "こり", "熱", "胃"))
            if modality_prior and modality_bot and topic_prior and topic_bot:
                notes.append("must_reference_prior:anaphora_modality_ok")
            else:
                failures.append(f"must_reference_prior:{keywords[:5]}")
        else:
            failures.append(f"must_reference_prior:{keywords[:5]}")
    return notes, failures


def _question_topic_tokens(user_message: str) -> list[str]:
    tokens: list[str] = []
    for pattern, syns in _QUESTION_TOPIC_SYNS:
        if pattern.search(user_message or ""):
            for s in syns:
                if s not in tokens:
                    tokens.append(s)
    for t in _extract_reference_tokens(user_message, min_len=2):
        if t not in tokens:
            tokens.append(t)
    return tokens[:10]


def _check_must_answer_question(ctx: TurnEvalContext) -> tuple[list[str], list[str]]:
    notes: list[str] = []
    failures: list[str] = []
    if not _is_question(ctx.user_message):
        return notes, failures

    text = ctx.bot_text or ""
    if len(text.strip()) < 15:
        failures.append("must_answer_question:too_short")
        return notes, failures

    if GREETING_ONLY_RE.match(text.strip()):
        failures.append("must_answer_question:greeting_only")
        return notes, failures

    topics = _question_topic_tokens(ctx.user_message)
    if topics and any(t.lower() in text.lower() for t in topics):
        notes.append("must_answer_question:ok")
        return notes, failures

    # 比較質問: 複数品目名が answer にあれば OK
    if re.search(r"どっち|どちら|どれ", ctx.user_message or ""):
        names = sum(1 for n in ("イブ", "バファリン", "カロナール", "ロキソニン") if n in text)
        if names >= 2:
            notes.append("must_answer_question:comparison_ok")
            return notes, failures

    failures.append("must_answer_question:no_user_topic")
    return notes, failures


def _check_no_clarify_when_ambiguous(
    ctx: TurnEvalContext,
    expect: dict[str, Any],
) -> tuple[list[str], list[str]]:
    """expect.expects_clarify=True のターンで Clarify が無い場合に FAIL。"""
    notes: list[str] = []
    failures: list[str] = []
    if not expect.get("expects_clarify"):
        return notes, failures
    if _is_clarify_response(ctx.bot_text):
        notes.append("expects_clarify:ok")
    elif REJECT_NO_RECO in (ctx.bot_text or "") or REJECT_NO_RECO_ALT in (ctx.bot_text or ""):
        failures.append("no_clarify_when_ambiguous:reject_template")
    else:
        failures.append("no_clarify_when_ambiguous:missing_clarify")
    return notes, failures


def evaluate_turn_expect(
    ctx: TurnEvalContext,
    expect: dict[str, Any],
    *,
    kind_route_fn: Optional[Callable[[str, str], str]] = None,
    greeting_only_re: re.Pattern[str] = GREETING_ONLY_RE,
) -> TurnEvalResult:
    """単一ターンの expect + グローバルルールを評価。"""
    notes: list[str] = []
    failures: list[str] = []
    rule_ids: list[str] = []

    g_notes, g_fail, g_rules = apply_global_rules(ctx)
    notes.extend(g_notes)
    failures.extend(g_fail)
    rule_ids.extend(g_rules)

    if ctx.http_status != 200:
        failures.append(f"http_{ctx.http_status}")

    text = ctx.bot_text or ""

    if expect.get("must_have_response", True):
        if len(text.strip()) < 5:
            failures.append("response_missing_or_too_short")
        else:
            notes.append("has_response")

    route = (kind_route_fn or (lambda k, c: "unknown"))(ctx.diagnosis_kind, text)
    exp_route = expect.get("primary_route")
    if exp_route and route != exp_route and route != "other":
        if exp_route == "Physical" and route in ("Counseling", "Concierge"):
            failures.append(f"route_mismatch expected={exp_route} got={route}")
        elif exp_route != "Counseling":
            failures.append(f"route_mismatch expected={exp_route} got={route}")
        else:
            notes.append(f"route_soft_match {route}")

    exp_kind = expect.get("diagnosis_kind")
    if exp_kind and (ctx.diagnosis_kind or "") != exp_kind:
        failures.append(f"kind_mismatch expected={exp_kind} got={ctx.diagnosis_kind}")

    for bad in expect.get("must_not") or []:
        if bad == "greeting_only" and greeting_only_re.match(text.strip()):
            failures.append("greeting_only")
        elif bad == "response_missing" and len(text.strip()) < 5:
            failures.append("response_missing")

    for kw in expect.get("context_keywords") or []:
        if str(kw).lower() in text.lower():
            notes.append(f"context_kw:{kw}")
        else:
            failures.append(f"missing_context_kw:{kw}")

    for bad in expect.get("must_not_contain") or []:
        if str(bad) in text:
            failures.append(f"must_not_contain:{bad}")

    if expect.get("must_answer") is True:
        if REJECT_NO_RECO in text or REJECT_NO_RECO_ALT in text:
            failures.append("must_answer:reject_template")

    if expect.get("must_not_repeat_prior_bot") and ctx.prior_bot_text:
        if text_similarity(text, ctx.prior_bot_text) >= 0.85:
            failures.append("must_not_repeat_prior_bot")

    n_notes, n_fail = _check_must_reference_prior(ctx, expect)
    notes.extend(n_notes)
    failures.extend(n_fail)

    if expect.get("must_answer_question") is True:
        q_notes, q_fail = _check_must_answer_question(ctx)
        notes.extend(q_notes)
        failures.extend(q_fail)

    c_notes, c_fail = _check_no_clarify_when_ambiguous(ctx, expect)
    notes.extend(c_notes)
    failures.extend(c_fail)

    status = "fail" if failures else "pass"
    return TurnEvalResult(
        turn_index=ctx.turn_index,
        passed=not failures,
        notes=notes,
        failures=failures,
        rule_ids=rule_ids,
        status=status,
    )


def build_turn_expect_map(spec: dict[str, Any]) -> dict[int, dict[str, Any]]:
    """turn_expects + 最終 expect を turn_index → expect にマップ。旧 expect は最終ターンのみ。"""
    setup = list(spec.get("setup") or [])
    raw_input = spec.get("input")
    has_input = raw_input is not None and str(raw_input).strip()
    total_turns = len(setup) + (1 if has_input else 0)
    if total_turns == 0:
        return {}

    out: dict[int, dict[str, Any]] = {}
    for entry in spec.get("turn_expects") or []:
        if not isinstance(entry, dict):
            continue
        idx = entry.get("turn")
        if idx is None:
            continue
        exp = dict(entry.get("expect") or {})
        out[int(idx)] = exp

    final_expect = dict(spec.get("expect") or {})
    last_idx = total_turns - 1
    if last_idx not in out and final_expect:
        out[last_idx] = final_expect
    elif last_idx in out and final_expect:
        merged = {**final_expect, **out[last_idx]}
        out[last_idx] = merged

    return out


def build_turn_contexts(
    turns: list[Any],
    *,
    user_attr: str = "user_message",
    bot_attr: str = "response_full",
    kind_attr: str = "diagnosis_kind",
    status_attr: str = "http_status",
    snippet_attr: str = "response_snippet",
) -> list[TurnEvalContext]:
    """TurnResult 相当のリストから TurnEvalContext を構築。"""
    contexts: list[TurnEvalContext] = []
    prior_user = ""
    prior_bot = ""
    for i, turn in enumerate(turns):
        if isinstance(turn, dict):
            user = str(turn.get(user_attr) or "")
            bot = str(turn.get(bot_attr) or turn.get(snippet_attr) or "")
            kind = str(turn.get(kind_attr) or "")
            status = int(turn.get(status_attr) or 0)
        else:
            user = str(getattr(turn, user_attr, ""))
            bot = str(getattr(turn, bot_attr, "") or getattr(turn, snippet_attr, ""))
            kind = str(getattr(turn, kind_attr, "") or "")
            status = int(getattr(turn, status_attr, 0))

        contexts.append(
            TurnEvalContext(
                turn_index=i,
                user_message=user,
                bot_text=bot,
                diagnosis_kind=kind,
                http_status=status,
                prior_user_message=prior_user,
                prior_bot_text=prior_bot,
                is_follow_up=i > 0,
            )
        )
        prior_user = user
        prior_bot = bot
    return contexts


def evaluate_scenario_all_turns(
    spec: dict[str, Any],
    turns: list[Any],
    *,
    kind_route_fn: Optional[Callable[[str, str], str]] = None,
    evaluate_all_turns: bool = False,
) -> tuple[bool, list[str], list[str], list[TurnEvalResult]]:
    """
    シナリオ全体を評価。

    evaluate_all_turns=False かつ turn_expects 無し: 最終ターンのみ（後方互換）。
    """
    if not turns:
        return False, [], ["no_turns"], []

    expect_map = build_turn_expect_map(spec)
    contexts = build_turn_contexts(turns)
    turn_results: list[TurnEvalResult] = []
    all_notes: list[str] = []
    all_failures: list[str] = []

    indices_to_eval: list[int]
    if expect_map:
        indices_to_eval = sorted(expect_map.keys())
    elif evaluate_all_turns:
        indices_to_eval = list(range(len(contexts)))
    else:
        indices_to_eval = [len(contexts) - 1]
        if not expect_map and spec.get("expect"):
            expect_map = {len(contexts) - 1: dict(spec.get("expect") or {})}

    for idx in indices_to_eval:
        if idx >= len(contexts):
            all_failures.append(f"turn_index_out_of_range:{idx}")
            continue
        ctx = contexts[idx]
        expect = expect_map.get(idx, {})
        if not expect and evaluate_all_turns:
            expect = {"must_have_response": True}
        result = evaluate_turn_expect(ctx, expect, kind_route_fn=kind_route_fn)
        turn_results.append(result)
        all_notes.extend([f"t{idx}:{n}" for n in result.notes])
        all_failures.extend([f"t{idx}:{f}" for f in result.failures])

    if spec.get("expect", {}).get("min_turns"):
        min_t = int(spec["expect"]["min_turns"])
        if len(turns) < min_t:
            all_failures.append("min_turns_not_met")

    ok = len(all_failures) == 0
    return ok, all_notes, all_failures, turn_results
