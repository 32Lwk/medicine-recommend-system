"""
LLMトリアージモジュール
ユーザー入力をカテゴリに分類し、適切な処理フローに振り分ける
2段階トリアージシステムを採用：
1. 第一段階：5つのカテゴリに分類（Physical, Emotional, Emergency, Ask, Other）
2. 第二段階：Otherに分類された場合、詳細なサブカテゴリに分類

違法薬物・規制薬物の検出は、キーワードマッチングで高速かつ正確に判定
"""

import json
import logging
import re
import time
from typing import Dict, Optional, List
from openai import OpenAI

# キーワードリストのインポート
try:
    from config.keywords import (
        SEVERE_DISEASE_KEYWORDS,
        SYMPTOM_KEYWORDS,
        TREATMENT_KEYWORDS,
        URGENT_SYMPTOM_KEYWORDS
    )
except ImportError:
    # フォールバック（開発環境などでconfig/keywords.pyが存在しない場合）
    SEVERE_DISEASE_KEYWORDS = {}
    SYMPTOM_KEYWORDS = []
    TREATMENT_KEYWORDS = []
    URGENT_SYMPTOM_KEYWORDS = []
    logging.warning("config/keywords.pyが見つかりません。キーワードリストを使用できません。")

logger = logging.getLogger(__name__)

_STAGE2_SKIP_MIN_CONFIDENCE = 0.85
_STORE_STAGE1_SUBCATEGORY_PREFIX = "store_inquiry"


def _should_skip_stage2_for_store(subcategory: str, confidence: float) -> bool:
    sub = (subcategory or "").strip().lower()
    return confidence >= 0.9 and sub.startswith(_STORE_STAGE1_SUBCATEGORY_PREFIX)


def _concierge_fast_path_hint(user_text: str) -> tuple[str, str] | None:
    """挨拶・メタ質問など、第二段階 Other 詳細分類 LLM を省略できるヒント。"""
    from src.services.concierge_intent import classify_concierge_intent, probe_meta_concierge_intent

    fast = classify_concierge_intent(user_text)
    if fast:
        return fast, "exact_match_gate"
    probed = probe_meta_concierge_intent(user_text)
    if probed:
        return probed, "keyword_probe"
    return None


def _session_admin_fast_path(user_text: str) -> Optional[Dict]:
    """session_admin キーワード確定時は stage1/stage2 LLM を省略。"""
    from src.services.concierge_intent import probe_session_admin_intent

    intent = probe_session_admin_intent(user_text)
    if not intent:
        return None
    return {
        "category": "Other",
        "confidence": 1.0,
        "subcategory": "session_admin",
        "requires_immediate_action": False,
        "reasoning": f"session_admin keyword probe ({intent})",
        "session_intent": intent,
        "concierge_intent": "session_ops",
        "concierge_intent_source": "session_keyword_probe",
    }

# 違法薬物のキーワードリスト（単語一致による高速検出）
ILLEGAL_DRUG_KEYWORDS = [
    "覚醒剤", "アンフェタミン", "メタンフェタミン", "大麻", "マリファナ", "THC", 
    "ヘロイン", "モルヒネ", "オキシコドン", "LSD", "MDMA", "エクスタシー", 
    "コカイン", "危険ドラッグ", "違法薬物", "フェンタニル", "メタドン",
    "合成カンナビノイド", "スパイス", "MDPV", "α-PVP", "4-MMC", "メフェドロン",
    "バルビツール酸系", "アヘン", "モルフィン", "コデイン", "デキストロメトルファン",
    "ケタミン", "PCP", "メスカリン", "シロシビン", "DMT", "5-MeO-DMT",
    "2C-B", "2C-I", "2C-E", "DOB", "DOC", "DOM", "MDA", "MDEA",
    "GHB", "GBL", "ロヒプノール", "フルニトラゼパム", "デートレイプドラッグ"
]

# 規制薬物のキーワードリスト（単語一致による高速検出）
CONTROLLED_DRUG_KEYWORDS = [
    "向精神薬", "麻薬", "指定薬物", "処方薬の乱用", "医療用麻薬",
    "精神安定剤", "睡眠薬", "鎮痛薬", "オピオイド", "ベンゾジアゼピン系",
    "ジアゼパム", "アルプラゾラム", "ロラゼパム", "クロナゼパム", "フルニトラゼパム",
    "ゾピクロン", "エスゾピクロン", "ゾルピデム", "バルビツール", "フェノバルビタール",
    "メタドン", "ブプレノルフィン", "トラマドール", "コデイン", "ヒドロコドン",
    "オキシコドン", "モルヒネ", "フェンタニル", "レミフェンタニル", "スフェンタニル"
]


def detect_illegal_or_controlled_drug(user_text: str) -> Optional[str]:
    """
    キーワードマッチングで違法薬物・規制薬物を検出（高速・正確）
    
    単語境界を考慮した検出を行い、誤検知を防止します。
    例: "DOC"は"document"の略として使われる場合があるため、単語境界をチェック
    OTC 不眠・睡眠薬相談文脈では規制薬物キーワード（睡眠薬等）を除外します。
    
    Args:
        user_text: ユーザーの入力テキスト
    
    Returns:
        "illegal" (違法薬物) または "controlled" (規制薬物) または None
    """
    import re

    from src.handlers.chat.controlled_drug_routing import should_skip_controlled_keyword
    
    user_text_lower = user_text.lower()
    
    # 違法薬物のキーワードチェック（単語境界を考慮）
    for keyword in ILLEGAL_DRUG_KEYWORDS:
        keyword_lower = keyword.lower()
        # 短いキーワード（3文字以下）は単語境界を厳密にチェック
        # 特に"DOC"のような短いキーワードは誤検知を避けるため、単語境界を必須とする
        if len(keyword) <= 3:
            # 単語境界を考慮したパターン（前後に単語文字が来ない）
            pattern = r'\b' + re.escape(keyword_lower) + r'\b'
            if re.search(pattern, user_text_lower):
                logger.info(f"🚫 違法薬物キーワード検出（キーワードマッチング）: {keyword}")
                return "illegal"
        else:
            # 長いキーワードは部分一致でも検出（誤検知のリスクが低い）
            if keyword_lower in user_text_lower:
                logger.info(f"🚫 違法薬物キーワード検出（キーワードマッチング）: {keyword}")
                return "illegal"
    
    # 規制薬物のキーワードチェック（単語境界を考慮）
    for keyword in CONTROLLED_DRUG_KEYWORDS:
        if should_skip_controlled_keyword(keyword, user_text):
            continue
        keyword_lower = keyword.lower()
        # 短いキーワード（3文字以下）は単語境界を厳密にチェック
        if len(keyword) <= 3:
            # 単語境界を考慮したパターン（前後に単語文字が来ない）
            pattern = r'\b' + re.escape(keyword_lower) + r'\b'
            if re.search(pattern, user_text_lower):
                logger.info(f"🚫 規制薬物キーワード検出（キーワードマッチング）: {keyword}")
                return "controlled"
        else:
            # 長いキーワードは部分一致でも検出（誤検知のリスクが低い）
            if keyword_lower in user_text_lower:
                logger.info(f"🚫 規制薬物キーワード検出（キーワードマッチング）: {keyword}")
                return "controlled"
    
    return None

# LLMトリアージ結果のキャッシュ（完全一致のみ・TTL 24h）
from dataclasses import dataclass
from datetime import datetime, timedelta

_TRIAGE_CACHE_TTL = timedelta(hours=24)
_MAX_CACHE_SIZE = 500


@dataclass
class _TriageCacheEntry:
    result: Dict
    created_at: datetime


_triage_cache: Dict[str, _TriageCacheEntry] = {}


def _purge_triage_cache() -> None:
    now = datetime.now()
    expired = [k for k, v in _triage_cache.items() if now - v.created_at > _TRIAGE_CACHE_TTL]
    for k in expired:
        del _triage_cache[k]
    while len(_triage_cache) >= _MAX_CACHE_SIZE:
        oldest = next(iter(_triage_cache))
        del _triage_cache[oldest]

# 第一段階：5つのカテゴリに分類
FIRST_STAGE_TRIAGE_PROMPT = """
あなたは薬剤師です。ユーザーの入力を以下の5つのカテゴリに分類してください。

【カテゴリ】
1. Physical（身体的症状）: 頭痛、発熱、のどの痛み、腹痛など、身体的な症状
2. Emotional（精神的・感情的症状）: 緊張、不安、ストレス、恋愛の悩みなど、心理的な症状
3. Emergency（緊急性が高い症状）: 心臓が痛い、呼吸困難、激しい頭痛など、即座に医療機関受診が必要な症状
4. Ask（医薬品質問）: 既存の推奨・相談履歴がある状態での、特定医薬品・用法・副作用などの追質問
5. Other（その他）: 上記4つに該当しないすべての入力（挨拶、不明な入力、店舗案内、遺失物関連、在庫確認、周辺施設の案内、不適切な要求など）

【重要な判定ルール（優先順位順）】
- 「心臓が痛い」「心臓部分が痛い」→ Emergency（身体的・緊急性高）
- 「心が痛い」「心が痛む」→ Emotional または Ambiguous_Heart（曖昧性あり）
- 「恋の病」「好きな人」→ Emotional（比喩的表現）
【医療行為依頼フラグ（category より優先）】
ユーザーが**このチャットボット**に対して、医師による診察・診断・診療をしてほしいと依頼しているかを `medical_examination_request` で必ず判定してください。

- `medical_examination_request: true` のとき → **症状の有無にかかわらず** `category` は必ず **Other**（第二段階で inappropriate_request/medical_examination）
- `medical_examination_request: false` のとき → 通常どおり症状・相談内容で category を決める

**true の例（症状＋依頼の複合文を含む）**
- 「診察してください」「診断して」「医者に見てほしい」
- 「熱があるので診察してください」「腹が痛いので診察してください」「頭痛なので診断してください」
- 「咳がひどいです。診療お願いします」

**false の例**
- 「頭痛がする」「発熱があります」（OTC 相談のみ。診察依頼なし）
- 「診断された」「診察を受けた」（過去の報告）
- 「熱があるので病院に行った方がいいですか？」（受診助言の相談。本チャットへの診察依頼ではない）

- 「緊張する」「不安」→ Emotional
- **【最優先・Physicalより前】症状の有無にかかわらず、本チャットへの医師による診察・診断・診療の依頼（「診察してください」「熱があるので診察してください」「診断して」など）→ Other（第二段階で inappropriate_request/medical_examination）**
- **ただし「診断された」「診察を受けた」など過去の報告のみ → Physical または general_other**
- 「頭痛」「発熱」→ Physical（上記の医療行為依頼が含まれない場合のみ）
- **「眠くて寝てしまう」「仕事中に寝てしまう」「眠気が強い」「眠い」「眠たい」など、眠気（sleepiness/drowsiness）の症状を訴える → Physical**
- **「眠れない」「不眠」「睡眠不足」「寝つきが悪い」など、不眠（insomnia）の症状を訴える → Emotional**
- **「睡眠薬を教えて」「睡眠薬について」「睡眠薬を知りたい」「睡眠改善薬を教えて」など、睡眠薬に関する質問 → Emotional（不眠の症状に対するカウンセリングが必要なため）**
- **注意: 眠気と不眠は明確に区別してください。眠気は日中の眠さ、不眠は夜間に眠れない症状です。**
- **「場所を教えてください」「どこにありますか」「トイレはどこですか」など、店舗案内に関する質問 → Other**
- **「風邪薬を教えて」「風邪薬ありますか」「市販薬を教えて」など、症状・薬探索の相談 → Physical（店舗在庫確認ではない。初回は推奨フローへ。Ask は既存推奨への追質問のみ）**
- **「在庫ありますか」「取り寄せできますか」「売り場はどこですか」など、店舗の在庫・売場位置の確認 → Other（第二段階で store_inquiry/inventory）**
- **「忘れ物を拾いました」「落とし物を拾いました」など、遺失物に関する質問 → Other**
- **「処方して」「処方してください」「処方薬を教えて」「処方薬をください」など、処方要求がある場合 → Other**
- **「診察して」「診察してください」「診断して」「診療してください」など、医師による診察・診断の依頼 → Other（第二段階で inappropriate_request/medical_examination）**
- **　処方箋医薬品名 → Other（処方箋医薬品のため、当システムでは対応不可）**
- **「痩せ薬」「ダイエット薬」「減量薬」「やせ薬」などのキーワード → Other**
- **「惚れ薬」「媚薬」「恋愛薬」などのキーワード → Other**
- **「完治」「病気を治す」「予防薬」「完璧に治す」などのキーワード → ただし、具体的な症状が述べられている場合はPhysicalまたはEmotionalカテゴリに分類（例：「風邪を完治したい」→ Physical、「頭痛を治したい」→ Physical）**
- **「併存症」と「主訴」の切り分け：**
  - 既往歴としての言及（例：「糖尿病の薬を飲んでいるが、風邪を完治させたい」）→ Physical（通常フロー）
  - 治療対象としての言及（例：「糖尿病を完治したい」）→ Other
- **「心臓」を含む表現は、症状キーワード（動悸など）が含まれている場合はPhysicalカテゴリに分類（誤判定対策）**
- **「アンチエイジング」「若返り」「老化防止」「若返る」などのキーワード → Other**
- **「胸を大きく」「バストアップ」「お尻を大きく」「鼻を高く」「目を大きく」「唇を厚く」「顔の形を変える」などのキーワード → Other**
- **「毛が生える」「ハゲが治る」「育毛剤」「発毛」などのキーワード → Other（ただし、市販薬のミノキシジルなどはケースバイケースで判断）**
- **「覚醒剤」「アンフェタミン」「メタンフェタミン」「大麻」「マリファナ」「THC」「ヘロイン」「モルヒネ」「オキシコドン」「LSD」「MDMA」「エクスタシー」「コカイン」「危険ドラッグ」「違法薬物」「フェンタニル」「メタドン」「合成カンナビノイド」「スパイス」「MDPV」「α-PVP」「4-MMC」「メフェドロン」「バルビツール酸系（違法使用）」などの違法薬物、または「大麻をください」などの違法薬物の要求 → Other**
- **「向精神薬」「麻薬」「指定薬物」「処方薬の乱用」「医療用麻薬」「精神安定剤（違法使用）」「睡眠薬（違法使用）」「鎮痛薬（違法使用）」「オピオイド（違法使用）」「ベンゾジアゼピン系（違法使用）」などの規制薬物 → Other**
- **その他の挨拶や不明な入力 → Other**
- **「できること」「マルチエージェント」「あなたは誰」「自己紹介」などアプリ説明・構成の質問 → Other（ConciergeAgent が応答）**

【比喩的表現・アニメ・小説のセリフの検出】
以下のような表現は比喩的表現やアニメ・小説のセリフの可能性が高いため、OtherカテゴリまたはEmotionalカテゴリとして分類してください：
- 「心臓を捧げよ」「心臓を捧げる」→ Other（アニメ・小説のセリフ）またはEmotional（比喩的表現）
- 「心臓を[動詞]」構文で、実際の身体的症状を表していない表現
- 明らかに比喩的・文学的・創作的表現
- 会話の文脈から、実際の身体的症状ではなく比喩的表現であることが明らかな場合

【会話履歴の考慮】
会話履歴が提供されている場合、以下の点を考慮してください：
- 直前のメッセージに恋愛関連のキーワード（「失恋」「好きな人」など）がある場合、現在のメッセージも恋愛文脈として扱う
- 会話の流れから、比喩的表現であることが推測できる場合は、それを反映する
- 直前の会話に在庫・店舗案内の文脈があり「ありますか」等の短い追い質問のみ → Other（第二段階で store_inquiry/inventory）
- セッション全体の文脈を考慮して判定する

【曖昧性の処理】
「心が痛い」のような表現は、身体的症状（心臓疾患）と心理的症状の両方の可能性があります。
この場合は、subcategoryに"Ambiguous_Heart"を設定し、詳細質問を生成する必要があることを示してください。
Ambiguous_Heart の場合は requires_immediate_action を false にしてください（緊急ルートには回さない）。

【confidence（確信度）の重要性】
- confidenceは0.0-1.0の範囲で、判定の確信度を示します
- 0.75未満の場合は、判定に不確実性があることを示します（ConfidenceGate で再判定）

【分類例（参考）】
- 「こんにちは」「おはよう」→ Other（挨拶。症状なし）
- 「頭が痛い」「風邪をひいた」→ Physical（medical_examination_request が false の場合のみ）
- **「熱があるので診察してください」「腹が痛いので診察してください」→ Other, medical_examination_request: true**
- **短い症状入力**（「頭痛」「発熱」「咳」など症状キーワードのみ、2〜4文字含む）→ Physical
- 「風邪薬を教えて」「風邪薬ありますか」「市販薬を教えてください」→ Physical（初回の薬探索・推奨依頼。店舗在庫ではない）
- 「陸上競技で使える風邪薬を教えて」（初回・推奨履歴なし）→ Physical（症状＋競技条件での推奨。Ask ではない）
- 「推奨された薬は競技で使えますか」→ Ask（既存推奨への追質問）
- 「このチャットでできることを教えて」→ Other（アプリ説明。capabilities は Concierge）
- 「眠れない」→ Emotional / 「眠気が強い」→ Physical
- 低い確信度の場合は、ユーザーに確認を求める必要があります
- 比喩的表現の可能性がある場合は、confidenceを低めに設定する

【回答形式】
JSON形式で回答してください。以下の形式を厳密に守ってください：
{
    "category": "カテゴリ名（Physical/Emotional/Emergency/Ask/Other）",
    "confidence": 0.0-1.0の数値,
    "subcategory": "基本的なサブカテゴリ（例: heart_pain, anxiety, headache, drowsiness, insomnia, metaphorical, ambiguous_heart, general_other）。Otherカテゴリの場合は「general_other」を設定してください。詳細な分類は第二段階で行います。",
    "medical_examination_request": true/false,
    "requires_immediate_action": true/false,
    "reasoning": "判定理由"
}
"""

# 第二段階：Otherカテゴリの詳細分類
SECOND_STAGE_OTHER_PROMPT = """
あなたは薬剤師です。第一段階で「Other」カテゴリに分類されたユーザー入力を、以下の詳細なサブカテゴリに分類してください。

【サブカテゴリ】
1. **inappropriate_request/prescription**: 処方薬の要求（「処方して」「処方してください」「処方薬を教えて」「処方薬をください」「マンジャロ」「チルゼパチド」など。マンジャロは処方箋医薬品（チルゼパチド）のため、このカテゴリに分類。違法薬物や規制薬物ではない）
2. **inappropriate_request/weight_loss**: 痩せ薬・ダイエット薬の要求（「痩せ薬」「ダイエット薬」「減量薬」「やせ薬」など）
3. **inappropriate_request/love_potion**: 惚れ薬・媚薬の要求（「惚れ薬」「媚薬」「恋愛薬」など）
4. **inappropriate_request/cure_prevention**: 完治・予防を目的とした薬の要求（重篤な疾患のみ。例：「がんを完治する薬」「糖尿病を完治したい」「心筋梗塞を予防したい」など。ただし、以下の場合はgeneral_otherとして分類：①「治療中」キーワードがある場合、②具体的な症状が述べられている場合、③症状キーワードが含まれている場合）
5. **inappropriate_request/anti_aging**: アンチエイジング・若返りの薬の要求（「アンチエイジング」「若返り」「老化防止」「若返る」など）
6. **inappropriate_request/body_shape**: 身体の特定部位の形状変化の薬の要求（「胸を大きく」「バストアップ」「お尻を大きく」「鼻を高く」「目を大きく」「唇を厚く」「顔の形を変える」など）
7. **inappropriate_request/hair_growth**: 毛が生える・ハゲが治る薬の要求（「毛が生える」「ハゲが治る」「育毛剤」「発毛」など。ただし、市販薬のミノキシジルなどはケースバイケースで判断）
8. **inappropriate_request/illegal**: 違法薬物の要求（「覚醒剤」「アンフェタミン」「メタンフェタミン」「大麻」「マリファナ」「THC」「ヘロイン」「モルヒネ」「オキシコドン」「LSD」「MDMA」「エクスタシー」「コカイン」「危険ドラッグ」「違法薬物」「フェンタニル」「メタドン」「合成カンナビノイド」「スパイス」「MDPV」「α-PVP」「4-MMC」「メフェドロン」「バルビツール酸系（違法使用）」「大麻をください」など）
9. **inappropriate_request/controlled**: 規制薬物の要求（「向精神薬」「麻薬」「指定薬物」「処方薬の乱用」「医療用麻薬」「精神安定剤（違法使用）」「睡眠薬（違法使用）」「鎮痛薬（違法使用）」「オピオイド（違法使用）」「ベンゾジアゼピン系（違法使用）」など）
10. **inappropriate_request/medical_examination**: 医師による診察・診断・診療の依頼（「診察してください」「診断して」「医者に見てほしい」「診療お願いします」など。当システムは医療行為を行えない。**ただし「診断された」「診察を受けた」など過去の事実の述べ方、症状の説明のみは general_other または Physical**）
11. **store_inquiry**: 店舗案内に関する質問（「場所を教えてください」「どこにありますか」「トイレはどこですか」など）
12. **store_inquiry/inventory**: 在庫確認に関する質問（「ありますか」「在庫」「取り寄せ」など）
13. **store_inquiry/facilities**: 周辺施設に関する質問（「近くに」「周辺に」「コンビニ」「銀行」など）
14. **store_inquiry/tax_free**: 免税に関する質問（「免税」「免税対応」など）
15. **store_inquiry/tourism**: 観光地に関する質問（「観光地」「観光」「名所」など）
16. **store_inquiry/business_hours**: 営業時間に関する質問（「営業時間」「アクセス」「開店」「閉店」など）
17. **store_inquiry/payment**: 支払いに関する質問（「支払い」「決済」「カード」「現金」など）
18. **store_inquiry/parking**: 駐車場に関する質問（「駐車場」「パーキング」「駐車」など）
19. **store_inquiry/services**: サービスに関する質問（「サービス」「取り扱い」「配達」など）
20. **lost_and_found**: 遺失物に関する質問（「忘れ物を拾いました」「落とし物を拾いました」など）
21. **session_admin**: 相談履歴・記憶の削除・要約・ステータス確認（「履歴消して」「記憶を消して」「履歴を要約して」「ステータスを教えて」「状態は？」など）
22. **general_other**: その他の挨拶や不明な入力（メタ質問・雑談・一声の挨拶もここ — 後段 Concierge が処理）

【重要な判定ルール（優先順位順）】
- **メタ質問・雑談・挨拶**
  - アプリの機能説明・自己紹介・天気・「こんにちは」など → general_other（Concierge が後段で処理）
  - 症状・店舗案内・医薬品・在庫確認は上記 store_inquiry 等のサブカテゴリを優先
- **【最優先】違法薬物・規制薬物の検出**
  - 「覚醒剤」「アンフェタミン」「メタンフェタミン」「大麻」「マリファナ」「THC」「ヘロイン」「モルヒネ」「オキシコドン」「LSD」「MDMA」「エクスタシー」「コカイン」「危険ドラッグ」「違法薬物」「フェンタニル」「メタドン」「合成カンナビノイド」「スパイス」「MDPV」「α-PVP」「4-MMC」「メフェドロン」「バルビツール酸系（違法使用）」などのキーワード、または「大麻をください」などの要求 → inappropriate_request/illegal
  - 「向精神薬」「麻薬」「指定薬物」「処方薬の乱用」「医療用麻薬」「精神安定剤（違法使用）」「睡眠薬（違法使用）」「鎮痛薬（違法使用）」「オピオイド（違法使用）」「ベンゾジアゼピン系（違法使用）」などのキーワード → inappropriate_request/controlled
- **不適切な要求の検出**
  - 「処方して」「処方してください」「処方薬を教えて」「処方薬をください」「マンジャロ」「チルゼパチド」など → inappropriate_request/prescription（マンジャロは処方箋医薬品のため、違法薬物や規制薬物ではない）
  - 「診察して」「診察してください」「診断して」「診療してください」「医者に見てほしい」「診療お願いします」など、**本チャットに対する医療行為の依頼** → inappropriate_request/medical_examination
  - **症状＋依頼の複合文も同様**（例：「熱があるので診察してください」「腹が痛いので診察してください」→ medical_examination。Physical ではない）
  - **ただし以下は medical_examination にしない：**
    - 「診断された」「診察を受けた」など過去の事実・報告
    - 具体的な症状の説明（例：「頭痛がします」→ Physical 第一段階）
    - 医師受診の助言を求める一般的な相談で症状が主（例：「熱があるので病院に行った方がいい？」→ general_other または Physical）
  - 「痩せ薬」「ダイエット薬」「減量薬」「やせ薬」など → inappropriate_request/weight_loss
  - 「惚れ薬」「媚薬」「恋愛薬」など → inappropriate_request/love_potion
  - **重篤な疾患の完治・予防要求のみ** → inappropriate_request/cure_prevention（例：「がんを完治する薬」「糖尿病を完治したい」「心筋梗塞を予防したい」など）
  - **ただし、以下の場合はgeneral_otherとして分類：**
    - 「治療中」キーワードがある場合（例：「糖尿病で通院中だけど、鼻水が止まらない」→ general_other）
    - 具体的な症状が述べられている場合（例：「風邪を完治したい」→ general_other）
    - 症状キーワードが含まれている場合（例：「動悸を治したい」→ general_other）
  - 「アンチエイジング」「若返り」「老化防止」「若返る」など → inappropriate_request/anti_aging
  - 「胸を大きく」「バストアップ」「お尻を大きく」「鼻を高く」「目を大きく」「唇を厚く」「顔の形を変える」など → inappropriate_request/body_shape
  - 「毛が生える」「ハゲが治る」「育毛剤」「発毛」など → inappropriate_request/hair_growth
- **店舗案内関連の検出**
  - 「場所を教えてください」「どこにありますか」「トイレはどこですか」など → store_inquiry
  - 「在庫ありますか」「取り寄せ」「売り場はどこ」「店に置いてありますか」など、**店舗の在庫・売場位置**の明示 → store_inquiry/inventory
  - **「風邪薬を教えて」「風邪薬ありますか」「市販薬を教えて」など、症状・薬探索の相談 → general_other（Physical 第一段階で分類。inventory ではない）**
  - **曖昧施設の位置質問（店舗・周辺文脈なし）**: 「大学はどこ？」「病院はどこ？」など、近くに/周辺に/店内などの文脈がなく単独の施設名＋位置質問 → general_other（Concierge へ。store_inquiry/facilities ではない）**
  - **本チャットの性質を問う質問（店舗案内ではない）**: 「ここは〜？」「こちらは〜ですか」で、このチャットや画面が病院・クリニック等何であるかを確認する → general_other（app_about）。施設の場所を聞いているわけではない**
  - 「近くに」「周辺に」「コンビニ」「銀行」など → store_inquiry/facilities
  - 「免税」「免税対応」など → store_inquiry/tax_free
  - 「観光地」「観光」「名所」など → store_inquiry/tourism
  - 「営業時間」「アクセス」「開店」「閉店」など → store_inquiry/business_hours
  - 「支払い」「決済」「カード」「現金」など → store_inquiry/payment
  - 「駐車場」「パーキング」「駐車」など → store_inquiry/parking
  - 「サービス」「取り扱い」「配達」など → store_inquiry/services
- **遺失物関連の検出**
  - 「忘れ物を拾いました」「落とし物を拾いました」など → lost_and_found
- **セッション操作（記憶・履歴）**
  - 「履歴消して」「記憶を消して」「履歴を要約して」「ステータスを教えて」など → session_admin
- **会話履歴・フォローアップ**
  - 直前の会話に在庫確認・店舗案内の文脈があり、現在の入力が「ありますか」「在庫は？」など短い追い質問のみ → store_inquiry/inventory
  - 直前の会話に症状・薬探索の文脈があり、短い追い質問 → general_other（Physical 経路）
- **その他**
  - 上記に該当しない場合 → general_other

【confidence（確信度）の重要性】
- confidenceは0.0-1.0の範囲で、判定の確信度を示します
- 0.75未満の場合は、判定に不確実性があることを示します（ConfidenceGate で再判定）

【分類例（参考・Other サブカテゴリのみ）】
- 「こんにちは」「おはよう」→ general_other
- 「このチャットでできることを教えて」→ general_other（アプリ説明）
- 「トイレはどこですか」→ store_inquiry
- 「風邪薬の在庫ありますか」「取り寄せできますか」→ store_inquiry/inventory
- 「風邪薬を教えて」「市販薬ありますか」→ general_other（薬探索。Physical 第一段階で分類）
- 「大学はどこ？」「病院はどこ？」（周辺・店内文脈なし）→ general_other
- 「マンジャロを処方して」→ inappropriate_request/prescription
- 「診察してください」→ inappropriate_request/medical_examination
- 「熱があるので診察してください」→ inappropriate_request/medical_examination（症状があっても医療行為依頼を優先）
- 「診断された」→ general_other（報告。症状相談へ誘導可）
- 「診察してください」「医者に診てもらいたい」→ inappropriate_request/medical_examination
- 「診断された」（過去の報告）→ general_other
- 「履歴消して」「ステータスを教えて」→ session_admin
- 低い確信度の場合は、general_other に分類することを検討してください

【回答形式】
JSON形式で回答してください。以下の形式を厳密に守ってください：
{
    "subcategory": "詳細サブカテゴリ（上記の22種類のいずれか）",
    "confidence": 0.0-1.0の数値,
    "reasoning": "判定理由"
}
"""


def llm_triage(
    user_text: str,
    client: OpenAI,
    use_cache: bool = True,
    *,
    conversation_history: Optional[List] = None,
    long_term_memory_block: Optional[str] = None,
) -> Dict:
    """
    LLMを使用してユーザー入力をカテゴリに分類（2段階トリアージシステム）
    
    違法薬物・規制薬物の検出は、キーワードマッチングで高速かつ正確に判定
    
    Args:
        user_text: ユーザーの入力テキスト
        client: OpenAIクライアントインスタンス
        use_cache: キャッシュを使用するか（デフォルト: True）
    
    Returns:
        {
            "category": "Physical" | "Emotional" | "Emergency" | "Ask" | "Other",
            "confidence": 0.0-1.0,
            "subcategory": str,  # 詳細カテゴリ（例: "heart_pain", "anxiety", "inappropriate_request/illegal"）
            "requires_immediate_action": bool,  # 緊急対応が必要か
            "reasoning": str  # 判定理由
        }
    """
    # ステップ0: 違法薬物・規制薬物のキーワードマッチング検出（最優先・高速）
    drug_type = detect_illegal_or_controlled_drug(user_text)
    if drug_type:
        logger.info(f"🚫 違法薬物・規制薬物を検出（キーワードマッチング）: {drug_type}")
        try:
            from src.services.routing_validator import verify_routing_async

            verify_routing_async(
                route_kind="illegal_drug",
                user_text=user_text,
                decided_category="Other",
                client=client,
                extra={"drug_type": drug_type},
            )
        except Exception:
            pass
        return {
            "category": "Other",
            "confidence": 1.0,
            "subcategory": f"inappropriate_request/{drug_type}",
            "requires_immediate_action": False,
            "reasoning": f"キーワードマッチングにより{drug_type}薬物を検出"
        }

    from src.services.medical_examination_request import (
        detect_medical_examination_request_exact,
    )

    if detect_medical_examination_request_exact(user_text):
        logger.info("🚫 医療行為依頼を検出（単独フレーズ fast-path）")
        return {
            "category": "Other",
            "confidence": 1.0,
            "subcategory": "inappropriate_request/medical_examination",
            "requires_immediate_action": False,
            "reasoning": "単独フレーズ完全一致により医療行為（診察・診断）依頼を検出",
        }

    from src.services.concierge_intent import looks_like_service_identity_question

    if looks_like_service_identity_question(user_text):
        logger.info("ℹ️ サービス本人確認質問を検出（general_other → app_about）")
        return {
            "category": "Other",
            "confidence": 0.98,
            "subcategory": "general_other",
            "requires_immediate_action": False,
            "service_identity_question": True,
            "reasoning": "本チャットの性質を問う質問（店舗案内ではない）",
        }

    def _medical_examination_triage_result(reasoning: str, confidence: float = 0.98) -> Dict:
        return {
            "category": "Other",
            "confidence": confidence,
            "subcategory": "inappropriate_request/medical_examination",
            "requires_immediate_action": False,
            "medical_examination_request": True,
            "reasoning": reasoning,
        }
    
    session_fast = _session_admin_fast_path(user_text)
    if session_fast:
        logger.info(
            "⏭️ トリアージ省略: session_admin intent=%s",
            session_fast.get("session_intent"),
        )
        return session_fast

    # ステップ0b: 挨拶・メタ質問は第一段階 LLM も省略（exact_match / keyword_probe のみ）
    fast_hint = _concierge_fast_path_hint(user_text)
    if fast_hint:
        concierge_intent, concierge_intent_source = fast_hint
        logger.info(
            "⏭️ 第一段階トリアージ省略: concierge_intent=%s source=%s",
            concierge_intent,
            concierge_intent_source,
        )
        return {
            "category": "Other",
            "confidence": 1.0,
            "subcategory": "general_other",
            "requires_immediate_action": False,
            "reasoning": f"stage1 skipped ({concierge_intent_source})",
            "concierge_intent": concierge_intent,
            "concierge_intent_source": concierge_intent_source,
        }

    from src.services.budget_guard import check_llm_allowed

    allowed, _ = check_llm_allowed()
    if not allowed:
        return {
            "category": "Other",
            "confidence": 1.0,
            "subcategory": "system/budget_blocked",
            "requires_immediate_action": False,
            "reasoning": "OpenAI monthly budget limit reached",
        }

    hist_d = ""
    mem_d = ""
    if conversation_history:
        from src.services.triage_history import history_digest as _hd

        hist_d = _hd(conversation_history)
    if long_term_memory_block:
        from src.services.triage_history import memory_digest as _md

        mem_d = _md(long_term_memory_block)

    if use_cache:
        from src.services.triage_cache import build_cache_key

        cache_key = build_cache_key(user_text, None, history_digest=hist_d, memory_digest=mem_d)
        _purge_triage_cache()
        entry = _triage_cache.get(cache_key)
        if entry and datetime.now() - entry.created_at <= _TRIAGE_CACHE_TTL:
            logger.debug(f"💾 キャッシュからLLMトリアージ結果を取得: {cache_key[:50]}...")
            return entry.result.copy()

    history_block = ""
    if conversation_history:
        from src.services.triage_history import format_triage_history_block

        history_block = format_triage_history_block(conversation_history)
    memory_section = ""
    if long_term_memory_block:
        memory_section = f"\n\n{long_term_memory_block.strip()}\n"
    history_section = (
        f"{memory_section}\n\n【直近の会話（圧縮）】\n{history_block}\n"
        if history_block and history_block != "（なし）"
        else (memory_section if memory_section else "")
    )

    try:
        from src.core.llm_client import chat_completion_create

        response = chat_completion_create(
            client,
            model_role="triage",
            path="llm_triage.stage1",
            messages=[
                {"role": "system", "content": "あなたは薬剤師です。ユーザーの入力を正確にカテゴリ分類してください。"},
                {
                    "role": "user",
                    "content": (
                        f"{FIRST_STAGE_TRIAGE_PROMPT}{history_section}\n\n"
                        f"【ユーザーの入力】\n{user_text}"
                    ),
                },
            ],
            temperature=0.1,
            max_tokens=300,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content

        # JSONをパース
        try:
            first_stage_result = json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"第一段階JSON解析エラー: {e}, レスポンス: {content}")
            # フォールバック: デフォルト値を返す
            return {
                "category": "Other",
                "confidence": 0.0,
                "subcategory": "unknown",
                "requires_immediate_action": False,
                "reasoning": f"JSON解析エラー: {str(e)}"
            }
        
        # 必須フィールドの検証
        category = first_stage_result.get("category", "Other")
        confidence = float(first_stage_result.get("confidence", 0.0))
        subcategory = first_stage_result.get("subcategory", "general_other")
        requires_immediate_action = bool(first_stage_result.get("requires_immediate_action", False))
        reasoning = first_stage_result.get("reasoning", "判定理由が提供されませんでした")
        medical_examination_request = bool(
            first_stage_result.get("medical_examination_request", False)
        )

        if medical_examination_request:
            logger.info("🚫 医療行為依頼を検出（第一段階LLM）")
            return _medical_examination_triage_result(
                f"第一段階: {reasoning}",
                confidence=max(confidence, 0.95),
            )

        if "ambiguous_heart" in (subcategory or "").lower():
            requires_immediate_action = False
        
        # confidenceの範囲チェック
        if confidence < 0.0:
            confidence = 0.0
        elif confidence > 1.0:
            confidence = 1.0
        
        # categoryの検証
        valid_categories = ["Physical", "Emotional", "Emergency", "Ask", "Other"]
        if category not in valid_categories:
            logger.warning(f"無効なカテゴリ: {category}, デフォルトでOtherに設定")
            category = "Other"
            confidence = 0.5
        
        concierge_intent: str | None = None
        concierge_intent_source: str | None = None
        session_intent: str | None = None

        # 第二段階：Otherカテゴリの場合は詳細分類を実行
        if category == "Other":
            session_probe = _session_admin_fast_path(user_text)
            fast_hint = _concierge_fast_path_hint(user_text)
            stage2_skipped = False

            if session_probe and confidence >= _STAGE2_SKIP_MIN_CONFIDENCE:
                subcategory = "session_admin"
                confidence = max(confidence, float(session_probe.get("confidence", 1.0)))
                reasoning = f"{reasoning} | stage2 skipped (session_keyword_probe)"
                session_intent = session_probe.get("session_intent")
                concierge_intent = "session_ops"
                concierge_intent_source = "session_keyword_probe"
                stage2_skipped = True
                logger.info(
                    "⏭️ 第二段階トリアージ省略: session_admin intent=%s",
                    session_intent,
                )
            elif fast_hint and confidence >= _STAGE2_SKIP_MIN_CONFIDENCE:
                concierge_intent, concierge_intent_source = fast_hint
                subcategory = "general_other"
                reasoning = f"{reasoning} | stage2 skipped ({concierge_intent_source})"
                stage2_skipped = True
                logger.info(
                    "⏭️ 第二段階トリアージ省略: concierge_intent=%s source=%s",
                    concierge_intent,
                    concierge_intent_source,
                )
            elif _should_skip_stage2_for_store(subcategory, confidence):
                stage2_skipped = True
                reasoning = f"{reasoning} | stage2 skipped (store_inquiry_stage1)"
                logger.info(
                    "⏭️ 第二段階トリアージ省略: store subcategory=%s conf=%.2f",
                    subcategory,
                    confidence,
                )

            if not stage2_skipped:
                try:
                    second_response = chat_completion_create(
                        client,
                        model_role="triage",
                        path="llm_triage.stage2",
                        messages=[
                            {
                                "role": "system",
                                "content": "あなたは薬剤師です。Otherカテゴリに分類された入力を詳細に分類してください。",
                            },
                            {
                                "role": "user",
                                "content": (
                                    f"{SECOND_STAGE_OTHER_PROMPT}{history_section}\n\n"
                                    f"【ユーザーの入力】\n{user_text}"
                                ),
                            },
                        ],
                        temperature=0.1,
                        max_tokens=200,
                        response_format={"type": "json_object"},
                    )

                    second_content = second_response.choices[0].message.content

                    try:
                        second_stage_result = json.loads(second_content)
                        detailed_subcategory = second_stage_result.get("subcategory", "general_other")
                        detailed_confidence = float(second_stage_result.get("confidence", confidence))
                        detailed_reasoning = second_stage_result.get("reasoning", reasoning)

                        if detailed_confidence < 0.0:
                            detailed_confidence = 0.0
                        elif detailed_confidence > 1.0:
                            detailed_confidence = 1.0

                        subcategory = detailed_subcategory
                        confidence = detailed_confidence
                        reasoning = f"第一段階: {reasoning} | 第二段階: {detailed_reasoning}"

                    except json.JSONDecodeError as e:
                        logger.error(f"第二段階JSON解析エラー: {e}, レスポンス: {second_content}")
                        subcategory = "general_other"
                except Exception as e:
                    logger.error(f"第二段階トリアージエラー: {e}")
                    subcategory = "general_other"

        result = {
            "category": category,
            "confidence": confidence,
            "subcategory": subcategory,
            "requires_immediate_action": requires_immediate_action,
            "reasoning": reasoning,
        }
        if concierge_intent:
            result["concierge_intent"] = concierge_intent
            result["concierge_intent_source"] = concierge_intent_source
        if session_intent:
            result["session_intent"] = session_intent
        
        # 不適切な要求が検出された場合、キャッシュを無効化（誤分類を防ぐため）
        if use_cache:
            from src.services.triage_cache import build_cache_key

            cache_key = build_cache_key(user_text, None, history_digest=hist_d, memory_digest=mem_d)
            subcategory_lower = result.get("subcategory", "").lower()
            if "inappropriate_request" in subcategory_lower:
                # キャッシュから削除（誤分類を防ぐため）
                if cache_key in _triage_cache:
                    del _triage_cache[cache_key]
                    logger.debug(f"💾 不適切な要求検出により、キャッシュを無効化: {cache_key[:50]}...")
                # キャッシュに保存しない（不適切な要求は毎回再判定）
                return result
        
        # キャッシュに保存（完全一致のみ）
        if use_cache:
            from src.services.triage_cache import build_cache_key

            cache_key = build_cache_key(user_text, None, history_digest=hist_d, memory_digest=mem_d)
            _purge_triage_cache()
            _triage_cache[cache_key] = _TriageCacheEntry(
                result=result.copy(),
                created_at=datetime.now(),
            )
            logger.debug(f"💾 LLMトリアージ結果をキャッシュに保存: {cache_key[:50]}...")
        
        return result
        
    except Exception as e:
        logger.error(f"LLMトリアージエラー: {e}")
        import traceback
        traceback.print_exc()
        from src.services.llm_unavailability import is_openai_infrastructure_error_text

        err_text = str(e)
        # エラー時は安全側に倒してOtherを返す
        return {
            "category": "Other",
            "confidence": 0.0,
            "subcategory": "error",
            "requires_immediate_action": False,
            "reasoning": f"エラーが発生しました: {err_text}",
            "infrastructure_error": is_openai_infrastructure_error_text(err_text),
        }


def check_heart_emergency_with_context(
    user_text: str,
    triage_result: Optional[Dict] = None,
    counseling_mode: Optional[Dict] = None,
    client: Optional[OpenAI] = None,
    conversation_history: Optional[List] = None
) -> Dict:
    """
    緊急症状（激しい胸痛、突然の呼吸困難など）を検出する関数
    URGENT_SYMPTOM_KEYWORDSを使用してキーワードベースで高速検出
    
    Args:
        user_text: ユーザーの入力テキスト
        triage_result: LLMトリアージ結果（オプション）
        counseling_mode: カウンセリングモード（オプション）
        client: OpenAIクライアント（オプション、LLM判定が必要な場合のみ使用）
        conversation_history: 会話履歴（オプション）
    
    Returns:
        {
            "is_emergency": bool,
            "confidence": float,
            "context_type": str,
            "reasoning": str,
            "threshold_used": float
        }
    """
    user_text_lower = user_text.lower()
    
    # キーワードベースの緊急症状検出（優先・高速）
    for keyword in URGENT_SYMPTOM_KEYWORDS:
        if keyword.lower() in user_text_lower:
            logger.warning(f"🚨 緊急症状キーワード検出: {keyword}")
            return {
                "is_emergency": True,
                "confidence": 0.95,
                "context_type": "urgent_symptom",
                "reasoning": f"緊急症状キーワード「{keyword}」を検出",
                "threshold_used": 0.9
            }
    
    # 既存の心臓緊急チェック（既存のロジックがある場合は統合）
    # ここでは簡易的な実装として、キーワードベースの検出のみを実装
    # より高度な判定が必要な場合は、LLMを使用した判定を追加可能
    
    return {
        "is_emergency": False,
        "confidence": 0.0,
        "context_type": "normal",
        "reasoning": "緊急症状は検出されませんでした",
        "threshold_used": 0.9
    }


def generate_contextual_emergency_message(
    user_text: str,
    emergency_result: Dict,
    counseling_mode: Optional[Dict] = None,
    triage_result: Optional[Dict] = None
) -> str:
    """
    緊急症状が検出された場合の警告メッセージを生成
    
    Args:
        user_text: ユーザーの入力テキスト
        emergency_result: 緊急症状検出結果
        counseling_mode: カウンセリングモード（オプション）
        triage_result: LLMトリアージ結果（オプション）
    
    Returns:
        警告メッセージ（文字列）
    """
    # 緊急症状が検出された場合の標準メッセージ
    emergency_message = """🚨 **緊急を要する症状が検出されました**

お申し出の症状は、急性心筋梗塞や肺塞栓などの緊急事態である可能性があります。

**直ちに以下のいずれかの対応を取ってください：**
- 救急車（119番）を呼ぶ
- 最寄りの救急外来を受診する

このシステムは一般用医薬品（OTC医薬品）の相談を対象としており、緊急を要する症状には対応できません。

お体を大切になさってください。"""

    return emergency_message
