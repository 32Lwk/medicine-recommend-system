"""
カウンセリング的返信モジュール
感情的症状に対するカウンセリング的返信とフォローアップ質問を生成
"""

import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional
from openai import OpenAI

# キーワードリストのインポート
try:
    from config.keywords import (
        SEVERE_DISEASE_KEYWORDS,
        SYMPTOM_KEYWORDS,
        TREATMENT_KEYWORDS,
        MEDICAL_PREVENTION_KEYWORDS
    )
except ImportError:
    # フォールバック（開発環境などでconfig/keywords.pyが存在しない場合）
    SEVERE_DISEASE_KEYWORDS = {}
    SYMPTOM_KEYWORDS = []
    TREATMENT_KEYWORDS = []
    MEDICAL_PREVENTION_KEYWORDS = []
    logging.warning("config/keywords.pyが見つかりません。キーワードリストを使用できません。")

# normalize_text関数のインポート
try:
    from src.core.scoring_utils import normalize_text
except ImportError:
    # フォールバック
    def normalize_text(text: str) -> str:
        if not text or not isinstance(text, str):
            return ""
        return text.lower().strip()

# トリアージ判定（counseling_triage から re-export）
from src.services.counseling_triage import (
    is_treatment_mention,
    has_specific_symptom,
    is_severe_disease_request,
    is_medical_prevention_request,
    is_psychiatric_disease_request,
    detect_inappropriate_request,
    detect_emotional_symptom_type,
    detect_app_specification_question,
)

# フォローアップ質問（counseling_followup から re-export）
from src.services.counseling_followup import (
    generate_follow_up_questions,
    should_ask_question,
)
# 拒否テンプレート・ログは counseling サブモジュールに移管（re-export）
from src.services.counseling.counseling_templates import (
    ILLEGAL_DRUG_REJECTION_TEMPLATES,
    generate_illegal_drug_rejection_message,
)
from src.services.counseling.counseling_logger import log_counseling_response
from src.services.counseling.counseling_prompts import get_counseling_prompt_template
from src.services.counseling.counseling_generator import (
    generate_counseling_response,
    personalize_response,
)
from src.services.counseling.counseling_questions import (
    should_generate_question_non_medical,
    generate_supportive_question,
)
from src.services.counseling.counseling_satisfaction import analyze_user_satisfaction
from src.services.counseling.counseling_summary import generate_counseling_summary
from src.services.counseling.counseling_topic_shift import detect_topic_shift
from src.services.counseling.counseling_processor import process_counseling_answer
from src.services.counseling.counseling_mode_handler import (
    start_counseling_mode,
    format_conversation_history,
    handle_user_input_in_counseling_mode,
)

logger = logging.getLogger(__name__)

# 後方互換のための re-export 一覧（__all__ は省略可。必要なら追加）
__all__ = [
    "normalize_text",
    "is_treatment_mention",
    "has_specific_symptom",
    "is_severe_disease_request",
    "is_medical_prevention_request",
    "is_psychiatric_disease_request",
    "detect_inappropriate_request",
    "detect_emotional_symptom_type",
    "detect_app_specification_question",
    "generate_follow_up_questions",
    "should_ask_question",
    "ILLEGAL_DRUG_REJECTION_TEMPLATES",
    "generate_illegal_drug_rejection_message",
    "log_counseling_response",
    "get_counseling_prompt_template",
    "generate_counseling_response",
    "personalize_response",
    "should_generate_question_non_medical",
    "generate_supportive_question",
    "analyze_user_satisfaction",
    "generate_counseling_summary",
    "detect_topic_shift",
    "process_counseling_answer",
    "start_counseling_mode",
    "format_conversation_history",
    "handle_user_input_in_counseling_mode",
]

