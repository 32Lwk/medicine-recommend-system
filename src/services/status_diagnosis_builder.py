"""Build status diagnosis v1 payloads for Sage UI."""
from __future__ import annotations

from typing import Any

from src.schemas.status_diagnosis_v1 import StatusAction, StatusDiagnosisV1, StatusSection
from src.services.reco_error_messages import ERROR_MESSAGES, MEDICAL_ADVICE_ITEMS

_MEDICAL_ADVICE_ITEMS = MEDICAL_ADVICE_ITEMS

SAGE_STATUS_MARKER = "sage_status"
SAGE_QA_MARKER = "sage_qa"


def build_diagnosis_notice(
    message: str,
    *,
    title: str = "診断名について",
    subtitle: str = "",
    feedback_context: dict[str, Any] | None = None,
    show_bug_report: bool = True,
    kind: str = "diagnosis_detected",
) -> StatusDiagnosisV1:
    return StatusDiagnosisV1(
        render="sage_status",
        variant="notice",
        title=title,
        subtitle=subtitle,
        message=message,
        show_feedback=True,
        show_bug_report=show_bug_report,
        feedback_context=feedback_context,
        kind=kind,
    )


def build_system_error_status(
    *,
    title: str = "一時的なエラーが発生しました",
    message: str = "処理中に問題が発生しました。しばらく時間をおいてからもう一度お試しください。",
) -> StatusDiagnosisV1:
    return StatusDiagnosisV1(
        render="sage_status",
        variant="error",
        title=title,
        message=message,
        hints=["もう一度お試しください", "問題が続く場合は薬剤師にご相談ください"],
        kind="system_error",
    )


def build_llm_unavailable_status(
    *,
    feedback_context: dict[str, Any] | None = None,
) -> StatusDiagnosisV1:
    """OpenAI quota / 429 等 — 既存 error カード（sage_status variant=error）。"""
    from src.services.budget_guard import get_admin_message

    info = ERROR_MESSAGES["llm_unavailable"]
    admin_body = (get_admin_message("llm_unavailable") or "").strip()
    message = admin_body or info["main_message"]
    summary = list(info.get("summary_items") or [])
    if not summary:
        summary = list(info.get("available_features") or []) + list(
            info.get("unavailable_features") or []
        )
    sections: list[StatusSection] = (
        [StatusSection(title="ご利用の目安", items=summary)] if summary else []
    )
    hints = list(info.get("recommendations") or [])
    return StatusDiagnosisV1(
        render="sage_status",
        variant="error",
        title=info["title"],
        subtitle=info.get("subtitle") or "",
        message=message,
        hints=hints,
        sections=sections,
        show_feedback=True,
        show_bug_report=True,
        feedback_context=feedback_context,
        kind="llm_unavailable",
    )


def build_escalation_status(
    message: str,
    *,
    medicine_type: str = "",
    feedback_context: dict[str, Any] | None = None,
) -> StatusDiagnosisV1:
    hints = [
        "速やかに医師の診察を受けてください",
        "市販薬での自己治療は推奨されません",
        "症状が悪化する場合は救急医療機関へ",
    ]
    sections = []
    if medicine_type:
        sections.append(
            StatusSection(title="医薬品の種類", items=[medicine_type])
        )
    return StatusDiagnosisV1(
        render="sage_status",
        variant="critical",
        title="重要な注意事項",
        subtitle="市販薬の使用は控え、医師にご相談ください。",
        message=message,
        hints=hints,
        sections=sections,
        feedback_context=feedback_context,
        kind="escalation",
    )


def build_medicine_type_unrecognized_status(
    *,
    feedback_context: dict[str, Any] | None = None,
) -> StatusDiagnosisV1:
    """医薬品種類が判定できない入力向けの caution ステータス。"""
    return StatusDiagnosisV1(
        render="sage_status",
        variant="caution",
        title="症状から医薬品を選べませんでした",
        subtitle="入力内容を変えるか、薬剤師にご相談ください。",
        message=(
            "医薬品種類が判定できませんでした。"
            "症状をより具体的に記述していただくか、医師にご相談ください。"
        ),
        hints=[
            "症状をより具体的に入力してください（例：「頭が痛い」「のどが痛い」）",
            "1週間以上続く場合は医療機関を受診してください",
        ],
        show_feedback=True,
        feedback_context=feedback_context,
        kind="medicine_type_unrecognized",
    )


def build_error_status(
    error_type: str,
    error_details: dict[str, Any] | None = None,
    *,
    feedback_context: dict[str, Any] | None = None,
) -> StatusDiagnosisV1:
    details = error_details or {}
    info = ERROR_MESSAGES.get(error_type, ERROR_MESSAGES["unknown_error"])
    reason = details.get("reason") or info["main_message"]
    variant = "error" if error_type in ("rule_based_error", "unknown_error") else "caution"
    return StatusDiagnosisV1(
        render="sage_status",
        variant=variant,  # type: ignore[arg-type]
        title=info["title"],
        message=reason,
        hints=list(info.get("recommendations") or []),
        sections=[
            StatusSection(
                title="医師への相談をお勧めします",
                items=list(_MEDICAL_ADVICE_ITEMS),
            )
        ],
        feedback_context=feedback_context,
        kind=error_type,
    )


def build_crisis_status(
    message: str,
    *,
    resources: list[dict[str, Any]] | None = None,
    title: str = "相談窓口のご案内",
) -> StatusDiagnosisV1:
    sections = []
    if resources:
        items = [
            f"{r.get('name', '')}: {r.get('contact', r.get('phone', ''))}".strip(": ")
            for r in resources
            if r.get("name") or r.get("contact") or r.get("phone")
        ]
        if items:
            sections.append(StatusSection(title="相談先", items=items))
    return StatusDiagnosisV1(
        render="sage_status",
        variant="security",
        title=title,
        message=message,
        sections=sections,
        show_feedback=False,
        kind="crisis_support",
    )


def build_emergency_status(
    message: str,
    *,
    title: str = "緊急のお知らせ",
    subtitle: str = "",
    hints: list[str] | None = None,
    kind: str = "emergency",
) -> StatusDiagnosisV1:
    return StatusDiagnosisV1(
        render="sage_status",
        variant="critical",
        title=title,
        subtitle=subtitle,
        message=message,
        hints=hints or [],
        show_feedback=False,
        kind=kind,
    )


def build_store_status(
    *,
    simple_message: str = "",
    message: str | None = None,
    inquiry_type: str | None = None,
    title: str | None = None,
    html: str | None = None,
    sections: list[StatusSection] | None = None,
    feedback_context: dict[str, Any] | None = None,
) -> StatusDiagnosisV1:
    text = (simple_message or message or "").strip()
    if title is None:
        title = _store_inquiry_title(inquiry_type)
    out_sections: list[StatusSection] = list(sections or [])
    if html and str(html).strip() and not out_sections:
        out_sections.append(StatusSection(title="詳細", html=str(html).strip()))
    return StatusDiagnosisV1(
        render="sage_status",
        variant="notice",
        title=title,
        message=text,
        sections=out_sections,
        kind=f"store_{inquiry_type}" if inquiry_type else "store_inquiry",
        show_feedback=True,
        feedback_context=feedback_context,
    )


_STORE_INQUIRY_TITLES: dict[str, str] = {
    "store_inquiry": "店舗案内",
    "lost_and_found": "遺失物のお問い合わせ",
    "inventory": "在庫確認",
    "facilities": "周辺施設",
    "tax_free": "免税について",
    "tourism": "周辺観光",
    "business_hours": "営業時間・アクセス",
    "payment": "お支払い方法",
    "parking": "駐車場",
    "services": "店舗サービス",
}


def _store_inquiry_title(inquiry_type: str | None) -> str:
    if not inquiry_type:
        return "店舗案内"
    return _STORE_INQUIRY_TITLES.get(inquiry_type, "店舗案内")


def _product_category_path(product_category: dict[str, Any]) -> str:
    category = str(product_category.get("category") or "").strip()
    subcategory = str(product_category.get("subcategory") or "").strip()
    product = str(product_category.get("product") or "").strip()
    parts = [p for p in (category, subcategory, product) if p]
    return " > ".join(parts)


def _product_display_name(product_category: dict[str, Any]) -> str:
    return str(
        product_category.get("product") or product_category.get("subcategory") or ""
    ).strip()


_STORE_USER_INTENT_KIND = {
    "facilities": "store_facilities",
    "locator": "store_locator",
    "inventory": "store_inventory",
    "external_chain": "store_locator",
}


def resolve_store_diagnosis_kind(
    store_inquiry_result: dict[str, Any],
    *,
    user_text: str = "",
) -> str:
    intent = store_inquiry_result.get("user_intent")
    if not intent and user_text:
        try:
            from src.services.store_inquiry_handler import classify_store_user_intent

            intent = classify_store_user_intent(user_text)
        except Exception:
            intent = None
    if isinstance(intent, str) and intent in _STORE_USER_INTENT_KIND:
        return _STORE_USER_INTENT_KIND[intent]
    inquiry_type = store_inquiry_result.get("inquiry_type")
    if inquiry_type == "store_inquiry":
        return "store_inquiry"
    if isinstance(inquiry_type, str) and inquiry_type.startswith("store_"):
        return inquiry_type
    if inquiry_type:
        return f"store_{inquiry_type}"
    return "store_inquiry"


def build_store_status_from_inquiry_result(
    store_inquiry_result: dict[str, Any],
    *,
    simple_message: str,
    feedback_context: dict[str, Any] | None = None,
) -> StatusDiagnosisV1:
    inquiry_type = store_inquiry_result.get("inquiry_type")
    sections: list[StatusSection] = []
    product_category = store_inquiry_result.get("product_category")
    if inquiry_type == "inventory" and isinstance(product_category, dict):
        product_name = _product_display_name(product_category)
        if product_name and product_name not in simple_message:
            sections.append(StatusSection(title="お探しの商品", items=[product_name]))
    facility_name = store_inquiry_result.get("facility_name")
    if inquiry_type == "facilities" and facility_name:
        sections.append(StatusSection(title="施設", items=[str(facility_name)]))
    user_text = str((feedback_context or {}).get("user_message") or "")
    return StatusDiagnosisV1(
        render="sage_status",
        variant="notice",
        title=_store_inquiry_title(inquiry_type if isinstance(inquiry_type, str) else None),
        message=simple_message.strip(),
        hints=[],
        sections=sections,
        kind=resolve_store_diagnosis_kind(store_inquiry_result, user_text=user_text),
        show_feedback=True,
        feedback_context=feedback_context,
    )


def build_qa_status(
    *,
    answer: str,
    sections: list[StatusSection] | None = None,
    title: str = "医薬品相談回答",
    feedback_context: dict[str, Any] | None = None,
) -> StatusDiagnosisV1:
    return StatusDiagnosisV1(
        render="sage_qa",
        variant="notice",
        title=title,
        message=answer,
        sections=sections or [],
        kind="medicine_qa",
        show_feedback=True,
        feedback_context=feedback_context,
    )


def build_qa_from_chat_response(
    chat_response: dict[str, Any],
    *,
    feedback_context: dict[str, Any] | None = None,
) -> StatusDiagnosisV1:
    section_map = [
        ("medicine_details", "医薬品の詳細"),
        ("interactions", "相互作用の注意"),
        ("doping_check", "ドーピングチェック"),
        ("side_effects", "副作用情報"),
        ("consultation_advice", "相談アドバイス"),
    ]
    sections: list[StatusSection] = []
    for key, title in section_map:
        val = chat_response.get(key)
        if val and str(val).strip():
            sections.append(StatusSection(title=title, items=[str(val).strip()]))
    return build_qa_status(
        answer=str(chat_response.get("answer") or "回答を取得できませんでした"),
        sections=sections,
        feedback_context=feedback_context,
    )


def build_emergency_status(
    *,
    subtype: str,
    language: str = "ja",
    simple_message: str = "",
) -> StatusDiagnosisV1:
    from src.services.medical_emergency_templates import get_medical_emergency_copy

    copy = get_medical_emergency_copy(subtype=subtype, language=language)
    sections: list[StatusSection] = []
    resources = copy.get("resources") or []
    if resources:
        items = []
        for r in resources:
            name = r.get("name", "")
            contact = r.get("phone") or r.get("contact") or r.get("description", "")
            if name or contact:
                items.append(f"{name}: {contact}".strip(": "))
        if items:
            sections.append(StatusSection(title="相談先", items=items))
    message = simple_message or copy.get("message") or ""
    return StatusDiagnosisV1(
        render="sage_status",
        variant=copy.get("variant", "critical"),  # type: ignore[arg-type]
        title=copy.get("title") or "緊急のお知らせ",
        message=message,
        hints=list(copy.get("hints") or []),
        sections=sections,
        show_feedback=False,
        kind=f"emergency_{subtype}",
    )


def build_concierge_capabilities_status() -> StatusDiagnosisV1:
    from src.content.concierge_knowledge import (
        get_app_info,
        get_capabilities,
        get_limitations,
    )

    app = get_app_info()
    caps = get_capabilities()
    limits = get_limitations()
    cap_items = [f"{c.get('title', '')}: {c.get('body', '')}" for c in caps if c.get("title")]
    sections = [
        StatusSection(title="できること", items=cap_items),
        StatusSection(title="できないこと・ご注意", items=list(limits)),
    ]
    return StatusDiagnosisV1(
        render="sage_status",
        variant="notice",
        title="このチャットでできること（β版）",
        subtitle=str(app.get("name") or ""),
        message=str(app.get("purpose") or ""),
        hints=["症状やお薬について、具体的にお書きください。"],
        sections=sections,
        kind="concierge_capabilities",
        show_feedback=True,
    )


def build_concierge_operator_status(intro_text: str) -> StatusDiagnosisV1:
    return StatusDiagnosisV1(
        render="sage_status",
        variant="notice",
        title="開発者・運営者への連絡",
        message=intro_text,
        kind="concierge_operator",
        show_feedback=True,
    )


def build_notice_status(
    message: str,
    *,
    title: str = "お知らせ",
    variant: str = "notice",
    hints: list[str] | None = None,
    sections: list[StatusSection] | None = None,
    kind: str | None = None,
    show_feedback: bool = False,
    feedback_context: dict[str, Any] | None = None,
) -> StatusDiagnosisV1:
    from src.utils.sage_message_plain import strip_internal_llm_prefix

    clean_message = strip_internal_llm_prefix(message)
    return StatusDiagnosisV1(
        render="sage_status",
        variant=variant,  # type: ignore[arg-type]
        title=title,
        message=clean_message,
        hints=hints or [],
        sections=sections or [],
        show_feedback=show_feedback,
        feedback_context=feedback_context,
        kind=kind,
    )


def build_counseling_status(
    message: str,
    *,
    title: str = "カウンセリング",
    kind: str = "counseling",
) -> StatusDiagnosisV1:
    return build_notice_status(message, title=title, kind=kind, show_feedback=False)


def build_ambiguous_heart_clarification_status(
    message: str,
    *,
    feedback_context: dict[str, Any] | None = None,
) -> StatusDiagnosisV1:
    """心が痛い — 身体的症状 vs 心理的症状の確認カード。"""
    return StatusDiagnosisV1(
        render="sage_status",
        variant="caution",
        title="症状の確認",
        subtitle="お身体の痛みか、お気持ちのつらさか教えてください",
        message=message,
        hints=[
            "胸や心臓の痛み・動悸・息苦しさ → 身体的な症状の可能性",
            "悲しみ・不安・ストレスによる「心の痛み」 → 心理的症状の可能性",
            "胸の痛みや息苦しさが強い場合は、すぐに医療機関へ相談してください",
        ],
        actions=[
            StatusAction(
                id="ambiguous_heart_physical",
                label="胸や心臓の物理的な痛み",
                kind="button",
            ),
            StatusAction(
                id="ambiguous_heart_emotional",
                label="気持ちのつらさ・心の痛み",
                kind="button",
            ),
        ],
        show_feedback=True,
        feedback_context=feedback_context,
        kind="ambiguous_heart_clarification",
    )


def build_concierge_text_status(
    message: str,
    *,
    title: str,
    kind: str,
) -> StatusDiagnosisV1:
    """Short concierge replies (greeting/chitchat/etc.) — plain chat bubble in Sage UI."""
    diag = build_notice_status(message, title=title, kind=kind, show_feedback=False)
    return diag.model_copy(update={"layout": "plain"})


def build_user_info_registration_status(
    registered_items: list[str],
    *,
    had_error: bool = False,
) -> StatusDiagnosisV1:
    sections: list[StatusSection] = []
    if registered_items:
        message = "以下の内容を反映しました。"
        sections.append(StatusSection(title="登録内容", items=registered_items))
    else:
        message = "新しい情報は見つかりませんでした。"
    hints: list[str] = []
    if had_error:
        hints.append("登録処理中にエラーが発生しましたが、医薬品推奨は続行します。")
    return build_notice_status(
        message,
        title="ユーザー情報",
        hints=hints,
        sections=sections,
        kind="user_info_registration",
    )


def build_attribute_update_status(user_attributes: dict[str, Any]) -> StatusDiagnosisV1:
    allergies = user_attributes.get("allergies") or []
    meds = user_attributes.get("current_medications") or []
    items = [
        f"年齢: {user_attributes.get('age', '未入力')}",
        f"性別: {user_attributes.get('gender', '未入力')}",
        f"アレルギー: {', '.join(allergies) if allergies else 'なし'}",
        f"服用中の薬: {', '.join(meds) if meds else 'なし'}",
    ]
    return build_notice_status(
        "属性情報を更新しました。",
        title="属性情報",
        sections=[StatusSection(title="登録内容", items=items)],
        hints=["症状について教えていただければ、更新された情報をもとに適切な医薬品をご提案いたします。"],
        kind="attribute_update_confirmation",
    )


def build_concierge_architecture_status() -> StatusDiagnosisV1:
    from src.content.concierge_knowledge import get_agents

    agents = get_agents()
    agent_items = [
        f"{a.get('name_ja', '')}: {a.get('role_one_liner', '')}"
        for a in agents
        if a.get("name_ja")
    ]
    sections = [
        StatusSection(
            title="市販薬の選び方",
            items=[
                "一般用医薬品（OTC）の候補選定はルールベースのアルゴリズムのみで行います。",
                "AI（LLM）が自由に薬名を創作して決めることはありません。",
                "お話の分類・説明文の生成・質問への回答などに AI を使います。",
            ],
        ),
        StatusSection(title="役割分担（マルチエージェント）", items=agent_items),
    ]
    return StatusDiagnosisV1(
        render="sage_status",
        variant="notice",
        title="このチャットの仕組み（β版）",
        subtitle="トリアージ後に専門のエージェントが応答します",
        message=(
            "症状の相談は PhysicalOrchestrator が、"
            "挨拶やアプリの説明・各種公式ドキュメントの案内は ConciergeAgent が担当します。"
        ),
        hints=["お体の不調やお薬のことでしたら、症状を教えてください。"],
        sections=sections,
        kind="concierge_architecture",
        show_feedback=True,
    )


def _mask_profile_for_user_display(profile: dict[str, Any]) -> list[str]:
    """ユーザー向けステータスカード用に PII をマスクしたプロファイル要約。"""
    p = profile or {}
    items: list[str] = []

    def _flag(key: str, label: str) -> None:
        val = p.get(key)
        if val is None or val == "" or val == []:
            items.append(f"{label}: 未登録")
        else:
            items.append(f"{label}: 登録あり")

    _flag("age", "年齢")
    _flag("gender", "性別")
    allergies = p.get("allergies") or []
    if allergies:
        items.append(f"アレルギー: {len(allergies)}件登録")
    else:
        items.append("アレルギー: 未登録")
    meds = p.get("current_medications") or []
    if meds:
        items.append(f"服用中の薬: {len(meds)}件登録")
    else:
        items.append("服用中の薬: 未登録")
    history = p.get("medical_history") or []
    if history:
        items.append(f"既往歴: {len(history)}件登録")
    else:
        items.append("既往歴: 未登録")
    return items


def build_session_integrated_status(
    *,
    session_snapshot: dict[str, Any],
    profile: dict[str, Any],
    summaries: list[dict[str, Any]] | None = None,
) -> StatusDiagnosisV1:
    """セッション + 長期記憶 + β版制限の統合ステータスカード（PII マスク）。"""
    from src.content.concierge_knowledge import get_app_info, get_limitations

    snap = session_snapshot or {}
    live_msgs = snap.get("messages") or []
    archive_msgs = snap.get("message_archive") or snap.get("messages_live") or []
    msg_count = max(len(live_msgs), len(archive_msgs))
    summary_count = len(summaries or [])
    app = get_app_info()
    limits = list(get_limitations() or [])[:4]

    sections = [
        StatusSection(
            title="このセッション",
            items=[
                f"メッセージ数（概算）: {msg_count}",
                f"セッション状態: {'アクティブ' if snap.get('session_active', True) else '非アクティブ'}",
            ],
        ),
        StatusSection(title="長期記憶（マスク表示）", items=_mask_profile_for_user_display(profile)),
        StatusSection(
            title="相談要約",
            items=[f"保存件数: {summary_count}件"],
        ),
        StatusSection(
            title="β版のご案内",
            items=limits or ["市販薬の相談支援ツール（試験運用）"],
        ),
    ]
    message = (
        f"{app.get('name', '本サービス')}の利用状況です。"
        "個人を特定できる詳細は表示していません。"
    )
    return StatusDiagnosisV1(
        render="sage_status",
        variant="notice",
        title="セッションステータス",
        subtitle=str(app.get("name") or ""),
        message=message,
        sections=sections,
        hints=["症状やお薬について、具体的にお書きください。"],
        kind="session_integrated_status",
        show_feedback=True,
    )


def build_concierge_app_about_status() -> StatusDiagnosisV1:
    from src.content.concierge_knowledge import get_app_info

    app = get_app_info()
    nature = str(app.get("service_nature") or "").strip().rstrip("。")
    not_a = str(app.get("explicitly_not") or "").strip().rstrip("。")
    purpose = str(app.get("purpose") or "").strip().rstrip("。")
    parts = []
    if nature:
        parts.append(f"こちらは{nature}です")
    if not_a:
        parts.append(not_a)
    if purpose:
        parts.append(purpose)
    message = "。".join(parts) + ("。" if parts else "")
    return StatusDiagnosisV1(
        render="sage_status",
        variant="notice",
        title="このツールについて",
        subtitle=str(app.get("name") or ""),
        message=message,
        hints=[],
        kind="concierge_app_about",
        show_feedback=True,
    )
