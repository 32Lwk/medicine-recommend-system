"""
処理中バブル用: マルチエージェントフロー定義・文言プール・エージェントメタデータ
"""
from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Optional, Tuple

# flow_id -> このフローで進捗に使う step_id の順序（weight は表示順のみ）
FLOW_STEP_SEQUENCES: Dict[str, List[str]] = {
    "greeting": ["validate", "triage", "counseling", "finalize"],
    "other_counseling": ["validate", "triage", "store", "counseling", "finalize"],
    "emotional": ["validate", "triage", "counseling", "finalize"],
    "confidence_check": ["validate", "triage", "counseling", "finalize"],
    "store": ["validate", "triage", "store", "finalize"],
    "emergency": ["validate", "triage", "emergency", "finalize"],
    "physical": [
        "validate",
        "triage",
        "attributes",
        "symptom_analysis",
        "medicine_select",
        "safety",
        "usage_notes",
        "finalize",
    ],
    "ask_qa": ["validate", "triage", "medicine_qa", "finalize"],
    "ask_to_physical": ["validate", "triage", "attributes", "symptom_analysis", "medicine_select", "finalize"],
    "default": [
        "validate",
        "triage",
        "diagnosis",
        "emergency",
        "store",
        "counseling",
        "attributes",
        "symptom_analysis",
        "medicine_select",
        "safety",
        "usage_notes",
        "translate",
        "finalize",
    ],
}

FLOW_WEIGHTS: Dict[str, int] = {
    "validate": 6,
    "triage": 10,
    "diagnosis": 6,
    "emergency": 12,
    "dialect": 5,
    "store": 8,
    "counseling": 12,
    "attributes": 9,
    "symptom_analysis": 14,
    "medicine_select": 16,
    "medicine_qa": 14,
    "safety": 10,
    "usage_notes": 11,
    "translate": 7,
    "finalize": 5,
}

AGENT_META: Dict[str, Dict[str, str]] = {
    "TriageAgent": {
        "role_ja": "トリアージ",
        "desc_ja": "Physical / Emotional / Ask / Other / Emergency に分類",
    },
    "SafetyGate": {
        "role_ja": "安全ゲート",
        "desc_ja": "診断名・不適切表現・緊急候補を決定的に確認",
    },
    "NLUAgent": {
        "role_ja": "NLU",
        "desc_ja": "症状・年齢・妊娠・併用薬など属性を抽出",
    },
    "PhysicalOrchestrator": {
        "role_ja": "症状推奨",
        "desc_ja": "ルールベース選定と LLM 説明を統合",
    },
    "ExplanationAgent": {
        "role_ja": "推奨理由",
        "desc_ja": "各医薬品の推奨理由を生成（SSE cards → explanations）",
    },
    "CounselingManager": {
        "role_ja": "カウンセリング",
        "desc_ja": "感情・不明要求・挨拶への共感的応答",
    },
    "StoreInquiryAgent": {
        "role_ja": "店舗案内",
        "desc_ja": "遺失物・営業時間・店内案内の判定と応答",
    },
    "EmergencyRouter": {
        "role_ja": "緊急ルーティング",
        "desc_ja": "医療緊急 / 店舗インシデント / クライシスを分岐",
    },
    "MedicineQAAgent": {
        "role_ja": "医薬品Q&A",
        "desc_ja": "推奨薬コンテキストで相互作用・ドーピング等を回答",
    },
    "ModerationAgent": {
        "role_ja": "モデレーション",
        "desc_ja": "境界クライシス・有害表現を検知",
    },
    "ChatOrchestrator": {
        "role_ja": "オーケストレータ",
        "desc_ja": "トリアージ結果に応じたエージェントへハンドオフ",
    },
}

# (flow_id, step_id) -> ラベル候補（大量パターン）
_LABEL_POOLS: Dict[Tuple[str, str], List[str]] = {}

def _pool(flow: str, step: str, *labels: str) -> None:
    _LABEL_POOLS[(flow, step)] = list(labels)


# --- greeting ---
_pool("greeting", "validate",
      "ご入力を確認しています", "メッセージの形式を確認しています", "入力内容を読み取っています",
      "送信内容を検証しています", "テキストを安全に受け取っています")
_pool("greeting", "triage",
      "挨拶かどうかを判定しています", "会話の意図を軽く分類しています", "トリアージ: 挨拶・雑談ルートを確認",
      "TriageAgent: 症状相談か挨拶かを切り分け", "入力が症状説明か社交辞令かを分析")
_pool("greeting", "counseling",
      "挨拶への返答を作成しています", "ようこそメッセージを準備しています", "CounselingManager: 導入の挨拶を生成",
      "窓口案内の文言を整えています", "次に伺う質問を組み立てています")
_pool("greeting", "finalize",
      "返答を表示用に整えています", "メッセージを仕上げています", "チャットへ反映しています")

# --- ask_qa ---
_pool("ask_qa", "validate",
      "質問内容を確認しています", "医薬品に関する質問かを確認", "入力を検証しています")
_pool("ask_qa", "triage",
      "質問モード（Ask）を確認しています", "TriageAgent: Ask カテゴリを確定", "医薬品Q&Aルートへ接続",
      "症状推奨ではなく Q&A 経路か判定", "ハンドオフ先: MedicineQAAgent")
_pool("ask_qa", "medicine_qa",
      "推奨医薬品の文脈を読み込んでいます", "MedicineQAAgent: 回答本文を生成", "相互作用・ドーピングを照合",
      "会話履歴と推奨薬リストを統合", "構造化回答（詳細・注意）を準備", "医薬品相談回答をストリーム配信",
      "質問に対する根拠付き回答を作成", "WADA 観点のドーピング確認を実施")
_pool("ask_qa", "finalize",
      "Q&Aカードを仕上げています", "フィードバック UI を付与", "回答をセッションに保存")

# --- physical ---
_pool("physical", "validate", "症状入力を確認", "入力テキストを検証", "ユーザー属性の前置確認")
_pool("physical", "triage", "Physical ルートを確定", "TriageAgent: 身体症状として分類", "推奨フローへハンドオフ")
_pool("physical", "attributes", "NLUAgent: 年齢・性別・妊娠を抽出", "症状と属性を整理", "ユーザー情報をマージ")
_pool("physical", "symptom_analysis", "症状パターンを詳細分析", "禁忌・併用の前提を確認", "スコアリング用特徴量を準備")
_pool("physical", "medicine_select", "最適な市販薬を選定", "ルールベース候補をランキング", "推奨カードを先行配信")
_pool("physical", "safety", "安全性・禁忌を最終確認", "年齢制限とリスク警告を付与", "妊娠・授乳の注意を確認")
_pool("physical", "usage_notes", "使用上の注意を生成", "服用方法の要点を整理", "薬剤師相談が必要か判定")
_pool("physical", "finalize", "推奨結果を仕上げ", "個別アドバイスを統合", "SSE 完了シグナルを送信")

# --- emotional ---
_pool("emotional", "validate", "お話の内容を確認", "入力を安全に受信")
_pool("emotional", "triage", "Emotional ルートを確定", "TriageAgent: 感情・心理症状を分類")
_pool("emotional", "counseling", "CounselingManager: 共感的返答を生成", "傾聴モードで整理", "フォローアップ質問を準備")
_pool("emotional", "finalize", "カウンセリング応答を保存")

# --- store ---
_pool("store", "validate", "店舗関連の質問か確認", "入力を検証")
_pool("store", "triage", "Other / 店舗案内ルートを確認", "TriageAgent: Other を評価")
_pool("store", "store", "StoreInquiryAgent: 遺失物・営業を判定", "店舗ナレッジを検索", "構造化 HTML を組み立て")
_pool("store", "finalize", "店舗案内を表示用に整形")

# --- emergency ---
_pool("emergency", "validate", "緊急キーワードをスキャン", "入力の危険度を一次確認")
_pool("emergency", "triage", "Emergency 候補を検出", "TriageAgent + SafetyGate: 緊急分類")
_pool("emergency", "emergency", "EmergencyRouter: サブタイプを確定", "119・受診・クライシス案内を選択", "手動キューへエスカレーション")
_pool("emergency", "finalize", "緊急応答を確定")

# --- other_counseling ---
_pool("other_counseling", "validate", "入力を確認", "メッセージを検証")
_pool("other_counseling", "triage", "意図が不明瞭か判定", "Other: 店舗以外の一般相談")
_pool("other_counseling", "store", "店舗案内でないことを確認", "StoreInquiryAgent: 非該当を確認")
_pool("other_counseling", "counseling", "CounselingManager: 窓口案内を生成", "症状の聞き取り文言を作成", "不明要求への丁寧な応答")
_pool("other_counseling", "finalize", "応答を保存")

# --- confidence_check ---
_pool("confidence_check", "validate", "確認質問の入力を検証")
_pool("confidence_check", "triage", "確信度が低いカテゴリを再確認", "TriageAgent: confidence < 0.7")
_pool("confidence_check", "counseling", "確認メッセージを生成", "追加情報をお願いする文案を作成")
_pool("confidence_check", "finalize", "確認応答を送信")

# default fallbacks per step (any flow)
_DEFAULT_STEP_POOLS: Dict[str, List[str]] = {
    "validate": [
        "入力を確認しています", "メッセージを検証しています", "送信内容をチェック",
        "テキストを解析する準備をしています", "安全チェックの前処理を実行",
    ],
    "triage": [
        "TriageAgent: カテゴリ分類中", "症状の種類を分析", "Physical / Ask / Other を判定",
        "マルチエージェント: トリアージ実行中", "ハンドオフ先エージェントを決定",
    ],
    "diagnosis": [
        "診断名・疾患キーワードを確認", "SafetyGate: 診断名検出", "表記ゆれを正規化",
    ],
    "medicine_qa": [
        "MedicineQAAgent: 医薬品質問に回答", "推奨薬コンテキストで Q&A 生成",
    ],
    "finalize": [
        "回答を仕上げています", "表示用に整形", "セッションへ反映",
    ],
}

STEP_DETAIL_AGENTS: Dict[str, Dict[str, Tuple[str, str]]] = {
    "emergency": {
        "crisis_language": ("EmergencyRouter", "クライシス言語 — 専門窓口案内"),
        "medical_self": ("EmergencyRouter", "医療緊急 — 119・受診を明示"),
        "store_incident": ("EmergencyRouter", "店舗インシデント — 店内対応"),
        "emergency_dispatch": ("EmergencyRouter", "緊急応答をディスパッチ"),
    },
    "medicine_select": {
        "explanation": ("ExplanationAgent", "各薬の推奨理由をストリーム"),
    },
    "attributes": {
        "nlu": ("NLUAgent", "症状・属性の抽出"),
    },
}

_CATEGORY_TO_FLOW: Dict[str, str] = {
    "Physical": "physical",
    "Emotional": "emotional",
    "Ask": "ask_qa",
    "Other": "other_counseling",
    "Emergency": "emergency",
}


def flow_for_triage_category(category: Optional[str], *, sub_flow: Optional[str] = None) -> str:
    if sub_flow:
        return sub_flow
    if category and category in _CATEGORY_TO_FLOW:
        return _CATEGORY_TO_FLOW[category]
    return "default"


def get_flow_steps(flow_id: str) -> List[str]:
    return FLOW_STEP_SEQUENCES.get(flow_id) or FLOW_STEP_SEQUENCES["default"]


def pick_label(
    flow_id: str,
    step_id: str,
    session_id: Optional[str],
    *,
    detail_code: Optional[str] = None,
) -> str:
    pool = _LABEL_POOLS.get((flow_id, step_id)) or _DEFAULT_STEP_POOLS.get(step_id) or ["処理中..."]
    key = f"{session_id or ''}:{flow_id}:{step_id}:{detail_code or ''}:{len(pool)}"
    idx = int(hashlib.sha256(key.encode()).hexdigest(), 16) % len(pool)
    return pool[idx]


def agent_detail_for_step(
    step_id: str,
    detail_code: Optional[str],
    flow_id: str,
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Returns (agent_name, agent_role_ja, flow_hint_ja)"""
    if detail_code and step_id in STEP_DETAIL_AGENTS:
        block = STEP_DETAIL_AGENTS[step_id].get(detail_code)
        if block:
            name, hint = block
            meta = AGENT_META.get(name, {})
            return name, meta.get("role_ja"), hint

    flow_agent_map = {
        "greeting": ("CounselingManager", "挨拶・導入"),
        "ask_qa": ("MedicineQAAgent", "医薬品 Q&A"),
        "physical": ("PhysicalOrchestrator", "症状に基づく推奨"),
        "emotional": ("CounselingManager", "感情・心理ケア"),
        "store": ("StoreInquiryAgent", "店舗・遺失物"),
        "emergency": ("EmergencyRouter", "緊急対応"),
        "other_counseling": ("CounselingManager", "一般窓口案内"),
        "confidence_check": ("TriageAgent", "低確信度の再確認"),
    }
    if step_id == "triage":
        return "TriageAgent", AGENT_META["TriageAgent"]["role_ja"], "カテゴリ分類とハンドオフ"
    if step_id == "validate":
        return "ChatOrchestrator", AGENT_META["ChatOrchestrator"]["role_ja"], "リクエスト受付"
    if flow_id in flow_agent_map:
        name, hint = flow_agent_map[flow_id]
        return name, AGENT_META.get(name, {}).get("role_ja"), hint
    return "ChatOrchestrator", AGENT_META["ChatOrchestrator"]["role_ja"], flow_id


def flow_description_ja(flow_id: str) -> str:
    desc = {
        "greeting": "挨拶 → 窓口案内（推奨なし）",
        "ask_qa": "Ask → MedicineQAAgent（chat-response 形式）",
        "physical": "Physical → NLU → 選定 → cards/SSE → 使用注意",
        "emotional": "Emotional → CounselingManager",
        "store": "Other → StoreInquiryAgent",
        "emergency": "Emergency → EmergencyRouter → 確定応答",
        "other_counseling": "Other（非店舗）→ CounselingManager",
        "confidence_check": "低 confidence → 確認質問",
        "default": "標準マルチエージェント経路",
    }
    return desc.get(flow_id, flow_id)


def compute_progress(flow_id: str, step_id: str) -> Tuple[int, int, int]:
    """Returns (step_index_1based, total_steps, percent)"""
    steps = get_flow_steps(flow_id)
    if step_id not in steps:
        # unknown step: use default catalog position
        steps = FLOW_STEP_SEQUENCES["default"]
    try:
        idx = steps.index(step_id)
    except ValueError:
        idx = 0
    total = len(steps)
    weight_sum = sum(FLOW_WEIGHTS.get(s, 5) for s in steps)
    reached = sum(FLOW_WEIGHTS.get(s, 5) for s in steps[: idx + 1])
    percent = min(100, int(round(100 * reached / max(weight_sum, 1))))
    return idx + 1, total, percent
