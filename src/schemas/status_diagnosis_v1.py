"""Status / notification diagnosis v1 for Sage UI."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class StatusSection(BaseModel):
    title: str
    items: list[str] = Field(default_factory=list)
    html: str | None = None
    commit: str = ""


class StatusAction(BaseModel):
    id: str
    label: str
    kind: Literal["button", "link"] = "button"
    action: str | None = None
    postback_text: str | None = None


class StatusDiagnosisV1(BaseModel):
    schema_version: Literal[1] = 1
    render: Literal["sage_status", "sage_qa"] = "sage_status"
    layout: Literal["card", "plain"] = "card"
    variant: Literal["notice", "caution", "critical", "error", "security"] = "notice"
    title: str
    subtitle: str = ""
    message: str = ""
    hints: list[str] = Field(default_factory=list)
    sections: list[StatusSection] = Field(default_factory=list)
    actions: list[StatusAction] = Field(default_factory=list)
    suggested_symptoms: list[dict[str, Any]] = Field(default_factory=list)
    show_feedback: bool = True
    show_bug_report: bool = False
    feedback_context: dict[str, Any] | None = None
    kind: str | None = None
    i18n: dict[str, dict[str, Any]] | None = None
    crisis_resources: list[dict[str, Any]] = Field(default_factory=list)
    emergency_message: str = ""

    def to_client_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude_none=True)
