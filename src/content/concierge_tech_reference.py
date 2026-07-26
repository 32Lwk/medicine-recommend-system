"""Concierge 技術 FAQ 用ローカル参照（Bedrock KB 不要・GCP/AWS 共通）。"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import List, Optional, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[2]
_TECH_DIR = _REPO_ROOT / "docs" / "concierge" / "technical"
_OPS_DOCS = (
    "docs/ops/AWS_FEATURES_ROLLOUT.md",
    "docs/ops/AWS_INFRA.md",
    "docs/ops/AWS_CODEPIPELINE.md",
    "docs/ops/CLOUDFLARE_R2_IMAGES.md",
    "docs/ops/AWS_BEDROCK_KB.md",
    "docs/ops/AWS_STAGING_CHECKLIST.md",
    "docs/ops/LOCAL_RAG.md",
    "docs/ops/GCP_RAG_MIGRATION_ADR.md",
    "docs/ops/CLOUD_RUN_LLM_ENV.md",
)

# 運用事実が必要な質問（クラウド比較・デプロイ・RAG 等）— deep でなくても ops を渡す
_OPS_GROUNDED_RE = re.compile(
    r"aws|gcp|cloud\s*run|ecs|fargate|codepipeline|codebuild|bedrock|"
    r"cloudfront|translate|polly|elastica?che|neon|r2|s3|"
    r"ステージング|staging|本番|prod|デプロイ|インフラ|クロスクラウド|"
    r"ローカル\s*rag|local\s*rag|knowledge\s*base|kb|"
    r"アーキテクチャ|architecture|マルチ[\s　\-]*エージェント",
    re.I,
)

_DEEP_DIVE_RE = re.compile(
    r"詳しく|もっと|深く|具体的|技術的|アーキテクチャ|インフラ|構成|デプロイ|"
    r"クロスクラウド|cross[\s-]?cloud|CodePipeline|CodeBuild|ECS|Bedrock|"
    r"CloudFront|Cloud\s*Run|Neon|Translate|Polly|R2|"
    r"AWS|GCP|ステージング|staging|"
    r"どうやって(動|構築|デプロイ)|仕組みを(教|説)|運用(構成|方法)",
    re.I,
)

_STRIP_NOISE_RE = re.compile(r"^#+\s*", re.MULTILINE)


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


@lru_cache(maxsize=1)
def _load_technical_documents() -> Tuple[Tuple[str, str], ...]:
    docs: List[Tuple[str, str]] = []
    if _TECH_DIR.is_dir():
        for path in sorted(_TECH_DIR.glob("*.md")):
            body = _read_text(path)
            if body:
                docs.append((path.name, body))
    for rel in _OPS_DOCS:
        path = _REPO_ROOT / rel
        body = _read_text(path)
        if body:
            docs.append((Path(rel).name, body))
    return tuple(docs)


def wants_technical_deep_dive(
    user_text: str,
    history: Optional[List[dict]] = None,
) -> bool:
    """技術質問の深掘り（長文・多参照）が望ましいか。"""
    text = (user_text or "").strip()
    if not text:
        return False
    if _DEEP_DIVE_RE.search(text):
        return True
    if _OPS_GROUNDED_RE.search(text):
        return True
    from src.services.concierge_agent_history import is_meta_follow_up_utterance

    if not is_meta_follow_up_utterance(text):
        return False
    for msg in reversed(history or []):
        role = msg.get("type") or msg.get("role")
        if role == "bot":
            intent = msg.get("concierge_intent") or ""
            kind = ""
            diag = msg.get("diagnosis")
            if isinstance(diag, dict):
                kind = str(diag.get("kind") or "")
            if intent == "architecture" or "architecture" in kind:
                return True
            return False
        if role == "user":
            break
    return False


def wants_ops_grounding(user_text: str) -> bool:
    """運用ドキュメント（docs/ops）を参照根拠に含めるべきか。"""
    text = (user_text or "").strip()
    if not text:
        return False
    return bool(_OPS_GROUNDED_RE.search(text) or _DEEP_DIVE_RE.search(text))


def format_concierge_technical_reference_block(
    *,
    max_total_chars: int = 18_000,
    include_ops_docs: bool = True,
) -> str:
    """
    LLM プロンプト用の技術ドキュメント参照ブロック。
    Bedrock KB が空でも architecture 回答の根拠になる。
    """
    docs = list(_load_technical_documents())
    if not include_ops_docs:
        docs = [(name, body) for name, body in docs if not name.startswith("AWS_")]

    lines = [
        "【技術ドキュメント参照（docs/concierge/technical/ 等・唯一の根拠）】",
        "記載にない構成・サービス名は推測で補わない。",
        "【ユーザーの質問】の主題に答える。聞かれていない一般論から始めない。",
        "医薬品の症状相談には踏み込まない。",
        "開示: 公開情報は述べてよい。深い内容はユーザーが詳しく求めたときのみ。",
        "禁止: 環境変数名・「env/設定を参照した」等のメタ・Secrets/APIキー。",
        "事実は利用者向けの言葉で（例: Amazon Translate を利用、而非 env 名の列挙）。",
        "",
    ]
    used = sum(len(x) for x in lines)
    for name, body in docs:
        block = f"### {name}\n{body.strip()}\n"
        if used + len(block) > max_total_chars:
            lines.append(f"…（以降のドキュメントは省略: {name} 他）")
            break
        lines.append(block)
        used += len(block)
    if len(lines) <= 4:
        lines.append("（技術ドキュメントが未配置です）")
    return "\n".join(lines).strip()


def augment_architecture_reference(
    base_reference: str,
    *,
    deep: bool = False,
    user_text: str = "",
) -> str:
    """architecture 用参照にローカル技術ドキュメント・ランタイム情報を追記。

    運用事実が問われる発話では deep でなくても ops ドキュメントを含める
    （非 deep で AWS/GCP 差分を推測で答える事故を防ぐ）。
    """
    include_ops = True  # architecture は常に technical + ops SSOT で根拠付け
    tech = format_concierge_technical_reference_block(
        max_total_chars=24_000 if (deep or wants_ops_grounding(user_text)) else 16_000,
        include_ops_docs=include_ops,
    )
    parts = [base_reference.rstrip(), tech]
    if deep or include_ops:
        try:
            from src.content.changelog_digest import format_changelog_digest_block

            parts.append(
                format_changelog_digest_block(max_releases=3, max_total_chars=6_000)
            )
        except Exception:
            pass
    grounding = (
        "\n\n【回答の根拠ルール】\n"
        "- 上記ドキュメントとランタイム情報に無いサービス名・URL・構成は推測で補わない。\n"
        "- GCP 本番と AWS ステージングの役割分担はドキュメントの記載に従う。\n"
        "- 不明な点は「公開ドキュメントに記載がありません」と述べ、創作しない。\n"
    )
    parts.append(grounding)
    merged = "\n\n".join(p for p in parts if p)
    from src.content.concierge_runtime_reference import augment_with_runtime_reference

    return augment_with_runtime_reference(merged, user_text, deep=deep or include_ops)
