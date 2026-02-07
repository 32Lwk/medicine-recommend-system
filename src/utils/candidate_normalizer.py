"""
候補医薬品のキー正規化モジュール

CSV由来の候補（製品名・成分・効能効果など日本語キー）と
スコアリングロジック（product_name・ingredients・efficacyなど英語キー）の
整合を取るための正規化を行う。単一責務で、キー名のマッピングのみを担当する。
"""

from typing import Dict

# 日本語キー → 英語キーのマッピング（スコアリングで参照されるキー名）
_JA_TO_EN_KEYS = (
    ("製品名", "product_name"),
    ("成分", "ingredients"),
    ("効能効果", "efficacy"),
    ("効能", "efficacy"),
    ("分類", "classification"),
    ("メーカー名", "manufacturer"),
    ("医薬品の種類", "medicine_type"),
    ("用法用量", "usage"),
    ("用法", "usage"),
)


def normalize_candidate_for_scoring(candidate: Dict) -> None:
    """
    候補医薬品辞書に英語キーのエイリアスを追加する（in-place）。

    CSVのDataFrame.to_dict()やget_medicines_by_type()などで
    日本語キー（製品名、成分、効能効果など）のみを持つ候補に対して、
    スコアリングロジックが期待する英語キー（product_name, ingredients, efficacyなど）
    を追加する。既に英語キーが存在する場合は上書きしない。

    Args:
        candidate: 候補医薬品の辞書（in-placeで更新される）
    """
    if not candidate or not isinstance(candidate, dict):
        return
    for ja_key, en_key in _JA_TO_EN_KEYS:
        if ja_key in candidate:
            existing = candidate.get(en_key)
            # 英語キーが無い、または空文字の場合のみコピー
            if existing is None or (isinstance(existing, str) and not existing.strip()):
                val = candidate.get(ja_key)
                if val is not None:
                    candidate[en_key] = val
