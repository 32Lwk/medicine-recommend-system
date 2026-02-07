"""
言語検出ユーティリティ

テキストから言語を自動検出する。
"""
import re


def detect_language(text, session_language=None):
    """
    テキストから言語を自動検出

    Args:
        text (str): 検出対象のテキスト
        session_language (str): セッションの既存言語情報（オプション）

    Returns:
        str: 検出された言語コード ('ja', 'en', 'ko', 'zh')
    """
    if not text or not isinstance(text, str):
        return 'ja'  # デフォルトは日本語

    text = text.strip()

    # セッションの既存言語情報がある場合は優先的に考慮
    if session_language and session_language != 'en':
        # 既存言語が日本語の場合、短いテキストは日本語として扱う
        if session_language == 'ja' and len(text) <= 10:
            # 日本語の一般的な医学用語・症状名リスト
            japanese_medical_terms = [
                '精神疾患', 'うつ病', '統合失調症', '不安障害', 'パニック障害',
                '頭痛', '腹痛', '発熱', '咳', '鼻水', '下痢', '便秘', '吐き気',
                '不眠', '倦怠感', '疲労感', 'ストレス', 'イライラ', '不安',
                '風邪', 'インフルエンザ', '花粉症', 'アレルギー', '湿疹',
                '肩こり', '腰痛', '関節痛', '筋肉痛', 'めまい', '動悸'
            ]
            if text in japanese_medical_terms:
                return 'ja'

    # 韓国語の文字が含まれているかチェック（ハングル）- 最初にチェック（重複がないため）
    if re.search(r'[\uAC00-\uD7AF]', text):
        return 'ko'

    # 中国語の文字が含まれているかチェック（簡体字・繁体字）
    chinese_chars = re.search(r'[\u4E00-\u9FFF]', text)
    if chinese_chars:
        # ひらがなやカタカナが含まれていれば日本語
        if re.search(r'[\u3040-\u309F\u30A0-\u30FF]', text):
            return 'ja'

        # 漢字のみの場合の判定を改善
        # 短いテキスト（10文字以下）で、日本語の一般的な医学用語の可能性がある場合は日本語として扱う
        if len(text) <= 10:
            # 日本語の一般的な医学用語・症状名リスト
            japanese_medical_terms = [
                '精神疾患', 'うつ病', '統合失調症', '不安障害', 'パニック障害',
                '頭痛', '腹痛', '発熱', '咳', '鼻水', '下痢', '便秘', '吐き気',
                '不眠', '倦怠感', '疲労感', 'ストレス', 'イライラ', '不安',
                '風邪', 'インフルエンザ', '花粉症', 'アレルギー', '湿疹',
                '肩こり', '腰痛', '関節痛', '筋肉痛', 'めまい', '動悸',
                'のどの痛み', '喉の痛み', '胃痛', '胸痛', '背痛'
            ]
            if text in japanese_medical_terms:
                return 'ja'

            # セッションの既存言語が日本語の場合は日本語として扱う
            if session_language == 'ja':
                return 'ja'

        # 長いテキストで漢字のみの場合は中国語の可能性が高い
        return 'zh'

    # 日本語の文字が含まれているかチェック（ひらがな、カタカナ）
    if re.search(r'[\u3040-\u309F\u30A0-\u30FF]', text):
        return 'ja'

    # デフォルトは英語
    return 'en'
