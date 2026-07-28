"""ConciergeAgent 向け意図分類（高速パスのみ。メタ意図は meta_triage.py）"""

from __future__ import annotations



import re

from typing import Literal, Optional



from src.utils.input_helpers import is_symptom_input



ConciergeIntent = Literal[
    "greeting",
    "thanks",
    "capabilities",
    "architecture",
    "app_about",
    "doc_privacy",
    "doc_terms",
    "doc_operator",
    "doc_consultation",
    "doc_app_overview",
    "doc_changelog",
    "chitchat",
    "redirect",
    "medical_handoff",
    "session_ops",
]



# 挨拶・感謝は完全一致（正規化後）

_EXACT_GREETINGS = frozenset({

    "こんにちは",

    "こんばんは",

    "おはよう",

    "おはようございます",

    "はじめまして",

    "初めまして",

    "hello",

    "hi",

    "hey",

    "yo",

    "good morning",

    "good evening",

    # カジュアル挨拶（短い入力で症状不明判定されやすいもの）

    "やあ",

    "やー",

    "やっほ",

    "やっほー",

    "やほ",

    "よー",

    "うい",

    "うぃ",

})



_EXACT_THANKS = frozenset({

    "ありがとう",

    "ありがとうございます",

    "どうも",

    "どうもありがとう",

    "thanks",

    "thank you",

    "サンキュー",

    "サンクス",

})

CONCIERGE_META_INTENTS = frozenset({
    "capabilities",
    "architecture",
    "app_about",
    "doc_privacy",
    "doc_terms",
    "doc_operator",
    "doc_consultation",
    "doc_app_overview",
    "doc_changelog",
})

_LEGAL_COMPLIANCE_META_RE = re.compile(
    r"薬機法|医薬品医療機器等法|景表法|景品表示法"
    r"|(法令|法的).{0,10}(問題|違反|遵守|適合|大丈夫)"
    r"|(この|本)(サービス|アプリ|ツール|チャット).{0,16}(違法|合法|問題ない|大丈夫)"
    r"|コンプライアンス",
    re.IGNORECASE,
)


def is_legal_compliance_meta_question(text: str) -> bool:
    """薬機法・景表法等の法令・コンプライアンスに関するメタ質問（医薬品相談ではない）。"""
    t = (text or "").strip()
    if not t:
        return False
    return bool(_LEGAL_COMPLIANCE_META_RE.search(t))


def _normalize_exact(text: str) -> str:

    t = (text or "").strip().lower()

    t = re.sub(r"\s+", "", t)

    return t





def _is_medicine_consultation(text: str) -> bool:

    t = text.lower()

    if _is_medicine_term_definition(text):
        return False

    if is_legal_compliance_meta_question(text):
        return False

    if re.search(r"ルールベース|rule[\s-]?based", text, re.I) and re.search(
        r"(選び方|スコア|仕組み|アルゴリズム|どう選|推奨)", text, re.I
    ):
        return False

    if re.search(
        r"(推奨|選び方|スコア).{0,12}(仕組み|方法|内部)|仕組み.{0,12}(推奨|薬|医薬)",
        text,
        re.I,
    ):
        return False

    if re.search(r"データ.{0,12}(保存|どこ|記憶)", text):
        return False

    if re.search(r"医薬品画像|images\.yutok|/otc/", text, re.I):
        return False

    hints = (

        "薬",

        "医薬品",

        "otc",

        "市販",

        "服用",

        "飲ん",

        "副作用",

        "ドーピング",

        "競技",

        "成分",

        "飲み合わせ",

        "禁忌",

        "処方箋",

        "処方",

        "購入先",

        "入手",

    )

    return any(h in t for h in hints)


def _is_medicine_term_definition(text: str) -> bool:
    """用語の意味を尋ねる質問（OTC/市販薬の定義など）は医薬品相談扱いにしない。"""
    t = (text or "").strip()
    if not t:
        return False
    tl = t.lower()
    if not re.search(r"(って|とは|てなに|の意味|是什么|\?|？)", t):
        return False
    if re.search(r"otc", tl):
        return True
    if "市販薬" in t and not is_symptom_input(t):
        # 「市販薬とは？」等の定義質問のみ。相談・探索（「市販薬でなんとか」）は除外。
        if re.search(r"(って|とは|てなに|の意味|是什么)", t):
            return True
        return False
    return False


def triage_has_concierge_meta_intent(triage_result: dict | None) -> bool:
    intent = (triage_result or {}).get("concierge_intent")
    return intent in CONCIERGE_META_INTENTS


def should_exit_counseling_for_concierge(
    user_text: str,
    *,
    triage_result: dict | None = None,
    alt_texts: list[str] | None = None,
) -> bool:
    """カウンセリング中でも Concierge に委譲すべきメタ質問か。"""
    if triage_has_concierge_meta_intent(triage_result):
        return True
    for raw in (user_text, *(alt_texts or [])):
        text = (raw or "").strip()
        if not text:
            continue
        probed = probe_meta_concierge_intent(text)
        if probed in CONCIERGE_META_INTENTS:
            return True
        if is_legal_compliance_meta_question(text):
            return True
        if looks_like_service_identity_question(text):
            return True
        if re.search(r"(誰|だれ).{0,12}(回答|返信|答え|応答)", text):
            return True
    return False





def looks_like_user_question(text: str) -> bool:
    """ユーザーが何かを尋ねている形式か（個別フレーズ列挙なし）。"""
    t = (text or "").strip()
    if not t:
        return False
    if "?" in t or "？" in t:
        return True
    return bool(
        re.search(
            r"(ですか|ますか|でしょうか|だろうか|かな|かい|かよ|のか|んですか)$",
            t.rstrip("？?"),
        )
    )


_INQUIRY_REQUEST_RE = re.compile(
    r"教えて|教えてください|知りたい|聞きたい|説明して|話して",
    re.I,
)
_CONVERSATIONAL_REQUEST_RE = re.compile(
    r"話相手|話しかけ|付き合って|退屈|暇だから|退屈だから|寂しい|誰か.*?話|話聞いて",
    re.I,
)


def looks_like_conversational_request(text: str) -> bool:
    """雑談・会話相手を求める入力（医薬品相談ではない）。"""
    t = (text or "").strip()
    if not t:
        return False
    return bool(_CONVERSATIONAL_REQUEST_RE.search(t))


def looks_like_inquiry(text: str) -> bool:
    """疑問符・語尾がなくても、情報や説明を求める入力か。"""
    t = (text or "").strip()
    if not t:
        return False
    if looks_like_user_question(t):
        return True
    if _INQUIRY_REQUEST_RE.search(t):
        return True
    return bool(_CONVERSATIONAL_REQUEST_RE.search(t))


def looks_like_service_identity_question(text: str) -> bool:
    """
    本チャット／この場所が何であるかを問う質問（近くの施設の場所案内ではない）。

    例: ここはクリニック？ / 病院ですか / 医者ですか
    非該当: 病院はどこ？ / 近くのクリニック
    """
    t = (text or "").strip()
    if not t or not looks_like_user_question(t):
        return False
    if re.search(r"(どこ|場所|近く|周辺|店内|売場)", t):
        return False
    if re.match(
        r"^(ここ|こちら|これ|この(チャット|サービス|アプリ|ツール|ボット))(は|って)",
        t,
    ):
        return True
    if re.match(r"^(あなた|あんた)(は|って)", t):
        return True
    if re.match(
        r"^(病院|医者|医師|クリニック|診療所|診察|薬局|薬屋|ドラッグストア)(ですか|ますか|かな|かい|かよ|？|\?)",
        t,
    ):
        return True
    return False


def infer_structural_concierge_intent(
    user_text: str,
    *,
    prior_meta_intent: Optional[str] = None,
    conversation_history: Optional[list] = None,
) -> Optional[ConciergeIntent]:
    """
    短い非医療・非店舗入力を構造的に greeting とみなす（辞書登録なし）。
    meta LLM スキップ時の軽量フォールバック用。質問形式は対象外。
    """
    from src.services.concierge_agent_history import should_block_structural_greeting

    if should_block_structural_greeting(
        user_text,
        prior_intent=prior_meta_intent,
        conversation_history=conversation_history,
    ):
        return None
    text = (user_text or "").strip()
    if not text or len(text) > 12:
        return None
    try:
        from src.services.counseling_triage import detect_prescription_procurement_request

        if detect_prescription_procurement_request(text):
            return None
    except ImportError:
        pass
    try:
        from src.utils.emoji_input import is_emoji_only_message

        if is_emoji_only_message(text):
            return None
    except ImportError:
        pass
    try:
        from src.security.aggressive_input import is_aggressive_expression

        if is_aggressive_expression(text)[0]:
            return None
    except ImportError:
        pass
    if looks_like_user_question(text):
        return None
    if _is_medicine_consultation(text):
        return None
    from src.utils.input_helpers import has_explicit_symptom_signal

    if has_explicit_symptom_signal(text):
        return None
    store_hints = (
        "店",
        "売場",
        "在庫",
        "トイレ",
        "忘れ物",
        "営業",
        "駐車",
        "免税",
        "レジ",
        "どこ",
        "場所",
        "コンビニ",
        "薬",
        "医薬",
        "うんこ",
        "うんち",
        "おしっこ",
        "用を足",
    )
    if any(h in text for h in store_hints):
        return None
    return "greeting"


def classify_concierge_intent(user_text: str) -> Optional[ConciergeIntent]:

    """

    キーワードによる高速 Concierge 意図（挨拶・感謝・雑談のみ）。

    capabilities/architecture 等のメタ意図は classify_meta_concierge_intent を使用。

    """

    text = (user_text or "").strip()

    if not text:

        return None



    if _is_medicine_consultation(text):

        return None



    exact = _normalize_exact(text)

    if exact in _EXACT_GREETINGS:

        return "greeting"

    if exact in _EXACT_THANKS and len(text) < 40:

        return "thanks"



    # 雑談パターンは候補のみ（確定は meta_triage LLM）
    return None


# トリアージ LLM を省略できるメタ意図（キーワードで十分に確度高いもの）
_PRE_TRIAGE_META_INTENTS = frozenset({
    "greeting",
    "thanks",
    "capabilities",
    "architecture",
    "app_about",
    "doc_privacy",
    "doc_terms",
    "doc_operator",
    "doc_consultation",
    "doc_app_overview",
    "doc_changelog",
})

_META_PROBE_RULES: list[tuple[re.Pattern[str], ConciergeIntent]] = [
    (re.compile(r"薬機法|医薬品医療機器等法|景表法|景品表示法"), "doc_terms"),
    (re.compile(r"(法令|法的).{0,10}(問題|違反|遵守|適合|大丈夫)"), "doc_terms"),
    (re.compile(r"(この|本)(サービス|アプリ|ツール|チャット).{0,16}(違法|合法|問題ない)"), "doc_terms"),
    (re.compile(r"プラポリ|プライバシー|個人情報|privacy", re.I), "doc_privacy"),
    (re.compile(r"利用規約|免責|禁止事項"), "doc_terms"),
    (re.compile(r"(あなた|あんた)(について|は誰|って何|は何|のこと)"), "app_about"),
    (re.compile(r"(この|本)(アプリ|ツール|ボット|チャット|サービス)(について|を教えて|の説明)"), "app_about"),
    (re.compile(r"自己紹介"), "app_about"),
    (re.compile(r"(この|本)(ツール|アプリ|ボット|チャット|サービス).{0,16}(誰|だれ).{0,8}(作|開発)"), "app_about"),
    (re.compile(r"(誰|だれ).{0,12}(作|開発|作った|作って).{0,8}(の|か)"), "app_about"),
    (re.compile(
        r"(この|本)(ツール|アプリ|ボット|チャット|サービス).{0,16}"
        r"(どうやって|どういう仕組み|どう動|何で|なにで|何を|なにを).{0,8}(動|使|動い|走|稼働)"
    ), "architecture"),
    (re.compile(r"(会話|相談|チャット|メッセージ).{0,12}(内容|履歴|データ).{0,8}(保存|どこ|残|記録)"), "architecture"),
    (re.compile(r"(この|本)(チャット|サービス|アプリ|ツール).{0,16}(GPT|OpenAI|LLM|AI|人工知能|生成AI)", re.I), "architecture"),
    (re.compile(r"(GPT|OpenAI|LLM|ChatGPT).{0,12}(使|利用|採用|ベース)", re.I), "architecture"),
    (re.compile(r"(更新履歴|最近.{0,16}(更新|変わ|新機能|改良|リリース|アップデート)|更新内容|更新.{0,6}教え|CHANGELOG|リリース履歴|変更履歴|関連更新)"), "doc_changelog"),
    (re.compile(r"what changed|recent(ly)?.*(update|change|release|app)", re.I), "doc_changelog"),
    (re.compile(r"(マルチエージェント|薬はどうやって|選び方の仕組み|内部構成)"), "architecture"),
    (re.compile(r"(技術スタック|技術構成|開発環境|使ってる技術|tech\s*stack|デプロイ|インフラ)"), "architecture"),
    (re.compile(r"Local\s*RAG|ローカル\s*RAG|local\s*rag|ナレッジベース|Knowledge\s*Base", re.I), "architecture"),
    (re.compile(r"(FastAPI|Cloud\s*Run|PostgreSQL|Gunicorn|Neon|Sage\s*Terrace)"), "architecture"),
    (re.compile(r"(ECS|ECR|CodePipeline|CodeBuild|CloudFront|Bedrock|Translate|Polly|ElastiCache|Personalize)", re.I), "architecture"),
    (re.compile(r"(AWS|GCP|クロスクラウド|cross[\s-]?cloud|Cloudflare|R2)", re.I), "architecture"),
    (re.compile(r"ルールベース|rule[\s-]?based"), "architecture"),
    (re.compile(r"データ.{0,12}(保存|どこ)"), "architecture"),
    (re.compile(r"(記憶|保存).{0,12}(どこ|仕組み|方法)"), "architecture"),
    (re.compile(r"(何ができる|できること|対応言語)"), "capabilities"),
    (re.compile(r"otc.{0,12}(って|とは|てなに|の意味)", re.I), "capabilities"),
    (re.compile(r"市販薬.{0,12}(って|とは|てなに|の意味)"), "capabilities"),
    (re.compile(r"(誰|だれ).{0,12}(回答|返信|答え|応答)"), "architecture"),
    (re.compile(r"(今|いま).{0,12}(答え|回答|返信|応答)"), "architecture"),
    (re.compile(r"(答え|回答|返信|応答).{0,12}(誰|だれ|なに|何)"), "architecture"),
    (re.compile(r"(運営者|連絡先|お問い合わせ|不具合.{0,4}報告)"), "doc_operator"),
    (re.compile(r"LINE.{0,16}(どこ|動|ホスト|Webhook|サーバ)", re.I), "architecture"),
    (re.compile(r"(CloudWatch|Cloud\s*Logging|/health|ヘルスチェック|監視|ログ(?:の|は|を|で|先|出力|確認))", re.I), "architecture"),
    (re.compile(r"(CDN|医薬品.{0,6}画像|images\.yutok|画像.{0,8}(CDN|配信|どこ))", re.I), "architecture"),
    (re.compile(r"(推奨|おすすめ|オススメ).{0,16}(ルール|LLM|AI|仕組み|ロジック|ベース)", re.I), "architecture"),
    (re.compile(r"(ルールベース|rule[_\s-]?based).{0,16}(推奨|おすすめ|市販薬|選)", re.I), "architecture"),
    (re.compile(r"Chat\s*Pipeline|IntentRouter", re.I), "architecture"),
    (re.compile(r"PhysicalOrchestrator|TriageAgent|ConciergeAgent", re.I), "architecture"),
    (re.compile(r"Comprehend\s*Medical", re.I), "architecture"),
    (re.compile(r"\bRedis\b|ElastiCache", re.I), "architecture"),
    (re.compile(r"\bWAF\b", re.I), "architecture"),
    (re.compile(r"ソースコード|公開リポジ|GitHub|github\.com", re.I), "architecture"),
    (re.compile(r"開示ポリシー|公開情報の開示", re.I), "architecture"),
    (re.compile(r"RECO_[A-Z0-9_]+|CHAT_PIPELINE_V2", re.I), "architecture"),
    (re.compile(r"(PMDA|厚労省|#7119|相談先|相談窓口)"), "doc_consultation"),
    (re.compile(r"(なぜ|どうして).{0,16}(作|開発|つく|創)"), "doc_app_overview"),
    (re.compile(r"(作成|開発).{0,8}(意図|理由|目的|きっかけ|背景|動機)"), "doc_app_overview"),
    (re.compile(r"(現状|いま|現在).{0,12}(β|ベータ|試験|運用|段階|どうな)"), "doc_app_overview"),
    (re.compile(r"(アプリの概要|開発背景|β版|ベータ版|セルフメディケーション.{0,8}(目指|実現))"), "doc_app_overview"),
    (re.compile(r"(将来|展望|この先|今後).{0,12}(どう|なに|何|ある)"), "doc_app_overview"),
    (re.compile(r"^(病院|クリニック)(ですか|？|\?)?"), "doc_app_overview"),
    (re.compile(r"医療行為.{0,8}(当た|該当)"), "doc_terms"),
    (re.compile(r"プリンシプルオブプログラミング|オブジェクト指向とは|デザインパターンとは"), "redirect"),
    (re.compile(r"(プログラミング|アルゴリズム|データ構造).{0,8}(とは|って何)"), "redirect"),
]

# Phase 3 (p3-concierge, 前半): API/SSE/rule_based 等の技術メタ質問プローブ。
# フラグ ROUTING_CONCIERGE_INTENT ON 時のみ probe_meta_concierge_intent から参照される
# （既存 _META_PROBE_RULES は無変更のまま維持し、追加のみで拡張する）。
_META_PROBE_RULES_EXTENDED: list[tuple[re.Pattern[str], ConciergeIntent]] = [
    (re.compile(r"API.{0,16}(仕組み|何|教えて|使い方|とは)", re.I), "architecture"),
    (re.compile(r"SSE|Server[\s-]?Sent[\s-]?Events?", re.I), "architecture"),
    # 既存 "ルールベース|rule[\s-]?based" はハイフン/空白のみ対応でアンダースコア非対応のため追加
    (re.compile(r"rule[_\s-]?based", re.I), "architecture"),
]


def _is_concierge_intent_routing_enabled() -> bool:
    try:
        from config.llm_flags import is_concierge_intent_routing_enabled

        return is_concierge_intent_routing_enabled()
    except ImportError:
        return False


# 本サービス app_about から除外: ユーザー自身の自己紹介
_USER_SELF_INTRO_RE = re.compile(
    r"(?:私|僕|ぼく|俺|おれ|わたし|わたくし|自分|ボク|アタシ|あたし)(?:の|は|が)?.{0,12}自己紹介",
)
# 他アプリ・他サービスの紹介依頼（「このツール/アプリ/チャット/サービス/ボット」は対象外）
_THIRD_PARTY_APP_INTRO_RE = re.compile(
    r"(?:"
    r"(?:ポケモン|ゲーム|あの|その|例の|隣の|友達の|彼の|彼女の).{0,24}(?:アプリ|アプリケーション|ツール|サービス)"
    r"|"
    r"この(?!ツール|アプリ|チャット|サービス|ボット).{0,20}(?:アプリ|アプリケーション)"
    r")"
    r".{0,16}(?:紹介|教えて|説明|とは)",
)


def is_excluded_service_app_about_request(text: str) -> bool:
    """ユーザー自身の自己紹介、または他アプリ／サービスの紹介依頼。"""
    t = (text or "").strip()
    if not t:
        return False
    if _USER_SELF_INTRO_RE.search(t):
        return True
    return bool(_THIRD_PARTY_APP_INTRO_RE.search(t))


def probe_service_app_about_request(text: str) -> bool:
    """
    本チャット／本サービス向けの自己紹介・説明要求のみ True。
    IntentRouter の app_about 補正ガード専用（他意図には使わない）。
    """
    if is_excluded_service_app_about_request(text):
        return False
    return probe_meta_concierge_intent(text) == "app_about"


_DOC_CHANGELOG_PROBE_EXCLUDE_RE = re.compile(
    r"ポケモン|ゲーム|あの|その|私|僕|ぼく|あなた|スマホ|iPhone|Android|"
    r"OS.{0,6}バージョン|人間として",
    re.I,
)


def is_excluded_doc_changelog_probe(text: str) -> bool:
    """他製品・ユーザー自身・OS 更新など本アプリ CHANGELOG 以外。"""
    return bool(_DOC_CHANGELOG_PROBE_EXCLUDE_RE.search((text or "").strip()))


_AMBIGUOUS_META_TOPIC_RE = re.compile(
    r"^(?:技術|法務|概要|アプリ|プライバシー|規約|インフラ|更新)[？?]?$"
)
# 指示語のみでトピックが不明な follow-up（文脈なし単発）
_ANAPHORA_ONLY_CLARIFY_RE = re.compile(
    r"^(?:それ|この|その|あれ|これ|そこ|ここ)"
    r"(?:について|に)?"
    r"(?:教えて|詳しく|知りたい|説明|もっと|続き)?[？?]?$",
    re.I,
)


def build_ambiguous_meta_clarification(user_text: str) -> Optional[str]:
    """probe が None の短文メタ質問向け clarifying 返答（1文）。"""
    text = (user_text or "").strip()
    if not text or len(text) > 24:
        return None
    if probe_meta_concierge_intent(text) or _is_medicine_consultation(text):
        return None
    if _AMBIGUOUS_META_TOPIC_RE.match(text) or _ANAPHORA_ONLY_CLARIFY_RE.match(text):
        return (
            "ご質問の内容をもう少し具体的にお書きください。"
            "例:「インフラ構成を教えて」「プライバシーポリシーは？」「何ができる？」"
        )
    return None


def probe_session_admin_intent(user_text: str) -> Optional[str]:
    """セッション操作（削除・要約・ステータス）のキーワードプローブ。"""
    from src.agents.session_agent import probe_session_admin_intent as _probe

    intent = _probe(user_text)
    return intent if intent else None


def probe_meta_concierge_intent(user_text: str) -> Optional[ConciergeIntent]:
    """
    メタ質問のキーワードプローブ。LLM トリアージ・meta_triage を省略する高速パス用。
    構造パターン（architecture 等）を医薬品相談ヒューリスティックより先に評価する。
    """
    text = (user_text or "").strip()
    if not text or len(text) > 120:
        return None
    for pattern, intent in _META_PROBE_RULES:
        if pattern.search(text):
            if intent == "app_about" and is_excluded_service_app_about_request(text):
                continue
            if intent == "doc_changelog" and is_excluded_doc_changelog_probe(text):
                continue
            return intent
    if _is_concierge_intent_routing_enabled():
        for pattern, intent in _META_PROBE_RULES_EXTENDED:
            if pattern.search(text):
                return intent
    if _is_medicine_consultation(text):
        return None
    return None


def resolve_pre_triage_concierge_intent(user_text: str) -> Optional[ConciergeIntent]:
    """挨拶・感謝・キーワード確定メタ意図。トリアージ前ルート対象なら intent を返す。"""
    fast = classify_concierge_intent(user_text)
    if fast in _PRE_TRIAGE_META_INTENTS:
        return fast
    probed = probe_meta_concierge_intent(user_text)
    if probed in _PRE_TRIAGE_META_INTENTS:
        return probed
    return None


def should_reset_off_topic(text: str) -> bool:

    if is_symptom_input(text):

        return True

    medicine_hints = ("薬", "医薬品", "otc", "市販", "服用", "飲ん", "副作用")

    t = text.lower()

    return any(h in t for h in medicine_hints)


