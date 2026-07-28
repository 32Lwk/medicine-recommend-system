"""
SSE ストリーム用イベントバス（同期チャット処理スレッド → async ジェネレータ）

stream_chat_events が StreamSink を ContextVar にセットし、
LLM コールバックから advice_delta / cards をキューへ投入する。
セッション単位のリングバッファで Last-Event-ID 再接続に対応する。
"""
from __future__ import annotations

import queue
import threading
import time
from contextvars import ContextVar
from typing import Any, Dict, List, Optional, Tuple

from src.services.processing_status import append_advice_preview

_stream_sink: ContextVar[Optional["StreamSink"]] = ContextVar("sse_stream_sink", default=None)

_SENTINEL = object()
_RING_TTL_SEC = 600.0
_RING_MAX = 512

_lock = threading.Lock()
_session_rings: Dict[str, List[Tuple[str, Dict[str, Any], str, float]]] = {}
_active_sinks: Dict[str, "StreamSink"] = {}
_stream_results: Dict[str, Tuple[Any, int, float]] = {}


class StreamSink:
    """スレッドセーフな SSE イベントキュー"""

    def __init__(self, session_id: str, *, max_buffer: int = 256) -> None:
        self.session_id = session_id
        self._q: queue.Queue = queue.Queue()
        self._closed = False
        self._seq = 0
        self._buffer: List[Tuple[str, Dict[str, Any], str]] = []
        self._max_buffer = max_buffer

    def emit(self, event: str, data: Dict[str, Any], event_id: Optional[str] = None) -> None:
        if self._closed:
            return
        self._seq += 1
        eid = event_id or str(self._seq)
        item = (event, data, eid)
        self._buffer.append(item)
        if len(self._buffer) > self._max_buffer:
            self._buffer.pop(0)
        _append_session_ring(self.session_id, item)
        self._q.put(item)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._q.put(_SENTINEL)

    def get(self, timeout: float = 0.05) -> Any:
        return self._q.get(timeout=timeout)

    def drain_nowait(self) -> List[Tuple[str, Dict[str, Any], str]]:
        out: List[Tuple[str, Dict[str, Any], str]] = []
        while True:
            try:
                item = self._q.get_nowait()
            except queue.Empty:
                break
            if item is _SENTINEL:
                continue
            out.append(item)
        return out

    def events_after(self, last_event_id: Optional[str]) -> List[Tuple[str, Dict[str, Any], str]]:
        if not last_event_id:
            return list(self._buffer)
        out: List[Tuple[str, Dict[str, Any], str]] = []
        found = False
        for event, data, eid in self._buffer:
            if found:
                out.append((event, data, eid))
            elif eid == last_event_id:
                found = True
        return out


def _purge_stale_rings() -> None:
    now = time.time()
    with _lock:
        stale = [sid for sid, ring in _session_rings.items() if ring and now - ring[-1][3] > _RING_TTL_SEC]
        for sid in stale:
            _session_rings.pop(sid, None)
            _stream_results.pop(sid, None)
        stale_res = [sid for sid, (_, _, ts) in _stream_results.items() if now - ts > _RING_TTL_SEC]
        for sid in stale_res:
            _stream_results.pop(sid, None)


def _append_session_ring(session_id: str, item: Tuple[str, Dict[str, Any], str]) -> None:
    _purge_stale_rings()
    with _lock:
        ring = _session_rings.setdefault(session_id, [])
        ring.append((item[0], item[1], item[2], time.time()))
        if len(ring) > _RING_MAX:
            del ring[: len(ring) - _RING_MAX]


def replay_session_events(
    session_id: str,
    last_event_id: Optional[str],
) -> List[Tuple[str, Dict[str, Any], str]]:
    """再接続時: リングバッファから Last-Event-ID 以降を返す"""
    _purge_stale_rings()
    with _lock:
        ring = list(_session_rings.get(session_id, []))
    if not last_event_id:
        return [(e, d, i) for e, d, i, _ in ring]
    out: List[Tuple[str, Dict[str, Any], str]] = []
    found = False
    for event, data, eid, _ in ring:
        if found:
            out.append((event, data, eid))
        elif eid == last_event_id:
            found = True
    return out


def is_session_stream_active(session_id: str) -> bool:
    with _lock:
        return session_id in _active_sinks


def get_active_session_sink(session_id: str) -> Optional[StreamSink]:
    with _lock:
        return _active_sinks.get(session_id)


def set_stream_result(session_id: str, body: Any, status_code: int) -> None:
    with _lock:
        _stream_results[session_id] = (body, status_code, time.time())


def peek_stream_result(session_id: str) -> Optional[Tuple[Any, int]]:
    """SSE 切断後にワーカーが保存した結果を参照（消費しない）。"""
    _purge_stale_rings()
    with _lock:
        raw = _stream_results.get(session_id)
    if not raw:
        return None
    return raw[0], raw[1]


def pop_stream_result(session_id: str) -> Optional[Tuple[Any, int]]:
    with _lock:
        raw = _stream_results.pop(session_id, None)
    if not raw:
        return None
    return raw[0], raw[1]


def get_stream_sink() -> Optional[StreamSink]:
    return _stream_sink.get()


def activate_stream_sink(
    session_id: str,
    *,
    allow_reattach: bool = True,
) -> Tuple[StreamSink, bool]:
    """
    StreamSink を有効化。
    Returns:
        (sink, reattach): 既存ストリームへの再接続なら reattach=True
    """
    _purge_stale_rings()
    with _lock:
        existing = _active_sinks.get(session_id)
        if existing and not existing._closed:
            if allow_reattach:
                _stream_sink.set(existing)
                return existing, True
            existing.close()
        sink = StreamSink(session_id)
        _active_sinks[session_id] = sink
        if session_id not in _session_rings:
            _session_rings[session_id] = []
    _stream_sink.set(sink)
    return sink, False


def bind_worker_stream_sink(session_id: Optional[str]) -> None:
    """ワーカースレッドで ContextVar に StreamSink を束縛（SSE 配信を有効化）。"""
    if not session_id:
        _stream_sink.set(None)
        return
    sink = get_active_session_sink(session_id)
    if sink and sink.session_id == session_id:
        _stream_sink.set(sink)
    else:
        _stream_sink.set(None)


def deactivate_stream_sink(session_id: Optional[str] = None) -> None:
    _stream_sink.set(None)
    if not session_id:
        return
    with _lock:
        _active_sinks.pop(session_id, None)


def clear_session_stream_state(session_id: str) -> None:
    with _lock:
        _active_sinks.pop(session_id, None)
        _session_rings.pop(session_id, None)
        _stream_results.pop(session_id, None)


def is_streaming_active(session_id: Optional[str] = None) -> bool:
    sink = get_stream_sink()
    if not sink:
        return False
    if session_id and sink.session_id != session_id:
        return False
    return True


def emit_sse_event(
    event: str,
    data: Dict[str, Any],
    *,
    session_id: Optional[str] = None,
    event_id: Optional[str] = None,
) -> None:
    sink = get_stream_sink()
    if not sink and session_id:
        sink = get_active_session_sink(session_id)
    if not sink:
        return
    if session_id and sink.session_id != session_id:
        return
    sink.emit(event, data, event_id=event_id)


def emit_advice_delta(chunk: str, session_id: Optional[str] = None) -> None:
    """医薬品推奨の個別アドバイス用ストリーム（推奨カード UI）"""
    if not chunk:
        return
    sid = session_id
    sink = get_stream_sink()
    if sink and not sid:
        sid = sink.session_id
    if sid:
        append_advice_preview(sid, chunk)
    emit_sse_event("advice_delta", {"text": chunk}, session_id=sid)


def emit_chat_delta(chunk: str, session_id: Optional[str] = None) -> None:
    """カウンセリング・挨拶など通常チャット吹き出し用ストリーム"""
    if not chunk:
        return
    emit_sse_event("chat_delta", {"text": chunk}, session_id=session_id)


def emit_cards(
    medicines: List[Dict[str, Any]],
    *,
    session_id: Optional[str] = None,
) -> None:
    payload = []
    from src.services.medicine_image_urls import enrich_medicine_image_url

    for i, med in enumerate(medicines[:5], 1):
        med = enrich_medicine_image_url(dict(med))
        efficacy = med.get("efficacy") or ""
        if not isinstance(efficacy, str):
            efficacy = str(efficacy) if efficacy is not None else ""
        payload.append(
            {
                "rank": i,
                "product_name": med.get("product_name") or med.get("name") or "",
                "manufacturer": med.get("manufacturer") or "",
                "efficacy": efficacy,
                "explanation": med.get("explanation") or med.get("reason") or "",
                "display_score": med.get("display_score"),
                "relative_score": med.get("relative_score"),
                "score": med.get("score"),
                "score_level": med.get("score_level") or "",
                "completeness_penalty": med.get("completeness_penalty", 0.0),
                "age_restriction": med.get("age_restriction") or "",
                "risk_warning": med.get("risk_warning") or "",
                "low_score_warning": bool(med.get("low_score_warning")),
                "medicine_type": med.get("medicine_type") or "",
                "image_url": med.get("image_url")
                or med.get("imageUrl")
                or med.get("hero_url")
                or med.get("product_image_url"),
                "symptoms": med.get("symptoms") or med.get("matched_symptoms") or [],
                "score_breakdown": med.get("score_breakdown") or med.get("scores"),
            }
        )
    emit_sse_event(
        "cards",
        {"medicines": payload, "count": len(payload)},
        session_id=session_id,
    )


def emit_reco_detail(
    detail: Dict[str, Any],
    *,
    session_id: Optional[str] = None,
) -> None:
    """Usage sections / enriched detail after core recommendation done."""
    if not detail:
        return
    emit_sse_event("reco_detail", detail, session_id=session_id)


def emit_bot_followup(
    *,
    session_id: Optional[str] = None,
    message_type: str = "explanations_ready",
    payload: Optional[Dict[str, Any]] = None,
) -> None:
    """Explanation 完了など第2応答のシグナル（クライアントは /api/sessions で本文取得）。"""
    emit_sse_event(
        "bot_followup",
        {"type": message_type, **(payload or {})},
        session_id=session_id,
    )


def emit_explanations(
    medicines: List[Dict[str, Any]],
    explanations: List[str],
    *,
    session_id: Optional[str] = None,
) -> None:
    """カード先行後の推奨理由（第2 SSE 応答）"""
    items = []
    for i, (med, text) in enumerate(zip(medicines[:5], explanations[:5]), 1):
        if not (text or "").strip():
            continue
        items.append(
            {
                "rank": med.get("rank") or i,
                "product_name": med.get("product_name") or med.get("name") or "",
                "explanation": text,
            }
        )
    if not items:
        return
    emit_sse_event(
        "explanations",
        {"items": items, "count": len(items)},
        session_id=session_id,
    )


def pseudo_stream_advice(
    text: str,
    session_id: Optional[str] = None,
    *,
    chunk_size: int = 24,
    delay_sec: float = 0.006,
) -> None:
    """DeepL 翻訳後など、完成テキストを推奨アドバイス用に疑似ストリーム配信"""
    if not text or not is_streaming_active(session_id):
        return
    for i in range(0, len(text), chunk_size):
        emit_advice_delta(text[i : i + chunk_size], session_id)
        if delay_sec > 0:
            time.sleep(delay_sec)


def qa_sse_preview_enabled() -> bool:
    """True のときのみ qa_delta / qa_section を SSE 送信（暫定 streaming-qa 用）。"""
    import os

    return os.getenv("QA_SSE_PREVIEW_ENABLED", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def emit_qa_delta(
    chunk: str,
    session_id: Optional[str] = None,
    *,
    section: str = "answer",
) -> None:
    """医薬品 Q&A: 回答本文などセクション単位のテキストストリーム"""
    if not chunk or not qa_sse_preview_enabled():
        return
    emit_sse_event(
        "qa_delta",
        {"section": section, "text": chunk},
        session_id=session_id,
    )


def emit_qa_section(
    section: str,
    html: str,
    *,
    session_id: Optional[str] = None,
) -> None:
    """医薬品 Q&A: 構造化セクション（相互作用等）の HTML 追送"""
    if not html or not section or not qa_sse_preview_enabled():
        return
    emit_sse_event(
        "qa_section",
        {"section": section, "html": html},
        session_id=session_id,
    )


def emit_qa_sections_from_response(
    chat_response: Dict[str, Any],
    session_id: Optional[str] = None,
) -> None:
    """完成した Q&A 応答から追加セクションを SSE 配信"""
    if not qa_sse_preview_enabled():
        return
    from src.services.medicine_qa_html import safe_format_html

    product_images_html = str(chat_response.get("product_images_html") or "").strip()
    if product_images_html:
        emit_qa_section("product_images", product_images_html, session_id=session_id)

    mapping = [
        ("medicine_details", "💊 医薬品の詳細", "#e3f2fd", "qa-medicine-details"),
        ("interactions", "⚠️ 相互作用の注意", "#fff3e0", "qa-interactions"),
        ("doping_check", "🏃 ドーピングチェック", "#ffebee", "qa-doping"),
        ("side_effects", "⚕️ 副作用情報", "#fce4ec", "qa-side-effects"),
        ("consultation_advice", "🩺 相談アドバイス", "#f1f8e9", "qa-consultation"),
    ]
    for key, title, bg, css_class in mapping:
        raw = chat_response.get(key) or ""
        if not raw:
            continue
        body = safe_format_html(raw)
        block = (
            f'<motion class="qa-section {css_class}" data-qa-section="{key}" '
            f'style="margin-top: 15px; padding: 10px; background: {bg}; border-radius: 5px;">'
            f"<strong>{title}:</strong><br>{body}</motion>"
        ).replace("<motion ", "<div ").replace("</motion>", "</div>")
        emit_qa_section(key, block, session_id=session_id)


def pseudo_stream_chat(
    text: str,
    session_id: Optional[str] = None,
    *,
    chunk_size: int = 24,
    delay_sec: float = 0.006,
) -> None:
    """DeepL 翻訳後など、完成テキストを通常チャット吹き出し用に疑似ストリーム配信"""
    if not text or not is_streaming_active(session_id):
        return
    for i in range(0, len(text), chunk_size):
        emit_chat_delta(text[i : i + chunk_size], session_id)
        if delay_sec > 0:
            time.sleep(delay_sec)
