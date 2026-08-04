"""Concierge architecture — クロスクラウド回答の grounding ルール（環境非依存）。"""
from __future__ import annotations


def architecture_grounding_rule() -> str:
    """GCP 本番 / AWS ステージングの比較質問向け。全環境で同一。"""
    return (
        "\n\n【回答の根拠ルール】\n"
        "- 上記ドキュメントとランタイム情報に無いサービス名・URL・構成は推測で補わない。\n"
        "- GCP 本番と AWS ステージングの役割分担はドキュメントの記載に従う。\n"
        "- ユーザーが比較・違いを聞いている場合は、両環境の要点を最初の段落で答える。\n"
        "- 不明な点は「公開ドキュメントに記載がありません」と述べ、創作しない。\n"
    )


def cross_cloud_grounding_rule() -> str:
    """augment_architecture_reference 等から参照されるエイリアス。"""
    return architecture_grounding_rule()
