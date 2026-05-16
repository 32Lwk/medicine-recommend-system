"""
医薬品 Q&A 応答の HTML 生成（ストリーミング・最終保存で共通利用）
"""
from __future__ import annotations

from typing import Any, Dict

from src.services.text_formatter import safe_format_qa_html


def safe_format_html(text: Any) -> str:
    return safe_format_qa_html(text)


def build_chat_response_inner_html(chat_response: Dict[str, Any]) -> str:
    """chat-response 内側 HTML（フィードバックボタンなし）"""
    answer_text = safe_format_html(chat_response.get("answer", "回答を取得できませんでした"))
    medicine_details = safe_format_html(chat_response.get("medicine_details", ""))
    interactions = safe_format_html(chat_response.get("interactions", ""))
    doping_check = safe_format_html(chat_response.get("doping_check", ""))
    side_effects = safe_format_html(chat_response.get("side_effects", ""))
    consultation_advice = safe_format_html(chat_response.get("consultation_advice", ""))

    parts = [
        '<div class="chat-response" data-streaming-qa="true">',
        "<h4>💬 医薬品相談回答</h4>",
        f'<p class="qa-answer"><strong>回答:</strong><br><span class="streaming-qa-answer">{answer_text}</span></p>',
    ]
    if medicine_details:
        parts.append(
            '<div class="qa-section qa-medicine-details" style="margin-top: 15px; padding: 10px; background: #e3f2fd; border-radius: 5px;">'
            f"<strong>💊 医薬品の詳細:</strong><br>{medicine_details}</div>"
        )
    if interactions:
        parts.append(
            '<div class="qa-section qa-interactions" style="margin-top: 15px; padding: 10px; background: #fff3e0; border-radius: 5px;">'
            f"<strong>⚠️ 相互作用の注意:</strong><br>{interactions}</div>"
        )
    if doping_check:
        parts.append(
            '<div class="qa-section qa-doping" style="margin-top: 15px; padding: 10px; background: #ffebee; border-radius: 5px;">'
            f"<strong>🏃 ドーピングチェック:</strong><br>{doping_check}</div>"
        )
    if side_effects:
        parts.append(
            '<div class="qa-section qa-side-effects" style="margin-top: 15px; padding: 10px; background: #fce4ec; border-radius: 5px;">'
            f"<strong>⚕️ 副作用情報:</strong><br>{side_effects}</div>"
        )
    if consultation_advice:
        parts.append(
            '<div class="qa-section qa-consultation" style="margin-top: 15px; padding: 10px; background: #f1f8e9; border-radius: 5px;">'
            f"<strong>🩺 相談アドバイス:</strong><br>{consultation_advice}</div>"
        )
    parts.append("</div>")
    return "\n".join(parts)
