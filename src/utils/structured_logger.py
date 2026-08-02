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


def shutdown_detail_log_executor() -> None:
    _detail_log_executor.shutdown(wait=False, cancel_futures=True)


atexit.register(shutdown_detail_log_executor)

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


def emit_pipeline_perf(payload: Dict[str, Any]) -> None:
    """PIPELINE_PERF ペイロードを構造化 JSONL に永続化する（計測専用・非挙動）。

    `log_pipeline_perf` が既に app.log へ `PIPELINE_PERF ...` を出力しているが、
    ローカル/テストでは p50/p95 やフェーズ別（triage/説明/翻訳）内訳を機械的に
    集計できる JSONL sink が無かったため、それを補う。
    """
    try:
        log_data = {
            "log_type": "pipeline_perf",
            "timestamp": datetime.now().isoformat(),
            **payload,
        }
        _write_to_jsonl("pipeline_perf_log.jsonl", log_data)
    except Exception as exc:  # 計測失敗は本処理に影響させない
        logger.error("pipeline_perf JSONL 書き込みエラー: %s", exc)


def emit_dialogue_route_shadow(
    *,
    session_id: str,
    user_input: str,
    decision: Dict[str, Any],
    triage_category: Optional[str] = None,
    triage_subcategory: Optional[str] = None,
    mismatch: bool = False,
    mismatch_kind: Optional[str] = None,
    dialogue_flags: Optional[Dict[str, bool]] = None,
) -> None:
    """IntentRouter shadow 観測ログ（Wave 1b）。"""
    timestamp = datetime.now().isoformat()
    log_data: Dict[str, Any] = {
        "log_type": "dialogue_route_shadow",
        "timestamp": timestamp,
        "session_id": session_id,
        "user_input": user_input,
        "mismatch": mismatch,
        "primary_route": decision.get("primary_route"),
        "sub_route": decision.get("sub_route"),
        "resolved_by": decision.get("resolved_by"),
        "confidence": decision.get("confidence"),
        "source": decision.get("source"),
    }
    if triage_category is not None:
        log_data["triage_category"] = triage_category
    if triage_subcategory is not None:
        log_data["triage_subcategory"] = triage_subcategory
    if mismatch_kind:
        log_data["mismatch_kind"] = mismatch_kind
    if dialogue_flags:
        log_data["dialogue_flags"] = dialogue_flags

    _write_to_jsonl("dialogue_route_shadow_log.jsonl", log_data)
    level = "WARNING" if mismatch else "INFO"
    _write_to_app_log(
        level,
        f"IntentRouter shadow [session_id: {session_id}] mismatch={mismatch}",
        log_data,
    )


def emit_dialogue_route_dispatch(
    *,
    session_id: str,
    user_input: str,
    decision: Dict[str, Any],
    handler: str,
    handled: bool,
    dialogue_flags: Optional[Dict[str, bool]] = None,
) -> None:
    """AgentDispatcher 本線 dispatch ログ（Wave 1b）。"""
    timestamp = datetime.now().isoformat()
    log_data: Dict[str, Any] = {
        "log_type": "dialogue_route_dispatch",
        "timestamp": timestamp,
        "session_id": session_id,
        "user_input": user_input,
        "handler": handler,
        "handled": handled,
        "primary_route": decision.get("primary_route"),
        "sub_route": decision.get("sub_route"),
        "resolved_by": decision.get("resolved_by"),
        "confidence": decision.get("confidence"),
        "source": decision.get("source"),
    }
    if dialogue_flags:
        log_data["dialogue_flags"] = dialogue_flags

    _write_to_jsonl("dialogue_route_dispatch_log.jsonl", log_data)
    level = "INFO" if handled else "WARNING"
    _write_to_app_log(
        level,
        f"AgentDispatcher [session_id: {session_id}] handler={handler} handled={handled}",
        log_data,
    )


def emit_dialogue_route_execution(
    *,
    session_id: str,
    user_input: str,
    dispatch_sub_route: Optional[str] = None,
    resolved_concierge_intent: Optional[str] = None,
    resolved_execution_intent: Optional[str] = None,
    llm_path: Optional[str] = None,
    layer_used: Optional[str] = None,
    mismatch: bool = False,
    handler: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    """dispatch 決定と実行 intent の整合性ログ（unified routing 観測）。"""
    timestamp = datetime.now().isoformat()
    log_data: Dict[str, Any] = {
        "log_type": "dialogue_route_execution",
        "timestamp": timestamp,
        "session_id": session_id,
        "user_input": user_input,
        "dispatch_sub_route": dispatch_sub_route,
        "resolved_concierge_intent": resolved_concierge_intent,
        "resolved_execution_intent": resolved_execution_intent,
        "llm_path": llm_path,
        "layer_used": layer_used,
        "mismatch": mismatch,
        "handler": handler,
    }
    if extra:
        log_data.update(extra)

    _write_to_jsonl("dialogue_route_execution_log.jsonl", log_data)
    level = "WARNING" if mismatch else "INFO"
    _write_to_app_log(
        level,
        f"Route execution [session_id: {session_id}] mismatch={mismatch}",
        log_data,
    )


def emit_local_rag_detail(
    *,
    event: str,
    namespace: str = "",
    retrieve_ms: Optional[float] = None,
    chunk_count: int = 0,
    route: str = "",
    category: str = "",
    intent: str = "",
    model: str = "",
    query_chars: int = 0,
    cache_hit: bool = False,
    embed_ms: Optional[float] = None,
    provider: str = "local_rag",
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    """Local RAG retrieve / embed 観測ログ（コスト・レイテンシ監視）。"""
    timestamp = datetime.now().isoformat()
    log_data: Dict[str, Any] = {
        "log_type": "local_rag_detail",
        "timestamp": timestamp,
        "event": event,
        "provider": provider,
        "namespace": namespace,
        "local_rag_retrieve_ms": retrieve_ms,
        "chunk_count": chunk_count,
        "route": route or None,
        "category": category or None,
        "intent": intent or None,
        "local_rag_embed_model": model or None,
        "local_rag_embed_query_chars": query_chars or None,
        "local_rag_embed_cache_hit": cache_hit,
        "local_rag_embed_ms": embed_ms,
    }
    if extra:
        log_data.update(extra)
    log_data = {k: v for k, v in log_data.items() if v is not None}

    _write_to_jsonl("local_rag_detail.jsonl", log_data)
    _write_to_app_log(
        "INFO",
        f"LocalRAG [{event}] ns={namespace} ms={retrieve_ms} chunks={chunk_count}",
        log_data,
    )

