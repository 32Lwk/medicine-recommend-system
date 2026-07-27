"""
Concierge 技術 FAQ — ローカル RAG retrieve と参照ブロック統合テスト（LLM なし）。

retrieve 結果がプロンプト参照に載ること、および代表クエリで SSOT 由来の
用語がヒットすることを検証する。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import pytest

from src.agents.concierge_agent import _meta_reference_block
from src.content.concierge_tech_reference import augment_architecture_reference
from src.services.bedrock_kb_retrieve import (
    augment_reference_with_kb,
    retrieve_concierge_context,
)


@dataclass(frozen=True)
class RagRetrieveCase:
    id: str
    query: str
    must_contain_any: Sequence[str]
    min_chunks: int = 1


RAG_RETRIEVE_CASES = [
    RagRetrieveCase(
        "rag_codepipeline",
        "CodePipeline デプロイ ECS ECR",
        ("CodePipeline", "CodeBuild", "ECR", "ECS"),
    ),
    RagRetrieveCase(
        "rag_cross_cloud",
        "GCP Cloud Run AWS ECS ステージング",
        ("GCP", "Cloud Run", "AWS", "ECS"),
    ),
    RagRetrieveCase(
        "rag_github_repo",
        "GitHub 公開リポジトリ ソースコード",
        ("GitHub", "github.com", "32Lwk"),
    ),
    RagRetrieveCase(
        "rag_gitlab_mirror",
        "GitLab ミラー 正本 GitHub",
        ("GitHub", "GitLab", "正本", "ミラー"),
    ),
    RagRetrieveCase(
        "rag_neon_db",
        "PostgreSQL Neon セッション 保存",
        ("PostgreSQL", "Neon"),
    ),
    RagRetrieveCase(
        "rag_bedrock_kb",
        "Bedrock Knowledge Base ingestion",
        ("Bedrock", "KB", "ingestion", "ナレッジ"),
    ),
    RagRetrieveCase(
        "rag_r2_cdn",
        "医薬品画像 CDN R2 images.yutok",
        ("R2", "images.yutok", "CDN"),
    ),
    RagRetrieveCase(
        "rag_multi_agent",
        "TriageAgent ConciergeAgent マルチエージェント",
        ("TriageAgent", "Concierge", "マルチ"),
    ),
    RagRetrieveCase(
        "rag_rule_based",
        "市販薬推奨 ルールベース rule based",
        ("ルールベース", "rule", "LLM"),
    ),
    RagRetrieveCase(
        "rag_sse",
        "SSE Server-Sent Events ストリーム",
        ("SSE", "Server-Sent", "ストリーム", "段階"),
    ),
]


@pytest.mark.parametrize("case", RAG_RETRIEVE_CASES, ids=lambda c: c.id)
def test_local_rag_retrieve_hits_relevant_docs(case: RagRetrieveCase):
    result = retrieve_concierge_context(
        case.query,
        top_k=5,
        intent="architecture",
        use_cache=False,
    )
    assert result["provider"] == "local_rag"
    assert result["chunk_count"] >= case.min_chunks, (
        f"{case.id}: no chunks for {case.query!r}"
    )
    combined = "\n".join(result.get("chunks") or [])
    assert any(needle in combined for needle in case.must_contain_any), (
        f"{case.id}: expected one of {case.must_contain_any} in:\n{combined[:500]}"
    )


def test_augment_reference_includes_local_rag_block():
    base = _meta_reference_block("architecture")
    base = augment_architecture_reference(base, deep=True, user_text="CodePipeline の流れ")
    augmented = augment_reference_with_kb(
        "CodePipeline デプロイフロー",
        base,
        intent="architecture",
        deep=True,
    )
    assert "ローカルナレッジ参照" in augmented or "Bedrock Knowledge Base" in augmented
    assert any(
        term in augmented
        for term in ("CodePipeline", "CodeBuild", "ECR", "ECS", "デプロイ")
    )


@pytest.mark.parametrize(
    "message,needles",
    [
        ("GitLabとGitHubの違いは？", ("GitHub", "GitLab")),
        ("このチャットGPT使ってる？", ("GPT", "OpenAI", "LLM", "生成")),
        ("インフラざっくり教えて", ("GCP", "AWS", "Cloud Run", "ECS")),
        ("データどこに残るの？", ("PostgreSQL", "Neon", "保存")),
    ],
)
def test_full_reference_stack_contains_ssot_terms(message: str, needles: tuple[str, ...]):
    """SSOT + tech md + local RAG の合成参照に期待語が含まれる。"""
    base = _meta_reference_block("architecture")
    ref = augment_architecture_reference(base, deep=True, user_text=message)
    ref = augment_reference_with_kb(message, ref, intent="architecture", deep=True)
    assert any(n in ref for n in needles), f"missing any of {needles} in reference for {message!r}"
