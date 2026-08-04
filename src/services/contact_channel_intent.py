"""連絡窓口・外部チャネル（LINE / 運営者）に関するユーザー意図の一般分類。



特定フレーズへの個別対応ではなく、チャネル種別（友だち追加 / 運営連絡 / 個人属性 / 技術）を切り分ける。

会話履歴に基づくフォローアップ（案内カード・連絡先の再表示依頼等）もここで扱う。

"""

from __future__ import annotations



import re

from typing import Any, Literal, Optional



ContactChannelKind = Literal[

    "line_account",

    "operator_contact",

    "operator_identity",

    "line_technical",

]



_LINE_TOKEN_RE = re.compile(r"line|ライン|ＬＩＮＥ", re.I)



_LINE_ACCOUNT_INTENT_RE = re.compile(

    r"(?:"

    r"(?:line|ライン|ＬＩＮＥ).{0,28}"

    r"(?:リンク|link|url|友達|友だち|追加|公式|qr|アカウント|account|id|コード|登録|フォロー|掲載)"

    r"|(?:リンク|link|url|qr|友達|友だち|追加).{0,20}(?:line|ライン|ＬＩＮＥ)"

    r"|(?:line|ライン|ＬＩＮＥ).{0,12}(?:を|の|は|って)?.{0,10}"

    r"(?:教えて|教え|ください|知りたい|欲しい|ほしい|ある|ない|使える|どこ|見せ)"

    r"|(?:この|本|当|このアプリ|アプリ|ツール|サービス|チャット|スマホ|携帯|スマートフォン).{0,24}"

    r"(?:line|ライン|ＬＩＮＥ)"

    r"|(?:line|ライン|ＬＩＮＥ).{0,16}(?:から|で|上).{0,10}(?:相談|使|利用|話|続|始)"

    r"|(?:line|ライン|ＬＩＮＥ).{0,12}(?:アプリ|版|bot|ボット|チャット|公式)"

    r"|add.{0,10}(?:line|friend)|line.{0,10}friend"

    r")",

    re.I,

)



_LINE_TECHNICAL_RE = re.compile(

    r"webhook|サーバ|サーバー|ホスト|インフラ|messaging\s*api|gcp|cloud\s*run"

    r"|連携.{0,10}(?:仕組み|構成|経路|どう|何で|アーキ)"

    r"|保存|データ|引き継ぎ|長期記憶|どこで(?:動|処理|ホスト|受信)"

    r"|(?:line|ライン).{0,16}(?:どこ|動|ホスト|webhook|サーバ)",

    re.I,

)



_OPERATOR_IDENTITY_RE = re.compile(

    r"(?:運営者|開発者|制作者|作者|作成者|開発した人|作った人|管理人|運用者).{0,16}"

    r"(?:誰|だれ|名前|氏名|大学|所属|どこ|どちら|プロフィール)"

    r"|(?:誰|だれ).{0,16}(?:作|開発|運営|作成|作って).{0,8}(?:の|か|？|\?|人|者)"

    r"|(?:作|開発|作成)(?:った|した)?.{0,6}(?:人|者).{0,10}(?:教え|誰|だれ|は|？|\?)"

    r"|(?:どこ|どちら|何).{0,12}(?:大学|学部|学科|研究室).{0,10}(?:の|が|は|人|？|\?)?"

    r"|(?:大学|学部|学科|研究室).{0,10}(?:どこ|どちら|何|教え)"

    r"|(?:運営|開発).{0,8}(?:主体|元|背景|会社|組織)",

    re.I,

)



_OPERATOR_CONTACT_RE = re.compile(

    r"(?:運営者|連絡先|お問い合わせ|問い合わせ|問合せ|不具合|バグ|bug|メール|mail|連絡)"

    r"|(?:報告|連絡|問い合わせ|問合せ).{0,8}(?:方法|先|フォーム|したい|ください)"

    r"|(?:開発者|運営).{0,8}(?:に|へ).{0,8}(?:連絡|問い合わせ|報告)"

    r"|(?:forms\.gle|不具合報告)",

    re.I,

)



_CONTACT_CHANNEL_SIGNAL_RE = re.compile(

    r"line|ライン|ＬＩＮＥ|運営|開発者|連絡|問い合わせ|問合せ|不具合|メール|qr|友達|友だち"

    r"|公式|アカウント|url|リンク|報告|バグ|案内カード|フォーム",

    re.I,

)



_LINE_ACCOUNT_FOLLOWUP_RE = re.compile(

    r"^(?:"

    r"リンク|url|qr|コード|友だち|友達|追加|もう一度|再度|それ|そのリンク|そのqr|掲載"

    r").{0,16}[?？!！。]*$",

    re.I,

)



_LINE_CONTEXT_FOLLOWUP_RE = re.compile(

    r"(?:リンク|url|qr|コード|友だち|友達|追加|公式|アカウント)",

    re.I,

)



# 本サービスのお問い合わせ UI カード（店舗案内・商品パッケージではない）

_SERVICE_CONTACT_UI_RE = re.compile(

    r"案内カード|連絡先(?:カード|の)?|お問い合わせ(?:先|カード)?|不具合報告(?:フォーム|カード)?"

    r"|問い合わせ(?:先|フォーム)?|メール(?:アドレス|は)?|forms\.gle",

    re.I,

)



_OPERATOR_PRIOR_KINDS = frozenset({

    "concierge_operator",

    "concierge_doc_operator",

})



_OPERATOR_CONTEXT_HINT_RE = re.compile(

    r"案内カード|連絡先|お問い合わせ|問い合わせ|メール|フォーム|不具合報告|下記",

    re.I,

)



_SHORT_CONTACT_FOLLOWUP_RE = re.compile(

    r"^(?:"

    r"見せて|見せ|表示|教えて|教え|もう一度|再度|それ|そのカード|カード|"

    r"連絡先|メール|フォーム|問い合わせ|どこ|載って|書いて"

    r").{0,20}[?？!！。]*$",

    re.I,

)



_STORE_PRODUCT_CARD_RE = re.compile(

    r"売り場|店内|商品|パッケージ|包装|OTC|市販薬|薬局|ドラッグ|レジ|棚",

    re.I,

)





def _last_bot_diagnosis_kind(history: Optional[list]) -> str:

    if not history:

        return ""

    for msg in reversed(history):

        if not isinstance(msg, dict) or msg.get("type") != "bot":

            continue

        diag = msg.get("diagnosis") or {}

        kind = str(diag.get("kind") or "").strip()

        if kind:

            return kind

        ci = str(msg.get("concierge_intent") or "").strip()

        if ci == "doc_operator":

            return "concierge_doc_operator"

        if msg.get("concierge_intent") == "capabilities":

            content = str(msg.get("content") or "")

            if "LINE で相談" in content or "concierge_line_account" in content:

                return "concierge_line_account"

    return ""





def _last_bot_message_text(history: Optional[list]) -> str:

    if not history:

        return ""

    for msg in reversed(history):

        if not isinstance(msg, dict) or msg.get("type") != "bot":

            continue

        diag = msg.get("diagnosis") or {}

        parts = [

            str(diag.get("message") or ""),

            str(diag.get("title") or ""),

        ]

        for sec in diag.get("sections") or []:

            if isinstance(sec, dict):

                parts.append(str(sec.get("html") or ""))

                parts.extend(str(x) for x in (sec.get("items") or []))

        return "\n".join(p for p in parts if p)

    return ""





def _recent_user_mentioned_line(history: Optional[list], *, turns: int = 4) -> bool:

    if not history:

        return False

    count = 0

    for msg in reversed(history):

        if not isinstance(msg, dict) or msg.get("type") != "user":

            continue

        text = str(msg.get("content") or "")

        if _LINE_TOKEN_RE.search(text):

            return True

        count += 1

        if count >= turns:

            break

    return False





def _prior_operator_context(history: Optional[list]) -> bool:
    """直近の会話が運営者・お問い合わせトピックか。"""
    if not history:
        return False
    if _last_bot_diagnosis_kind(history) in _OPERATOR_PRIOR_KINDS:
        return True
    if _OPERATOR_CONTEXT_HINT_RE.search(_last_bot_message_text(history)):
        return True
    for msg in reversed(history):
        if not isinstance(msg, dict):
            continue
        if msg.get("concierge_intent") == "doc_operator":
            return True
    for msg in reversed(history):
        if not isinstance(msg, dict) or msg.get("type") != "user":
            continue
        text = str(msg.get("content") or "")
        if _OPERATOR_IDENTITY_RE.search(text) or _OPERATOR_CONTACT_RE.search(text):
            return True
        if re.search(r"運用者|運営者|開発者", text):
            return True
        break
    return False





def is_service_contact_ui_request(

    text: str,

    *,

    history: Optional[list] = None,

) -> bool:

    """

    本サービスのお問い合わせ案内カードに関する依頼か（店舗・商品画像ではない）。

    medicine_qa / store ルートから除外するための一般判定。

    """

    t = (text or "").strip()

    if not t:

        return False

    if _STORE_PRODUCT_CARD_RE.search(t) and not _SERVICE_CONTACT_UI_RE.search(t):

        return False

    if _SERVICE_CONTACT_UI_RE.search(t):

        return True

    if history and _prior_operator_context(history):

        if _SHORT_CONTACT_FOLLOWUP_RE.match(t):

            return True

        if len(t) <= 28 and re.search(

            r"見せ|教え|表示|載|書い|送|フォーム|メール|連絡|問い合わせ|どこ",

            t,

        ):

            return True

    return False





def normalize_operator_intro_for_inline_card(intro_text: str) -> str:

    """同一カード内に連絡先がある場合、誤解を招く「直後の案内カード」表現を置換。"""

    text = (intro_text or "").strip()

    if not text:

        return text

    text = re.sub(

        r"直後の案内カード(?:に(?:は|記載|あり)|の)",

        "下記のお問い合わせ欄",

        text,

    )

    text = re.sub(

        r"この直後の案内カード",

        "下記",

        text,

    )

    text = re.sub(

        r"案内カードに(?:は|記載|あり)",

        "下記にお問い合わせ先を掲載して",

        text,

    )

    return text





def classify_contact_channel_question(

    text: str,

    *,

    history: Optional[list] = None,

) -> Optional[ContactChannelKind]:

    """連絡チャネル系の質問を分類。該当しなければ None。"""

    t = (text or "").strip()

    if not t:

        return None



    if is_service_contact_ui_request(t, history=history):

        return "operator_contact"



    last_kind = _last_bot_diagnosis_kind(history)

    if last_kind == "concierge_line_account":

        if _LINE_ACCOUNT_FOLLOWUP_RE.match(t) or _LINE_CONTEXT_FOLLOWUP_RE.search(t):

            return "line_account"

        if len(t) <= 24 and re.search(r"(?:教えて|もう一度|再度|見せ)", t):

            return "line_account"



    if _recent_user_mentioned_line(history) and _LINE_CONTEXT_FOLLOWUP_RE.search(t):

        if not _OPERATOR_IDENTITY_RE.search(t):

            return "line_account"



    has_line = bool(_LINE_TOKEN_RE.search(t))

    if has_line:

        if _LINE_TECHNICAL_RE.search(t):

            return "line_technical"

        if _LINE_ACCOUNT_INTENT_RE.search(t):

            return "line_account"

        if _OPERATOR_IDENTITY_RE.search(t) and not _LINE_ACCOUNT_INTENT_RE.search(t):

            return "operator_identity"



    if _OPERATOR_IDENTITY_RE.search(t) and not has_line:

        return "operator_identity"



    if _OPERATOR_CONTACT_RE.search(t):

        if has_line and _LINE_ACCOUNT_INTENT_RE.search(t):

            return "line_account"

        return "operator_contact"



    if history and _prior_operator_context(history) and len(t) <= 32:

        if re.search(r"^(?:それ|その|もう一度|再度)", t):

            return "operator_contact"



    return None





def is_line_account_link_question(

    text: str,

    *,

    history: Optional[list] = None,

) -> bool:

    kind = classify_contact_channel_question(text, history=history)

    return kind == "line_account"





def is_operator_identity_question(text: str, *, history: Optional[list] = None) -> bool:

    return classify_contact_channel_question(text, history=history) == "operator_identity"





def is_operator_contact_question(text: str, *, history: Optional[list] = None) -> bool:

    kind = classify_contact_channel_question(text, history=history)

    return kind in ("operator_contact", "operator_identity")





def contact_channel_to_concierge_intent(kind: Optional[ContactChannelKind]) -> Optional[str]:

    if kind == "line_account":

        return "capabilities"

    if kind in ("operator_contact", "operator_identity"):

        return "doc_operator"

    if kind == "line_technical":

        return "architecture"

    return None





def should_use_line_account_payload(

    text: str,

    *,

    history: Optional[list] = None,

) -> bool:

    return is_line_account_link_question(text, history=history)





def classify_contact_channel_llm(

    text: str,

    client: Any,

    *,

    history: Optional[list] = None,

    session_id: Optional[str] = None,

) -> Optional[ContactChannelKind]:

    """曖昧な連絡チャネル質問のみ LLM で分類（regex 未決定時）。"""

    t = (text or "").strip()

    if not t or len(t) > 120:

        return None



    rule_kind = classify_contact_channel_question(t, history=history)

    if rule_kind:

        return None



    if not _CONTACT_CHANNEL_SIGNAL_RE.search(t) and not (

        history and _prior_operator_context(history) and len(t) <= 40

    ):

        return None



    hist_lines = []

    for msg in (history or [])[-6:]:

        if isinstance(msg, dict):

            role = msg.get("type") or msg.get("role") or "user"

            content = str(msg.get("content") or "")[:160]

            hist_lines.append(f"{role}: {content}")

    hist_block = "\n".join(hist_lines) or "（なし）"

    last_bot = _last_bot_message_text(history)[:300] if history else ""



    prompt = f"""市販薬相談チャットへの発言が、次のどれに該当するか JSON で答えてください。



- line_account: 本サービスの LINE 公式アカウント URL・友だち追加・QR（利用者向け）

- operator_contact: 不具合報告・お問い合わせ・メール等の運営連絡先、または直前の運営者案内に続く「案内カード見せて」「連絡先は？」等

- operator_identity: 運営者の氏名・所属・大学など個人属性の開示要求

- line_technical: LINE 連携の技術・インフラ・Webhook・データ保存の仕組み

- none: 上記以外（症状相談・薬の質問・店舗の案内カード・商品画像など）



【直前ボット応答の抜粋】

{last_bot or "（なし）"}



【会話履歴】

{hist_block}



【発言】

{t}



{{"kind": "line_account|operator_contact|operator_identity|line_technical|none", "confidence": 0.0-1.0}}

"""

    try:

        from src.core.llm_client import chat_completion_create



        resp = chat_completion_create(

            client,

            model_role="concierge",

            path="contact_channel.classify",

            messages=[

                {"role": "system", "content": "JSONのみ返してください。"},

                {"role": "user", "content": prompt},

            ],

            temperature=0.0,

            max_tokens=80,

            response_format={"type": "json_object"},

            session_id=session_id,

        )

        import json



        raw = (resp.choices[0].message.content or "").strip()

        start, end = raw.find("{"), raw.rfind("}")

        if start < 0 or end <= start:

            return None

        data = json.loads(raw[start : end + 1])

        kind = str(data.get("kind") or "none").lower()

        conf = float(data.get("confidence") or 0)

        if conf < 0.55 or kind == "none":

            return None

        if kind in (

            "line_account",

            "operator_contact",

            "operator_identity",

            "line_technical",

        ):

            return kind  # type: ignore[return-value]

    except Exception:

        return None

    return None


