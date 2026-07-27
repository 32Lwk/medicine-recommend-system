"""bedrock_kb_retrieve.py"""
import sys
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch):
    monkeypatch.delenv("CONCIERGE_RAG_PROVIDER", raising=False)
    monkeypatch.delenv("MEDICINE_RAG_PROVIDER", raising=False)
    monkeypatch.delenv("BEDROCK_KB_ID", raising=False)
    monkeypatch.delenv("BEDROCK_MEDICINE_KB_ID", raising=False)
    monkeypatch.delenv("BEDROCK_KB_SEARCH_MODE", raising=False)


def test_retrieve_local_when_bedrock_disabled():
    from src.services.bedrock_kb_retrieve import retrieve_concierge_context

    result = retrieve_concierge_context("Cloud Run とは")
    assert result["provider"] == "local_rag"
    assert result["chunk_count"] >= 0


def test_retrieve_calls_bedrock_managed(monkeypatch):
    monkeypatch.setenv("CONCIERGE_RAG_PROVIDER", "bedrock_kb")
    monkeypatch.setenv("BEDROCK_KB_ID", "KB123")
    monkeypatch.setenv("BEDROCK_KB_SEARCH_MODE", "managed")

    mock_client = MagicMock()
    mock_client.retrieve.return_value = {
        "retrievalResults": [
            {
                "content": {"text": "chunk one"},
                "location": {"s3Location": {"uri": "s3://bucket/doc.md"}},
                "score": 0.9,
            }
        ]
    }
    mock_boto3 = MagicMock()
    mock_boto3.client.return_value = mock_client
    with patch.dict(sys.modules, {"boto3": mock_boto3}):
        from src.services.bedrock_kb_retrieve import retrieve_concierge_context

        result = retrieve_concierge_context("architecture", top_k=3, use_cache=False)
    assert result["chunk_count"] == 1
    assert result["chunks"][0] == "chunk one"
    assert "s3://bucket/doc.md" in result["source_uris"]
    cfg = mock_client.retrieve.call_args.kwargs["retrievalConfiguration"]
    assert "managedSearchConfiguration" in cfg
    assert cfg["managedSearchConfiguration"]["numberOfResults"] == 3


def test_retrieve_vector_mode_for_legacy_kb(monkeypatch):
    monkeypatch.setenv("CONCIERGE_RAG_PROVIDER", "bedrock_kb")
    monkeypatch.setenv("BEDROCK_KB_ID", "KB123")
    monkeypatch.setenv("BEDROCK_KB_SEARCH_MODE", "vector")

    mock_client = MagicMock()
    mock_client.retrieve.return_value = {"retrievalResults": []}
    mock_boto3 = MagicMock()
    mock_boto3.client.return_value = mock_client
    with patch.dict(sys.modules, {"boto3": mock_boto3}):
        from src.services.bedrock_kb_retrieve import retrieve_concierge_context

        retrieve_concierge_context("architecture", use_cache=False)
    cfg = mock_client.retrieve.call_args.kwargs["retrievalConfiguration"]
    assert "vectorSearchConfiguration" in cfg


def test_retrieve_filters_low_score_chunks(monkeypatch):
    monkeypatch.setenv("CONCIERGE_RAG_PROVIDER", "bedrock_kb")
    monkeypatch.setenv("BEDROCK_KB_ID", "KB123")
    monkeypatch.setenv("BEDROCK_KB_MIN_SCORE", "0.5")

    mock_client = MagicMock()
    mock_client.retrieve.return_value = {
        "retrievalResults": [
            {
                "content": {"text": "keep me"},
                "location": {"s3Location": {"uri": "s3://bucket/good.md"}},
                "score": 0.82,
            },
            {
                "content": {"text": "drop me"},
                "location": {"s3Location": {"uri": "s3://bucket/bad.md"}},
                "score": 0.21,
            },
        ]
    }
    mock_boto3 = MagicMock()
    mock_boto3.client.return_value = mock_client
    with patch.dict(sys.modules, {"boto3": mock_boto3}):
        from src.services.bedrock_kb_retrieve import retrieve_concierge_context

        result = retrieve_concierge_context("architecture", use_cache=False)
    assert result["chunk_count"] == 1
    assert result["chunks"] == ["keep me"]
    assert result["dropped_low_score"] == 1


def test_medicine_retrieve_builds_query_with_product_names(monkeypatch):
    monkeypatch.setenv("MEDICINE_RAG_PROVIDER", "bedrock_kb")
    monkeypatch.setenv("BEDROCK_MEDICINE_KB_ID", "MEDKB")

    mock_client = MagicMock()
    mock_client.retrieve.return_value = {
        "retrievalResults": [
            {
                "content": {"text": "interaction row"},
                "location": {"s3Location": {"uri": "s3://bucket/interactions.csv"}},
                "score": 0.91,
            }
        ]
    }
    mock_boto3 = MagicMock()
    mock_boto3.client.return_value = mock_client
    with patch.dict(sys.modules, {"boto3": mock_boto3}):
        from src.services.bedrock_kb_retrieve import retrieve_medicine_context

        result = retrieve_medicine_context(
            "併用できますか",
            recommended_medicines=[{"product_name": "カロナールA"}],
            use_cache=False,
        )
    assert result["chunk_count"] == 1
    query = mock_client.retrieve.call_args.kwargs["retrievalQuery"]["text"]
    assert "併用できますか" in query
    assert "カロナールA" in query


def test_medicine_retrieve_none_provider_skips_rag(monkeypatch):
    monkeypatch.setenv("MEDICINE_RAG_PROVIDER", "none")

    with patch(
        "src.services.local_rag_retrieve.retrieve_local_context",
    ) as mock_local:
        from src.services.bedrock_kb_retrieve import retrieve_medicine_context

        result = retrieve_medicine_context("のどが痛い", use_cache=False)
    assert result["chunk_count"] == 0
    mock_local.assert_not_called()


def test_augment_medicine_prompt_appends_kb_block(monkeypatch):
    monkeypatch.setenv("MEDICINE_RAG_PROVIDER", "bedrock_kb")
    monkeypatch.setenv("BEDROCK_MEDICINE_KB_ID", "MEDKB")

    with patch(
        "src.services.bedrock_kb_retrieve.retrieve_medicine_context",
        return_value={
            "chunks": ["イブプロフェンとワーファリンは高リスク"],
            "source_uris": ["s3://bucket/interactions.csv"],
        },
    ):
        from src.services.bedrock_kb_retrieve import augment_medicine_prompt_with_kb

        out = augment_medicine_prompt_with_kb("併用", "base prompt")
    assert "base prompt" in out
    assert "医薬品ナレッジベース参照" in out
    assert "イブプロフェン" in out


def test_build_medicine_retrieval_query_includes_nlu_and_concomitant():
    from src.services.bedrock_kb_retrieve import build_medicine_retrieval_query

    q = build_medicine_retrieval_query(
        "併用できますか",
        [{"product_name": "ロキソニン"}],
        nlu_result={"symptoms": [{"name": "頭痛"}]},
        concomitant_medications=["ワーファリン"],
        use_comprehend=False,
    )
    assert "併用できますか" in q
    assert "ロキソニン" in q
    assert "頭痛" in q
    assert "ワーファリン" in q


def test_build_medicine_retrieval_query_comprehend_medications(monkeypatch):
    monkeypatch.setenv("COMPREHEND_MEDICAL_ENABLED", "1")
    with patch(
        "src.services.comprehend_medical.extract_medical_entities",
        return_value={"medications": ["イブプロフェン"], "symptoms": []},
    ):
        from src.services.bedrock_kb_retrieve import build_medicine_retrieval_query

        q = build_medicine_retrieval_query("併用", use_comprehend=True)
    assert "イブプロフェン" in q


def test_high_risk_csv_block_prepended(monkeypatch):
    monkeypatch.setenv("MEDICINE_RAG_PROVIDER", "bedrock_kb")
    monkeypatch.setenv("BEDROCK_MEDICINE_KB_ID", "MEDKB")

    import pandas as pd

    df = pd.DataFrame(
        [
            {
                "成分A": "ロキソプロフェン",
                "成分B": "ワーファリン",
                "相互作用レベル": "高",
                "説明": "出血リスク増加",
            }
        ]
    )
    with patch("src.core.scoring_utils.load_interactions_data", return_value=df):
        from src.services.bedrock_kb_retrieve import augment_medicine_prompt_with_kb

        with patch(
            "src.services.bedrock_kb_retrieve.retrieve_medicine_context",
            return_value={
                "chunks": ["# 相互作用\n- **相互作用レベル**: 高"],
                "source_uris": ["s3://bucket/interactions/x.md"],
            },
        ):
            out = augment_medicine_prompt_with_kb(
                "ロキソプロフェン ワーファリン 併用",
                "base",
                recommended_medicines=[{"ingredients": "ロキソプロフェン"}],
            )
    assert "CSV 参照" in out
    assert "出血リスク増加" in out


def test_sse_and_non_stream_share_kb_augment(monkeypatch):
    """answer_prompt と prompt_body の両方で augment が呼ばれること。"""
    monkeypatch.setenv("MEDICINE_RAG_PROVIDER", "bedrock_kb")
    monkeypatch.setenv("BEDROCK_MEDICINE_KB_ID", "MEDKB")

    calls = []

    def _fake_augment(query, base, **kwargs):
        calls.append(base[:40])
        return base + "\n\nKB_BLOCK"

    with patch(
        "src.services.bedrock_kb_retrieve.augment_medicine_prompt_with_kb",
        side_effect=_fake_augment,
    ), patch(
        "src.services.sse_emit.is_streaming_active",
        return_value=True,
    ), patch(
        "src.core.llm_client.chat_completion_stream",
        return_value="はい、食後が望ましいです。",
    ), patch(
        "src.core.medicine.medicine_response_builder._build_structured_qa_from_stream",
        return_value={"answer": "ok", "medicine_details": "", "interactions": "",
                    "doping_check": "", "side_effects": "", "consultation_advice": ""},
    ):
        from src.core.medicine.medicine_response_builder import chat_with_medicine_context

        chat_with_medicine_context(
            "食後に飲むべき？",
            [],
            [{"product_name": "カロナールA", "manufacturer": "第一三共"}],
            client=MagicMock(),
            session_id="web-test-session",
        )
    assert len(calls) == 2
    assert all("KB_BLOCK" not in c for c in calls)  # augment appends, records pre-augment base


def test_augment_reference_local_rag_appends_block(monkeypatch):
    """CONCIERGE_RAG_PROVIDER=local（既定）でも retrieve 結果を参照ブロックに追記する。"""
    monkeypatch.delenv("CONCIERGE_RAG_PROVIDER", raising=False)

    with patch(
        "src.services.bedrock_kb_retrieve.retrieve_concierge_context",
        return_value={
            "chunks": ["CodePipeline → CodeBuild → ECR → ECS"],
            "source_uris": ["docs/concierge/technical/01-cross-cloud-architecture.md"],
            "provider": "local_rag",
        },
    ):
        from src.services.bedrock_kb_retrieve import augment_reference_with_kb

        out = augment_reference_with_kb(
            "CodePipeline デプロイ", "LOCAL SSOT", intent="architecture"
        )
    assert "LOCAL SSOT" in out
    assert "ローカルナレッジ参照" in out
    assert "CodePipeline" in out


def test_augment_reference_empty_local_returns_base(monkeypatch):
    monkeypatch.delenv("CONCIERGE_RAG_PROVIDER", raising=False)

    with patch(
        "src.services.bedrock_kb_retrieve.retrieve_concierge_context",
        return_value={"chunks": [], "source_uris": [], "provider": "local_rag"},
    ):
        from src.services.bedrock_kb_retrieve import augment_reference_with_kb

        out = augment_reference_with_kb("質問", "LOCAL ONLY", intent="architecture")
    assert out == "LOCAL ONLY"


def test_augment_reference_kb_off_returns_base(monkeypatch):
    monkeypatch.setenv("CONCIERGE_RAG_PROVIDER", "none")

    from src.services.bedrock_kb_retrieve import augment_reference_with_kb

    out = augment_reference_with_kb("CodePipeline", "LOCAL SSOT", intent="architecture")
    assert out == "LOCAL SSOT"


def test_augment_reference_appends_kb_block(monkeypatch):
    monkeypatch.setenv("CONCIERGE_RAG_PROVIDER", "bedrock_kb")
    monkeypatch.setenv("BEDROCK_KB_ID", "CONKB")

    with patch(
        "src.services.bedrock_kb_retrieve.retrieve_concierge_context",
        return_value={
            "chunks": ["ECS Express Gateway デプロイ"],
            "source_uris": ["s3://bucket/ops/AWS_INFRA.md"],
        },
    ):
        from src.services.bedrock_kb_retrieve import augment_reference_with_kb

        out = augment_reference_with_kb(
            "CodePipeline デプロイ", "LOCAL SSOT", intent="architecture"
        )
    assert "LOCAL SSOT" in out
    assert "Bedrock Knowledge Base" in out
    assert "ECS Express Gateway" in out


def test_augment_reference_empty_retrieve_fallback(monkeypatch):
    monkeypatch.setenv("CONCIERGE_RAG_PROVIDER", "bedrock_kb")
    monkeypatch.setenv("BEDROCK_KB_ID", "CONKB")

    with patch(
        "src.services.bedrock_kb_retrieve.retrieve_concierge_context",
        return_value={"chunks": [], "source_uris": []},
    ):
        from src.services.bedrock_kb_retrieve import augment_reference_with_kb

        out = augment_reference_with_kb("質問", "LOCAL ONLY", intent="architecture")
    assert out == "LOCAL ONLY"


def test_build_concierge_retrieval_query_architecture():
    from src.services.bedrock_kb_retrieve import build_concierge_retrieval_query

    q = build_concierge_retrieval_query("CodePipeline", "architecture")
    assert "CodePipeline" in q
    assert "ECS" in q or "CodePipeline" in q
    assert "インフラ" in q or "デプロイ" in q


def test_augment_reference_capabilities_uses_top_k_2(monkeypatch):
    monkeypatch.setenv("CONCIERGE_RAG_PROVIDER", "bedrock_kb")
    monkeypatch.setenv("BEDROCK_KB_ID", "CONKB")

    with patch(
        "src.services.bedrock_kb_retrieve.retrieve_concierge_context",
        return_value={"chunks": ["機能一覧"], "source_uris": []},
    ) as mock_retrieve:
        from src.services.bedrock_kb_retrieve import augment_reference_with_kb

        augment_reference_with_kb("できること", "base", intent="capabilities")
    assert mock_retrieve.call_args.kwargs["top_k"] == 2
