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


def format_public_runtime_reference_block() -> str:
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
        use_bedrock_kb_rag,
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
        if use_bedrock_kb_rag():
            lines.append("- Concierge ナレッジ検索: Bedrock KB 設定済み（全文同期は準備中の場合あり）")
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
        else:
            lines.append("- 読み上げ: Web Speech API（ブラウザ）")

    img = get_medicine_image_cdn_base()
    if img:
        lines.append(f"- 医薬品画像 CDN: {img.rstrip('/')}/")

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
    block = format_public_runtime_reference_block()
    if not block:
        return base
    return f"{base.rstrip()}\n\n{block}"
