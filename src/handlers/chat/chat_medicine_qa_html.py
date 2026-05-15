"""
医薬品相談 Q&A 回答の HTML 整形（質問ルート・フォローアップ共通）
"""
from __future__ import annotations

import html
import random
import time
from typing import Any, Dict


def safe_format_html(text: Any) -> str:
    if not text:
        return ""
    if isinstance(text, list):
        lines = []
        for item in text:
            if isinstance(item, dict):
                name = item.get("製品名") or item.get("name") or ""
                comp = item.get("主成分") or item.get("成分") or ""
                use = item.get("用途") or item.get("efficacy") or ""
                summary = " / ".join(s for s in [name, comp, use] if s)
                if summary:
                    lines.append(summary)
            else:
                lines.append(str(item))
        text = "\n".join(lines)
    elif isinstance(text, dict):
        text = "\n".join(f"{k}: {v}" for k, v in text.items())
    else:
        text = str(text)
    return html.escape(text).replace("\n", "<br>")


def build_medicine_qa_html(chat_response: Dict[str, Any]) -> str:
    ans = safe_format_html(chat_response.get("answer", "回答を取得できませんでした"))
    med_det = safe_format_html(chat_response.get("medicine_details", ""))
    inter = safe_format_html(chat_response.get("interactions", ""))
    doping = safe_format_html(chat_response.get("doping_check", ""))
    side_eff = safe_format_html(chat_response.get("side_effects", ""))
    consult = safe_format_html(chat_response.get("consultation_advice", ""))
    return f"""
<div class="chat-response">
<h4>💬 医薬品相談回答</h4>
<p><strong>回答:</strong><br>{ans}</p>
{f'<div style="margin-top: 15px; padding: 10px; background: #e3f2fd; border-radius: 5px;"><strong>💊 医薬品の詳細:</strong><br>{med_det}</div>' if med_det else ''}
{f'<div style="margin-top: 15px; padding: 10px; background: #fff3e0; border-radius: 5px;"><strong>⚠️ 相互作用の注意:</strong><br>{inter}</div>' if inter else ''}
{f'<div style="margin-top: 15px; padding: 10px; background: #ffebee; border-radius: 5px;"><strong>🏃 ドーピングチェック:</strong><br>{doping}</div>' if doping else ''}
{f'<div style="margin-top: 15px; padding: 10px; background: #fce4ec; border-radius: 5px;"><strong>⚕️ 副作用情報:</strong><br>{side_eff}</div>' if side_eff else ''}
{f'<div style="margin-top: 15px; padding: 10px; background: #f1f8e9; border-radius: 5px;"><strong>🩺 相談アドバイス:</strong><br>{consult}</div>' if consult else ''}
</div>"""


def append_feedback_buttons(html_body: str) -> tuple[str, str]:
    message_id = f"msg_{int(time.time() * 1000)}_{random.randint(1000, 9999)}"
    full = html_body + f"""
<div class="feedback-buttons" style="margin-top: 20px; padding: 15px; background: #f8f9fa; border-radius: 8px; border: 1px solid #dee2e6;">
<p style="margin: 0 0 10px 0; font-weight: bold; color: #495057;">この回答はいかがでしたか？</p>
<button class="feedback-btn-positive" onclick="handlePositiveFeedback('{message_id}')" style="background: #28a745; color: white; border: none; padding: 8px 16px; margin-right: 10px; border-radius: 4px; cursor: pointer; font-size: 14px; min-width: 80px;">適切</button>
<button class="feedback-btn-negative" onclick="handleNegativeFeedback('{message_id}')" style="background: #dc3545; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; font-size: 14px; min-width: 80px;">不適切</button>
</div>"""
    return full, message_id
