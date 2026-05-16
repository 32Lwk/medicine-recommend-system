"""
メディカル緊急・クライシス向けユーザー応答テンプレ（店舗カードとは別 UX）
"""
from __future__ import annotations

from html import escape
from typing import Any, Dict


def build_medical_emergency_html(
    *,
    subtype: str,
    language: str = "ja",
    user_message: str = "",
) -> str:
    lang = language if language in ("ja", "en", "ko", "zh") else "ja"
    if subtype == "crisis_language":
        return _build_crisis_html(lang)
    return _build_medical_self_html(lang)


def _build_medical_self_html(lang: str) -> str:
    copy = {
        "ja": {
            "title": "緊急の可能性があります",
            "body": "お伝えいただいた内容から、早急な医療機関の受診または救急のご利用が必要な可能性があります。",
            "call": "日本国内では <strong>119番（救急）</strong> にご連絡ください。",
            "stop": "市販薬の自己判断での使用はお控えください。",
            "unlock": "症状が落ち着き、緊急ではないと判断される場合のみ、画面の案内に従って相談を再開できます。",
        },
        "en": {
            "title": "Possible medical emergency",
            "body": "Based on your message, you may need urgent in-person medical care.",
            "call": "In Japan, call <strong>119 (ambulance)</strong> for emergencies.",
            "stop": "Please do not rely on over-the-counter medicine selection alone.",
            "unlock": "You may resume consultation only if you are sure this is not an emergency.",
        },
        "ko": {
            "title": "응급 가능성이 있습니다",
            "body": "입력 내용상 즉시 의료기관 방문 또는 응급 연락이 필요할 수 있습니다.",
            "call": "일본에서는 <strong>119(구급)</strong>에 연락해 주세요.",
            "stop": "일반의약품만으로 스스로 판단하지 마세요.",
            "unlock": "응급이 아니라고 확신할 때만 상담을 재개해 주세요.",
        },
        "zh": {
            "title": "可能存在紧急情况",
            "body": "根据您的描述，可能需要尽快就医或拨打急救电话。",
            "call": "在日本请拨打 <strong>119（急救）</strong>。",
            "stop": "请勿仅凭自行选择非处方药处理。",
            "unlock": "仅在确认并非紧急情况后，方可按画面指引继续咨询。",
        },
    }
    c = copy.get(lang, copy["ja"])
    return f"""
<div class="emergency-medical-card" role="alert">
  <h3>{escape(c['title'])}</h3>
  <p>{escape(c['body'])}</p>
  <p class="emergency-call">{c['call']}</p>
  <p><a href="tel:119" class="emergency-tel-link">119</a></p>
  <p>{escape(c['stop'])}</p>
  <p class="emergency-unlock-hint">{escape(c['unlock'])}</p>
</div>
"""


def _build_crisis_html(lang: str) -> str:
    try:
        from src.core.crisis_detection import get_crisis_support_resources

        data: Dict[str, Any] = get_crisis_support_resources(lang)
        title = escape(data.get("title", ""))
        message = escape(data.get("message", ""))
        emergency = escape(data.get("emergency_message", ""))
        resources_html = ""
        for r in data.get("resources", [])[:4]:
            name = escape(str(r.get("name", "")))
            desc = escape(str(r.get("description", "")))
            phone = r.get("phone")
            line = f"<li><strong>{name}</strong>: {desc}"
            if phone:
                line += f' — <a href="tel:{escape(str(phone))}">{escape(str(phone))}</a>'
            line += "</li>"
            resources_html += line
        stop_msg = {
            "ja": "市販薬の自己判断での使用はお控えください。",
            "en": "Please do not rely on OTC medicine selection alone.",
            "ko": "일반의약품만으로 스스로 판단하지 마세요.",
            "zh": "请勿仅凭自行选择非处方药处理。",
        }
        return f"""
<div class="emergency-crisis-card" role="alert">
  <h3>{title}</h3>
  <p>{message}</p>
  <p class="emergency-call">{emergency}</p>
  <p><a href="tel:119" class="emergency-tel-link">119</a></p>
  <ul>{resources_html}</ul>
  <p>{escape(stop_msg.get(lang, stop_msg['ja']))}</p>
</div>
"""
    except ImportError:
        return _build_medical_self_html(lang)
