"""Build diagnosis v1 structured payloads from recommendation pipeline results."""
from __future__ import annotations

import html
import logging
import re
from typing import Any

from src.schemas.recommendation_diagnosis_v1 import DiagnosisV1, RecoError, UsageSection
from src.services.reco_error_messages import ERROR_MESSAGES
from src.services.recommendation_client_payload import enrich_recommended_medicines

logger = logging.getLogger(__name__)

SAGE_RECO_MARKER = "sage_reco"
SAGE_STATUS_MARKER = "sage_status"

_ERROR_TYPE_MAP: dict[str, tuple[str, str]] = {
    "no_candidates": ("no_candidates", "warn"),
    "rule_based_error": ("rule_error", "danger"),
    "missing_critical_info": ("missing_info", "warn"),
    "unknown_error": ("unknown", "danger"),
}


def _symptom_names(symptoms: list[Any] | None) -> list[str]:
    if not symptoms:
        return []
    out: list[str] = []
    for s in symptoms:
        if isinstance(s, str) and s.strip():
            out.append(s.strip())
        elif isinstance(s, dict):
            name = s.get("name") or s.get("symptom") or ""
            if name:
                out.append(str(name).strip())
        elif s is not None:
            out.append(str(s).strip())
    return out[:8]


def build_reco_error(error_type: str, error_details: dict[str, Any] | None = None) -> RecoError:
    details = error_details or {}
    mapped_type, default_severity = _ERROR_TYPE_MAP.get(
        error_type, ("unknown", "info")
    )
    info = ERROR_MESSAGES.get(error_type, ERROR_MESSAGES["unknown_error"])
    reason = details.get("reason") or info["main_message"]
    return RecoError(
        type=mapped_type,  # type: ignore[arg-type]
        severity=default_severity,  # type: ignore[arg-type]
        title=info["title"],
        message=reason,
        recommendations=list(info.get("recommendations") or []),
    )


def build_escalation_error(
    doctor_consultation: str,
    medicine_type: str = "",
) -> RecoError:
    return RecoError(
        type="escalation",
        severity="danger",
        title="重要な注意事項",
        message=doctor_consultation or "市販薬の使用は控え、医師にご相談ください。",
        recommendations=[
            "速やかに医師の診察を受けてください",
            "市販薬での自己治療は推奨されません",
            "症状が悪化する場合は救急医療機関へ",
        ],
    )


def compute_ingredient_overlap(
    recommended_medicines: list[dict[str, Any]],
) -> dict[str, Any] | None:
    if not recommended_medicines:
        return None
    try:
        from src.core.rule_based_recommendation import check_ingredient_overlap

        overlap_result = check_ingredient_overlap(recommended_medicines)
        if not overlap_result.get("has_overlap"):
            return None
        overlap_summaries: list[str] = []
        for overlap in overlap_result.get("overlapping_ingredients", []):
            medicines_list = "、".join(overlap.get("medicines", []))
            summary = (
                f"{overlap.get('warning_message', '')}：{medicines_list}"
                f"{overlap.get('side_effect_message', '')}"
            )
            overlap_summaries.append(summary)
        display_summaries = overlap_summaries[:2]
        if len(overlap_summaries) > 2:
            display_summaries.append(f"他{len(overlap_summaries) - 2}件の重複あり")
        highest_severity = overlap_result.get("highest_severity", "blue")
        severity_titles = {
            "red": "成分の重複について（重複禁止）",
            "yellow": "成分の重複について（注意）",
            "blue": "成分の重複について（情報）",
        }
        return {
            "summaries": display_summaries,
            "severity": highest_severity,
            "title": severity_titles.get(highest_severity, severity_titles["blue"]),
        }
    except Exception as exc:
        logger.warning("成分重複チェックエラー: %s", exc)
        return None


def build_usage_sections(usage_notes: str) -> list[UsageSection]:
    """Parse usage_notes text/HTML into structured UsageSection list."""
    if not usage_notes or not str(usage_notes).strip():
        return []
    text = str(usage_notes).strip()
    if "<strong>" in text and "<br" in text:
        parts = re.split(r"<br\s*/?>\s*<br\s*/?>", text, flags=re.IGNORECASE)
        sections: list[UsageSection] = []
        for idx, part in enumerate(parts):
            part = part.strip()
            if not part:
                continue
            title_match = re.match(r"<strong>([^<]+)</strong>", part, re.IGNORECASE)
            title = title_match.group(1).strip() if title_match else f"使用上の注意 {idx + 1}"
            sections.append(
                UsageSection(
                    id=f"usage-html-{idx + 1}",
                    kind="per_medicine",
                    title=title,
                    html=part,
                    default_expanded=False,
                )
            )
        return sections[:4]

    sections = []
    current_kind = "other"
    current_title = "使用上の注意"
    current_items: list[str] = []
    section_idx = 0

    def _flush() -> None:
        nonlocal section_idx, current_items, current_title, current_kind
        if not current_items:
            return
        section_idx += 1
        sections.append(
            UsageSection(
                id=f"usage-{section_idx}",
                kind=current_kind,  # type: ignore[arg-type]
                title=current_title,
                items=list(current_items),
                default_expanded=current_kind == "contraindication",
            )
        )
        current_items = []

    for raw_line in text.split("\n"):
        line = raw_line.strip()
        if not line:
            continue
        if re.match(r"^[123]つ目[：:]", line):
            _flush()
            current_kind = "per_medicine"
            current_title = line.replace("：", ":").split(":")[0]
            continue
        if line.startswith("【使ってはいけない人】"):
            _flush()
            current_kind = "contraindication"
            current_title = "使ってはいけない人"
            continue
        if line.startswith("【OTC医薬品について】"):
            _flush()
            current_kind = "otc_info"
            current_title = "OTC医薬品について"
            continue
        if line.startswith("【服用時の注意】"):
            _flush()
            current_kind = "usage_caution"
            current_title = "服用時の注意"
            continue
        if line.startswith("年齢制限:"):
            line = line.replace("年齢制限:", "年齢制限: ").strip()
        current_items.append(line)

    _flush()
    return sections[:4]


def build_admin_block(
    recommendation_result: dict[str, Any],
    *,
    session_id: str | None = None,
) -> dict[str, Any]:
    admin: dict[str, Any] = {}
    for key in (
        "nlu_result",
        "safety_result",
        "score_breakdown",
        "candidate_counts",
        "algorithm",
    ):
        if key in recommendation_result:
            admin[key] = recommendation_result[key]
    if session_id:
        admin["session_id"] = session_id
    return admin


def build_diagnosis_v1(
    recommendation_result: dict[str, Any],
    *,
    session_id: str | None = None,
    include_usage_sections: bool = True,
) -> DiagnosisV1:
    """Build diagnosis v1 from a recommendation_result dict."""
    symptoms = _symptom_names(recommendation_result.get("symptoms"))
    medicine_type = recommendation_result.get("medicine_type") or ""
    medicines = enrich_recommended_medicines(
        recommendation_result.get("recommended_medicines") or [],
        medicine_type=medicine_type or None,
        symptoms=symptoms,
    )
    usage_notes = recommendation_result.get("usage_notes") or ""
    usage_sections = (
        build_usage_sections(usage_notes) if include_usage_sections else []
    )
    overlap = compute_ingredient_overlap(medicines)
    error: RecoError | None = None

    if recommendation_result.get("error"):
        error = build_reco_error(
            recommendation_result.get("error_type", "unknown_error"),
            recommendation_result.get("error_details") or {},
        )
    elif recommendation_result.get("escalation"):
        error = build_escalation_error(
            recommendation_result.get("doctor_consultation") or "",
            medicine_type,
        )
    elif not medicines:
        error = RecoError(
            type="no_candidates",
            severity="warn",
            title=ERROR_MESSAGES["no_candidates"]["title"],
            message=ERROR_MESSAGES["no_candidates"]["main_message"],
            recommendations=list(ERROR_MESSAGES["no_candidates"]["recommendations"]),
        )

    return DiagnosisV1(
        render="sage_reco",
        symptoms=symptoms,
        medicine_type=medicine_type or None,
        recommended_medicines=medicines,
        personalized_advice=recommendation_result.get("personalized_advice") or "",
        ingredient_overlap=overlap,
        usage_sections=usage_sections,
        doctor_consultation=recommendation_result.get("doctor_consultation") or "",
        critical_questions=list(recommendation_result.get("critical_questions") or []),
        additional_questions=list(
            recommendation_result.get("additional_questions") or []
        ),
        missing_priority=recommendation_result.get("missing_priority"),
        influenza_risk=bool(recommendation_result.get("influenza_risk")),
        influenza_reason=recommendation_result.get("influenza_reason") or "",
        severity_escalation=recommendation_result.get("severity_escalation") or "",
        error=error,
        algorithm=recommendation_result.get("algorithm"),
        admin=build_admin_block(recommendation_result, session_id=session_id),
    )


def build_display_summary(diagnosis: DiagnosisV1) -> str:
    """Plain-text summary for logs and feedback (200–500 chars target)."""
    parts: list[str] = []
    if diagnosis.symptoms:
        parts.append("症状: " + "、".join(diagnosis.symptoms[:5]))
    if diagnosis.recommended_medicines:
        names = [
            str(m.get("product_name") or m.get("name") or "")
            for m in diagnosis.recommended_medicines[:3]
        ]
        names = [n for n in names if n]
        if names:
            parts.append("推奨: " + "、".join(names))
    if diagnosis.error:
        parts.append(diagnosis.error.message[:120])
    elif diagnosis.personalized_advice:
        parts.append(diagnosis.personalized_advice[:200])
    if diagnosis.doctor_consultation:
        parts.append(diagnosis.doctor_consultation[:120])
    text = " ".join(parts).strip()
    if len(text) > 500:
        return text[:497] + "..."
    return text or "医薬品推奨結果"


def merge_reco_detail(
    diagnosis: dict[str, Any],
    detail: dict[str, Any],
) -> dict[str, Any]:
    """Merge reco_detail SSE payload (usage_sections) into diagnosis dict."""
    merged = dict(diagnosis)
    if detail.get("usage_sections"):
        merged["usage_sections"] = detail["usage_sections"]
    return merged
