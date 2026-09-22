"""Content-only policy adapters (no session/DB/routing/Jev side effects)."""
from __future__ import annotations

from typing import Any, Optional

from src.dialogue.routing.policy_types import AdapterResult, MutationPlan, PolicyDecision
from src.dialogue.routing.turn_signal_snapshot import TurnSignalSnapshot

# Fixed OTC boundary copy — not LLM; not a prescription judgment.
_PRESCRIPTION_BOUNDARY = (
    "申し訳ありません。当サービスでは医師の処方箋が必要な医薬品の処方や"
    "処方の代行はできません。必要に応じて医療機関を受診してください。"
    "市販薬（OTC）についてのご相談であれば、具体的な症状やお困りごとをお書きください。"
)


def adapt_prescription(
    decision: PolicyDecision,
    snapshot: TurnSignalSnapshot,
    *,
    user_text: str,
) -> AdapterResult:
    del snapshot  # fingerprint-only consumers use decision/observability
    content = _PRESCRIPTION_BOUNDARY
    plan = MutationPlan(
        append_user=True,
        user_text=user_text,
        append_bot=True,
        bot_legacy_content=content,
        bot_kind="policy_prescription_boundary",
        bot_variant="notice",
        bot_title="処方について",
        record_inappropriate=True,
        inappropriate_type="prescription",
        inappropriate_blocked=False,
        start_counseling=False,
    )
    return AdapterResult(
        content=content,
        mutation_plan=plan,
        observability={
            "adapter": "prescription",
            "detector_source": decision.detector_source,
            "llm_used": False,
        },
    )


_AMBIGUOUS_SLEEP_BOUNDARY = (
    "睡眠薬のご相談ですね。当サービスでは処方薬の入手や処方の代行はできません。"
    "市販の睡眠改善薬に関する一般的な情報であればお手伝いできます。"
    "不眠の症状、年齢、いまお使いの薬、医師から処方されている薬があれば、"
    "その内容をお書きください。"
)


def adapt_ambiguous_controlled(
    decision: PolicyDecision,
    snapshot: TurnSignalSnapshot,
    *,
    user_text: str,
) -> AdapterResult:
    """Neutral clarification — never illegal/criminal template."""
    del decision
    content = _AMBIGUOUS_SLEEP_BOUNDARY
    plan = MutationPlan(
        append_user=True,
        user_text=user_text,
        append_bot=True,
        bot_legacy_content=content,
        bot_kind="policy_ambiguous_controlled_clarify",
        bot_variant="notice",
        bot_title="睡眠薬についてのご案内",
        record_inappropriate=True,
        inappropriate_type="unknown_controlled_policy",
        inappropriate_blocked=False,
        set_illegal_drug_block=False,
    )
    return AdapterResult(
        content=content,
        mutation_plan=plan,
        observability={
            "adapter": "ambiguous_controlled",
            "subtype": "unknown_controlled_policy",
            "fingerprint": snapshot.normalized_text_fingerprint,
            "criminal_template": False,
        },
    )


def adapt_controlled_or_illegal(
    decision: PolicyDecision,
    snapshot: TurnSignalSnapshot,
    *,
    user_text: str,
    triage_result: Optional[dict[str, Any]] = None,
) -> AdapterResult:
    from src.handlers.chat.inappropriate_drug_block_route import (
        resolve_illegal_or_controlled_type,
    )
    from src.services.counseling.counseling_templates import (
        generate_illegal_drug_rejection_message,
    )
    from src.services.status_diagnosis_builder import build_notice_status

    # Prefer typed subtype; never default unresolved → illegal
    req = decision.subtype if decision.subtype in ("illegal", "controlled") else None
    if req is None:
        req = resolve_illegal_or_controlled_type(triage_result, user_text)
    if req not in ("illegal", "controlled"):
        # Fail closed to neutral ambiguous — not criminal template
        return adapt_ambiguous_controlled(decision, snapshot, user_text=user_text)

    content = generate_illegal_drug_rejection_message(req)
    title = "違法薬物のご相談" if req == "illegal" else "規制薬物のご相談"
    sage = build_notice_status(
        content.strip(),
        title=title,
        variant="critical",
        kind=f"inappropriate_drug_{req}",
        show_feedback=True,
    ).to_client_dict()
    plan = MutationPlan(
        append_user=True,
        user_text=user_text,
        append_bot=True,
        bot_legacy_content=content.strip(),
        bot_kind=f"inappropriate_drug_{req}",
        bot_variant="critical",
        bot_title=title,
        record_inappropriate=True,
        inappropriate_type=req,
        inappropriate_blocked=True,
        set_illegal_drug_block=True,
        sage_diagnosis=sage,
    )
    return AdapterResult(
        content=content.strip(),
        mutation_plan=plan,
        status_proposal=sage,
        observability={
            "adapter": "controlled_or_illegal",
            "subtype": req,
            "detector_source": decision.detector_source,
            "fingerprint": snapshot.normalized_text_fingerprint,
        },
    )


def adapt_medical_examination(
    decision: PolicyDecision,
    snapshot: TurnSignalSnapshot,
    *,
    user_text: str,
) -> AdapterResult:
    from src.services.counseling.counseling_templates import (
        generate_medical_examination_boundary_message,
    )

    del decision
    content = generate_medical_examination_boundary_message()
    plan = MutationPlan(
        append_user=True,
        user_text=user_text,
        append_bot=True,
        bot_legacy_content=content,
        bot_kind="policy_medical_examination_boundary",
        bot_variant="notice",
        bot_title="診察について",
        record_inappropriate=True,
        inappropriate_type="medical_examination",
        inappropriate_blocked=False,
    )
    return AdapterResult(
        content=content,
        mutation_plan=plan,
        observability={
            "adapter": "medical_examination",
            "fingerprint": snapshot.normalized_text_fingerprint,
        },
    )


def run_policy_adapter(
    decision: PolicyDecision,
    snapshot: TurnSignalSnapshot,
    *,
    user_text: str,
    triage_result: Optional[dict[str, Any]] = None,
) -> AdapterResult | None:
    if decision.kind is None or decision.action == "continue":
        return None
    if decision.kind == "prescription":
        return adapt_prescription(decision, snapshot, user_text=user_text)
    if decision.kind == "controlled_or_illegal":
        return adapt_controlled_or_illegal(
            decision, snapshot, user_text=user_text, triage_result=triage_result
        )
    if decision.kind == "medical_examination":
        return adapt_medical_examination(decision, snapshot, user_text=user_text)
    if decision.kind == "ambiguous_controlled":
        return adapt_ambiguous_controlled(decision, snapshot, user_text=user_text)
    return None
