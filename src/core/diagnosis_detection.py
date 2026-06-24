"""
診断名検出モジュール

テキストが診断名（疾患名）かどうかを判定し、
副作用言及の検出を行う。
"""
import re
import unicodedata
import logging

logger = logging.getLogger(__name__)

# 診断名のみでも OTC 相談フローへ進めてよい疾患（ユーザーが相談入口として使うことが多い）
OTC_CONSULTATION_ENTRY_DIAGNOSES = frozenset({
    '花粉症',
    'アレルギー性鼻炎',
    '季節性アレルギー性鼻炎',
    '常年性アレルギー性鼻炎',
})

# 副作用言及のキーワード
SIDE_EFFECT_KEYWORDS = [
    '副作用', '副作用で', '副作用が', '副作用の', '副作用が出', '副作用が出た',
    '副作用が出て', '副作用が出ています', '副作用が出ました', '副作用について',
    '副作用がひどい', '副作用がつらい', '薬の副作用', '処方薬の副作用',
    'お薬の副作用', '薬を飲んだら', '薬で', '飲み始めてから',
    '抗がん剤', '抗がん剤の副作用', '治療薬の副作用',
]


def _is_otc_consultation_entry(
    diagnosis_only: bool,
    detected_names: list,
    *,
    has_side_effect: bool,
    has_high_risk_context: bool,
    has_treatment: bool,
) -> bool:
    """花粉症など OTC 相談入口 — 診断名ブロックをかけず通常フローへ。"""
    if not diagnosis_only or has_side_effect or has_high_risk_context or has_treatment:
        return False
    if not detected_names:
        return False
    return all(d in OTC_CONSULTATION_ENTRY_DIAGNOSES for d in detected_names)


def _should_skip_environmental_allergy_diagnosis_block(
    text: str,
    detected_names: list,
    *,
    has_side_effect: bool,
    has_high_risk_context: bool,
    has_treatment: bool,
) -> bool:
    """花粉症+頭痛など — allergies で管理し診断名カウンセリング・Physical ブロックを避ける。"""
    if has_side_effect or has_high_risk_context or has_treatment:
        return False
    if not detected_names or not all(d in OTC_CONSULTATION_ENTRY_DIAGNOSES for d in detected_names):
        return False
    try:
        from src.utils.input_helpers import has_explicit_symptom_signal

        return has_explicit_symptom_signal(text)
    except ImportError:
        return False


def is_diagnosis_only(text: str, diagnosis: str) -> bool:
    """
    テキストが診断名のみ（症状の記述がない）かどうかを判定する。

    感情・状態に関する否定語（あかん、つらい、やばいなど）を含む場合は
    診断名のみと判定しない（ユーザーが症状を訴えている可能性がある）。

    Args:
        text: 検出対象のテキスト
        diagnosis: 検出された診断名

    Returns:
        True: 診断名のみの場合
        False: 症状や感情表現が含まれる場合
    """
    if not text or not isinstance(text, str):
        return True
    text = text.strip()
    if not diagnosis:
        return True

    try:
        from config.dialect_dictionary import EMOTIONAL_NEGATIVE_WORDS
        from config.keywords import SYMPTOM_KEYWORDS
    except ImportError:
        EMOTIONAL_NEGATIVE_WORDS = []
        SYMPTOM_KEYWORDS = []

    # 感情・状態に関する否定語が含まれる場合は診断名のみと判定しない
    if any(word in text for word in EMOTIONAL_NEGATIVE_WORDS):
        return False

    # 症状キーワードが含まれる場合は診断名のみではない
    if any(kw in text for kw in SYMPTOM_KEYWORDS):
        return False

    # 診断名を除いた残りのテキストを取得
    remaining = text.replace(diagnosis, '').strip()

    # Unicode正規化して記号・スペースを除去
    remaining_nf = unicodedata.normalize('NFKC', remaining)
    remaining_clean = re.sub(r'[\s　。、．，!?！？･・「」『』（）【】]', '', remaining_nf)

    # 助詞・助動詞のみをストップワードとして除去
    stopwords = ['です', 'だ', 'です。', 'だ。', 'です、', 'だ、', 'で', 'の', 'は', 'が', 'を', 'に', 'と', 'か', 'ね', 'よ']
    for sw in stopwords:
        remaining_clean = remaining_clean.replace(sw, '')

    # 残りが空または非常に短い（2文字以下）場合は診断名のみ
    return len(remaining_clean) <= 2


def has_side_effect_mention(text: str) -> bool:
    """
    テキストに副作用の言及があるかどうかを判定する。

    Args:
        text: 検出対象のテキスト

    Returns:
        True: 副作用の言及がある場合
        False: 副作用の言及がない場合
    """
    if not text or not isinstance(text, str):
        return False
    text_lower = text.lower().strip()
    return any(kw in text for kw in SIDE_EFFECT_KEYWORDS)


def is_diagnosis_term(text):
    """
    テキストが診断名（疾患名）かどうかを判定
    過去形や他人の話など、現在の状態に関係ない場合は除外する
    治療中キーワードが含まれている場合は除外する（通常の医薬品推奨フローに進むべき）
    
    Args:
        text (str): 検出対象のテキスト
    
    Returns:
        tuple: (is_diagnosis, diagnosis_type, suggested_response)
            - is_diagnosis: 診断名かどうか
            - diagnosis_type: 診断名の種類（'mental_health', 'chronic', 'serious', 'other'）
            - suggested_response: 推奨される返信内容
    """
    import re
    
    if not text or not isinstance(text, str):
        return (False, None, None)
    
    text = text.strip()
    
    # 高リスクコンテキストキーワードの定義（疑い・検査中のコンテキスト）
    HIGH_RISK_CONTEXT_KEYWORDS = [
        '疑い', '疑われる', '疑わしい', '可能性', '可能性が高い',
        '検査', '検査中', '検査結果', '検査結果待ち', '検査予定',
        '精密検査', '再検査', '追加検査', '詳しい検査',
        '数値が悪い', '数値が高い', '数値が低い',
        '再確認', '確認中', '要確認'
    ]
    
    # 副作用メッセージテンプレート（構造化フォーマット）
    SIDE_EFFECT_MESSAGE_TEMPLATE = """お薬の副作用に対する市販薬の使用は、現在の治療に影響を及ぼす恐れがあります。
自己判断で服用せず、必ず主治医にご相談ください。

特に、抗がん剤などの治療薬の副作用の場合、市販薬が治療薬の吸収や効果に
影響を与える可能性があります。

【医師に相談する際に伝えるべきポイント】
以下の情報をメモして、医師に伝えてください：

1. 副作用の内容
   - どのような症状が出ていますか？（例：吐き気、便秘、頭痛など）

2. 発生時期
   - いつから症状が出始めましたか？
   - 薬を飲み始めてからどのくらいで出ましたか？

3. 服用中の薬
   - どのような薬（処方薬）を飲んでいますか？
   - 薬の名前や種類がわかれば教えてください

4. 症状の変化
   - 症状は続いていますか？
   - 時間が経つにつれて良くなっていますか、悪くなっていますか？
   - 市販薬を飲みたい理由は何ですか？

これらの情報を整理してから医師に相談することで、より適切なアドバイスが受けられます。"""
    
    # 過去形・他人の話・既往歴を表す除外パターン（診断名の前後10-20文字以内にこれらの語がある場合は除外）
    exclusion_context_words = [
        # 時間的表現（過去）
        '過去', '以前', '昔', '前', '過去に', 'かつて', '先月', '先週', '去年', '昨年',
        '一昨年', '数年前', '数ヶ月前', '数週間前', 'なった', '罹患', '診断', 'かかった',
        'だった', 'でした', 'でした', 'だったです', 'でしたです',
        
        # 他人・家族関係
        '知り合い', '友人', '家族', '父', '母', '兄弟', '姉妹', '祖父', '祖母', '親',
        '配偶者', '夫', '妻', '彼', '彼女', '子供', '息子', '娘', '他人', '同僚',
        '上司', '部下', '隣人',
        
        # ペット関連
        '猫', '犬', 'ペット', '動物',
        
        # 治癒表現
        '治り', '完治', '回復', '治った', '治癒', '改善', '良くなった',
        'リミッター解除', 'もう治って', '薬やめた', '完治して', '前の病気',
        
        # 将来表現
        '将来', '未来', '怖い', '心配', '不安',
        
        # 医学用語（既往歴・持病）
        '既往症', '既往歴', '持病', '基礎疾患', '基礎疾病', '既往疾患',
        '病歴', '診断歴', '治療歴', '罹患歴',
        'もっている', '持っている', 'かかっている', 'かかってる',
        'あり', 'あります', 'があります', 'がある',
        
        # 逆接表現（既往歴を述べた後の逆接）
        'ですが', 'ですが、', 'ですが。', 'だけど', 'だけど、', 'だけど。',
        'なんですが', 'なんですが、', 'なんですが。',
        'がありますが', 'がありますが、', 'があるのですが', 'があるのですが、',
        'を患っていますが', 'を患っていますが、', 'を患ってますが', 'を患ってますが、',
        'と言われていますが', 'と言われていますが、', 'と言われてますが', 'と言われてますが、',
        'と診断されていますが', 'と診断されていますが、', 'と診断されてますが', 'と診断されてますが、',
    ]
    
    # 既往歴を示す正規表現パターン
    medical_history_patterns = [
        r'既往症[としてはが]*',
        r'持病[としてはが]*',
        r'基礎疾患[としてはが]*',
        r'基礎疾病[としてはが]*',
        r'既往[歴疾患]*[としてはが]*',
        r'病歴[としてはが]*',
        r'[がはを]ある[が、。]',
        r'[がはを]あります[が、。]',
        r'[がはを]持って[いいます]*[が、。]',
        r'[とが]言われて[いいます]*[が、。]',
        r'[とが]診断されて[いいます]*[が、。]',
        r'[とが]患って[いいます]*[が、。]',
    ]
    
    # 文脈を考慮した診断名検出関数
    def check_diagnosis_with_context(diagnosis, text, exclusion_words):
        """診断名が検出対象かどうかを文脈を考慮して判定"""
        if diagnosis not in text:
            return False
        
        # 診断名の位置を特定（最初の出現位置を検出）
        index = text.find(diagnosis)
        if index == -1:
            return False
        
        # 診断名の前後15文字を抽出（主体・時間軸の除外判定を最適化）
        start = max(0, index - 15)
        end = min(len(text), index + len(diagnosis) + 15)
        context = text[start:end]
        
        # 逆接表現の定義
        adversative_expressions = ['ですが', 'ですが、', 'だけど', 'だけど、', 'がありますが', 'がありますが、',
                                   'を患っていますが', 'を患っていますが、', 'と言われていますが', 'と言われていますが、',
                                   'と診断されていますが', 'と診断されていますが、', 'なんですが', 'なんですが、', 'なんですが。']
        
        # 症状キーワードの定義（逆接表現の後に続く場合、診断名を除外しない）
        # 既往症があっても、それとは関係のない症状がある場合は除外しない
        symptom_keywords = [
            # 身体的症状（頭部・神経系）
            '頭痛', '発熱', '熱', 'めまい', 'ふらつき', '立ちくらみ',
            # 呼吸器系
            '咳', 'せき', '鼻水', '鼻づまり', 'くしゃみ', 'のどの痛み', '喉が痛い', '息切れ', '息が切れる', '呼吸困難',
            # 消化器系
            '腹痛', 'お腹が痛い', '胃痛', '胃が痛い', '下痢', '便秘', '吐き気', '嘔吐', '胸やけ', '胃もたれ', '消化不良',
            # 循環器系
            '動悸', '心臓がドキドキ', '心臓がバクバク', '脈が速い',
            # 全身症状
            '疲労', '疲労感', '倦怠感', 'だるさ', 'むくみ', '寒気', '悪寒',
            # 運動器系
            '関節痛', '筋肉痛', '腰痛', '肩こり', '背中の痛み', '首の痛み',
            # 皮膚系
            'かゆみ', '痒み', '発疹', '湿疹', '蕁麻疹', '皮膚の乾燥', '皮膚の異常',
            # 睡眠・精神系
            '不眠', '眠れない', '眠気', 'イライラ', '不安', 'ストレス',
            # 眼科系
            '目の疲れ', '目が疲れる', '目のかゆみ', '目がかゆい', '目の充血', '目が赤い',
            # 耳鼻科系
            '耳鳴り', '耳の痛み', '耳が痛い',
            # 口腔系
            '口内炎', '口の痛み', '歯痛', '歯が痛い',
            # 女性特有
            '生理痛', '月経痛', '月経不順', '更年期症状',
            # その他の症状表現
            '痛み', '痛い', '違和感', '不調', '症状', '辛い', '苦しい', 'しんどい',
            # 疾患名（症状として扱う）
            '風邪', 'インフルエンザ', 'かぜ', 'カゼ', '感冒', '胃腸炎',
            # 市販薬関連（症状があることを示唆）
            '市販薬', '薬', '探しています', '欲しい', 'おすすめ', '相談',
            # 症状の継続・程度を表す表現
            '続いています', '続いている', 'します', 'しています', 'ひどい', 'ひどく',
            'あります', 'ある', 'でます', '出ます', 'します', 'しています'
        ]
        
        # 「があります」「がある」の特別処理: 「診断名があります」のような単純な表記は除外しない
        # ただし、「既往症として診断名があります」のような場合は除外する
        # ただし、逆接表現（「ですが」「がありますが」など）の後に症状がある場合は除外しない
        simple_existence_patterns = ['があります', 'がある', 'あり', 'あります']
        medical_history_keywords = ['既往症', '既往歴', '持病', '基礎疾患', '基礎疾病', '既往疾患', '病歴']
        
        # 診断名の前の部分を確認（最大30文字）
        before_diagnosis = text[max(0, index - 30):index]
        has_medical_history_keyword = any(keyword in before_diagnosis for keyword in medical_history_keywords)
        
        # 診断名の後の部分を確認（逆接表現と症状の有無をチェック）
        diagnosis_end = index + len(diagnosis)
        after_diagnosis = text[diagnosis_end:]
        # 逆接表現の後に症状があるかチェック（最大100文字まで）
        after_diagnosis_check = after_diagnosis[:100] if len(after_diagnosis) > 100 else after_diagnosis
        
        # 1. 除外語が文脈内にあるかチェック
        # 除外しない理由（症状があるなど）が見つかった場合のフラグ
        should_exclude = False  # デフォルトは除外しない
        
        for word in exclusion_words:
            if word in context:
                # 「があります」「がある」の特別処理
                if word in simple_existence_patterns:
                    # 医学用語（既往症など）が前にない場合は除外しない
                    if not has_medical_history_keyword:
                        # 単純な「診断名があります」の場合は除外しない（should_excludeはFalseのまま）
                        continue  # 次の除外語をチェック
                    
                    # 医学用語がある場合でも、逆接表現の後に症状がある場合は除外しない
                    # 例：「既往症として糖尿病がありますが、風邪をひきました」
                    has_symptom_after_expr = False
                    for expr in adversative_expressions:
                        if expr in after_diagnosis_check:
                            expr_index = after_diagnosis_check.find(expr)
                            if expr_index != -1:
                                after_expr = after_diagnosis_check[expr_index + len(expr):expr_index + len(expr) + 80]
                                # 症状キーワードが続くかチェック
                                if any(keyword in after_expr for keyword in symptom_keywords):
                                    has_symptom_after_expr = True
                                    break  # 症状が見つかったらループを抜ける
                    
                    if has_symptom_after_expr:
                        # 症状が続く場合は除外しない（既往症があっても別の症状があるパターン）
                        # 症状がある場合は、他の除外語のチェックをスキップしてTrueを返す
                        return True  # 診断名を検出する
                    
                    # 逆接表現の後に症状がない場合は除外（既往歴のみのパターン）
                    should_exclude = True  # 除外する
                    continue  # この除外語については除外する、次のチェックに進む
                
                # 逆接表現の場合は、その後に症状キーワードが続くかチェック
                if word in adversative_expressions:
                    # 診断名の後の部分を取得（逆接表現の後の部分）
                    # after_diagnosis_checkは既に定義済み
                    
                    # 逆接表現の位置を特定（より広範囲にチェック）
                    adversative_index = after_diagnosis_check.find(word)
                    if adversative_index != -1:
                        # 逆接表現の後の部分を取得（最大80文字に拡大、より確実に症状を検出）
                        after_adversative = after_diagnosis_check[adversative_index + len(word):adversative_index + len(word) + 80]
                        
                        # 症状キーワードが続くかチェック
                        has_symptom_after = any(keyword in after_adversative for keyword in symptom_keywords)
                        if has_symptom_after:
                            # 症状が続く場合は除外しない（診断名+症状のパターン）
                            # 既往症があっても、それとは関係のない症状がある場合は除外しない
                            # 症状がある場合は、他の除外語のチェックをスキップしてTrueを返す
                            return True  # 診断名を検出する
                    
                    # 症状が続かない場合は除外（既往歴のみのパターン）
                    should_exclude = True  # 除外する
                    continue  # この除外語については除外する、次のチェックに進む
                
                current_indicators = ['現在', '今', '最近', 'この頃', '現在は', '今は', '現在も', '今も']
                has_current_indicator = any(indicator in context for indicator in current_indicators)
                if has_current_indicator:
                    # 逆接表現がない場合のみ続行
                    adversative_in_context = any(expr in context for expr in adversative_expressions)
                    if not adversative_in_context:
                        # 現在を示す語がある場合は除外しない（should_excludeはFalseのまま）
                        continue  # 次のチェックに進む
                    else:
                        # 逆接表現がある場合、その後に症状があるかチェック
                        # after_diagnosis_checkは既に定義済み
                        has_symptom_after = False
                        for expr in adversative_expressions:
                            if expr in after_diagnosis_check:
                                adversative_index = after_diagnosis_check.find(expr)
                                if adversative_index != -1:
                                    # 最大80文字に拡大（より確実に症状を検出）
                                    after_adversative = after_diagnosis_check[adversative_index + len(expr):adversative_index + len(expr) + 80]
                                    if any(keyword in after_adversative for keyword in symptom_keywords):
                                        has_symptom_after = True
                                        break  # 症状が見つかったらループを抜ける
                        
                        if has_symptom_after:
                            # 症状が続く場合は除外しない（既往症があっても別の症状があるパターン）
                            # 症状がある場合は、他の除外語のチェックをスキップしてTrueを返す
                            return True  # 診断名を検出する
                        # 症状が続かない場合は除外（既往歴のみのパターン）
                        should_exclude = True  # 除外する
                        continue  # 次のチェックに進む
                
                # その他の除外語の場合は除外
                should_exclude = True  # 除外する
                continue  # 次のチェックに進む
        
        # 除外する理由が見つかり、除外しない理由（症状があるなど）がなかった場合のみ除外
        if should_exclude:
            return False
        
        # 2. 正規表現パターンで既往歴表現をチェック
        for pattern in medical_history_patterns:
            # 診断名の前後15文字以内でパターンを検索（最適化）
            pattern_start = max(0, index - 15)
            pattern_end = min(len(text), index + len(diagnosis) + 15)
            pattern_context = text[pattern_start:pattern_end]
            
            if re.search(pattern, pattern_context):
                # 「現在」「今」などの現在を示す語がない場合のみ除外
                current_indicators = ['現在', '今', '最近', 'この頃', '現在は', '今は', '現在も', '今も']
                has_current_indicator = any(indicator in pattern_context for indicator in current_indicators)
                if not has_current_indicator:
                    return False
        
        return True
    
    # 精神疾患・精神科関連の診断名（拡充版・重複削除）
    mental_health_diagnoses = [
        # 気分障害
        'うつ病', '鬱病', '憂鬱症', '大うつ病性障害', '気分障害',
        '双極性障害', '躁うつ病','躁鬱症','躁鬱', '躁鬱病', 'うつ状態', '抑うつ',
        
        # 不安障害
        'パニック障害', '不安障害', '全般性不安障害', 'GAD',
        '社交不安障害', 'SAD', '広場恐怖症', '特定恐怖症',
        
        # 強迫性障害・関連
        '強迫性障害', 'OCD', '身体醜形障害', 'ためこみ症',
        
        # トラウマ関連
        'PTSD', '心的外傷後ストレス障害', '複雑性PTSD', 'CPTSD',
        '適応障害', '急性ストレス障害',
        
        # 解離性障害
        '解離性障害', '解離性同一性障害', '離人症',
        
        # 摂食障害
        '摂食障害', '拒食症', '神経性無食欲症', 'AN', '神経性過食症', 'BN',
        '過食性障害', 'BED',
        
        # 発達障害
        'ADHD', '注意欠如・多動性障害', '注意欠陥多動性障害',
        '自閉症スペクトラム', 'ASD', '自閉症', 'アスペルガー症候群',
        '学習障害', 'LD', '知的障害',
        
        # 認知症・認知障害
        '認知症', 'アルツハイマー', 'アルツハイマー病', 'アルツハイマー型認知症',
        'レビー小体型認知症', '血管性認知症', '前頭側頭型認知症',
        '軽度認知障害', 'MCI',
        
        # 統合失調症・精神病性障害
        '統合失調症', '統合失調感情障害', '妄想性障害', '短期精神病性障害',
        
        # その他
        '精神疾患', '精神病', '神経症', 'パーソナリティ障害',
        '境界性パーソナリティ障害', 'BPD', '依存症', 'アルコール依存症',
        '薬物依存症', 'ギャンブル依存症',
        
        # 睡眠障害（精神疾患としても扱われる）
        '不眠症', '慢性不眠症', '原発性不眠症',
    ]
    
    # 悪性腫瘍・がん関連（拡充版）
    cancer_diagnoses = [
        'がん', '癌', '悪性腫瘍', '悪性新生物', '悪性新腫瘍',
        '白血病', 'リンパ腫', 'ホジキンリンパ腫', '非ホジキンリンパ腫',
        '骨髄腫', '多発性骨髄腫', 'メラノーマ', '悪性黒色腫',
        '肉腫', '軟部肉腫', '脳腫瘍', '悪性脳腫瘍',
        '肺がん', '肺癌', '胃がん', '胃癌', '大腸がん', '大腸癌',
        '乳がん', '乳癌', '子宮がん', '子宮癌', '子宮頸がん',
        '肝がん', '肝癌', '膵がん', '膵癌', '腎がん', '腎癌',
        '前立腺がん', '前立腺癌', '食道がん', '食道癌',
    ]
    
    # 慢性疾患・重篤な疾患（拡充版）
    chronic_serious_diagnoses = [
        # 膠原病・リウマチ
        'リウマチ', '関節リウマチ', 'RA', '膠原病', 'SLE', '全身性エリテマトーデス',
        '強皮症', '皮膚筋炎', '多発性筋炎', '混合性結合組織病', 'MCTD',
        'シェーグレン症候群', 'ベーチェット病', '血管炎',
        
        # 腎疾患
        '腎臓病', '慢性腎臓病', 'CKD', '腎不全', '慢性腎不全',
        '急性腎不全', '腎炎', '糸球体腎炎', 'IgA腎症', '透析',
        '血液透析', '腹膜透析', '腎移植',
        
        # 肝疾患
        '肝臓病', '慢性肝炎', '急性肝炎', '肝炎', 'B型肝炎', 'C型肝炎',
        '肝硬変', '肝不全', '脂肪肝', 'NASH', 'NAFLD',
        '原発性胆汁性胆管炎', 'PBC', '自己免疫性肝炎', 'AIH',
        
        # 心疾患・循環器疾患
        '心不全', '慢性心不全', '急性心不全', '虚血性心疾患', '狭心症',
        '心筋梗塞', '不整脈', '心房細動', '房室ブロック',
        '拡張型心筋症', '肥大型心筋症', '心筋症',
        '高血圧', '本態性高血圧', '二次性高血圧', '高血圧症',
        '低血圧', '起立性低血圧', '本態性低血圧',
        '動脈硬化', '動脈硬化症', 'アテローム性動脈硬化',
        
        # 呼吸器疾患
        'COPD', '慢性閉塞性肺疾患', '間質性肺炎', 'IPF',
        '肺線維症', '気管支喘息', '喘息', '肺気腫',
        
        # 血液疾患
        '貧血', '鉄欠乏性貧血', '再生不良性貧血', '溶血性貧血',
        '血友病', '血小板減少症', 'ITP', '血栓性血小板減少性紫斑病', 'TTP',
        
        # 代謝疾患
        '糖尿病', '1型糖尿病', '2型糖尿病', '糖尿病性腎症',
        '糖尿病性網膜症', '糖尿病性神経障害',
    ]
    
    # 神経疾患・その他の重篤な疾患（拡充版）
    other_serious_diagnoses = [
        # 神経疾患
        'てんかん', '癲癇', 'パーキンソン病', '多発性硬化症', 'MS',
        '筋萎縮性側索硬化症', 'ALS', '脊髄小脳変性症',
        'ハンチントン病', '筋ジストロフィー', '重症筋無力症',
        'ギラン・バレー症候群', 'CIDP', '三叉神経痛',
        
        # 消化器疾患
        'クローン病', '潰瘍性大腸炎', 'UC', 'IBD', '炎症性腸疾患',
        '劇症肝炎', '急性膵炎', '慢性膵炎',
        
        # 内分泌疾患
        '橋本病', '慢性甲状腺炎', 'バセドウ病', '甲状腺機能亢進症',
        '甲状腺機能低下症', 'クッシング症候群', 'アジソン病',
        '副腎皮質機能不全', '副腎皮質機能亢進症',
        
        # 感染症（重篤なもの・医師診断が必要なもの）
        'COVID-19', 'コロナ', 'コロナウイルス', '新型コロナウイルス',
        '結核', '活動性結核', 'HIV', 'エイズ', 'AIDS',
        'インフルエンザ', 'インフル', '流行性感冒', '流感',
        '肺炎', '細菌性肺炎', 'ウイルス性肺炎', 'マイコプラズマ肺炎',
        '尿路感染症', '膀胱炎', '腎盂腎炎', '複雑性膀胱炎',
        '蜂窩織炎', '蜂巣炎', '丹毒',
        '帯状疱疹', 'ヘルペス', '単純ヘルペス',
        'RSウイルス感染症', 'RSウイルス',
        
        # 循環器疾患（急性・血栓性疾患）
        '深部静脈血栓症', 'DVT', '肺血栓塞栓症', 'PE',
        
        # 消化器疾患（追加）
        '胃潰瘍', '十二指腸潰瘍', '消化性潰瘍',
        '逆流性食道炎', 'GERD', '胃食道逆流症',
        '過敏性腸症候群', 'IBS', '過敏性大腸症候群',
        '機能性ディスペプシア', 'FD',
        
        # 皮膚疾患
        'アトピー性皮膚炎', 'アトピー',
        '尋常性乾癬', '乾癬', '関節症性乾癬',
        '接触皮膚炎', 'アレルギー性接触皮膚炎',
        '白斑', '尋常性白斑', '白癜',
        '円形脱毛症', '脱毛症',
        '掌蹠膿疱症', '掌蹠膿胞症',
        '皮膚筋炎',  # 膠原病として既にあるが、皮膚症状としても重要
        
        # 眼科疾患
        '緑内障', '原発開放隅角緑内障', '原発閉塞隅角緑内障',
        '網膜剥離', '網膜裂孔',
        '加齢黄斑変性', 'AMD', '黄斑変性',
        'ぶどう膜炎', '虹彩炎',
        
        # 耳鼻咽喉科疾患
        '慢性副鼻腔炎', '蓄膿症', '副鼻腔炎',
        '中耳炎', '急性中耳炎', '慢性中耳炎', '滲出性中耳炎',
        'メニエール病', 'メニエル病', 'メニエール症候群',
        '良性発作性頭位めまい症', 'BPPV',
        '突発性難聴',
        
        # 婦人科疾患
        '子宮筋腫', '子宮平滑筋腫',
        '子宮内膜症', '子宮腺筋症',
        '多嚢胞性卵巣症候群', 'PCOS', '多囊胞性卵巣症候群',
        '更年期障害', '更年期症候群', '閉経後症候群',
        '卵巣がん', '卵巣癌', '卵巣腫瘍',
        '子宮外妊娠', '異所性妊娠',
        
        # 泌尿器疾患
        '前立腺肥大症', 'BPH', '良性前立腺肥大症',
        '腎結石', '尿路結石', '腎盂結石', '尿管結石',
        '慢性腎盂腎炎',
        '間質性膀胱炎', 'IC',
        
        # 整形外科・運動器疾患
        '変形性関節症', '変形性膝関節症', '変形性股関節症',
        '骨粗鬆症', '骨粗しょう症',
        '腱鞘炎', 'ばね指', 'ドケルバン病',
        '五十肩', '肩関節周囲炎', '凍結肩',
        '脊柱管狭窄症', '腰部脊柱管狭窄症',
        '腰椎椎間板ヘルニア', '頚椎椎間板ヘルニア',
        
        # アレルギー疾患
        'アレルギー性鼻炎', '花粉症', '季節性アレルギー性鼻炎',
        '食物アレルギー', 'アナフィラキシー',
        '気管支喘息', '喘息',  # 呼吸器疾患として既にあるが、アレルギー疾患としても重要
        
        # 睡眠障害
        '不眠症', '慢性不眠症', '原発性不眠症',
        '睡眠時無呼吸症候群', 'SAS', '閉塞性睡眠時無呼吸症候群', 'OSAS',
        'ナルコレプシー', '過眠症',
        'レストレスレッグス症候群', 'RLS', 'むずむず脚症候群',
        
        # その他
        '先天性疾患', '遺伝性疾患', '奇形', '染色体異常','ダウン症','ダウン症候群','21トリソミー'
    ]
    
    # すべての診断名を検出（複数診断名対応）
    detected_diagnoses = []  # (diagnosis, diagnosis_type) のタプルのリスト
    
    # 診断名の検出（優先順位: serious > mental_health > chronic > other）
    # 1. 悪性腫瘍（serious）
    for diagnosis in cancer_diagnoses:
        if check_diagnosis_with_context(diagnosis, text, exclusion_context_words):
            detected_diagnoses.append((diagnosis, 'serious'))
    
    # 2. 精神疾患（mental_health）
    for diagnosis in mental_health_diagnoses:
        if check_diagnosis_with_context(diagnosis, text, exclusion_context_words):
            detected_diagnoses.append((diagnosis, 'mental_health'))
    
    # 3. 慢性疾患・重篤な疾患（chronic）
    for diagnosis in chronic_serious_diagnoses:
        if check_diagnosis_with_context(diagnosis, text, exclusion_context_words):
            detected_diagnoses.append((diagnosis, 'chronic'))
    
    # 4. その他の重篤な疾患（other）
    for diagnosis in other_serious_diagnoses:
        if check_diagnosis_with_context(diagnosis, text, exclusion_context_words):
            detected_diagnoses.append((diagnosis, 'other'))
    
    # 診断名が検出されなかった場合は早期リターン
    if not detected_diagnoses:
        return (False, None, None)
    
    # 優先順位で診断名を選択（serious > mental_health > chronic > other）
    priority_order = {'serious': 0, 'mental_health': 1, 'chronic': 2, 'other': 3}
    detected_diagnoses.sort(key=lambda x: priority_order.get(x[1], 999))
    selected_diagnosis, selected_type = detected_diagnoses[0]
    
    # すべての検出された診断名のリスト
    all_diagnosis_names = [d[0] for d in detected_diagnoses]
    all_diagnosis_types = list({t for _, t in detected_diagnoses})
    
    # フィルタリングの連鎖を適用（エラーハンドリング付き）
    # 1. 高リスクフィルター（診断名検出後にAND条件でチェック）
    try:
        has_high_risk_context = any(keyword in text for keyword in HIGH_RISK_CONTEXT_KEYWORDS)
    except Exception as e:
        logger.error(f"❌ 高リスクコンテキストチェックでエラー: {e}")
        has_high_risk_context = False  # 安全側に倒す
    
    # 2. 診断名のみ判定
    try:
        diagnosis_only = is_diagnosis_only(text, selected_diagnosis)
    except Exception as e:
        logger.error(f"❌ 診断名のみ判定でエラー: {e}")
        diagnosis_only = True  # 安全側に倒す（診断名のみとして扱う）
    
    # 3. 症状の有無確認
    try:
        from src.services.counseling_response import has_specific_symptom
        has_symptom = has_specific_symptom(text)
    except ImportError:
        has_symptom = False
    except Exception as e:
        logger.error(f"❌ 症状確認でエラー: {e}")
        has_symptom = False  # 安全側に倒す
    
    # 4. 副作用フィルター
    try:
        has_side_effect = has_side_effect_mention(text)
    except Exception as e:
        logger.error(f"❌ 副作用検出でエラー: {e}")
        has_side_effect = False  # 安全側に倒す
    
    # 5. 治療中チェック
    try:
        from src.services.counseling_response import is_treatment_mention
        has_treatment = is_treatment_mention(text, skip_diagnosis_only=True)
    except ImportError:
        has_treatment = False
    except Exception as e:
        logger.error(f"❌ 治療中チェックでエラー: {e}")
        has_treatment = False  # 安全側に倒す
    
    # ログ記録：フィルタリング結果
    try:
        logger.info(f"🔍 フィルタリング結果: diagnosis_only={diagnosis_only}, has_symptom={has_symptom}, has_treatment={has_treatment}, has_side_effect={has_side_effect}, has_high_risk_context={has_high_risk_context}")
    except Exception:
        pass  # ログ記録のエラーは無視

    if _is_otc_consultation_entry(
        diagnosis_only,
        all_diagnosis_names,
        has_side_effect=has_side_effect,
        has_high_risk_context=has_high_risk_context,
        has_treatment=has_treatment,
    ):
        logger.info(
            "🌸 OTC相談入口: detected=%s — 診断名ブロックをスキップ",
            all_diagnosis_names,
        )
        return (False, None, None)

    if _should_skip_environmental_allergy_diagnosis_block(
        text,
        all_diagnosis_names,
        has_side_effect=has_side_effect,
        has_high_risk_context=has_high_risk_context,
        has_treatment=has_treatment,
    ):
        logger.info(
            "🌸 環境アレルギー+具体症状: detected=%s — 診断名ブロックをスキップ",
            all_diagnosis_names,
        )
        return (False, None, None)
    
    # メッセージ生成（高リスクコンテキストの場合は専用メッセージ）
    try:
        if has_high_risk_context:
            message = f'「{selected_diagnosis}」について検査中や疑いの状態であることをお知らせいただき、ありがとうございます。\n\n'
            message += f'検査結果待ちや疑いの状態の場合、診断が確定していない状態での市販薬の使用は避けるべきです。\n'
            message += f'必ず医師の診断を受けてから、適切な治療を開始してください。\n\n'
            message += f'検査結果が出るまでの間は、自己判断で市販薬を使用せず、医師の指示に従ってください。'
            
            return (True, selected_type, {
                'message': message,
                'escalation_required': True,
                'escalation_reason': f'診断名「{selected_diagnosis}」と高リスクコンテキストが検出されました。',
                'has_symptom': has_symptom,
                'has_treatment': has_treatment,
                'has_side_effect': has_side_effect,
                'should_show_counseling': False,
                'diagnosis_only': diagnosis_only,
                'detected_diagnoses': all_diagnosis_names,
                'selected_diagnosis': selected_diagnosis,
                'diagnosis_block_types': all_diagnosis_types,
                'has_high_urgency_symptom': False,  # 後で実装
                'high_risk_context': True
            })
        
        # 副作用が検出された場合の専用メッセージ
        if has_side_effect:
            side_effect_message = SIDE_EFFECT_MESSAGE_TEMPLATE
            
            # 複数診断名の場合はマージ
            if len(all_diagnosis_names) > 1:
                diagnosis_list = '、'.join(all_diagnosis_names[:-1]) + '、' + all_diagnosis_names[-1]
                message_prefix = f'{diagnosis_list}などの持病をお持ちの方で、'
            else:
                message_prefix = f'「{selected_diagnosis}」をお持ちの方で、'
            
            return (True, selected_type, {
            'message': message_prefix + side_effect_message,
            'escalation_required': True,
            'escalation_reason': f'診断名「{selected_diagnosis}」と副作用が検出されました。',
            'has_symptom': has_symptom,
            'has_treatment': has_treatment,
            'has_side_effect': True,
            'should_show_counseling': False,
            'diagnosis_only': diagnosis_only,
            'detected_diagnoses': all_diagnosis_names,
            'selected_diagnosis': selected_diagnosis,
            'diagnosis_block_types': all_diagnosis_types,
                'has_high_urgency_symptom': False,  # 後で実装
                'high_risk_context': False
            })
        
        # 診断名のみの場合
        if diagnosis_only:
            # 複数診断名の場合はマージ
            if len(all_diagnosis_names) > 1:
                diagnosis_list = '、'.join(all_diagnosis_names[:-1]) + '、' + all_diagnosis_names[-1]
                message_prefix = f'{diagnosis_list}などの持病をお持ちの方へ：\n\n'
            else:
                message_prefix = f'「{selected_diagnosis}」は診断名であり、具体的な症状ではありません。\n\n'
            
            if selected_type == 'serious':
                message = message_prefix + '悪性腫瘍の治療は医師の診断と処方薬が必須です。\n市販薬での対応は困難ですので、必ずかかりつけの医師や専門医にご相談ください。\n\n現在の症状について教えていただけますと、より適切なご案内ができます。'
            elif selected_type == 'mental_health':
                message = message_prefix + '市販薬での対応が難しい可能性があります。以下のいずれかをお試しください：\n1. 具体的な症状（例：不眠、不安、イライラ、倦怠感など）を教えてください\n2. 医師や薬剤師にご相談ください\n\n※精神疾患の治療は専門医の診断と処方薬が必要な場合があります。'
            elif selected_type == 'chronic':
                message = message_prefix + '慢性疾患や重篤な疾患の場合は、医師の診断と処方薬が必要です。\n市販薬での対応が難しい可能性がありますので、以下のいずれかをお試しください：\n1. 具体的な症状（例：頭痛、発熱、痛みなど）を教えてください\n2. かかりつけの医師や薬剤師にご相談ください'
            else:
                message = message_prefix + '市販薬での対応が難しい可能性があります。以下のいずれかをお試しください：\n1. 具体的な症状（例：痛み、発熱、不調など）を教えてください\n2. かかりつけの医師や薬剤師にご相談ください'
            
            return (True, selected_type, {
                'message': message,
                'escalation_required': True,
                'escalation_reason': f'診断名「{selected_diagnosis}」のみが検出されました。',
                'has_symptom': False,
                'has_treatment': has_treatment,
                'has_side_effect': False,
                'should_show_counseling': False,
                'diagnosis_only': True,
                'detected_diagnoses': all_diagnosis_names,
                'selected_diagnosis': selected_diagnosis,
                'diagnosis_block_types': all_diagnosis_types,
                'has_high_urgency_symptom': False,  # 後で実装
                'high_risk_context': False
            })
        
        # 診断名+症状の場合
        # 複数診断名の場合はマージ
        if len(all_diagnosis_names) > 1:
            diagnosis_list = '、'.join(all_diagnosis_names[:-1]) + '、' + all_diagnosis_names[-1]
            message_prefix = f'{diagnosis_list}などの持病をお持ちの方へ：\n\n'
        else:
            message_prefix = f'「{selected_diagnosis}」をお持ちの方へ：\n\n'
        
        if selected_type == 'serious':
            message = message_prefix + '体調変化が主疾患に関連している可能性があります。\n悪性腫瘍の治療は医師の診断と処方薬が必須です。\n市販薬での対応は困難ですので、必ずかかりつけの医師や専門医にご相談ください。'
        elif selected_type == 'mental_health':
            message = message_prefix + 'お薬の飲み合わせ（相互作用）が非常に多いため、市販薬の使用には注意が必要です。\n医師や薬剤師にご相談ください。'
        elif selected_type == 'chronic':
            message = message_prefix + '数値管理（血圧、血糖値など）に影響が出る可能性があります。\n市販薬を使用する場合は、かかりつけの医師や薬剤師にご相談ください。'
        else:
            message = message_prefix + '市販薬を使用する場合は、かかりつけの医師や薬剤師にご相談ください。'
        
        return (True, selected_type, {
            'message': message,
            'escalation_required': True,
            'escalation_reason': f'診断名「{selected_diagnosis}」と症状が検出されました。',
            'has_symptom': True,
            'has_treatment': has_treatment,
            'has_side_effect': False,
            'should_show_counseling': True,  # 症状がある場合はカウンセリングフローにも流す
            'diagnosis_only': False,
            'detected_diagnoses': all_diagnosis_names,
            'selected_diagnosis': selected_diagnosis,
            'diagnosis_block_types': all_diagnosis_types,
            'has_high_urgency_symptom': False,  # 後で実装
            'high_risk_context': False
        })
    except Exception as e:
        logger.error(f"診断名メッセージ生成でエラー: {e}")
        return (True, selected_type, {
            'message': f'「{selected_diagnosis}」についてご相談いただきありがとうございます。医師や薬剤師にご相談ください。',
            'escalation_required': True,
            'escalation_reason': 'エラーが発生しました。',
            'has_symptom': has_symptom,
            'has_treatment': has_treatment,
            'has_side_effect': has_side_effect,
            'should_show_counseling': False,
            'diagnosis_only': diagnosis_only,
            'detected_diagnoses': all_diagnosis_names,
            'selected_diagnosis': selected_diagnosis,
            'diagnosis_block_types': all_diagnosis_types,
            'has_high_urgency_symptom': False,
            'high_risk_context': False
        })
