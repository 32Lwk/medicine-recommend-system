"""Concierge 技術 RAG / SSOT 参照の共有ドキュメント一覧（local_rag / S3 sync / prompt 注入）。"""
from __future__ import annotations

from typing import Tuple

# local_rag_index._concierge_docs_raw と sync-concierge-kb-to-s3.sh / concierge_tech_reference で共用
CONCIERGE_OPS_DOCS: Tuple[str, ...] = (
    "docs/ops/AWS_FEATURES_ROLLOUT.md",
    "docs/ops/AWS_INFRA.md",
    "docs/ops/AWS_CODEPIPELINE.md",
    "docs/ops/CLOUDFLARE_R2_IMAGES.md",
    "docs/ops/AWS_BEDROCK_KB.md",
    "docs/ops/AWS_STAGING_CHECKLIST.md",
    "docs/ops/LOCAL_RAG.md",
    "docs/ops/GCP_RAG_MIGRATION_ADR.md",
    "docs/ops/CLOUD_RUN_LLM_ENV.md",
    "docs/ops/CAPACITY_PLANNING.md",
    "docs/ops/AWS_LOG_ANALYSIS.md",
    "docs/ops/GITLAB_TEMPORARY_MIGRATION.md",
)

CONCIERGE_DEV_DOCS: Tuple[str, ...] = (
    "docs/dev/CHAT_PIPELINE_V2.md",
    "docs/dev/MEDICINE_QA_ROUTING.md",
    "docs/dev/MEDICINE_BRAND_RESOLVE.md",
    "docs/dev/ARCHITECTURE_MULTI_AGENT.md",
    "docs/dev/FASTAPI_ARCHITECTURE.md",
    "docs/dev/ROUTE_SPEC.md",
)
