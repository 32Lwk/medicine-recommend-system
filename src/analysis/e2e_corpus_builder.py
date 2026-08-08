"""
ログ由来 E2E コーパス構築 — セッションリプレイ・クラスタ dedupe・比率調整・不足自動生成。

PR 用 500 分岐: ログ自動抽出（主）+ テンプレ自動生成（不足 bucket 補完）。
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Sequence

from src.analysis.log_secret_redaction import redact_text
from src.analysis.session_conversation_analysis import (
    classify_user_input,
    extract_pairs_from_conversation_history,
)

# PR 500 の intent bucket 配分（合計 500）
DEFAULT_BUCKET_QUOTAS: dict[str, int] = {
    "medicine_thread": 125,
    "side_effect_qa": 75,
    "comparison": 50,
    "physical_symptom": 75,
    "store": 50,
    "concierge_meta": 50,
    "greeting_short": 25,
    "general": 50,
}

_MEDICINE_BRAND_RE = re.compile(
    r"ロキソニン|バファリン|カロナール|タイレノール|イブ|セデス|パブロン|ルル|アセトアミノフェン|イブプロフェン",
    re.I,
)
_COMPARE_RE = re.compile(r"どっち|どれ|比較|違い|vs|結局|1番|2番|3つ", re.I)
_FOLLOWUP_RE = re.compile(
    r"家に|うちに|さっき|それ|この薬|平気|大丈夫|一緒|併用|飲み合わせ|説明書|Sは|プレミアム",
    re.I,
)
_SESSION_OPS_RE = re.compile(
    r"削除|消して|履歴|記録|要約|ステータス|status|summarize|delete|この会話",
    re.I,
)
_GPT_SIM_PROMPT_RE = re.compile(
    r"症状(?:を|が)?(?:教えて|詳しく)|もう少し詳しく教えてください|具体的に教え",
    re.I,
)
_CHITCHAT_RE = re.compile(
    r"疲れ|眠れ|ストレス|最近|市販薬に頼|相談したい|話を聞",
    re.I,
)

_PII_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\b\d{2,4}[-‐]?\d{2,4}[-‐]?\d{3,4}\b"), "[PHONE]"),
    (re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"), "[EMAIL]"),
    (re.compile(r"〒?\d{3}-?\d{4}"), "[POSTAL]"),
)

_V2_TEST_SESSION_RE = re.compile(r"v2-test-|local-v2-chat-test", re.I)
_ASSISTANT_MARKERS = re.compile(r"アシスタント\s*:|assistant\s*:", re.I)
_USER_PREFIX = re.compile(r"^ユーザー\s*:\s*")


def _strip_gpt_sim_prefix(text: str) -> str:
    out = _USER_PREFIX.sub("", (text or "").strip())
    if _ASSISTANT_MARKERS.search(out):
        out = _ASSISTANT_MARKERS.split(out, maxsplit=1)[0].strip()
    return out


def _looks_like_assistant_turn(text: str) -> bool:
    t = (text or "").strip()
    if not t or _ASSISTANT_MARKERS.search(t):
        return True
    if len(t) > 320:
        return True
    assistant_phrases = (
        "心配ですね",
        "お気軽に",
        "お尋ねください",
        "お待ちしています",
        "ご注意ください",
        "教えてくださいね",
        "お手伝いできます",
    )
    if any(p in t for p in assistant_phrases):
        return True
    if t.count("。") >= 2 and len(t) > 70:
        return True
    polite_tail = ("くださいね", "どうぞ")
    if len(t) > 90 and any(p in t for p in polite_tail):
        return True
    return False


def _normalize_user_turn(text: str) -> str:
    cleaned = _strip_gpt_sim_prefix(text)
    return sanitize_user_text(cleaned)


def is_valid_user_turn(text: str) -> bool:
    normalized = _normalize_user_turn(text)
    if len(normalized) < 2 or len(normalized) > 280:
        return False
    return not _looks_like_assistant_turn(normalized)


def sanitize_user_text(text: str) -> str:
    """fixture 用ユーザー発話の PII / シークレットマスク。"""
    out = redact_text((text or "").strip())
    for pattern, repl in _PII_PATTERNS:
        out = pattern.sub(repl, out)
    return re.sub(r"\s+", " ", out).strip()


def _normalize_for_signature(text: str) -> str:
    t = sanitize_user_text(text).lower()
    t = re.sub(r"[。!！?？\s]+", "", t)
    return t[:80]


def infer_e2e_bucket(user_input: str, *, setup: Sequence[str] | None = None) -> str:
    """PR コーパス用 intent bucket（ログ1ターン + setup 文脈）。"""
    text = (user_input or "").strip()
    blob = " ".join(list(setup or []) + [text])
    labels = classify_user_input(text)

    if _SESSION_OPS_RE.search(text) and not _MEDICINE_BRAND_RE.search(blob):
        return "session_ops"
    if _GPT_SIM_PROMPT_RE.search(text):
        return "gpt_sim_assistant"
    if _CHITCHAT_RE.search(text) and not _MEDICINE_BRAND_RE.search(blob) and not _FOLLOWUP_RE.search(text):
        return "concierge_chitchat"

    if _COMPARE_RE.search(blob):
        return "comparison"
    if "side_effect_qa" in labels or re.search(r"副作用|眠く|眠気|平気|併用|飲み合わせ", blob):
        if _MEDICINE_BRAND_RE.search(blob) or _FOLLOWUP_RE.search(blob):
            return "medicine_thread" if _FOLLOWUP_RE.search(text) and not _COMPARE_RE.search(text) else "side_effect_qa"
        return "side_effect_qa"
    if _MEDICINE_BRAND_RE.search(blob) or _FOLLOWUP_RE.search(blob):
        return "medicine_thread"
    if "physical_symptom" in labels:
        return "physical_symptom"
    if _STORE_RE.search(blob) or "off_topic_store" in labels:
        return "store"
    if "about_or_capabilities" in labels or "meta_follow_up" in labels:
        return "concierge_meta"
    if "greeting" in labels or "short_or_emoji" in labels:
        return "greeting_short"
    return "general"


def scenario_signature(bucket: str, setup: Sequence[str], user_input: str) -> str:
    parts = [_normalize_for_signature(p) for p in list(setup) + [user_input]]
    raw = bucket + "|" + "|".join(p for p in parts if p)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


@dataclass
class ReplayScenario:
    scenario_id: str
    bucket: str
    setup: list[str]
    input: str
    source: str
    session_id: str = ""
    turn_index: int = 0
    signature: str = ""
    generated: bool = False

    def to_yaml_dict(self) -> dict[str, Any]:
        expect: dict[str, Any] = {"must_have_response": True}
        if self.bucket == "medicine_thread":
            expect["min_turns"] = len(self.setup) + 1
            expect.setdefault("must_not", [])
            if "greeting_only" not in expect["must_not"]:
                expect["must_not"].append("greeting_only")
        elif self.bucket == "comparison":
            expect["min_turns"] = max(2, len(self.setup) + 1)
        elif self.bucket == "store":
            expect["primary_route"] = "Store"
        elif self.bucket in ("concierge_meta", "concierge_chitchat"):
            expect["primary_route"] = "Concierge"
        elif self.bucket == "session_ops":
            expect["primary_route"] = "SessionOps"
            expect.setdefault("must_not_contain", [])
            if "推奨医薬品の情報では回答できません" not in expect["must_not_contain"]:
                expect["must_not_contain"].append("推奨医薬品の情報では回答できません")
        elif self.bucket == "physical_symptom" and not self.setup:
            expect["primary_route"] = "Physical"

        out: dict[str, Any] = {
            "id": self.scenario_id,
            "category": self.bucket,
            "wave": "log-corpus" if not self.generated else "generated-fill",
            "input": self.input,
            "description": f"{'generated' if self.generated else self.source} turn {self.turn_index}",
            "expect": expect,
        }
        turn_expects = _infer_rule_turn_expects(self.bucket, self.setup, self.input)
        if turn_expects:
            out["turn_expects"] = turn_expects
        if self.setup:
            out["setup"] = list(self.setup)
        if self.session_id:
            out["meta"] = {
                "session_id": self.session_id,
                "signature": self.signature,
                "source": self.source,
            }
        return out


def _load_counseling_jsonl(path: Path) -> dict[str, list[dict[str, Any]]]:
    by_session: dict[str, list[dict[str, Any]]] = defaultdict(list)
    if not path.is_file():
        return by_session
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if str(row.get("log_type") or "") not in ("", "counseling_detail"):
            if row.get("log_type") and row.get("log_type") != "counseling_detail":
                continue
        sid = str(row.get("session_id") or "").strip()
        if not sid or _V2_TEST_SESSION_RE.search(sid):
            continue

        seen_in_row: set[str] = set()
        pairs = extract_pairs_from_conversation_history(row.get("conversation_history"))
        if pairs:
            for pair in pairs:
                ui = _normalize_user_turn(str(pair.get("user_input") or ""))
                if not is_valid_user_turn(ui) or ui in seen_in_row:
                    continue
                seen_in_row.add(ui)
                by_session[sid].append({"session_id": sid, "user_input": ui, "timestamp": row.get("timestamp")})
            continue

        ui = _normalize_user_turn(str(row.get("user_input") or ""))
        if is_valid_user_turn(ui) and ui not in seen_in_row:
            by_session[sid].append({"session_id": sid, "user_input": ui, "timestamp": row.get("timestamp")})
    return by_session


def _load_gcp_analysis_sessions(analysis_dirs: Iterable[Path]) -> dict[str, list[dict[str, Any]]]:
    """log/analysis/<stem>/ 内 user_sessions / session_conversations から取込。"""
    out: dict[str, list[dict[str, Any]]] = defaultdict(list)

    def _ingest_sessions(sessions: Sequence[dict[str, Any]], *, label: str) -> None:
        for sess in sessions:
            sid = str(sess.get("session_id") or "").strip()
            if not sid or _V2_TEST_SESSION_RE.search(sid):
                continue
            for turn in sess.get("turns") or []:
                ui = _normalize_user_turn(str(turn.get("user_input") or ""))
                if ui and is_valid_user_turn(ui):
                    out[sid].append({"session_id": sid, "user_input": ui, "source": label})

    def _ingest_counseling_rows(rows: Sequence[dict[str, Any]], *, label: str) -> None:
        by_sid: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            sid = str(row.get("session_id") or "").strip()
            if not sid or _V2_TEST_SESSION_RE.search(sid):
                continue
            pairs = extract_pairs_from_conversation_history(row.get("conversation_history"))
            if pairs:
                for pair in pairs:
                    ui = _normalize_user_turn(str(pair.get("user_input") or ""))
                    if is_valid_user_turn(ui):
                        by_sid[sid].append({"session_id": sid, "user_input": ui, "source": label})
                continue
            ui = _normalize_user_turn(str(row.get("user_input") or ""))
            if is_valid_user_turn(ui):
                by_sid[sid].append({"session_id": sid, "user_input": ui, "source": label})
        for sid, items in by_sid.items():
            out[sid].extend(items)

    for base in analysis_dirs:
        candidates = [
            base / "session_conversations.json",
            base / "user_sessions.json",
            base / "sections" / "user_sessions.json",
        ]
        loaded = False
        for path in candidates:
            if not path.is_file():
                continue
            try:
                blob = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            if path.name == "user_sessions.json":
                counseling = blob.get("counseling_details") or []
                if counseling:
                    _ingest_counseling_rows(counseling, label="gcp_counseling_detail")
                    loaded = True
                sessions = (
                    (blob.get("session_conversations") or {}).get("sessions")
                    or blob.get("sessions")
                    or []
                )
                if sessions:
                    _ingest_sessions(sessions, label="gcp_user_sessions")
                    loaded = True
            else:
                sessions = blob.get("sessions") or []
                if sessions:
                    _ingest_sessions(sessions, label="gcp_session_conversations")
                    loaded = True
        if not loaded:
            chat_flow = base / "sections" / "chat_flow.json"
            if chat_flow.is_file():
                try:
                    cf = json.loads(chat_flow.read_text(encoding="utf-8"))
                    for trace in cf.get("exported_traces") or []:
                        sid = str(trace.get("session_id") or "").strip()
                        ui = _normalize_user_turn(str(trace.get("user_message") or ""))
                        if sid and ui and is_valid_user_turn(ui):
                            out[sid].append(
                                {"session_id": sid, "user_input": ui, "source": "gcp_chat_flow"}
                            )
                except json.JSONDecodeError:
                    pass
    return out


def _dedupe_preserve_order(items: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def _narrative_score(setup: Sequence[str], user_input: str) -> float:
    """setup→input の時系列自然さ（低いほど棄却候補）。"""
    parts = list(setup) + [user_input]
    score = 1.0
    for i, part in enumerate(parts):
        if _SESSION_OPS_RE.search(part) and i < len(parts) - 1:
            if _MEDICINE_BRAND_RE.search(parts[-1]) or _FOLLOWUP_RE.search(parts[-1]):
                score -= 0.4
        if _GPT_SIM_PROMPT_RE.search(part):
            score -= 0.5
    if len(setup) >= 2 and setup[-1] == setup[-2]:
        score -= 0.3
    return max(0.0, score)


def _infer_rule_turn_expects(bucket: str, setup: Sequence[str], user_input: str) -> list[dict[str, Any]]:
    """ルールベース turn_expects 草案（golden enrich とも共有）。"""
    total = len(setup) + (1 if user_input.strip() else 0)
    if total == 0:
        return []
    expects: list[dict[str, Any]] = []
    brands = _MEDICINE_BRAND_RE.findall(" ".join(list(setup) + [user_input]))
    last_idx = total - 1

    if bucket in ("medicine_thread", "comparison", "side_effect_qa") and brands:
        for idx in range(total):
            exp: dict[str, Any] = {"must_have_response": True}
            if idx > 0:
                exp["must_not"] = ["greeting_only"]
                exp["must_reference_prior"] = True
            if idx == last_idx:
                exp["must_not_repeat_prior_bot"] = True
                if "？" in user_input or "?" in user_input or _COMPARE_RE.search(user_input):
                    exp["must_answer_question"] = True
            exp["context_keywords"] = list(dict.fromkeys(brands))[:2]
            expects.append({"turn": idx, "expect": exp})
    elif bucket == "session_ops":
        expects.append(
            {
                "turn": last_idx,
                "expect": {
                    "primary_route": "SessionOps",
                    "must_have_response": True,
                    "must_not_contain": ["推奨医薬品の情報では回答できません"],
                },
            }
        )
    elif bucket == "concierge_chitchat":
        expects.append(
            {
                "turn": last_idx,
                "expect": {
                    "primary_route": "Concierge",
                    "must_have_response": True,
                    "must_not_contain": ["推奨医薬品の情報では回答できません"],
                },
            }
        )
    elif bucket == "concierge_meta":
        expects.append(
            {
                "turn": last_idx,
                "expect": {"primary_route": "Concierge", "must_have_response": True},
            }
        )
    return expects


def extract_replay_scenarios_from_sessions(
    sessions: dict[str, list[dict[str, Any]]],
    *,
    source_label: str,
    min_turns: int = 2,
    max_turns: int = 8,
) -> list[ReplayScenario]:
    """セッションをスライディングウィンドウで setup+input シナリオ化。"""
    scenarios: list[ReplayScenario] = []
    for sid, rows in sessions.items():
        inputs: list[str] = []
        for row in rows:
            ui = _normalize_user_turn(str(row.get("user_input") or ""))
            if ui and is_valid_user_turn(ui) and (not inputs or inputs[-1] != ui):
                inputs.append(ui)
        if len(inputs) < min_turns:
            continue
        if len(inputs) > max_turns:
            inputs = inputs[-max_turns:]
        inputs = _dedupe_preserve_order(inputs)
        if len(inputs) < min_turns:
            continue
        for idx in range(1, len(inputs)):
            setup = inputs[:idx]
            user_input = inputs[idx]
            if _narrative_score(setup, user_input) < 0.45:
                continue
            bucket = infer_e2e_bucket(user_input, setup=setup)
            if bucket in ("gpt_sim_assistant",):
                continue
            sig = scenario_signature(bucket, setup, user_input)
            scenarios.append(
                ReplayScenario(
                    scenario_id=f"log-{sid[-8:]}-t{idx}",
                    bucket=bucket,
                    setup=setup,
                    input=user_input,
                    source=source_label,
                    session_id=sid,
                    turn_index=idx + 1,
                    signature=sig,
                )
            )
    return scenarios


def cluster_dedupe_scenarios(
    scenarios: Sequence[ReplayScenario],
) -> list[ReplayScenario]:
    """signature 単位で代表1件に圧縮。"""
    best: dict[str, ReplayScenario] = {}
    for sc in scenarios:
        key = sc.signature or scenario_signature(sc.bucket, sc.setup, sc.input)
        sc.signature = key
        prev = best.get(key)
        if prev is None or len(sc.setup) > len(prev.setup):
            best[key] = sc
    return list(best.values())


def _generated_templates() -> dict[str, list[tuple[list[str], str]]]:
    """不足 bucket 用 — v2_context_intent_expanded 由来の非理想パターン。"""
    return {
        "medicine_thread": [
            ([], "ロキソニンの写真見せて"),
            (["ロキソニンの写真見せて"], "うちにもあるわ"),
            (["ロキソニンについて教えて"], "Sついてないかも"),
            (["頭が痛い"], "どっちがいい？"),
            (["今ロキソニン飲んでます"], "お酒飲んでも平気？"),
        ],
        "comparison": [
            (["頭痛がひどい"], "イブとカロナール比較して"),
            (["ロキソニンとイブの違いは？"], "胃弱いならどっち"),
        ],
        "side_effect_qa": [
            ([], "ロキソニン 副作用"),
            (["ロキソニンSについて"], "マジ眠くなる？"),
        ],
        "physical_symptom": [
            ([], "頭痛い"),
            ([], "のど痛い"),
            ([], "熱っぽい"),
        ],
        "store": [
            (["頭痛い"], "近くの薬局どこ？"),
        ],
        "concierge_meta": [
            (["ロキソニンの副作用教えて"], "技術スタックは？"),
        ],
        "greeting_short": [
            ([], "こんにちは"),
            ([], "おはよう"),
            ([], "はじめまして"),
        ],
        "general": [
            ([], "市販薬について教えて"),
        ],
    }


def generate_fill_scenarios(
    bucket: str,
    count: int,
    *,
    existing_signatures: set[str],
    id_prefix: str = "gen",
) -> list[ReplayScenario]:
    templates = _generated_templates().get(bucket) or []
    if not templates:
        return []
    out: list[ReplayScenario] = []
    ti = 0
    while len(out) < count and ti < count * 5:
        setup, user_input = templates[ti % len(templates)]
        if ti >= len(templates):
            user_input = f"{user_input}（例{ti // len(templates) + 1}）"
        sig = scenario_signature(bucket, setup, user_input)
        ti += 1
        if sig in existing_signatures:
            continue
        existing_signatures.add(sig)
        out.append(
            ReplayScenario(
                scenario_id=f"{id_prefix}-{bucket}-{len(out)+1:03d}",
                bucket=bucket,
                setup=list(setup),
                input=user_input,
                source="auto_generated",
                turn_index=len(setup) + 1,
                signature=sig,
                generated=True,
            )
        )
    return out


def balance_corpus(
    scenarios: Sequence[ReplayScenario],
    *,
    quotas: dict[str, int] | None = None,
    total: int = 500,
) -> tuple[list[ReplayScenario], dict[str, Any]]:
    """bucket 配额に従い選定し、不足分を自動生成。"""
    quotas = dict(quotas or DEFAULT_BUCKET_QUOTAS)
    if sum(quotas.values()) != total:
        scale = total / max(sum(quotas.values()), 1)
        quotas = {k: max(1, int(v * scale)) for k, v in quotas.items()}
        delta = total - sum(quotas.values())
        if delta:
            quotas["medicine_thread"] = quotas.get("medicine_thread", 0) + delta

    by_bucket: dict[str, list[ReplayScenario]] = defaultdict(list)
    for sc in scenarios:
        by_bucket[sc.bucket].append(sc)

    for bucket in by_bucket:
        by_bucket[bucket].sort(key=lambda s: (-len(s.setup), s.session_id))

    selected: list[ReplayScenario] = []
    existing_sigs: set[str] = set()
    stats: dict[str, Any] = {"from_logs": {}, "generated": {}, "target": quotas}

    for bucket, target in quotas.items():
        pool = by_bucket.get(bucket) or []
        picked = 0
        for sc in pool:
            if picked >= target:
                break
            if sc.signature in existing_sigs:
                continue
            existing_sigs.add(sc.signature)
            selected.append(sc)
            picked += 1
        stats["from_logs"][bucket] = picked
        if picked < target:
            fill = generate_fill_scenarios(
                bucket,
                target - picked,
                existing_signatures=existing_sigs,
            )
            selected.extend(fill)
            stats["generated"][bucket] = len(fill)

    for i, sc in enumerate(selected):
        sc.scenario_id = f"corpus-{sc.bucket[:8]}-{i+1:04d}"

    stats["total_selected"] = len(selected)
    stats["bucket_counts"] = dict(Counter(s.bucket for s in selected))
    return selected, stats


def build_corpus_from_log_sources(
    *,
    counseling_path: Path,
    analysis_dirs: Sequence[Path] | None = None,
    total: int = 500,
    quotas: dict[str, int] | None = None,
) -> tuple[list[ReplayScenario], dict[str, Any]]:
    sessions = _load_counseling_jsonl(counseling_path)
    log_scenarios = extract_replay_scenarios_from_sessions(
        sessions, source_label="counseling_detail"
    )

    if analysis_dirs:
        gcp_sessions = _load_gcp_analysis_sessions(analysis_dirs)
        log_scenarios.extend(
            extract_replay_scenarios_from_sessions(
                gcp_sessions, source_label="gcp_aws_analysis"
            )
        )

    deduped = cluster_dedupe_scenarios(log_scenarios)
    selected, stats = balance_corpus(deduped, quotas=quotas, total=total)
    stats["raw_scenarios"] = len(log_scenarios)
    stats["deduped_scenarios"] = len(deduped)
    stats["counseling_sessions"] = len(sessions)
    return selected, stats


def write_corpus_yaml(
    scenarios: Sequence[ReplayScenario],
    path: Path,
    *,
    source: str = "log-auto-extract",
) -> None:
    payload = {
        "version": 1,
        "source": source,
        "count": len(scenarios),
        "scenarios": [s.to_yaml_dict() for s in scenarios],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        import yaml

        path.write_text(
            yaml.safe_dump(payload, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
    except ImportError:
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
