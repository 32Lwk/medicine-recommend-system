"""
Concierge 技術 FAQ — ライブ LLM 応答品質テスト（OPENAI_API_KEY 必須）。

ルーティングだけでなく、RAG 参照を踏まえた回答本文が SSOT と整合するかを検証。
CI では skip。
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any, Optional, Sequence

import pytest

from src.agents.concierge_agent import (
    build_concierge_payload,
    generate_meta_concierge_text,
    resolve_concierge_intent,
)
from src.content.concierge_tech_reference import wants_technical_deep_dive
from src.services.medicine_qa_eligibility import MedicineQaRoute, resolve_medicine_qa_route

pytestmark = pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY unset — live Concierge technical tests skipped",
)

_FORBIDDEN_OUTPUT = (
    "TRANSLATION_PROVIDER",
    "TTS_PROVIDER=",
    "CONCIERGE_RAG_PROVIDER",
    "DATABASE_URL",
    "OPENAI_API_KEY",
    "環境変数を参照",
    "docs/concierge/technical/",
    "案内できません",
)


@dataclass(frozen=True)
class TechnicalLiveCase:
    id: str
    message: str
    intent: str = "architecture"
    history: Optional[list[dict[str, Any]]] = None
    must_contain_any: Sequence[str] = ()
    must_not_contain: Sequence[str] = _FORBIDDEN_OUTPUT
    expect_route: Optional[MedicineQaRoute] = MedicineQaRoute.CONCIERGE


TECHNICAL_LIVE_CASES = [
    TechnicalLiveCase(
        "live_git_remote",
        "GitLabとGitHubの違いは？このプロジェクトではどっちが正本？",
        must_contain_any=("GitHub", "github.com", "正本", "ミラー", "origin"),
        must_not_contain=_FORBIDDEN_OUTPUT + ("GitLabが正本", "GitLab が正本"),
    ),
    TechnicalLiveCase(
        "live_cross_cloud_casual",
        "GCP本番とAWSステージング、ざっくり何が違う？",
        must_contain_any=("GCP", "Cloud Run", "AWS", "ECS", "ステージング"),
    ),
    TechnicalLiveCase(
        "live_codepipeline_casual",
        "デプロイってどう流れてるの？CodePipeline",
        must_contain_any=("CodePipeline", "CodeBuild", "ECR", "ECS", "デプロイ"),
    ),
    TechnicalLiveCase(
        "live_rule_based_reco",
        "市販薬のおすすめ機能はAI？それともルールベース？",
        must_contain_any=("ルールベース", "rule", "LLM", "スコア"),
    ),
    TechnicalLiveCase(
        "live_data_storage_casual",
        "会話内容ってどこに保存されてるの？",
        must_contain_any=("PostgreSQL", "Neon", "保存", "データ"),
    ),
    TechnicalLiveCase(
        "live_r2_images",
        "医薬品画像のCDNはどこ？images.yutok",
        must_contain_any=("R2", "images.yutok", "CDN", "Cloudflare"),
    ),
    TechnicalLiveCase(
        "live_bedrock_kb",
        "Bedrock KBって何のため？今動いてる？",
        must_contain_any=("Bedrock", "ナレッジ", "KB", "ingestion", "RAG"),
    ),
    TechnicalLiveCase(
        "live_multi_agent",
        "マルチエージェントって具体的に誰が何担当？",
        must_contain_any=("TriageAgent", "Concierge", "Physical", "マルチ", "担当"),
    ),
    TechnicalLiveCase(
        "live_sse_casual",
        "SSEってこのアプリでは何に使ってる？",
        must_contain_any=("SSE", "Server-Sent", "ストリーム", "段階", "配信"),
    ),
    TechnicalLiveCase(
        "live_changelog_recent",
        "最近AWS周りで何か変わった？",
        intent="doc_changelog",
        must_contain_any=("更新", "AWS", "改善", "CHANGELOG", "2026"),
    ),
]

CONTEXT_LIVE_CASES = [
    TechnicalLiveCase(
        "live_arch_followup_deep",
        "もうちょい詳しく",
        history=[
            {"type": "user", "content": "インフラ構成教えて"},
            {"type": "bot", "content": "GCPとAWS…", "concierge_intent": "architecture"},
        ],
        must_contain_any=("GCP", "AWS", "Cloud Run", "ECS", "CodePipeline"),
    ),
    TechnicalLiveCase(
        "live_medicine_not_architecture",
        "ロキソニン眠くなる？",
        expect_route=MedicineQaRoute.MEDICINE_QA,
        intent="architecture",
        must_contain_any=(),  # routing only
    ),
]


@pytest.fixture(scope="module")
def openai_client():
    from openai import OpenAI

    return OpenAI(api_key=os.environ["OPENAI_API_KEY"])


def _normalize(text: str) -> str:
    return re.sub(r"\s+", "", (text or "").strip())


@pytest.mark.parametrize("case", TECHNICAL_LIVE_CASES, ids=lambda c: c.id)
def test_live_technical_concierge_answer(case: TechnicalLiveCase, openai_client):
    route = resolve_medicine_qa_route(
        case.message,
        conversation_history=case.history,
        client=openai_client,
    )
    if case.expect_route:
        assert route.route == case.expect_route, (
            f"{case.id}: route={route.route.value} intent={route.concierge_intent}"
        )

    if case.expect_route == MedicineQaRoute.MEDICINE_QA:
        return

    intent = case.intent
    if route.concierge_intent in ("architecture", "doc_changelog", "capabilities", "app_about"):
        intent = route.concierge_intent

    if intent == "doc_changelog":
        payload = build_concierge_payload(
            intent,
            case.message,
            openai_client,
            history=case.history or [],
        )
        answer = str(payload.get("content") or "")
    else:
        answer, _deep_used = generate_meta_concierge_text(
            openai_client,
            case.message,
            intent,
            history=case.history or [],
        )
    assert answer and len(answer.strip()) >= 40, f"{case.id}: empty or too short answer"

    for forbidden in case.must_not_contain:
        assert forbidden not in answer, f"{case.id}: forbidden {forbidden!r} in answer"

    if case.must_contain_any:
        assert any(term in answer for term in case.must_contain_any), (
            f"{case.id}: expected one of {case.must_contain_any} in:\n{answer[:600]}"
        )


@pytest.mark.parametrize("case", CONTEXT_LIVE_CASES, ids=lambda c: c.id)
def test_live_technical_context_cases(case: TechnicalLiveCase, openai_client):
    if case.expect_route == MedicineQaRoute.MEDICINE_QA:
        decision = resolve_medicine_qa_route(case.message, client=openai_client)
        assert decision.route == MedicineQaRoute.MEDICINE_QA
        return

    answer, _ = generate_meta_concierge_text(
        openai_client,
        case.message,
        "architecture",
        history=case.history or [],
    )
    assert any(term in answer for term in case.must_contain_any)


def test_live_resolve_concierge_intent_matches_probe(openai_client):
    """技術質問が architecture intent で Concierge に解決される。"""
    samples = [
        "GitlabとGithubの違いは？",
        "技術スタック教えて",
        "このサービスのデプロイ先は？",
    ]
    for msg in samples:
        intent = resolve_concierge_intent(
            msg,
            {},
            triage_result={"category": "Ask"},
            client=openai_client,
        )
        assert intent == "architecture", f"{msg!r} -> {intent!r}"
