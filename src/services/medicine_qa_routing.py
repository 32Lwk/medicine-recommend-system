"""医薬品 Q&A と副作用 Q&A の意図ベース切り分け。"""
from __future__ import annotations

import html
import re
from typing import Any, Literal, Optional

from src.dialogue.routing.context_signals import extract_drug_entities

MedicineQaFocus = Literal[
    "comparison",
    "side_effect",
    "doping",
    "interaction",
    "usage",
    "ingredient",
    "age",
    "product_image",
    "general",
]

# 副作用 Q&A に限定する話題（高信頼 gate 用）
_SIDE_EFFECT_TOPIC_KEYWORDS = (
    "副作用",
    "side effect",
    "sideeffect",
    "眠くなる",
    "眠気",
    "安全",
    "飲んでいい",
    "飲んでもいい",
    "飲んで良い",
    "ダメ",
    "禁忌",
)

_SIDE_EFFECT_QA_RE = re.compile(
    r"(.+?)(?:って|は|の)(?:眠い|眠くなる|眠気|副作用|安全|飲んで(?:も)?(?:いい|良い)|ダメ)",
    re.IGNORECASE,
)

# 質問・説明依頼の最小シグナル（口語・省略含む）
_QUESTION_INTENT_RE = re.compile(
    r"[?？]|教えて|説明|とは|知りたい|どう|何が|何を|どれ|選び|見せて|見て|見たい|"
    r"普通|正常|normal|平気|大丈夫|使える|飲める|ええ|いい(?:？|\?)?|"
    r"違う|どっち|どれ|結局|入って|中身",
    re.IGNORECASE,
)

_PHOTO_KEYWORDS = (
    "写真",
    "見せて",
    "見て",
    "見たい",
    "パッケージ",
    "外観",
    "包装",
    "箱",
    "package",
    "photo",
    "画像",
    "見た目",
)
_INGREDIENT_KEYWORDS = (
    "成分",
    "主成分",
    "有効成分",
    "配合",
    "含有",
    "何が入",
    "何入",
    "入って",
    "中身",
    "active ingredient",
    "activeingredient",
)
_AGE_KEYWORDS = (
    "年齢",
    "何歳",
    "小児",
    "子供",
    "こども",
    "子ども",
    "未就学",
    "小学生",
    "中学生",
    "高校生",
    "幼稚園",
    "保育園",
    "赤ちゃん",
    "乳児",
    "幼児",
    "乳幼児",
    "妊婦",
    "妊娠",
    "授乳",
    "高齢",
    "おじい",
    "おばあ",
    "爺",
    "婆",
    "何才",
    "kids",
    "child",
    "children",
    "pregnant",
    "pregnancy",
    "elderly",
)
_AGE_GRADE_RE = re.compile(r"小[1-6１-６]|中[1-3１-３]|高[1-3１-３]|\d+\s*代")
_ANAPHORA_MARKERS = (
    "この薬",
    "その薬",
    "あの薬",
    "それ",
    "あれ",
    "先ほど",
    "さっき",
    "これ",
    "この",
    "こちら",
    "そちら",
    "あちら",
    "that",
    "this medicine",
    "the medicine",
    "the drug",
)
_DOSE_INTERVAL_RE = re.compile(r"何時間|間隔|空け|また飲|4時間|何時間おき")
_VAGUE_OPINION_RE = re.compile(
    r"^(?:どう思う|やばくない|大丈夫|平気|どうなの|どうなん)[？?。！!…]*$"
)

_SPORTS_KEYWORDS = (
    "競技",
    "ドーピング",
    "陸上",
    "マラソン",
    "大会",
    "レース",
    "試合",
    "駅伝",
    "track meet",
    "trackmeet",
    "anti-doping",
    "antidoping",
    "marathon",
    "race",
    "competition",
    "doping",
)
_INTERACTION_KEYWORDS = (
    "併用",
    "一緒に",
    "飲み合わせ",
    "相互作用",
    "同時に",
    "同時",
    "同日",
    "ダブル",
    "重ね飲み",
    "併用注意",
)
_ALCOHOL_KEYWORDS = (
    "お酒",
    "酒",
    "アルコール",
    "ビール",
    "ワイン",
    "飲酒",
    "alcohol",
    "飲んでる",
    "晩酌",
    "飲み会",
    "乾杯",
    "チューハイ",
    "酎ハイ",
    "ハイボール",
    "缶チューハイ",
)
_TRAVEL_IMPORT_KEYWORDS = (
    "空港",
    "持ち込",
    "入国",
    "海外",
    "旅行",
    "税関",
    "飛行機",
    "出国",
    "国境",
    "止められ",
    "引っか",
    "海关",
)
_SYMPTOM_RECO_ASK_RE = re.compile(
    r"市販薬|"
    r"薬(?:を|は)?(?:何|なに|ある|買|使)|"
    r"何(?:か|が)(?:いい|ええ|ある)|"
    r"何を(?:飲|使|買)|"
    r"教えて(?:ほしい|ください)?|"
    r"提案|"
    r"違う(?:ん|の)?|"
    r"じゃ(?:あ|なく)|"
    r"実(?:は|際)",
    re.IGNORECASE,
)
_SYMPTOM_PIVOT_RE = re.compile(
    r"やっぱ(?:り)?|そっち|キツ|つら|違う|"
    r"も出(?:て)?|もある|も出てき|"
    r"咳|去痰|鎮咳|鼻水|発熱|のど|喉|熱出",
    re.IGNORECASE,
)
_ELDERLY_CONTEXT_RE = re.compile(r"お年寄り|高齢|孫|ご高齢|年寄り")
_ANAPHORA_EFFICACY_RE = re.compile(r"効果|どんな|何に効|どういう")
_EFFICACY_KEYWORDS_RE = re.compile(r"効き目|効果|効く|効き|どれくらい効")
_USAGE_KEYWORDS = ("飲み方", "用法", "用量", "何錠", "いつ飲", "食後", "食前", "空腹", "ご飯", "頻度", "何回", "何度")
_SIDE_EFFECT_CAUSAL_DRINK_RE = re.compile(
    r"飲(?:ん?だ(?:ら|と|れば|後|あと)|ん?で(?:も|から|)?|む(?:と|たら|れば)|め(?:ば|る))"
)
# 副作用トピックの症状クラス（特定フレーズ列挙ではなく身体反応カテゴリ）
_SIDE_EFFECT_SYMPTOM_RE = re.compile(
    r"眠い|眠く|眠気|ガチ眠|爆睡|sleepy|drows(?:y|iness)|side\s*effects?|"
    r"だる|むか|ムカ|吐き気|nausea|dizzy|dizziness|めまい|"
    r"じんましん|発疹|皮疹|かゆ|痒|rash|"
    r"お腹|胃.*(?:痛|キツ|むか|ムカ|優し|負担)|(?:優し|負担).{0,4}胃|腹パン|キツ",
    re.IGNORECASE,
)
_SIDE_EFFECT_NORMALCY_RE = re.compile(
    r"普通|正常|normal|大丈夫|平気|心配|しゃーな|しゃーなし|問題|よくある|アリ",
    re.IGNORECASE,
)
_USAGE_DRINK_RE = re.compile(r"飲(?:め|み|ん|んで|む)|服用|摂取")
_USAGE_FREQUENCY_RE = re.compile(r"頻度|何回|なん回|何度|どのくらい|一日|1日|毎日|回まで")
_PICK_KEYWORDS = ("どっち", "どれが", "どれを", "どれ使", "おすすめ", "オススメ", "お勧め", "選ぶ", "選べ", "迷", "いい")
_COMPARISON_INTENT_RE = re.compile(
    r"どう違|何が違|使い分|選べな|迷っ|代わり|似て|別(?:物|の)?|"
    r"強(?:い|め|さ)|弱(?:い|め|さ)|マイルド|効き目|効(?:き|く)|"
    r"どれ(?:を|が)?(?:選|使|買|飲)|違う(?:の|ん)|同じ(?:なの|か)|"
    r"比べ|対比|ベスト|おすす|オススメ|better|which|milder",
    re.IGNORECASE,
)

_GENERIC_BOILERPLATE_MARKERS = (
    "詳細は登録販売者にご確認ください",
    "ドーピング情報を確認してください",
    "風邪薬を複数同時に内服しないでください",
    "眠気・口渇・胃腸障害などが出ることがあります",
    "推奨医薬品の情報では回答できません",
    "詳細情報を取得できませんでした",
    "飲み合わせ情報を取得できませんでした",
    "ドーピング規制の確認ができませんでした",
    "副作用情報を取得できませんでした",
)

_QA_NOISE_PHRASE_RE = re.compile(
    r"剤形(?:は|が)?(?:この情報(?:から|では|上)?)?(?:確認|明記)(?:でき|され)(?:ません|ない)"
    r"|(?:この情報(?:から|では|上)?)?(?:確認|明記)(?:でき|され)(?:ません|ない)"
)

_GENERIC_CONSULTATION_ONLY_RE = re.compile(
    r"^(?:胃潰瘍|出血|持病|他の(?:お)?薬|服用中|痛み|熱).{0,80}?"
    r"(?:医師|登録販売者).{0,40}(?:相談|ご相談)(?:してください|ください)[。]?$"
)

_COMPARISON_RULE_SECTION_KEYS = frozenset(
    {"medicine_details", "interactions", "side_effects", "consultation_advice"}
)

_QA_SECTION_KEYS = (
    "medicine_details",
    "interactions",
    "doping_check",
    "side_effects",
    "consultation_advice",
)

_FOCUS_ALLOWED_SECTIONS: dict[str, set[str]] = {
    "comparison": {"medicine_details", "interactions", "side_effects", "consultation_advice"},
    "side_effect": {"medicine_details", "side_effects", "consultation_advice"},
    "doping": {"medicine_details", "doping_check", "consultation_advice"},
    "interaction": {"medicine_details", "interactions", "consultation_advice"},
    "usage": {"medicine_details", "consultation_advice"},
    "ingredient": {"medicine_details", "side_effects", "consultation_advice"},
    "age": {"medicine_details", "consultation_advice"},
    "product_image": {"medicine_details", "consultation_advice"},
    "general": {"medicine_details", "consultation_advice"},
}

_SECTION_TITLES: dict[str, dict[str, str]] = {
    "comparison": {
        "medicine_details": "製品比較",
        "interactions": "併用・重複の注意",
        "side_effects": "副作用の違い",
        "consultation_advice": "選び方のポイント",
    },
    "side_effect": {
        "medicine_details": "医薬品の詳細",
        "side_effects": "副作用情報",
    },
    "doping": {
        "medicine_details": "医薬品の詳細",
        "doping_check": "ドーピングチェック",
    },
    "interaction": {
        "medicine_details": "医薬品の詳細",
        "interactions": "相互作用の注意",
    },
    "usage": {
        "medicine_details": "医薬品の詳細",
        "consultation_advice": "用法の注意",
    },
    "ingredient": {
        "medicine_details": "成分情報",
        "side_effects": "成分に関する注意",
    },
    "age": {
        "medicine_details": "医薬品の詳細",
        "consultation_advice": "年齢制限",
    },
    "product_image": {
        "medicine_details": "製品情報",
    },
}


def _dedupe_brand_mentions(brands: list[str]) -> list[str]:
    """同一製品の通称・略称・正式名の重複を除く（ロキソニン+ロキソ 等）。"""
    ordered = sorted(brands, key=len, reverse=True)
    out: list[str] = []
    for b in ordered:
        if any(b != kept and b in kept for kept in out):
            continue
        out.append(b)
    return out


def _extract_brand_mentions(text: str) -> list[str]:
    """通称・略称の部分一致（日本語境界対応）。"""
    q = (text or "").strip()
    if not q:
        return []
    found: list[str] = []
    from src.services.medicine_brand_resolve import MEDICINE_BRAND_HINTS

    for hint in sorted(MEDICINE_BRAND_HINTS, key=len, reverse=True):
        if hint in q and hint not in found:
            found.append(hint)
    from src.services.local_rag_query import _BRAND_SHORTHANDS

    for shorthand in sorted(_BRAND_SHORTHANDS, key=len, reverse=True):
        if shorthand in q and shorthand not in found:
            found.append(shorthand)
    return _dedupe_brand_mentions(found)


def _is_plausible_drug_mention(token: str) -> bool:
    t = (token or "").strip()
    if not t or len(t) > 20:
        return False
    from src.services.local_rag_query import _is_drug_like_token

    if _is_drug_like_token(t):
        return True
    from src.services.medicine_brand_resolve import MEDICINE_BRAND_HINTS

    return any(h in t or t in h for h in MEDICINE_BRAND_HINTS)


def _resolve_medicine_entities(
    text: str,
    *,
    conversation_history: list[dict[str, Any]] | None = None,
    recommended_medicines: list[dict[str, Any]] | None = None,
) -> list[str]:
    """通称・略称・成分・履歴・推奨から医薬品言及を統合解決。"""
    from src.services.local_rag_context import extract_context_substances

    found: list[str] = []
    for hint in _extract_brand_mentions(text):
        if hint not in found:
            found.append(hint)
    for hint in extract_drug_entities(text):
        if hint not in found and _is_plausible_drug_mention(hint):
            found.append(hint)
    for ing in _ingredients_in_text(text):
        if ing not in found and _is_plausible_drug_mention(ing):
            found.append(ing)
    for med in recommended_medicines or []:
        if not isinstance(med, dict):
            continue
        name = str(med.get("product_name") or med.get("name") or "").strip()
        if name and name not in found:
            found.append(name)
    if conversation_history:
        for substance in extract_context_substances(conversation_history):
            if (
                substance
                and substance not in found
                and _is_plausible_drug_mention(substance)
            ):
                found.append(substance)
    return found[:8]


def _distinct_brand_count(
    text: str,
    *,
    conversation_history: list[dict[str, Any]] | None = None,
    recommended_medicines: list[dict[str, Any]] | None = None,
    include_history: bool = True,
) -> int:
    """比較 intent 用 — ブランド通称の distinct 数。"""
    parts = [text or ""]
    if include_history and conversation_history:
        from src.services.local_rag_context import _history_user_texts, normalize_conversation_history

        parts.extend(_history_user_texts(normalize_conversation_history(conversation_history)))
    blob = " ".join(parts)
    brands = _extract_brand_mentions(blob)
    for med in recommended_medicines or []:
        if isinstance(med, dict):
            name = str(med.get("product_name") or med.get("name") or "").strip()
            if name and name not in brands:
                brands.append(name)
    brands = _dedupe_brand_mentions(brands)
    # イブ / イブプロフェン 等の重複を brand 先頭で粗く統合
    roots: set[str] = set()
    for b in brands:
        roots.add(b[: min(3, len(b))] if len(b) <= 4 else b)
    return len(roots)


def is_travel_import_context(text: str) -> bool:
    """海外持ち込み・空港検査など旅行文脈（家の在庫報告と区別）。"""
    return any(k in (text or "") for k in _TRAVEL_IMPORT_KEYWORDS)


def _history_has_symptom_context(
    conversation_history: list[dict[str, Any]] | None,
    recommended_medicines: list[dict[str, Any]] | None,
) -> bool:
    from src.utils.input_helpers import has_explicit_symptom_signal

    if recommended_medicines:
        return True
    if not conversation_history:
        return False
    blob = " ".join(
        str(m.get("content") or m.get("message") or "")
        for m in conversation_history[-8:]
        if isinstance(m, dict)
    )
    return has_explicit_symptom_signal(blob)


def is_symptom_recommendation_followup(
    text: str,
    *,
    conversation_history: list[dict[str, Any]] | None = None,
    recommended_medicines: list[dict[str, Any]] | None = None,
) -> bool:
    """
    症状スレッド中の「市販薬ある？」「違うん、咳」等 — 製品比較 Q&A ではなく推奨フローへ。
    """
    t = (text or "").strip()
    if not t or not _history_has_symptom_context(conversation_history, recommended_medicines):
        return False
    if any(k in t for k in ("違い", "どっち", "比較", "vs", "どう違")):
        return False
    if _distinct_brand_count(
        t,
        conversation_history=None,
        recommended_medicines=None,
        include_history=False,
    ) >= 2:
        return False
    from src.utils.input_helpers import has_explicit_symptom_signal

    if _SYMPTOM_RECO_ASK_RE.search(t):
        return True
    if has_explicit_symptom_signal(t) and not _resolve_medicine_entities(
        t,
        conversation_history=conversation_history,
        recommended_medicines=recommended_medicines,
    ):
        return True
    return False


def is_symptom_pivot_followup(
    text: str,
    *,
    conversation_history: list[dict[str, Any]] | None = None,
    recommended_medicines: list[dict[str, Any]] | None = None,
) -> bool:
    """推奨後に別症状・主訴の追加（咳も…、やっぱりそっちがキツい等）→ 再推奨。"""
    t = (text or "").strip()
    if not t or not _history_has_symptom_context(conversation_history, recommended_medicines):
        return False
    if any(k in t for k in ("違い", "どっち", "比較", "vs", "どう違")):
        return False
    from src.utils.input_helpers import has_explicit_symptom_signal

    if not has_explicit_symptom_signal(t):
        return False
    if _SYMPTOM_PIVOT_RE.search(t):
        return True
    if re.search(r"咳|去痰|鎮咳", t) and re.search(r"教えて|効く|薬|市販|ほしい|ある", t):
        return True
    return False


def is_symptom_only_initial(
    text: str,
    *,
    conversation_history: list[dict[str, Any]] | None = None,
    recommended_medicines: list[dict[str, Any]] | None = None,
) -> bool:
    """初回の症状申告のみ（薬名・履歴なし）→ Physical 優先。"""
    from src.utils.input_helpers import has_explicit_symptom_signal
    from src.services.concierge_intent import looks_like_inquiry

    t = (text or "").strip()
    if not t or not has_explicit_symptom_signal(t):
        return False
    if recommended_medicines:
        return False
    if conversation_history:
        user_turns = sum(
            1 for m in conversation_history if isinstance(m, dict) and m.get("type") == "user"
        )
        if user_turns > 0:
            return False
    if _resolve_medicine_entities(
        t,
        conversation_history=conversation_history,
        recommended_medicines=recommended_medicines,
    ):
        return False
    if looks_like_inquiry(t) and re.search(r"薬|市販|教えて|おすすめ|選", t):
        return False
    try:
        from src.services.medicine_discovery_routing import (
            has_medicine_discovery_intent,
            has_sports_medicine_context,
        )

        if has_medicine_discovery_intent(t) or has_sports_medicine_context(t):
            return False
    except ImportError:
        pass
    if looks_like_inquiry(t) and re.search(
        r"副作用|成分|違い|ドーピング|併用|飲み合わせ", t
    ):
        return False
    return True


def should_prioritize_physical_for_symptom(
    text: str,
    *,
    conversation_history: list[dict[str, Any]] | None = None,
    recommended_medicines: list[dict[str, Any]] | None = None,
) -> bool:
    """症状スレッドでは medicine_qa（成分比較）より Physical / 再推奨を優先。"""
    return (
        is_symptom_recommendation_followup(
            text,
            conversation_history=conversation_history,
            recommended_medicines=recommended_medicines,
        )
        or is_symptom_pivot_followup(
            text,
            conversation_history=conversation_history,
            recommended_medicines=recommended_medicines,
        )
        or is_symptom_only_initial(
            text,
            conversation_history=conversation_history,
            recommended_medicines=recommended_medicines,
        )
    )


def _has_travel_import_intent(
    text: str,
    *,
    conversation_history: list[dict[str, Any]] | None = None,
    recommended_medicines: list[dict[str, Any]] | None = None,
) -> bool:
    t = (text or "").strip()
    if is_travel_import_context(t):
        if recommended_medicines:
            return True
        if _resolve_medicine_entities(
            t,
            conversation_history=conversation_history,
            recommended_medicines=recommended_medicines,
        ):
            return True
    try:
        from src.services.reco_followup_signals import is_travel_thread_followup

        if is_travel_thread_followup(
            t,
            conversation_history=conversation_history,
        ):
            return True
    except ImportError:
        pass
    if conversation_history:
        blob = " ".join(
            str(m.get("content") or m.get("message") or "")
            for m in conversation_history[-6:]
            if isinstance(m, dict)
        )
        if any(
            k in blob
            for k in ("ロキソニン", "バファリン", "カロナール", "タイレノール", "イブ", "パブロン")
        ):
            if is_travel_import_context(blob) or is_travel_import_context(t):
                return True
    return False


def _has_comparison_intent(
    text: str,
    *,
    conversation_history: list[dict[str, Any]] | None = None,
    recommended_medicines: list[dict[str, Any]] | None = None,
) -> bool:
    t = (text or "").strip()
    if is_symptom_recommendation_followup(
        t,
        conversation_history=conversation_history,
        recommended_medicines=recommended_medicines,
    ):
        return False

    pick_or_diff = any(
        k in t.lower()
        for k in (
            "違い",
            "どっち",
            "どれ",
            "比較",
            "何が違",
            "結局",
            "vs",
            "which",
            "milder",
            "better",
        )
    ) or bool(_COMPARISON_INTENT_RE.search(t))

    if _is_anaphoric_reference(t) and _ANAPHORA_EFFICACY_RE.search(t) and not pick_or_diff:
        return False

    suitability = any(
        k in t
        for k in ("平気", "大丈夫", "一緒", "同時", "併用", "同日", "飲み合わせ", "OK", "ok")
    )

    rec_meds = [m for m in (recommended_medicines or []) if isinstance(m, dict)]
    if len(rec_meds) >= 2:
        if pick_or_diff and not (suitability and not pick_or_diff):
            return True
        if _is_anaphoric_reference(t) and _has_informational_intent(t) and not suitability:
            return True

    brand_count = _distinct_brand_count(
        t,
        conversation_history=None,
        recommended_medicines=recommended_medicines,
        include_history=False,
    )
    # 現発話に2剤以上でも、併用・飲み合わせ確認は comparison ではない
    if brand_count >= 2:
        if suitability and not pick_or_diff:
            return False
        return True
    if pick_or_diff and conversation_history:
        if _distinct_brand_count(
            "",
            conversation_history=conversation_history,
            recommended_medicines=recommended_medicines,
            include_history=True,
        ) >= 2:
            return True
    return False


def _has_interaction_intent(
    text: str,
    *,
    conversation_history: list[dict[str, Any]] | None = None,
    recommended_medicines: list[dict[str, Any]] | None = None,
) -> bool:
    """併用・飲み合わせ（アルコール・文脈 substance 含む）。"""
    t = (text or "").strip()
    if any(k in t for k in _INTERACTION_KEYWORDS):
        return True
    if any(k in t for k in _ALCOHOL_KEYWORDS):
        return True
    suitability = any(
        k in t for k in ("平気", "大丈夫", "使える", "飲める", "一緒", "同時", "併用", "OK", "ok")
    ) or _is_anaphoric_reference(t)
    if conversation_history and suitability:
        blob = " ".join(
            str(m.get("content") or m.get("message") or "")
            for m in conversation_history[-6:]
            if isinstance(m, dict)
        )
        if any(k in blob for k in _ALCOHOL_KEYWORDS):
            return True
    if recommended_medicines and any(k in t for k in _ALCOHOL_KEYWORDS) and suitability:
        return True
    return False


def _has_efficacy_concern_intent(text: str) -> bool:
    return bool(_EFFICACY_KEYWORDS_RE.search(text or ""))


def _normalize_ws(text: str, *, limit: int = 200) -> str:
    return re.sub(r"\s+", " ", (text or "").replace("\n", " ")).strip()[:limit]


def _ingredients_in_text(text: str) -> list[str]:
    from src.services.local_rag_router import _extract_ingredients_from_text

    return _extract_ingredients_from_text(text)


def _is_concierge_operator_card_request(text: str, *, history: list | None = None) -> bool:
    """本サービスのお問い合わせ案内カード依頼（商品画像・店舗案内ではない）。"""
    from src.services.contact_channel_intent import is_service_contact_ui_request

    return is_service_contact_ui_request(text, history=history)


def _has_product_image_intent(
    text: str,
    *,
    conversation_history: list | None = None,
) -> bool:
    t = (text or "").strip()
    if _is_concierge_operator_card_request(t, history=conversation_history):
        return False
    if any(k in t for k in _PHOTO_KEYWORDS):
        return True
    # 「見た目どんな感じ」等、提示依頼語がなくても外観を問う形
    if "見た目" in t and (
        "?" in t
        or t.endswith(("?", "？"))
        or any(k in t for k in ("どんな", "どう", "知りたい", "教えて"))
    ):
        return True
    return False


def _has_allergen_intent(
    text: str,
    *,
    conversation_history: list[dict[str, Any]] | None = None,
) -> bool:
    """成分・食物アレルギー・添加物に関する follow-up か（会話文脈優先）。"""
    t = (text or "").strip()
    if not t:
        return False
    if re.search(r"アレルギ|allerg", t, re.I):
        return True
    if re.search(r"添加物|由来成分|含まれ|入って", t) and re.search(
        r"卵|乳|小麦|そば|落花生|ピーナッツ|成分",
        t,
    ):
        return True
    if conversation_history:
        blob = " ".join(
            str(m.get("content") or m.get("message") or "")
            for m in conversation_history[-8:]
            if isinstance(m, dict)
        )
        if re.search(r"アレルギ|allerg", blob, re.I) and (
            _is_anaphoric_reference(t) or re.search(r"大丈夫|平気|影響|入って|含", t)
        ):
            return True
    return False


def _has_ingredient_intent(text: str) -> bool:
    t = (text or "").strip()
    return any(k in t for k in _INGREDIENT_KEYWORDS)


def _history_has_life_stage_context(blob: str) -> bool:
    """履歴に年齢・ライフステージ（小児〜高齢・妊娠等）の手がかりがあるか。

    学校種ごとの個別列挙ではなく、既存のライフステージ語彙＋数値年齢で見る。
    """
    if not blob:
        return False
    blob_l = blob.lower()
    if any((k in blob_l) if k.isascii() else (k in blob) for k in _AGE_KEYWORDS):
        return True
    if re.search(r"\d+歳", blob) or _AGE_GRADE_RE.search(blob):
        return True
    return False


def _looks_medicine_suitability_ask(text: str) -> bool:
    """市販薬・服用の可否を問う型か（症状の追加報告ではない）。"""
    t = (text or "").strip()
    if not t:
        return False
    # 症状追記だけ（「咳も出ている」「元気がない」等）を年齢 intent にしない
    medicineish = bool(
        re.search(r"薬|市販|OTC|服用|飲|使|解熱|鎮痛|pill|tablet|medicine|drug", t, re.I)
    )
    # 可否・適合の問い（個別副作用語の列挙ではなく「使えるか」型）
    okish = bool(
        re.search(
            r"大丈夫|平気|飲める|使える|よい|良い|いい|宜|まだ早|"
            r"いける|無理|OK|ok|safe|can\b",
            t,
            re.I,
        )
    )
    questionish = bool(re.search(r"[?？]|どう|かな|ん？|教えて|知りたい", t))
    if medicineish and (okish or questionish):
        return True
    if okish and questionish:
        return True
    return False


def _has_age_intent(
    text: str,
    *,
    conversation_history: list[dict[str, Any]] | None = None,
    user_attributes: dict[str, Any] | None = None,
) -> bool:
    """年齢・ライフステージ（小児/妊婦/高齢等）の服用可否トピックか。"""
    t = (text or "").strip()
    if any(k in t.lower() for k in _AGE_KEYWORDS):
        return True
    if re.search(r"\d+歳", t) or _AGE_GRADE_RE.search(t):
        return True
    # English: can kids take ...
    if re.search(r"\b(?:kids?|children|child|pregnant|elderly)\b", t, re.I):
        if re.search(r"\b(?:take|ok|safe|can)\b", t, re.I) or "？" in t or "?" in t:
            return True
    attrs = user_attributes or {}
    if attrs.get("age") and _looks_medicine_suitability_ask(t):
        return True
    if conversation_history:
        blob = " ".join(
            str(m.get("content") or m.get("message") or "")
            for m in conversation_history[-6:]
            if isinstance(m, dict)
        )
        if _history_has_life_stage_context(blob) and _looks_medicine_suitability_ask(t):
            return True
    return False


def _has_dose_interval_intent(text: str) -> bool:
    return bool(_DOSE_INTERVAL_RE.search(text or ""))


def _has_doping_intent(
    text: str,
    *,
    conversation_history: list[dict[str, Any]] | None = None,
) -> bool:
    t = (text or "").strip()
    if any(k in t for k in _SPORTS_KEYWORDS):
        return True
    if conversation_history:
        blob = " ".join(
            str(m.get("content") or m.get("message") or "")
            for m in conversation_history[-6:]
            if isinstance(m, dict)
        )
        if any(k in blob for k in _SPORTS_KEYWORDS):
            if any(
                k in t
                for k in ("使える", "飲める", "大丈夫", "平気", "使っていい", "使って", "OK", "ok")
            ) or _is_anaphoric_reference(t):
                return True
    return False


def _has_usage_intent(
    text: str,
    *,
    conversation_history: list[dict[str, Any]] | None = None,
    recommended_medicines: list[dict[str, Any]] | None = None,
) -> bool:
    """用法・用量・服用間隔（口語・指示語 follow-up 含む）。"""
    t = (text or "").strip()
    # how often / 頻度は用法（「飲んでいい」副作用キーワードより優先）
    if re.search(r"how\s*often|頻度|何回|何時間|間隔", t, re.I):
        if _USAGE_DRINK_RE.search(t) or any(k in t for k in ("飲", "服用", "OK", "ok", "いい")):
            return True
    # 「飲むと眠い/飲んだら副作用」等の因果表現は usage ではない
    if _SIDE_EFFECT_CAUSAL_DRINK_RE.search(t) and _has_side_effect_topic_intent(t):
        if not any(k in t for k in _USAGE_KEYWORDS) and not _USAGE_FREQUENCY_RE.search(t):
            if not _has_dose_interval_intent(t):
                return False
    if any(k in t for k in _USAGE_KEYWORDS) or _has_dose_interval_intent(t):
        return True
    if _USAGE_FREQUENCY_RE.search(t):
        # 「1日なん回まで？」のように服用語がなくても頻度質問は usage
        if (
            _USAGE_DRINK_RE.search(t)
            or any(k in t for k in ("まで", "OK", "ok", "いい", "可能"))
            or bool(recommended_medicines)
            or bool(conversation_history)
        ):
            return True
    has_context = bool(conversation_history) or bool(recommended_medicines)
    if _is_anaphoric_reference(t) and has_context:
        if _SIDE_EFFECT_CAUSAL_DRINK_RE.search(t) and _has_side_effect_topic_intent(t):
            if not any(k in t for k in _USAGE_KEYWORDS) and not _USAGE_FREQUENCY_RE.search(t):
                return False
        if _USAGE_DRINK_RE.search(t) or _USAGE_FREQUENCY_RE.search(t):
            return True
        if any(k in t for k in ("食後", "食前", "用法", "用量", "間隔", "空腹")):
            return True
    return False


def _is_anaphoric_reference(text: str) -> bool:
    """指示語・省略参照（日英）。薬剤名がなくても文脈依存の follow-up を検出。"""
    t = (text or "").strip()
    if not t:
        return False
    if any(m in t for m in _ANAPHORA_MARKERS):
        return True
    # English: "Is it okay to drink/take that?"
    if re.search(r"\b(?:that|this|it)\b", t, re.I) and re.search(
        r"\b(?:drink|take|ok|okay|safe|fine|medicine|drug|pill)\b",
        t,
        re.I,
    ):
        return True
    return False


def _has_informational_intent(text: str) -> bool:
    t = (text or "").strip()
    if _QUESTION_INTENT_RE.search(t):
        return True
    if _COMPARISON_INTENT_RE.search(t):
        return True
    if any(k in t for k in _INFORMATIONAL_TOPIC_KEYWORDS()):
        return True
    return False


def _INFORMATIONAL_TOPIC_KEYWORDS() -> tuple[str, ...]:
    return (
        *_PHOTO_KEYWORDS,
        *_INGREDIENT_KEYWORDS,
        *_AGE_KEYWORDS,
        *_USAGE_KEYWORDS,
        *_INTERACTION_KEYWORDS,
        *_SPORTS_KEYWORDS,
        *_SIDE_EFFECT_TOPIC_KEYWORDS,
        "違い",
        "比較",
        "どっち",
        "使っていい",
        "使ってもいい",
        "使える",
        "飲める",
    )


def _has_side_effect_topic_intent(text: str) -> bool:
    """multi-focus 用（写真・比較と共存可）。症状クラス＋正規性確認で判定。"""
    t = (text or "").strip()
    if not t:
        return False
    if _SIDE_EFFECT_QA_RE.search(t):
        return True
    if any(k in t for k in _SIDE_EFFECT_TOPIC_KEYWORDS):
        return True
    if _SIDE_EFFECT_SYMPTOM_RE.search(t):
        if _SIDE_EFFECT_NORMALCY_RE.search(t):
            return True
        if "?" in t or t.endswith(("?", "？")):
            return True
        # 「飲んだらじんましんっぽくなった」等、因果＋症状は副作用トピック
        if _SIDE_EFFECT_CAUSAL_DRINK_RE.search(t):
            return True
        # 「これ胃に優しい？」— 指示語＋胃負担の確認
        if _is_anaphoric_reference(t) and re.search(r"胃|優し|負担", t):
            return True
    return False


def is_strict_medicine_side_effect_question(
    text: str,
    *,
    conversation_history: list[dict[str, Any]] | None = None,
    recommended_medicines: list[dict[str, Any]] | None = None,
) -> bool:
    """副作用・眠気に関する医薬品 Q&A のみ True（gate / early route 用）。"""
    t = (text or "").strip()
    if not t:
        return False
    entities = _resolve_medicine_entities(
        t,
        conversation_history=conversation_history,
        recommended_medicines=recommended_medicines,
    )
    if _has_product_image_intent(t, conversation_history=conversation_history) or _distinct_brand_count(
        t,
        conversation_history=conversation_history,
        recommended_medicines=recommended_medicines,
    ) >= 2:
        return False
    if _SIDE_EFFECT_QA_RE.search(t):
        return True
    if not entities and not _ingredients_in_text(t):
        if not (_is_anaphoric_reference(t) and (conversation_history or recommended_medicines)):
            if not _has_side_effect_topic_intent(t):
                return False
    if any(k in t for k in _SIDE_EFFECT_TOPIC_KEYWORDS):
        return True
    if _has_side_effect_topic_intent(t):
        return True
    return False


def is_medicine_information_question(
    text: str,
    *,
    conversation_history: list[dict[str, Any]] | None = None,
    recommended_medicines: list[dict[str, Any]] | None = None,
) -> bool:
    """
    医薬品情報質問（比較・説明・選び方・写真等）。
    ブランド名・成分名・指示語+履歴のいずれかで gate を通す。
    """
    t = (text or "").strip()
    if not t:
        return False
    if _is_concierge_operator_card_request(t, history=conversation_history):
        return False

    try:
        from src.services.store_inquiry_handler import is_probable_store_inquiry_any

        if is_probable_store_inquiry_any(t):
            return False
    except Exception:
        pass

    try:
        from src.services.concierge_agent_history import is_meta_follow_up_utterance

        if is_meta_follow_up_utterance(t):
            return False
    except Exception:
        pass

    from src.utils.input_helpers import has_explicit_symptom_signal

    has_entity = bool(
        _resolve_medicine_entities(
            t,
            conversation_history=conversation_history,
            recommended_medicines=recommended_medicines,
        )
    ) or bool(_ingredients_in_text(t))
    has_context = bool(recommended_medicines) or bool(conversation_history)

    # 初回の症状申告（薬名・推奨文脈なし）は推奨フロー優先。age 等 focus だけでは Q&A 直行しない。
    if should_prioritize_physical_for_symptom(
        t,
        conversation_history=conversation_history,
        recommended_medicines=recommended_medicines,
    ):
        return False

    if has_explicit_symptom_signal(t) and not has_entity and not has_context:
        return False

    if not has_entity:
        focuses = infer_medicine_qa_focuses(
            t,
            conversation_history=conversation_history,
            recommended_medicines=recommended_medicines,
        )
        if focuses and focuses != ["general"] and _has_informational_intent(t):
            if not has_context and _is_anaphoric_reference(t):
                return False
            return True
        if _is_anaphoric_reference(t) and has_context and _has_informational_intent(t):
            if is_strict_medicine_side_effect_question(
                t,
                conversation_history=conversation_history,
                recommended_medicines=recommended_medicines,
            ):
                return len(infer_medicine_qa_focuses(
                    t,
                    conversation_history=conversation_history,
                    recommended_medicines=recommended_medicines,
                )) >= 2 or _has_product_image_intent(t, conversation_history=conversation_history)
            return True
        return False

    if is_strict_medicine_side_effect_question(
        t,
        conversation_history=conversation_history,
        recommended_medicines=recommended_medicines,
    ):
        focuses = infer_medicine_qa_focuses(
            t,
            conversation_history=conversation_history,
            recommended_medicines=recommended_medicines,
            use_llm_enrichment=False,
        )
        if len(focuses) >= 2 or _has_product_image_intent(t, conversation_history=conversation_history):
            return True
        if recommended_medicines and (
            _has_efficacy_concern_intent(t)
            or (_has_informational_intent(t) and re.search(r"どう|気になる|心配", t))
        ):
            return True
        return False

    focuses = infer_medicine_qa_focuses(
        t,
        conversation_history=conversation_history,
        recommended_medicines=recommended_medicines,
    )
    if focuses and focuses != ["general"] and _has_informational_intent(t):
        return True

    return _has_informational_intent(t)


def should_skip_recommendation_for_medicine_qa(text: str) -> bool:
    """明示的な医薬品名 Q&A では症状推奨を走らせない。"""
    from src.services.medicine_qa_eligibility import MedicineQaRoute, resolve_medicine_qa_route

    decision = resolve_medicine_qa_route(text, client=None)
    if decision.route in (MedicineQaRoute.PHYSICAL, MedicineQaRoute.CONCIERGE):
        return False
    return is_medicine_information_question(text) or is_strict_medicine_side_effect_question(
        text
    )


def infer_medicine_qa_focuses(
    user_message: str,
    *,
    conversation_history: list[dict[str, Any]] | None = None,
    recommended_medicines: list[dict[str, Any]] | None = None,
    user_attributes: dict[str, Any] | None = None,
    use_llm_enrichment: bool = True,
) -> list[MedicineQaFocus]:
    """質問意図に応じた focus 一覧（複合 intent 対応）。"""
    from src.services.request_scope_cache import get_or_set

    t = (user_message or "").strip()
    cache_key = (
        "medicine_qa_focuses",
        t,
        use_llm_enrichment,
        len(conversation_history or ()),
        len(recommended_medicines or ()),
        tuple(sorted((user_attributes or {}).keys())),
    )

    def _compute() -> list[MedicineQaFocus]:
        return _infer_medicine_qa_focuses_uncached(
            t,
            conversation_history=conversation_history,
            recommended_medicines=recommended_medicines,
            user_attributes=user_attributes,
            use_llm_enrichment=use_llm_enrichment,
        )

    return list(get_or_set(cache_key, _compute))


def _infer_medicine_qa_focuses_uncached(
    t: str,
    *,
    conversation_history: list[dict[str, Any]] | None = None,
    recommended_medicines: list[dict[str, Any]] | None = None,
    user_attributes: dict[str, Any] | None = None,
    use_llm_enrichment: bool = True,
) -> list[MedicineQaFocus]:
    focuses: list[MedicineQaFocus] = []

    try:
        from src.services.reco_followup_signals import is_wellness_alternative_topic

        if is_wellness_alternative_topic(t) and recommended_medicines:
            return ["general"]
    except ImportError:
        pass

    alcohol_in_utterance = any(k in t for k in _ALCOHOL_KEYWORDS)
    if alcohol_in_utterance and _has_interaction_intent(
        t,
        conversation_history=conversation_history,
        recommended_medicines=recommended_medicines,
    ):
        return ["interaction"]

    has_product_image = _has_product_image_intent(t, conversation_history=conversation_history)
    if has_product_image:
        focuses.append("product_image")
    if not has_product_image and _has_comparison_intent(
        t,
        conversation_history=conversation_history,
        recommended_medicines=recommended_medicines,
    ):
        focuses.append("comparison")
    if _has_travel_import_intent(
        t,
        conversation_history=conversation_history,
        recommended_medicines=recommended_medicines,
    ):
        focuses.append("doping")
    if _has_side_effect_topic_intent(t):
        focuses.append("side_effect")
    if _has_age_intent(
        t,
        conversation_history=conversation_history,
        user_attributes=user_attributes,
    ):
        focuses.append("age")
    if _has_ingredient_intent(t):
        try:
            from src.services.reco_followup_signals import is_wellness_alternative_topic

            if not is_wellness_alternative_topic(t):
                focuses.append("ingredient")
        except ImportError:
            focuses.append("ingredient")
    if _has_doping_intent(t, conversation_history=conversation_history):
        focuses.append("doping")
    if _has_allergen_intent(t, conversation_history=conversation_history):
        focuses.append("ingredient")
    if _has_interaction_intent(
        t,
        conversation_history=conversation_history,
        recommended_medicines=recommended_medicines,
    ):
        focuses.append("interaction")
    if _has_usage_intent(
        t,
        conversation_history=conversation_history,
        recommended_medicines=recommended_medicines,
    ):
        focuses.append("usage")

    if _is_anaphoric_reference(t) and _ANAPHORA_EFFICACY_RE.search(t):
        focuses = [f for f in focuses if f != "comparison"]
        if not any(f in focuses for f in ("usage", "side_effect", "age")):
            focuses.append("usage")

    if _ELDERLY_CONTEXT_RE.search(t) and recommended_medicines:
        focuses = [f for f in focuses if f not in ("comparison", "ingredient")]
        if "age" not in focuses:
            focuses.append("age")

    if not focuses:
        focuses.append("general")

    if use_llm_enrichment:
        try:
            from src.services.medicine_qa_focus_llm import enrich_medicine_qa_focuses_llm

            focuses = enrich_medicine_qa_focuses_llm(
                t,
                focuses,
                conversation_history=conversation_history,
                recommended_medicines=recommended_medicines,
            )
        except Exception:
            pass

    return focuses


def infer_medicine_qa_focus(user_message: str) -> MedicineQaFocus:
    """後方互換: 先頭 focus を返す。"""
    return infer_medicine_qa_focuses(user_message)[0]


def infer_medicine_qa_focuses_for_session(
    user_message: str,
    session: Any,
    sid: Optional[str] = None,
) -> list[MedicineQaFocus]:
    """session / DB から history・推奨履歴を解決して focus を推定。"""
    ctx = get_medicine_qa_session_context(session, sid)
    return infer_medicine_qa_focuses(
        user_message,
        conversation_history=ctx["conversation_history"],
        recommended_medicines=ctx["recommended_medicines"],
        user_attributes=ctx["user_attributes"],
    )


def get_medicine_qa_session_context(
    session: Any,
    sid: Optional[str] = None,
) -> dict[str, Any]:
    """Medicine QA routing 用の session 文脈。"""
    from src.services.medicine_thread_context import (
        expand_messages_for_llm,
        resolve_session_recommended_medicines,
    )
    from src.services.session_manager import get_session_from_db

    session_data = get_session_from_db(sid) if sid else None
    if not isinstance(session_data, dict):
        session_data = {}
    messages = list(session_data.get("messages") or (session or {}).get("messages") or [])
    history = expand_messages_for_llm(messages[-10:])
    from src.services.medicine_thread_context import resolve_session_recommended_medicines

    recommended = resolve_session_recommended_medicines(
        session,
        sid=sid,
        messages=messages,
    )
    attrs = dict(
        session_data.get("user_attributes")
        or (session or {}).get("user_attributes")
        or {}
    )
    return {
        "conversation_history": history,
        "recommended_medicines": recommended,
        "user_attributes": attrs,
    }


def should_use_medicine_qa_unified(
    focuses: list[str] | None,
    *,
    user_message: str = "",
) -> bool:
    """
    ハイブリッド route: 単独副作用のみ side_effect_qa、それ以外は medicine_qa。
    """
    fs = [f for f in (focuses or infer_medicine_qa_focuses(user_message)) if f != "general"]
    if not fs:
        return True
    if len(fs) >= 2:
        return True
    only = fs[0]
    if only in ("product_image", "comparison", "ingredient", "age", "doping", "interaction", "usage"):
        return True
    if only == "side_effect":
        if _has_efficacy_concern_intent(user_message):
            return True
        return False
    return True


def is_comparison_pick_question(text: str) -> bool:
    t = (text or "").strip()
    if "違い" in t or "どう違" in t or "何が違" in t:
        return False
    return any(k in t for k in _PICK_KEYWORDS) or bool(
        re.search(r"どれ(?:を|が)?(?:選|使|買|飲)", t)
    )


def needs_medicine_clarification(
    user_message: str,
    *,
    recommended_medicines: list[dict[str, Any]] | None = None,
    conversation_history: list[dict[str, Any]] | None = None,
) -> bool:
    """薬が特定できない曖昧発話のとき Clarify。"""
    t = (user_message or "").strip()
    if recommended_medicines:
        return False

    has_substance = False
    if conversation_history:
        from src.services.local_rag_context import extract_context_substances

        has_substance = bool(extract_context_substances(conversation_history))
    if has_substance:
        return False

    if _is_anaphoric_reference(t):
        return True
    # 「どう思う？」「やばくない？」等、評価だけ・対象薬なし
    if len(t) <= 16 and _VAGUE_OPINION_RE.search(t):
        if not _resolve_medicine_entities(t, conversation_history=conversation_history):
            return True
    return False


def is_generic_qa_boilerplate(text: str) -> bool:
    s = (text or "").strip()
    if not s:
        return True
    return any(marker in s for marker in _GENERIC_BOILERPLATE_MARKERS)


def _qa_product_line_html(name: str, description: str) -> str:
    """製品名と説明を改行崩れしにくい HTML ブロックで返す。"""
    from src.services.text_formatter import _qa_product_line_html as _product_line_html

    return _product_line_html(name, description)


def _medicine_use_detail_html(
    medicines: list[dict[str, Any]],
    user_message: str,
    *,
    limit: int = 3,
) -> str:
    from src.core.medicine.medicine_response_builder import _short_medicine_use_hint

    parts: list[str] = []
    for med in medicines[:limit]:
        name = str(med.get("product_name") or "").strip()
        if not name:
            continue
        parts.append(_qa_product_line_html(name, _short_medicine_use_hint(med, user_message)))
    return "".join(parts)


def _infer_dosage_form(med: dict[str, Any]) -> str:
    """用法・製品名から剤形を推定（不明なら空）。"""
    usage = str(med.get("usage") or "")
    name = str(med.get("product_name") or "")
    blob = f"{name} {usage}"
    if "カプセル" in blob:
        return "カプセル"
    if "錠" in blob:
        return "錠剤"
    if "散" in name or "散剤" in blob:
        return "散剤"
    if "内服液" in blob or "ドリンク" in blob:
        return "液剤"
    if any(k in name for k in ("ゲル", "ローション", "クリーム", "テープ", "パップ", "スプレー")):
        return "外用"
    return ""


def _ingredient_comparison_traits(ingredients: str) -> dict[str, str]:
    """成分系統ごとの比較用メタ（効き目・胃負担・選び方）。"""
    ing = (ingredients or "").lower()
    if "ロキソプロフェン" in ing:
        return {
            "class_label": "NSAIDs",
            "potency": "効き目が比較的早く・強めとされることが多い",
            "gi": "胃腸への負担に注意（食後・短期使用が目安）",
            "pick": "効き目を優先したい場面向き",
        }
    if "イブプロフェン" in ing and "アセトアミノフェン" not in ing:
        return {
            "class_label": "NSAIDs",
            "potency": "バランス型で広く使われる",
            "gi": "胃腸障害に注意（製品により胃粘膜保護成分あり）",
            "pick": "比較的マイルドさを重視する場面向き",
        }
    if "アスピリン" in ing:
        return {
            "class_label": "NSAIDs",
            "potency": "解熱鎮痛効果あり",
            "gi": "胃腸障害・出血に注意（空腹時は避ける）",
            "pick": "アスピリン系を選ぶ場合向き（抗凝固薬使用中は避ける）",
        }
    if "アセトアミノフェン" in ing and "イブプロフェン" not in ing:
        return {
            "class_label": "アセトアミノフェン",
            "potency": "解熱鎮痛（炎症を伴う痛みはNSAIDsより弱いことが多い）",
            "gi": "胃への負担は比較的少ないとされる",
            "pick": "胃が弱い・NSAIDsが合わない方向き",
        }
    cls = _ingredient_class_hint(ing)
    if "NSAIDs" in cls:
        return {
            "class_label": "NSAIDs",
            "potency": "解熱鎮痛効果あり",
            "gi": "胃腸障害に注意",
            "pick": "効き目重視向き（胃に弱い方は食後・短期使用に注意）",
        }
    if "アセトアミノフェン" in cls:
        return {
            "class_label": "アセトアミノフェン",
            "potency": "解熱鎮痛",
            "gi": "過量服用に注意",
            "pick": "胃に比較的優しい選択肢になりやすい",
        }
    return {"class_label": "", "potency": "", "gi": "", "pick": ""}


def _pick_hint_for_medicine(med: dict[str, Any]) -> str:
    """選好質問向けの製品別選び方ヒント。"""
    traits = _ingredient_comparison_traits(str(med.get("ingredients") or ""))
    return traits.get("pick") or ""


def _ingredient_class_hint(ingredients: str) -> str:
    ing = (ingredients or "").lower()
    if "ロキソプロフェン" in ing or "イブプロフェン" in ing or "アスピリン" in ing:
        if "アセトアミノフェン" in ing and "イブプロフェン" not in ing:
            return "アセトアミノフェン系"
        return "NSAIDs（非ステロイド性消炎鎮痛薬）系"
    if "アセトアミノフェン" in ing:
        return "アセトアミノフェン系"
    return ""


def _comparison_lines(medicines: list[dict[str, Any]], user_message: str) -> str:
    parts: list[str] = []
    for med in medicines[:4]:
        name = str(med.get("product_name") or "").strip()
        if not name:
            continue
        ingredients = _normalize_ws(str(med.get("ingredients") or ""), limit=120)
        traits = _ingredient_comparison_traits(ingredients)
        form = _infer_dosage_form(med)
        class_part = ""
        if traits["class_label"] == "NSAIDs":
            class_part = "解熱鎮痛薬、"
        elif traits["class_label"] == "アセトアミノフェン":
            class_part = "アセトアミノフェン系、"
        form_part = f"{form}。" if form else ""
        body = (
            f"主成分は{ingredients or '要確認'}（{class_part}{traits['potency']}）。"
            f"{form_part}{traits['gi']}"
        )
        parts.append(_qa_product_line_html(name, body))
    return "".join(parts)


def _comparison_interaction_note(medicines: list[dict[str, Any]]) -> str:
    names_by_class: dict[str, list[str]] = {}
    for med in medicines:
        name = str(med.get("product_name") or "").strip()
        if not name:
            continue
        cls = _ingredient_class_hint(str(med.get("ingredients") or ""))
        if cls:
            names_by_class.setdefault(cls, []).append(name)

    nsaid_names = names_by_class.get("NSAIDs（非ステロイド性消炎鎮痛薬）系", [])
    if len(nsaid_names) >= 2:
        joined = "・".join(nsaid_names[:3])
        return (
            f"{joined} はいずれも同系統の解熱鎮痛薬です。"
            "同時期に重ねて使わないでください（胃腸障害・出血リスクが増えます）。"
            "特にアスピリンとイブプロフェンの併用は避けてください。"
        )
    classes = set(names_by_class)
    if len(classes) >= 2:
        return "成分系統が異なる製品です。併用の可否は症状・年齢・持病を踏まえ登録販売者にご確認ください。"
    return ""


def _comparison_side_effect_note(medicines: list[dict[str, Any]]) -> str:
    seen: set[str] = set()
    notes: list[str] = []
    for med in medicines[:4]:
        ingredients = str(med.get("ingredients") or "")
        traits = _ingredient_comparison_traits(ingredients)
        name = str(med.get("product_name") or "").strip()
        if not name or not traits["gi"]:
            continue
        key = traits["class_label"] + traits["gi"]
        if key in seen:
            continue
        seen.add(key)
        notes.append(f"【{name}】{traits['gi']}")
    if not notes:
        return ""
    notes.append("服用後に胃痛・吐き気・黒い便・出血しやすい等があれば使用を中止して受診してください。")
    return " ".join(notes)


def _comparison_scenario_hints(medicines: list[dict[str, Any]]) -> list[str]:
    """2〜4製品比較向けの状況別選び方（成分系統ベース）。"""
    hints: list[str] = []
    classes: list[str] = []
    potency_strong: list[str] = []
    potency_mild: list[str] = []
    gi_gentle: list[str] = []

    for med in medicines[:4]:
        name = str(med.get("product_name") or "").strip()
        ing = str(med.get("ingredients") or "").lower()
        traits = _ingredient_comparison_traits(ing)
        cls = traits.get("class_label") or _ingredient_class_hint(ing)
        if cls:
            classes.append(cls)
        if "ロキソプロフェン" in ing and name:
            potency_strong.append(name)
        elif "イブプロフェン" in ing and "アセトアミノフェン" not in ing and name:
            potency_mild.append(name)
        if "アセトアミノフェン" in ing and "イブプロフェン" not in ing and name:
            gi_gentle.append(name)

    nsaid_count = sum(1 for c in classes if c == "NSAIDs")
    has_acet = any(c == "アセトアミノフェン" for c in classes)

    if potency_strong and potency_mild:
        hints.append(
            "効き目を優先するならロキソプロフェン系、"
            "胃への負担を気にするならイブプロフェン系を検討する方が多いです。"
        )
    if nsaid_count >= 2:
        hints.append(
            "同系統の解熱鎮痛薬は同時期に重ねて使わないでください。"
        )
    if has_acet and nsaid_count >= 1:
        hints.append(
            "胃が弱い・NSAIDsが合わない場合はアセトアミノフェン系が候補になりやすいです。"
        )
    if len(medicines) >= 3 and not hints:
        hints.append(
            "まず主成分の系統（解熱鎮痛薬 / アセトアミノフェン）で絞り込むと選びやすくなります。"
        )
    return hints


def _comparison_pick_advice(medicines: list[dict[str, Any]], user_message: str) -> str:
    """比較質問（2〜4製品）向けの具体的な選び方。"""
    if len(medicines) < 2:
        return ""
    blocks: list[str] = []
    for med in medicines[:4]:
        name = str(med.get("product_name") or "").strip()
        hint = _pick_hint_for_medicine(med)
        if name and hint:
            blocks.append(_qa_product_line_html(name, hint))
    for hint in _comparison_scenario_hints(medicines):
        blocks.append(f'<p class="ui-qa-product-line ui-qa-product-line--scenario">{html.escape(hint)}</p>')
    if not blocks:
        return ""
    footer = "持病・他のお薬・年齢によって最適な選択は変わります。迷ったら用途と成分を伝えて登録販売者に相談してください。"
    blocks.append(
        f'<p class="ui-qa-product-line ui-qa-product-line--footnote">{html.escape(footer)}</p>'
    )
    return "".join(blocks)


def _pick_advice_lines(medicines: list[dict[str, Any]], user_message: str) -> str:
    if len(medicines) >= 2:
        return _comparison_pick_advice(medicines, user_message)
    return ""


def _age_restriction_lines(medicines: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for med in medicines[:3]:
        name = str(med.get("product_name") or "")
        age = str(med.get("age_restriction") or med.get("年齢制限") or "").strip()
        if name and age:
            parts.append(f"**{name}**：{age}")
    return "\n".join(parts)


def _ingredient_lines(medicines: list[dict[str, Any]], user_message: str) -> str:
    parts: list[str] = []
    for med in medicines[:2]:
        name = str(med.get("product_name") or "")
        ingredients = _normalize_ws(str(med.get("ingredients") or ""), limit=160)
        if name:
            parts.append(_qa_product_line_html(name, ingredients or "要確認"))
    if not parts and _ingredients_in_text(user_message):
        ings = _ingredients_in_text(user_message)[:3]
        parts.append(
            f"**{ings[0]}** に関する一般的な情報です。"
            + (f" 同系統の代表例として市販品に含まれることがあります。" if ings else "")
        )
    return "".join(parts)


def _sections_for_focus(
    focus: str,
    user_message: str,
    meds: list[dict[str, Any]],
) -> dict[str, str]:
    out: dict[str, str] = {k: "" for k in _QA_SECTION_KEYS}

    if focus == "comparison" and meds:
        out["medicine_details"] = _comparison_lines(meds, user_message)
        interaction = _comparison_interaction_note(meds)
        if interaction:
            out["interactions"] = interaction
        side = _comparison_side_effect_note(meds)
        if side:
            out["side_effects"] = side
        pick = _pick_advice_lines(meds, user_message)
        out["consultation_advice"] = pick or (
            "持病・年齢・他のお薬の服用がある場合は、用途と成分を伝えて登録販売者に相談すると選びやすくなります。"
        )
        return out

    if focus == "side_effect" and meds:
        from src.services.medicine_side_effect_section import build_side_effect_section

        sec = build_side_effect_section(user_message, meds)
        if sec.get("side_effects"):
            out["side_effects"] = str(sec["side_effects"])
        out["medicine_details"] = _medicine_use_detail_html(meds, user_message)
        return out

    if focus == "doping" and meds:
        out["medicine_details"] = _medicine_use_detail_html(meds, user_message)
        dop_parts: list[str] = []
        for m in meds[:3]:
            name = str(m.get("product_name") or "")
            dop = str(m.get("doping_prohibited") or "")
            cat = str(m.get("competition_category") or "")
            if "あり" in dop:
                dop_parts.append(f"**{name}**：禁止物質あり（{cat or '競技会区分要確認'}）。")
            elif name:
                dop_parts.append(f"**{name}**：リスト記載の禁止物質なし（大会規定は要確認）。")
        out["doping_check"] = " ".join(dop_parts)
        return out

    if focus == "interaction" and meds:
        out["medicine_details"] = _medicine_use_detail_html(meds, user_message)
        note = _comparison_interaction_note(meds)
        if note:
            out["interactions"] = note
        return out

    if focus == "usage" and meds:
        out["medicine_details"] = _medicine_use_detail_html(meds, user_message)
        usage_bits = [
            _normalize_ws(str(m.get("usage") or ""), limit=160)
            for m in meds[:2]
            if m.get("usage")
        ]
        if usage_bits:
            out["consultation_advice"] = " ".join(usage_bits)
        return out

    if focus == "ingredient":
        out["medicine_details"] = _ingredient_lines(meds, user_message)
        return out

    if focus == "age" and meds:
        out["medicine_details"] = _medicine_use_detail_html(meds, user_message, limit=2)
        age_lines = _age_restriction_lines(meds)
        if age_lines:
            out["consultation_advice"] = age_lines
        return out

    if focus == "product_image" and meds:
        return out

    if meds:
        out["medicine_details"] = _medicine_use_detail_html(meds, user_message, limit=2)
    return out


def _merge_section_dicts(parts: list[dict[str, str]]) -> dict[str, str]:
    merged: dict[str, str] = {k: "" for k in _QA_SECTION_KEYS}
    for part in parts:
        for key, val in part.items():
            val = str(val or "").strip()
            if not val:
                continue
            if merged[key]:
                if val not in merged[key]:
                    merged[key] = merged[key] + "\n" + val
            else:
                merged[key] = val
    return merged


def build_focused_qa_sections(
    user_message: str,
    medicines: list[dict[str, Any]] | None,
    *,
    conversation_history: list[dict[str, Any]] | None = None,
    user_attributes: dict[str, Any] | None = None,
) -> dict[str, str]:
    """質問意図（複数 focus）に沿った補足フィールドを返す。"""
    try:
        from src.services.reco_followup_signals import is_wellness_alternative_topic

        if is_wellness_alternative_topic(user_message):
            names = [
                str(m.get("product_name") or m.get("name") or "").strip()
                for m in (medicines or [])[:2]
                if isinstance(m, dict)
            ]
            names = [n for n in names if n]
            prior = f"先ほどご案内した{names[0]}などの市販薬に加え、" if names else ""
            return {
                "medicine_details": "",
                "interactions": "",
                "doping_check": "",
                "side_effects": "",
                "consultation_advice": (
                    f"{prior}"
                    "サプリメント（食物繊維・マグネシウム等）は食品区分で、"
                    "医薬品の市販薬とは効能・安全性の評価基準が異なります。"
                    "自然由来を重視される場合も、症状が続くときは登録販売者に"
                    "体質・持病・併用薬を伝えて相談されると安心です。"
                ),
            }
    except ImportError:
        pass

    focuses = infer_medicine_qa_focuses(
        user_message,
        conversation_history=conversation_history,
        recommended_medicines=medicines,
        user_attributes=user_attributes,
    )
    meds = medicines or []
    parts = [_sections_for_focus(f, user_message, meds) for f in focuses if f != "general"]
    if not parts and meds:
        parts = [_sections_for_focus("general", user_message, meds)]
    return _merge_section_dicts(parts)


def _allowed_sections_for_focuses(focuses: list[str]) -> set[str]:
    allowed: set[str] = set()
    for f in focuses:
        allowed |= _FOCUS_ALLOWED_SECTIONS.get(f, _FOCUS_ALLOWED_SECTIONS["general"])
    return allowed or set(_QA_SECTION_KEYS)


def _clean_qa_text(text: str) -> str:
    """QA 本文からノイズフレーズを除去。"""
    cleaned = _QA_NOISE_PHRASE_RE.sub("", str(text or ""))
    cleaned = re.sub(r"[、。]{2,}", "。", cleaned)
    if "ui-qa-product-line" in cleaned or (
        cleaned.strip().startswith("<") and ">" in cleaned
    ):
        return cleaned.strip("、")
    cleaned = re.sub(r"\s+", " ", cleaned.replace("\n", " ")).strip()
    return cleaned.strip("、")


def _is_generic_consultation_only(text: str) -> bool:
    s = _clean_qa_text(text)
    if not s:
        return True
    if _GENERIC_CONSULTATION_ONLY_RE.match(s):
        return True
    if "ui-qa-product-line" in s:
        return False
    markers = ("登録販売者", "医師")
    if any(m in s for m in markers) and len(s) < 90:
        actionable = ("効き目", "胃", "マイルド", "向き", "優先", "併用", "NSAIDs", "アスピリン", "イブプロフェン")
        if not any(a in s for a in actionable):
            return True
    return False


def _text_overlaps(existing: str, candidate: str, *, min_len: int = 24) -> bool:
    a = _normalize_ws(existing, limit=400).rstrip("。、")
    b = _normalize_ws(candidate, limit=400).rstrip("。、")
    if not a or not b or len(b) < min_len:
        return False
    if b in a or a in b:
        return True
    if len(b) >= 40 and b[:40] in a:
        return True
    return False


def _dedupe_qa_sections(out: dict[str, Any], main_answer: str) -> dict[str, Any]:
    """セクション間・主回答との重複を除去。"""
    answer = _clean_qa_text(main_answer)
    if answer:
        out["answer"] = answer

    priority = ("medicine_details", "interactions", "side_effects", "consultation_advice")
    accumulated = answer
    for key in priority:
        val = _clean_qa_text(str(out.get(key) or ""))
        if not val:
            out[key] = ""
            continue
        if key == "consultation_advice" and "ui-qa-product-line" in val:
            out[key] = val
            accumulated = f"{accumulated} {val}".strip()
            continue
        if _is_generic_consultation_only(val) and key == "consultation_advice":
            out[key] = ""
            continue
        if accumulated and _text_overlaps(accumulated, val):
            out[key] = ""
            continue
        out[key] = val
        accumulated = f"{accumulated} {val}".strip()

    if str(out.get("interactions") or "").strip():
        inter = str(out.get("interactions") or "")
        side = _clean_qa_text(str(out.get("side_effects") or ""))
        if side:
            unique_sents: list[str] = []
            for sent in re.split(r"(?<=[。!！?？])", side):
                chunk = sent.strip()
                if chunk and not _text_overlaps(inter, chunk, min_len=12):
                    unique_sents.append(chunk)
            out["side_effects"] = "".join(unique_sents).strip()
    return out


def merge_focused_qa_sections(
    parsed: dict[str, Any],
    focused: dict[str, str],
    qa_focuses: list[str],
) -> dict[str, Any]:
    """ルールベース補足をマージ。comparison では LLM セクションを上書き。"""
    out = dict(parsed)
    prefer_rule = "comparison" in qa_focuses
    for key in _QA_SECTION_KEYS:
        rule_val = str(focused.get(key) or "").strip()
        if not rule_val:
            continue
        if prefer_rule and key in _COMPARISON_RULE_SECTION_KEYS:
            out[key] = rule_val
        elif not str(out.get(key) or "").strip():
            out[key] = rule_val
    return out


def prune_qa_response(
    chat_response: dict[str, Any],
    user_message: str,
    *,
    answer: str | None = None,
    focuses: list[str] | None = None,
) -> dict[str, Any]:
    """汎用テンプレ・回答重複・質問と無関係な補足を除去する。"""
    out = dict(chat_response)
    fs = focuses or infer_medicine_qa_focuses(user_message)
    out["qa_focus"] = fs[0] if len(fs) == 1 else "general"
    out["qa_focuses"] = fs
    main_answer = _normalize_ws(str(answer or out.get("answer") or ""), limit=500)
    allowed = _allowed_sections_for_focuses(fs)

    for key in _QA_SECTION_KEYS:
        val = _clean_qa_text(str(out.get(key) or ""))
        if key not in allowed:
            out[key] = ""
            continue
        if not val or is_generic_qa_boilerplate(val):
            out[key] = ""
            continue
        if main_answer and _text_overlaps(main_answer, val):
            out[key] = ""
            continue

    out = _dedupe_qa_sections(out, str(answer or out.get("answer") or ""))

    if not str(out.get("answer") or "").strip():
        for key in _QA_SECTION_KEYS:
            if str(out.get(key) or "").strip():
                out["answer"] = "お近くの登録販売者にご相談ください。"
                break
    return out


def section_title_for_focus(focus: str, field_key: str, default: str) -> str:
    return _SECTION_TITLES.get(focus, {}).get(field_key, default)


def section_title_for_focuses(focuses: list[str], field_key: str, default: str) -> str:
    for f in focuses:
        title = _SECTION_TITLES.get(f, {}).get(field_key)
        if title:
            return title
    return default
