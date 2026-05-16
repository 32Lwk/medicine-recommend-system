"""
処理中バブル用: ユーザー向け進捗文言（簡潔・非技術・約50分類）
"""
from __future__ import annotations

import hashlib
from typing import Dict, List, Optional, Tuple

# (flow_id, step_id, detail_code) -> 固定1文言（サブフェーズ）
_DETAIL_LABELS: Dict[Tuple[str, str, str], str] = {
    # --- ask_qa / medicine_qa ---
    ("ask_qa", "medicine_qa", "context_load"): "これまでの推奨お薬を確認しています",
    ("ask_qa", "medicine_qa", "history_read"): "会話の流れを読み取っています",
    ("ask_qa", "medicine_qa", "question_parse"): "ご質問の要点を整理しています",
    ("ask_qa", "medicine_qa", "interaction_check"): "飲み合わせの注意を確認しています",
    ("ask_qa", "medicine_qa", "doping_check"): "競技・検査向けの注意を確認しています",
    ("ask_qa", "medicine_qa", "side_effect_check"): "副作用の情報を確認しています",
    ("ask_qa", "medicine_qa", "answer_draft"): "回答の下書きを作成しています",
    ("ask_qa", "medicine_qa", "answer_compose"): "わかりやすい回答文に整えています",
    ("ask_qa", "medicine_qa", "safety_review"): "安全面の注意を最終確認しています",
    ("ask_qa", "medicine_qa", "format_response"): "回答を見やすい形にまとめています",
    # --- physical / symptom_analysis ---
    ("physical", "symptom_analysis", "llm_classify"): "症状から市販薬の種類を判定しています",
    ("physical", "symptom_analysis", "symptom_extract"): "お話から症状のキーワードを拾っています",
    # --- physical / safety（禁忌は rule_based 内の安全性チェック時）---
    ("physical", "safety", "contra_check"): "年齢・妊娠・併用薬の安全性を確認しています",
    # --- physical / medicine_select ---
    ("physical", "medicine_select", "candidate_search"): "症状に合うお薬候補を探しています",
    ("physical", "medicine_select", "rule_match"): "症状に合うお薬候補を照合しています",
    ("physical", "medicine_select", "scoring"): "候補のお薬の適合度を評価しています",
    ("physical", "medicine_select", "ranking"): "おすすめ順に並べ替えています",
    ("physical", "medicine_select", "explanation"): "おすすめの理由を作成しています",
    ("physical", "medicine_select", "filter_contra"): "飲んではいけない組み合わせを除外しています",
    # --- physical / attributes ---
    ("physical", "attributes", "profile_register"): "お話から年齢・性別などを読み取っています",
    ("physical", "attributes", "nlu"): "症状とお客様情報を整理しています",
    # --- emergency ---
    ("emergency", "emergency", "crisis_language"): "専門の相談窓口をご案内する準備をしています",
    ("emergency", "emergency", "medical_self"): "緊急時の受診・連絡先を整理しています",
    ("emergency", "emergency", "store_incident"): "店内での対応方法を整理しています",
    ("emergency", "emergency", "emergency_dispatch"): "緊急時のご案内文を準備しています",
}

# (flow_id, step_id) -> ローテーション用プール（detail なし時・待機中）
_STEP_POOLS: Dict[Tuple[str, str], List[str]] = {
    ("ask_qa", "validate"): [
        "ご入力を確認しています",
        "質問文を読み取っています",
        "送信内容をチェックしています",
    ],
    ("ask_qa", "triage"): [
        "医薬品の質問かどうかを見分けています",
        "相談の種類を確認しています",
        "質問モードへ切り替えています",
    ],
    ("ask_qa", "medicine_qa"): [
        "推奨したお薬の情報を確認しています",
        "ご質問に答える準備をしています",
        "お薬の説明を組み立てています",
        "注意点をまとめています",
        "回答を作成しています",
    ],
    ("ask_qa", "finalize"): [
        "回答を仕上げています",
        "表示用に整えています",
    ],
    ("physical", "validate"): [
        "症状の入力を確認しています",
        "お話の内容を読み取っています",
    ],
    ("physical", "triage"): [
        "症状相談として受け付けています",
        "お体の不調についての相談と判断しています",
    ],
    ("physical", "attributes"): [
        "お客様の情報を確認しています",
        "年齢・性別の情報を整理しています",
        "アレルギーや併用薬を確認しています",
    ],
    ("physical", "symptom_analysis"): [
        "症状の内容を読み取っています",
        "該当しそうな市販薬の種類を探しています",
    ],
    ("physical", "medicine_select"): [
        "候補のお薬を比較しています",
        "症状への合致度を見ています",
        "おすすめのお薬を選んでいます",
    ],
    ("physical", "safety"): [
        "飲み合わせの注意を確認しています",
        "年齢に合った用量を確認しています",
        "妊娠・授乳中の注意を確認しています",
    ],
    ("physical", "usage_notes"): [
        "飲み方・用法を整理しています",
        "使用上の注意を作成しています",
    ],
    ("physical", "finalize"): [
        "推奨結果をまとめています",
        "回答を仕上げています",
    ],
    ("greeting", "validate"): ["ご入力を確認しています", "メッセージを受け取りました"],
    ("greeting", "triage"): ["挨拶かどうかを確認しています"],
    ("greeting", "counseling"): ["ご挨拶への返答を準備しています"],
    ("greeting", "finalize"): ["返答を表示用に整えています"],
    ("concierge", "concierge"): ["ご案内の文面を準備しています", "できることを整理しています"],
    ("emotional", "counseling"): ["お話に寄り添う返答を考えています"],
    ("store", "store"): ["店舗に関するご質問を確認しています"],
    ("emergency", "emergency"): ["緊急度を確認しています", "必要なご案内を準備しています"],
}

# step_id のみ（flow 不明時フォールバック）
_DEFAULT_STEP_POOLS: Dict[str, List[str]] = {
    "validate": ["ご入力を確認しています", "メッセージを読み取っています"],
    "triage": ["相談の種類を確認しています", "内容を分類しています"],
    "medicine_qa": ["医薬品のご質問に答える準備をしています", "お薬の情報を確認しています"],
    "symptom_analysis": ["症状を読み取っています", "市販薬の種類を探しています"],
    "medicine_select": ["おすすめのお薬を選んでいます", "候補を比較しています"],
    "safety": ["安全性を確認しています"],
    "usage_notes": ["使用上の注意を作成しています"],
    "finalize": ["回答を仕上げています"],
}


def all_user_label_count() -> int:
    """登録済みユーザー向け文言の種類数（テスト用）"""
    return len(_DETAIL_LABELS) + sum(len(v) for v in _STEP_POOLS.values()) + sum(
        len(v) for v in _DEFAULT_STEP_POOLS.values()
    )


def get_user_label(
    flow_id: str,
    step_id: str,
    session_id: Optional[str],
    *,
    detail_code: Optional[str] = None,
) -> str:
    dc = (detail_code or "").strip()
    if dc:
        fixed = _DETAIL_LABELS.get((flow_id, step_id, dc))
        if fixed:
            return fixed
        fixed = _DETAIL_LABELS.get(("", step_id, dc))
        if fixed:
            return fixed

    pool = _STEP_POOLS.get((flow_id, step_id))
    if not pool:
        pool = _DEFAULT_STEP_POOLS.get(step_id)
    if not pool:
        pool = ["処理中..."]

    key = f"{session_id or ''}:{flow_id}:{step_id}:{dc}:{len(pool)}"
    idx = int(hashlib.sha256(key.encode()).hexdigest(), 16) % len(pool)
    return pool[idx]
