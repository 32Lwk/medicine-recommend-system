"""Shared error copy for Sage diagnosis v1 and legacy HTML formatters."""
from __future__ import annotations

from typing import Any

ERROR_MESSAGES: dict[str, dict[str, Any]] = {
    "no_candidates": {
        "title": "医薬品が見つかりませんでした",
        "main_message": "入力された症状に対して、適切な市販薬が見つかりませんでした。",
        "recommendations": [
            "症状をより具体的に記述してください（例：痛みの部位、程度、継続期間など）",
            "症状が1週間以上続いている場合は、医療機関を受診することをお勧めします",
            "重症の症状がある場合は、速やかに医師の診察を受けてください",
        ],
    },
    "rule_based_error": {
        "title": "推奨システムエラー",
        "main_message": "症状の解析中にエラーが発生しました。",
        "recommendations": [
            "症状を別の表現で入力し直してください",
            "具体的な症状名（例：頭痛、発熱、のどの痛みなど）を含めて記述してください",
            "症状が続く場合は、医療機関を受診することをお勧めします",
        ],
    },
    "missing_critical_info": {
        "title": "症状が検出されませんでした",
        "main_message": "入力されたテキストから症状を検出できませんでした。",
        "recommendations": [
            "具体的な症状名を含めて記述してください（例：「頭が痛い」「熱がある」など）",
            "症状の部位や程度も記述すると、より適切な推奨が可能です",
            "症状が続く場合は、医療機関を受診することをお勧めします",
        ],
    },
    "unknown_error": {
        "title": "システムエラー",
        "main_message": "推奨システムでエラーが発生しました。",
        "recommendations": [
            "症状を再度入力してください",
            "症状が続く場合は、医療機関を受診することをお勧めします",
            "問題が解決しない場合は、薬剤師または登録販売者にご相談ください",
        ],
    },
}

MEDICAL_ADVICE_ITEMS: list[str] = [
    "症状が1週間以上続いている場合",
    "症状が悪化している場合",
    "高熱（38.5度以上）が続く場合",
    "重症の症状がある場合（激しい痛み、呼吸困難、意識障害など）",
    "妊娠中・授乳中の場合",
    "7歳未満のお子様の場合",
]
