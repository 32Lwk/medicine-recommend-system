"""
危機キーワード検出モジュール

自殺・自傷関連の危険ワードを検出し、
相談先情報を返す。
"""
import re


def detect_crisis_keywords(user_message):
    """
    自殺・自傷関連の危険ワードを検出する関数
    医薬品相談ツールの特性を考慮した充実したキーワードリスト

    Args:
        user_message (str): ユーザーの入力メッセージ

    Returns:
        tuple: (検出されたかどうか, 検出されたキーワードのリスト)
    """
    crisis_keywords = [
        # 直接的な表現
        '死にたい', '消えたい', '自殺', '希死念慮', '死にたいです', '消えたいです',
        '生きていても意味がない', '生きる意味がない', '生きていても仕方ない',
        'もうだめ', 'だめだ', '終わり', '終わらせたい', '命を絶ちたい',
        'この世から消えたい', '存在したくない', 'いなくなってしまいたい',
        '自殺願望', '自殺念慮', '死にたい気持ち', '死にたいです',

        # 薬物関連の危険表現
        '過量服薬', 'OD', '致死量', '大量服薬', '薬を全部飲む', '薬で死にたい',
        '薬を一気に飲む', '薬を飲みすぎた', '薬で楽になりたい', 'ODしたい',
        '過剰摂取', 'オーバードーズ', '薬を多く飲む', '薬を混ぜる', '薬の致死量', '睡眠薬致死量',
        '薬で眠りたい', 'overdose', '薬を使って消えたい', 'overdoseした',
        '薬で楽になりたい',

        # 自傷行為関連
        'リスカ', '自傷', 'リストカット', '手首切った', '血を見たくなる',

        # 死に方・方法の表現
        '死に方', '楽な死に方', '眠るように死にたい', '首を吊る', '飛び降り',
        '飛び込み', '死ぬ方法', '消える方法', '死ぬ勇気', '命を捨てたい',
        '死に場所', '死を考えている', '命を終わらせたい', '死ぬ準備',
        '終わりにしたい', '倒れたい', '死ぬしかない',

        # 感情・心理状態（身体的症状の文脈では検出しない）
        '生きたくない', 'もう終わりたい', '生きるのがつらい', '限界',
        '助けて', '誰にも言えない', 'いなくなりたい',
        '誰も理解してくれない', 'どうでもいい', '生きる意味', '価値がない',
        '自分が嫌い', '存在したくない', '消えてしまいたい', 'もう無理',
        'もういいや', '終わらせたい',
        # 注意: '苦しい'は身体的症状の文脈（「胸が苦しい」「息が苦しい」など）でも使われるため、
        # 明示的な希死念慮の文脈でのみ検出する（後続の処理で文脈を考慮）

        # 英語の危険ワード
        'suicide', 'kill myself', 'want to die', 'end my life', 'overdose'
    ]

    # 大文字小文字を区別せずに検索
    user_message_lower = user_message.lower()

    # 身体的症状の文脈を検出（危機キーワードの誤検出を防ぐため）
    physical_symptom_patterns = [
        r'胸.*(?:が|の).*苦しい',
        r'息.*(?:が|の).*苦しい',
        r'呼吸.*(?:が|の).*苦しい',
        r'苦しい.*(?:胸|息|呼吸)',
        r'胸.*(?:が|の).*痛い',
        r'心臓.*(?:が|の).*苦しい',
        r'失恋.*(?:して|で).*苦しい',
        r'恋愛.*(?:で|の).*苦しい',
    ]

    # 恋愛文脈キーワード
    romantic_keywords = ['失恋', '好きな人', '恋愛', '恋', 'ときめき', 'ドキドキ', 'バクバク', '好き', '片思い', '両思い', '告白', '振られた', '別れた']
    has_romantic_context = any(keyword in user_message for keyword in romantic_keywords)

    # 身体的症状の文脈かどうかを判定
    has_physical_context = any(re.search(pattern, user_message, re.IGNORECASE) for pattern in physical_symptom_patterns)

    detected_keywords = []
    for keyword in crisis_keywords:
        if not _keyword_matches(keyword, user_message_lower):
            continue
        # 「苦しい」は身体的症状の文脈では検出しない
        if keyword == '苦しい':
            if has_physical_context or has_romantic_context:
                continue
        detected_keywords.append(keyword)

    return len(detected_keywords) > 0, detected_keywords


def _keyword_matches(keyword: str, user_message_lower: str) -> bool:
    """危機キーワードの部分一致。短い英字は単語境界で誤検出（例: nodo→OD）を防ぐ。"""
    kw = keyword.lower()
    if kw.isascii() and len(kw) <= 3:
        return bool(
            re.search(
                r"(?<![a-zA-Z])" + re.escape(kw) + r"(?![a-zA-Z])",
                user_message_lower,
                re.IGNORECASE,
            )
        )
    return kw in user_message_lower


def get_crisis_support_resources(language='ja'):
    """
    自殺防止相談先の情報を取得する関数

    Args:
        language (str): 言語コード ('ja', 'en', 'ko', 'zh')

    Returns:
        dict: 相談先情報とメッセージ
    """
    # 多言語対応のメッセージテンプレート
    messages = {
        'ja': {
            'title': 'あなたの気持ちを大切に思っています',
            'message': '今、とてもつらい状況かもしれません。一人で抱え込まず、信頼できる相談先があります。',
            'emergency': '緊急の場合は、すぐに119番（救急）または110番（警察）に連絡してください。'
        },
        'en': {
            'title': 'Your feelings matter',
            'message': 'Professional support is available. Please contact a crisis counselor.',
            'emergency': 'In emergency, call 119 (ambulance) or 110 (police) immediately.'
        },
        'ko': {
            'title': '당신의 마음을 소중히 생각합니다',
            'message': '전문 상담사가 도움을 드릴 수 있습니다. 위기 상담원에게 연락하세요.',
            'emergency': '응급상황 시 즉시 119(구급차) 또는 110(경찰)에 연락하세요.'
        },
        'zh': {
            'title': '我们关心您的感受',
            'message': '专业支持服务可用。请联系危机咨询师。',
            'emergency': '紧急情况请立即拨打119（救护车）或110（警察）。'
        }
    }

    # 相談先情報（日本語メイン、他言語は最低限）
    resources = [
        {
            'name': 'いのちの電話',
            'organization': '一般社団法人 日本いのちの電話連盟',
            'phone': '0120-783-556',
            'hours': '24時間対応',
            'website': 'https://www.inochinodenwa.org/?page_id=267',
            'description': '24時間いつでも相談できる電話窓口です',
            'description_en': '24-hour crisis hotline',
            'description_ko': '24시간 위기 상담 전화',
            'description_zh': '24小时危机热线'
        },
        {
            'name': 'ライフリンク',
            'organization': 'NPO法人 自殺対策支援センター ライフリンク',
            'line': 'https://line.me/R/ti/p/@eds9972b',
            'line_qr': 'https://qr-official.line.me/gs/M_eds9972b_GW.png?openQrModal=true&searchId=eds9972b',
            'description': 'LINEで相談できます',
            'description_en': 'Available via LINE chat',
            'description_ko': 'LINE 채팅 상담 가능',
            'description_zh': '可通过LINE聊天咨询'
        },
        {
            'name': 'いのち支える自殺対策推進センター',
            'organization': 'JSCP',
            'website': 'https://jscp.or.jp/',
            'description': '自殺対策に関する情報と相談窓口',
            'description_en': 'Suicide prevention information and support',
            'description_ko': '자살 예방 정보 및 상담',
            'description_zh': '自杀预防信息和支持'
        },
        {
            'name': 'まもろうよ こころ',
            'organization': '厚生労働省',
            'website': 'https://www.mhlw.go.jp/mamorouyokokoro/',
            'description': '厚生労働省の心の健康に関する情報サイト',
            'description_en': 'Mental health information from Ministry of Health',
            'description_ko': '보건복지부 정신건강 정보 사이트',
            'description_zh': '厚生劳动省心理健康信息网站'
        }
    ]

    # 言語に応じた説明文を選択
    for resource in resources:
        if language != 'ja':
            desc_key = f'description_{language}'
            if desc_key in resource:
                resource['description'] = resource[desc_key]

    return {
        'title': messages.get(language, messages['ja'])['title'],
        'message': messages.get(language, messages['ja'])['message'],
        'emergency_message': messages.get(language, messages['ja'])['emergency'],
        'resources': resources
    }
