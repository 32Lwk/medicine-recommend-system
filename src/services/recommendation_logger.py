"""
推奨セッションのロギングサービス

rule_based_recommendation から分離（SRP改善）
"""

import json
import logging
import os
from datetime import datetime
from typing import Dict, Optional

from src import PROJECT_ROOT

logger = logging.getLogger(__name__)
BASE_DIR = PROJECT_ROOT
_DEBUG_MODE = os.getenv('DEBUG_MODE', 'false').lower() == 'true'


def log_recommendation_session(
    user_text: str,
    user_info: Dict,
    result: Dict,
    session_id: Optional[str] = None,
    app_output: Optional[str] = None,
    log_file: str = "recommendation_log.jsonl"
):
    """
    推奨セッションをログに保存（監査用）
    """
    try:
        from src.utils.structured_logger import log_recommendation_detail
    except ImportError:
        logger.warning("structured_loggerがインポートできません。旧形式のログを出力します。")
        log_recommendation_detail = None

    if not session_id:
        import uuid
        session_id = str(uuid.uuid4())

    llm_meta = {}
    try:
        from src.services.llm_metrics import get_llm_summary
        llm_meta = get_llm_summary()
    except Exception:
        pass

    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "user_text": user_text,
        "user_info": user_info,
        "result": result,
        "llm_metrics": llm_meta,
    }

    log_dir = os.path.join(BASE_DIR, 'log')
    log_path = os.path.join(log_dir, "log", log_file)
    os.makedirs(os.path.dirname(log_path), exist_ok=True)

    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')

    if log_recommendation_detail:
        if not app_output:
            recommended_medicines = result.get('recommended_medicines', [])
            if recommended_medicines:
                medicine_names = [m.get('product_name', '') for m in recommended_medicines[:3]]
                app_output = f"推奨医薬品: {', '.join(medicine_names)}"
            else:
                app_output = f"推奨結果: {result.get('status', 'unknown')}"

        nlu_result = result.get('nlu_result', {})
        candidate_counts = result.get('candidate_counts', {
            "initial": 0,
            "after_scoring": 0,
            "after_filtering": 0
        })
        recommended_medicines = result.get('recommended_medicines', [])
        medicines_with_scores = []
        for medicine in recommended_medicines:
            medicine_detail = {
                "product_name": medicine.get('product_name', ''),
                "medicine_type": medicine.get('medicine_type', ''),
                "final_score": medicine.get('score', medicine.get('final_score')),
                "total_score": medicine.get('score', medicine.get('final_score')),
                "raw_score": medicine.get('raw_score'),
                "display_score": medicine.get('display_score'),
                "relative_score": medicine.get('relative_score'),
                "score_breakdown": medicine.get('score_breakdown', {}),
                "max_possible_score": medicine.get('max_possible_score'),
                "original_rank": medicine.get('original_rank')
            }
            medicines_with_scores.append(medicine_detail)
        translated_output = result.get('translated_output')
        log_recommendation_detail(
            session_id=session_id,
            user_input=user_text,
            app_output=app_output,
            nlu_result=nlu_result,
            candidate_counts=candidate_counts,
            recommended_medicines=medicines_with_scores,
            translated_output=translated_output
        )

    if _DEBUG_MODE or logger.level <= logging.DEBUG:
        logger.debug(f"ログ保存完了: {log_path}")
