"""
構造化ログモジュール
app.logとJSONLファイルの両方に構造化ログを出力する機能を提供
"""

import atexit
import json
import os
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)

# counseling_detail の JSONL 書き込みのみ別スレッド（stdout/GCP は同期 — Cloud Run で応答返却後にワーカーが落ちると非同期 emit が欠落する）
_detail_log_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="detail_log")
atexit.register(lambda: _detail_log_executor.shutdown(wait=False, cancel_futures=False))

# ログディレクトリのパス
from src import PROJECT_ROOT
LOG_DIR = os.path.join(PROJECT_ROOT, 'log')
os.makedirs(LOG_DIR, exist_ok=True)


def _write_to_jsonl(log_file: str, data: Dict) -> None:
    """
    JSONLファイルにデータを書き込む
    
    Args:
        log_file: ログファイル名（log/ディレクトリ内）
        data: 書き込むデータ
    """
    try:
        log_path = os.path.join(LOG_DIR, log_file)
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(data, ensure_ascii=False) + '\n')
    except Exception as e:
        logger.error(f"JSONLログ書き込みエラー ({log_file}): {e}")


def _write_to_app_log(level: str, message: str, data: Dict) -> None:
    """
    app.logに構造化ログを書き込む
    
    Args:
        level: ログレベル（INFO, ERROR等）
        message: ログメッセージ
        data: ログデータ（JSON形式で出力）
    """
    try:
        # Cloud Logging は改行ごとに別エントリになるため、1 行 compact JSON にする。
        # 解析側 gcp_cloud_run_log_parser も multiline 再構成に対応しているが、
        # 出力を 1 行にすることで conversation_history 等のネスト分割を根本回避する。
        log_data_str = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        log_message = f"[{level}] {message}\n{log_data_str}"
        
        if level == 'ERROR':
            logger.error(log_message)
        elif level == 'WARNING':
            logger.warning(log_message)
        else:
            logger.info(log_message)
    except Exception as e:
        logger.error(f"app.log書き込みエラー: {e}")


def log_recommendation_detail(
    session_id: str,
    user_input: str,
    app_output: str,
    nlu_result: Dict,
    candidate_counts: Dict,  # {"initial": int, "after_scoring": int, "after_filtering": int}
    recommended_medicines: List[Dict],  # 各医薬品に全スコアを含む
    translated_output: Optional[str] = None,
    diagnosis_snapshot: Optional[Dict] = None,
    display_summary: Optional[str] = None,
) -> None:
    """
    医薬品推奨の詳細ログを記録
    
    Args:
        session_id: セッションID
        user_input: ユーザー入力
        app_output: アプリケーション出力
        nlu_result: NLU解析結果
        candidate_counts: 各段階の候補数
        recommended_medicines: 推奨医薬品リスト（全スコアを含む）
        translated_output: 翻訳後のテキスト（オプション）
    """
    timestamp = datetime.now().isoformat()
    
    log_data = {
        "log_type": "recommendation_detail",
        "timestamp": timestamp,
        "session_id": session_id,
        "user_input": user_input,
        "app_output": app_output,
        "nlu_result": nlu_result,
        "candidate_counts": candidate_counts,
        "recommended_medicines": recommended_medicines,
        "translated_output": translated_output,
    }
    if diagnosis_snapshot is not None:
        log_data["diagnosis_snapshot"] = diagnosis_snapshot
    if display_summary is not None:
        log_data["display_summary"] = display_summary
    
    # JSONLファイルに出力
    _write_to_jsonl("recommendation_detail_log.jsonl", log_data)
    
    # app.logに出力
    _write_to_app_log("INFO", f"医薬品推奨詳細ログ [session_id: {session_id}]", log_data)


def log_counseling_detail(
    session_id: str,
    user_input: str,
    response: str,
    conversation_history: Optional[List[Dict]] = None,
    *,
    async_log: bool = True,
    routing_meta: Optional[Dict[str, Any]] = None,
) -> None:
    """
    カウンセリングの詳細ログを記録
    
    Args:
        session_id: セッションID
        user_input: ユーザー入力
        response: システムの返信
        conversation_history: 会話履歴（最新N件、オプショナル）
        async_log: True なら別スレッドで書き込み（既定・応答遅延なし）
    """
    timestamp = datetime.now().isoformat()
    history = list(conversation_history) if conversation_history is not None else []
    payload = {
        "log_type": "counseling_detail",
        "timestamp": timestamp,
        "session_id": session_id,
        "user_input": user_input,
        "response": response,
        "conversation_history": history,
    }
    if routing_meta:
        for key, val in routing_meta.items():
            if val is not None:
                payload[key] = val

    session_id = payload.get("session_id", "")
    try:
        # GCP Cloud Logging は stdout 経由のため、HTTP 応答前に同期で出す。
        _write_to_app_log(
            "INFO",
            f"カウンセリング詳細ログ [session_id: {session_id}]",
            payload,
        )
    except Exception as exc:
        logger.error("counseling_detail app.log 書き込みエラー: %s", exc)
        raise

    if async_log:
        _detail_log_executor.submit(
            _write_counseling_detail_jsonl,
            payload,
        )
        return
    _write_counseling_detail_jsonl(payload)


def _write_counseling_detail_jsonl(log_data: Dict[str, Any]) -> None:
    """counseling_detail を JSONL に書き込む（ワーカースレッド可）。"""
    try:
        _write_to_jsonl("counseling_detail_log.jsonl", log_data)
    except Exception as exc:
        logger.error("counseling_detail JSONL 書き込みエラー: %s", exc)


def log_medicine_question_detail(
    session_id: str,
    user_input: str,
    response: str
) -> None:
    """
    医薬品質疑応答の詳細ログを記録
    
    Args:
        session_id: セッションID
        user_input: ユーザーの質問
        response: システムの回答
    """
    timestamp = datetime.now().isoformat()
    
    log_data = {
        "log_type": "medicine_question_detail",
        "timestamp": timestamp,
        "session_id": session_id,
        "user_input": user_input,
        "response": response
    }
    
    # JSONLファイルに出力
    _write_to_jsonl("medicine_question_detail_log.jsonl", log_data)
    
    # app.logに出力
    _write_to_app_log("INFO", f"医薬品質疑応答詳細ログ [session_id: {session_id}]", log_data)


def log_translation_detail(
    session_id: str,
    original_text: str,
    translated_text: str,
    target_language: str
) -> None:
    """
    翻訳の詳細ログを記録
    
    Args:
        session_id: セッションID
        original_text: 翻訳前のテキスト
        translated_text: 翻訳後のテキスト
        target_language: 翻訳先言語
    """
    timestamp = datetime.now().isoformat()
    
    log_data = {
        "log_type": "translation_detail",
        "timestamp": timestamp,
        "session_id": session_id,
        "original_text": original_text,
        "translated_text": translated_text,
        "target_language": target_language
    }
    
    # JSONLファイルに出力
    _write_to_jsonl("translation_detail_log.jsonl", log_data)
    
    # app.logに出力
    _write_to_app_log("INFO", f"翻訳詳細ログ [session_id: {session_id}, language: {target_language}]", log_data)


def log_error_detail(
    session_id: Optional[str],
    error_type: str,
    error_message: str,
    stack_trace: str,
    user_input: Optional[str],
    system_state: Dict,
    user_display_message: str,
    conversation_history: Optional[List[Dict]] = None
) -> None:
    """
    エラーの詳細ログを記録
    
    Args:
        session_id: セッションID（オプション）
        error_type: エラータイプ
        error_message: エラーメッセージ
        stack_trace: スタックトレース
        user_input: エラー発生時のユーザー入力
        system_state: エラー発生時のシステム状態
        user_display_message: ユーザーに表示されたメッセージ
        conversation_history: 会話履歴（最新N件、オプショナル。エラー時のみ記録）
    """
    timestamp = datetime.now().isoformat()
    
    log_data = {
        "log_type": "error_detail",
        "timestamp": timestamp,
        "session_id": session_id,
        "error_type": error_type,
        "error_message": error_message,
        "stack_trace": stack_trace,
        "user_input": user_input,
        "system_state": system_state,
        "user_display_message": user_display_message
    }
    
    # 会話履歴がある場合のみ追加
    if conversation_history is not None:
        log_data["conversation_history"] = conversation_history
    
    # JSONLファイルに出力
    _write_to_jsonl("error_detail_log.jsonl", log_data)
    
    # app.logに出力
    session_str = f"[session_id: {session_id}]" if session_id else "[session_id: unknown]"
    _write_to_app_log("ERROR", f"エラー詳細ログ {session_str} [type: {error_type}]", log_data)


def log_user_interaction(
    session_id: str,
    user_input: str,
    app_output: str
) -> None:
    """
    ユーザーインタラクションの基本ログを記録
    
    Args:
        session_id: セッションID
        user_input: ユーザー入力
        app_output: アプリケーション出力
    """
    timestamp = datetime.now().isoformat()
    
    log_data = {
        "log_type": "user_interaction",
        "timestamp": timestamp,
        "session_id": session_id,
        "user_input": user_input,
        "app_output": app_output
    }
    
    # JSONLファイルに出力
    _write_to_jsonl("user_interaction_log.jsonl", log_data)
    
    # app.logに出力（簡潔に）
    logger.info(f"ユーザーインタラクション [session_id: {session_id}]: 入力={user_input[:100]}..., 出力長={len(app_output)}文字")

