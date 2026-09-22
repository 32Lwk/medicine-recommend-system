"""Typed PolicyDecision / EnforcementResult for A-3 (not RouteDecision)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Optional

PolicyKind = Literal[
    "prescription",
    "controlled_or_illegal",
    "medical_examination",
    "ambiguous_controlled",
]

PolicyAction = Literal[
    "block",
    "boundary_guidance",
    "safe_clarification",
    "continue",
]

FallbackReason = Literal[
    "none",
    "detector_error",
    "adapter_error",
    "incomplete_evaluation",
    "unknown_kind",
    "empty_content",
    "db_commit_unknown",
    "db_save_failed",
    "rollback_failed",
    "llm_timeout",
    "llm_empty",
]


@dataclass(frozen=True)
class PolicyDecision:
    kind: PolicyKind | None
    action: PolicyAction
    detector_source: str
    confidence: float
    reason_code: str
    evaluation_complete: bool
    subtype: str | None = None


@dataclass(frozen=True)
class MutationPlan:
    append_user: bool = False
    user_text: str = ""
    append_bot: bool = False
    bot_legacy_content: str = ""
    bot_kind: str = "policy_enforcement"
    bot_variant: str = "caution"
    bot_title: str = "ご案内"
    record_inappropriate: bool = False
    inappropriate_type: str = ""
    inappropriate_blocked: bool = False
    set_illegal_drug_block: bool = False
    start_counseling: bool = False
    counseling_symptom_type: str = ""
    sage_diagnosis: dict[str, Any] | None = None


@dataclass(frozen=True)
class AdapterResult:
    content: str
    mutation_plan: MutationPlan
    observability: dict[str, Any] = field(default_factory=dict)
    status_proposal: dict[str, Any] | None = None


@dataclass(frozen=True)
class PolicyEnforcementResult:
    handled: bool
    response: dict[str, Any] | None
    status_code: int | None
    policy_kind: PolicyKind | None
    action: PolicyAction | None
    fallback_reason: str | None
    observability_fields: dict[str, Any] = field(default_factory=dict)
    db_commit_status: str | None = None  # confirmed|failed|unknown|memory_only|skipped
