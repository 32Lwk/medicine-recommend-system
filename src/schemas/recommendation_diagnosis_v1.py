"""Recommendation diagnosis v1 — canonical structured payload for Sage UI."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class UsageSection(BaseModel):
    id: str
    kind: Literal[
        "per_medicine",
        "contraindication",
        "usage_caution",
        "otc_info",
        "other",
    ]
    title: str
    items: list[str] = Field(default_factory=list)
    html: str | None = None
    default_expanded: bool = False


class RecoError(BaseModel):
    type: Literal[
        "no_candidates",
        "escalation",
        "missing_info",
        "rule_error",
        "unknown",
    ]
    severity: Literal["warn", "danger", "info"]
    title: str
    message: str
    recommendations: list[str] = Field(default_factory=list)


class DiagnosisV1(BaseModel):
    schema_version: Literal[1] = 1
    render: Literal["sage_reco", "sage_status", "sage_qa"]
    symptoms: list[str] = Field(default_factory=list)
    medicine_type: str | None = None
    recommended_medicines: list[dict[str, Any]] = Field(default_factory=list)
    personalized_advice: str = ""
    ingredient_overlap: dict[str, Any] | None = None
    usage_sections: list[UsageSection] = Field(default_factory=list)
    doctor_consultation: str = ""
    critical_questions: list[str] = Field(default_factory=list)
    additional_questions: list[str] = Field(default_factory=list)
    missing_priority: str | None = None
    influenza_risk: bool = False
    influenza_reason: str = ""
    age_policy_notice: str = ""
    severity_escalation: str = ""
    error: RecoError | None = None
    feedback_context: dict[str, Any] | None = None
    show_feedback: bool = True
    i18n: dict[str, dict[str, Any]] | None = None
    admin: dict[str, Any] | None = None
    algorithm: str | None = None

    def to_client_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude_none=True)

    def to_user_dict(self) -> dict[str, Any]:
        return strip_for_user_api(self.to_client_dict())


_ADMIN_KEYS = frozenset(
    {
        "admin",
        "nlu_result",
        "safety_result",
        "score_breakdown",
    }
)


def strip_for_user_api(data: dict[str, Any] | None) -> dict[str, Any] | None:
    """Remove admin-only fields from diagnosis for user-facing API/storage."""
    if not data:
        return data
    out = dict(data)
    for key in _ADMIN_KEYS:
        out.pop(key, None)
    out.pop("admin", None)
    return out
