"""
トリアージ分析ログモジュール
トリアージ結果、confidenceスコア、話題転換スコアなどをログに保存し、改善ループを実現
"""

import json
import os
from datetime import datetime
from typing import Dict, Optional, List

def log_triage_result(
    session_id: str,
    user_input: str,
    triage_result: Dict,
    sanitized_input: Optional[str] = None,
    processing_time_ms: Optional[float] = None,
    user_action: Optional[str] = None  # "confirmed", "rejected", "continued"
) -> None:
    """
    トリアージ結果をログに保存
    
    Args:
        session_id: セッションID
        user_input: ユーザーの元の入力
        triage_result: トリアージ結果（category, confidence, subcategory, reasoning）
        sanitized_input: サニタイズ後の入力（オプション）
        processing_time_ms: 処理時間（ミリ秒、オプション）
        user_action: ユーザーのアクション（確認を求めた場合のユーザー応答、オプション）
    """
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "session_id": session_id,
        "user_input": user_input,
        "sanitized_input": sanitized_input or user_input,
        "triage_category": triage_result.get("category"),
        "triage_subcategory": triage_result.get("subcategory"),
        "confidence_score": triage_result.get("confidence"),
        "requires_immediate_action": triage_result.get("requires_immediate_action"),
        "reasoning": triage_result.get("reasoning"),
        "processing_time_ms": processing_time_ms,
        "user_action": user_action,  # 確認を求めた場合のユーザー応答
        "confidence_threshold": 0.7,  # 現在の閾値（設定値として保存）
        "emergency_threshold": 0.5,  # Emergencyカテゴリの閾値
    }
    
    # ログディレクトリの作成
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'log')
    os.makedirs(log_dir, exist_ok=True)
    
    # ログファイルに保存（JSONL形式）
    log_file = os.path.join(log_dir, 'triage_analytics.jsonl')
    try:
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"トリアージログ保存エラー: {e}")


def log_topic_shift_detection(
    session_id: str,
    user_input: str,
    topic_shift_result: Dict,
    current_counseling_topic: str,
    conversation_history_length: int,
    was_topic_shifted: bool
) -> None:
    """
    話題転換検知結果をログに保存
    
    Args:
        session_id: セッションID
        user_input: ユーザーの入力
        topic_shift_result: 話題転換検知結果（is_topic_shift, new_topic_category, relation_to_current_topic, confidence, reasoning）
        current_counseling_topic: 現在のカウンセリングトピック
        conversation_history_length: 会話履歴の長さ
        was_topic_shifted: 実際に話題転換が実行されたかどうか
    """
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "session_id": session_id,
        "user_input": user_input,
        "current_counseling_topic": current_counseling_topic,
        "conversation_history_length": conversation_history_length,
        "is_topic_shift": topic_shift_result.get("is_topic_shift"),
        "new_topic_category": topic_shift_result.get("new_topic_category"),
        "relation_to_current_topic": topic_shift_result.get("relation_to_current_topic"),
        "topic_shift_confidence": topic_shift_result.get("confidence"),
        "reasoning": topic_shift_result.get("reasoning"),
        "was_topic_shifted": was_topic_shifted,  # 実際に話題転換が実行されたか
        "relation_threshold": 0.3,  # 現在の閾値（設定値として保存）
        "relation_high_threshold": 0.5,  # 関連性が高いと判定する閾値
    }
    
    # ログディレクトリの作成
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'log')
    os.makedirs(log_dir, exist_ok=True)
    
    # ログファイルに保存（JSONL形式）
    log_file = os.path.join(log_dir, 'topic_shift_analytics.jsonl')
    try:
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"話題転換ログ保存エラー: {e}")


def log_confidence_check(
    session_id: str,
    user_input: str,
    triage_result: Dict,
    confidence_threshold: float,
    was_confirmation_requested: bool,
    user_response: Optional[str] = None
) -> None:
    """
    confidenceスコアチェックの結果をログに保存
    
    Args:
        session_id: セッションID
        user_input: ユーザーの入力
        triage_result: トリアージ結果
        confidence_threshold: 使用された閾値
        was_confirmation_requested: 確認が求められたかどうか
        user_response: ユーザーの応答（確認を求めた場合、オプション）
    """
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "session_id": session_id,
        "user_input": user_input,
        "triage_category": triage_result.get("category"),
        "confidence_score": triage_result.get("confidence"),
        "confidence_threshold": confidence_threshold,
        "was_confirmation_requested": was_confirmation_requested,
        "user_response": user_response,  # 確認を求めた場合のユーザー応答
        "was_below_threshold": triage_result.get("confidence", 1.0) < confidence_threshold,
    }
    
    # ログディレクトリの作成
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'log')
    os.makedirs(log_dir, exist_ok=True)
    
    # ログファイルに保存（JSONL形式）
    log_file = os.path.join(log_dir, 'confidence_analytics.jsonl')
    try:
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Confidenceログ保存エラー: {e}")


def log_counseling_completion(
    session_id: str,
    counseling_mode: Dict,
    completion_reason: str,
    total_questions: int,
    collected_info_count: int
) -> None:
    """
    カウンセリング完了時のログを保存
    
    Args:
        session_id: セッションID
        counseling_mode: カウンセリングモードの状態
        completion_reason: 完了理由（"normal", "crisis_detected", "no_progress"）
        total_questions: 総質問数
        collected_info_count: 収集できた情報の数
    """
    started_at = counseling_mode.get("started_at")
    duration_seconds = None
    if started_at:
        try:
            start_time = datetime.fromisoformat(started_at)
            duration_seconds = (datetime.now() - start_time).total_seconds()
        except (ValueError, TypeError):
            pass
    
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "session_id": session_id,
        "symptom_type": counseling_mode.get("symptom_type"),
        "completion_reason": completion_reason,
        "total_questions": total_questions,
        "collected_info_count": collected_info_count,
        "counseling_duration_seconds": duration_seconds,
        "started_at": started_at,
    }
    
    # ログディレクトリの作成
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'log')
    os.makedirs(log_dir, exist_ok=True)
    
    # ログファイルに保存（JSONL形式）
    log_file = os.path.join(log_dir, 'counseling_analytics.jsonl')
    try:
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"カウンセリング完了ログ保存エラー: {e}")

