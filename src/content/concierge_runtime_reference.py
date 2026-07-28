"""Concierge 向け公開ランタイム情報（プロンプト補助・env 名はユーザーに出さない）。"""
from __future__ import annotations

import os
import re
from typing import Optional

_RUNTIME_QUESTION_RE = re.compile(
    r"デプロイ|反映|ビルド|commit|コミット|バージョン|revision|"
    r"今の環境|現在の環境|いま動|今動|どの版|どのバージョン|"
    r"health|ヘルス|本番とステージング|ステージングと本番",
    re.I,
)


def wants_runtime_reference(user_text: str) -> bool:
    return bool(_RUNTIME_QUESTION_RE.search((user_text or "").strip()))


def format_public_runtime_reference_block(*, user_text: str = "") -> str:
    """
    プロセス内の公開情報のみ（/health 相当）。
    環境変数名・Secrets は列挙しない。
    """
    from config.aws_features import (
        get_medicine_image_cdn_base,
        get_static_cdn_base_url,
        get_translation_provider,
        get_tts_provider,
        is_aws_staging_site,
    )

    lines = [
        "【公開デプロイ情報（利用者向け事実。回答では env 名・参照方法に触れない）】",
    ]
    commit = (os.getenv("GIT_COMMIT") or "").strip()
    if commit:
        short = commit[:12]
        lines.append(f"- 反映ビルド（短縮）: {short}")

    site = (os.getenv("PUBLIC_SITE_URL") or "").strip().rstrip("/")
    if site:
        lines.append(f"- 公開 URL: {site}")

    if is_aws_staging_site():
        lines.append("- 環境: AWS ステージング（ECS Express Gateway）")
        if get_translation_provider() == "translate":
            lines.append("- 翻訳: Amazon Translate を利用")
        else:
            lines.append("- 翻訳: DeepL（レガシー設定）")
        if get_tts_provider() == "polly":
            lines.append("- 読み上げ: Amazon Polly を利用")
        elif get_tts_provider() == "google":
            lines.append("- 読み上げ: Google Cloud Text-to-Speech を利用")
        else:
            lines.append("- 読み上げ: Web Speech API（ブラウザ）")
        lines.append("- Concierge ナレッジ検索: Local RAG（BM25 + 埋め込み）")
        cdn = get_static_cdn_base_url()
        if cdn:
            lines.append(f"- static アセット CDN: {cdn}")
    else:
        lines.append("- 環境: GCP 本番またはローカル開発")
        lines.append("- ホスティング: Google Cloud Run（本番）")
        if get_translation_provider() == "translate":
            lines.append("- 翻訳: Amazon Translate を利用")
        else:
            lines.append("- 翻訳: DeepL を利用")
        if get_tts_provider() == "polly":
            lines.append("- 読み上げ: Amazon Polly を利用")
        elif get_tts_provider() == "google":
            lines.append("- 読み上げ: Google Cloud Text-to-Speech を利用（POST /api/tts）")
        else:
            lines.append("- 読み上げ: Web Speech API（ブラウザ）")

    img = get_medicine_image_cdn_base()
    if img:
        lines.append(f"- 医薬品画像 CDN: {img.rstrip('/')}/")

    ut = (user_text or "").strip()
    if re.search(r"/health/aws|health\s*/\s*aws", ut, re.I):
        lines.append(
            "- GET /health/aws — 翻訳・TTS・KB 等の利用有無（Secrets や env 変数名は含まない）"
        )
    if re.search(r"\b/health\b|ヘルス", ut, re.I):
        lines.append("- GET /health — 稼働状態と git_commit（短縮）")

    repo = os.getenv("GIT_REPO_URL") or "https://github.com/32Lwk/medicine-recommend-system"
    if repo.strip():
        lines.append(f"- ソース公開: {repo.strip().rstrip('/')}")

    return "\n".join(lines)


def augment_with_runtime_reference(
    base: str,
    user_text: str,
    *,
    deep: bool = False,
) -> str:
    if not deep and not wants_runtime_reference(user_text):
        return base
    block = format_public_runtime_reference_block(user_text=user_text)
    if not block:
        return base
    return f"{base.rstrip()}\n\n{block}"
