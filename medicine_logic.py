import pandas as pd
from openai import OpenAI
import os
import re
import time
import logging
from typing import Dict
from debug_logger import add_network_log, performance_stats
from datetime import datetime
# from typing import List
# from openai.types.chat import ChatCompletionMessageParam ←不要なので削除

# ログ設定
logger = logging.getLogger(__name__)

# このファイルのあるディレクトリを基準にCSVファイルの絶対パスを取得
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
CSV_PATH = os.path.join(DATA_DIR, "otc_medicine_data.csv")

logger.info(f'CSVファイル絶対パス: {CSV_PATH}')
logger.info(f'ファイル存在: {os.path.exists(CSV_PATH)}')

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

def is_diagnosis_term(text):
    """
    テキストが診断名（疾患名）かどうかを判定
    過去形や他人の話など、現在の状態に関係ない場合は除外する
    
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
    
    # 過去形・他人の話・既往歴を表す除外パターン（診断名の前後50文字以内にこれらの語がある場合は除外）
    exclusion_context_words = [
        # 時間的表現（過去）
        '過去', '以前', '昔', '前', '過去に', 'かつて', '先月', '先週', '去年', '昨年',
        '一昨年', '数年前', '数ヶ月前', '数週間前', 'なった', '罹患', '診断', 'かかった',
        'だった', 'でした', 'でした', 'だったです', 'でしたです',
        
        # 他人・家族関係
        '知り合い', '友人', '家族', '父', '母', '兄弟', '姉妹', '祖父', '祖母', '親',
        '配偶者', '夫', '妻', '彼', '彼女', '子供', '息子', '娘', '他人', '同僚',
        '上司', '部下', '隣人',
        
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
        
        # 診断名の前後50文字を抽出（範囲を拡大）
        start = max(0, index - 50)
        end = min(len(text), index + len(diagnosis) + 50)
        context = text[start:end]
        
        # 1. 除外語が文脈内にあるかチェック
        for word in exclusion_words:
            if word in context:
                # ただし、「現在」「今」「最近」など現在を示す語があれば除外しない
                # ただし、逆接表現（「ですが」「がありますが」など）の場合は除外する
                if word in ['ですが', 'ですが、', 'だけど', 'だけど、', 'がありますが', 'がありますが、',
                           'を患っていますが', 'を患っていますが、', 'と言われていますが', 'と言われていますが、',
                           'と診断されていますが', 'と診断されていますが、']:
                    return False
                
                current_indicators = ['現在', '今', '最近', 'この頃', '現在は', '今は', '現在も', '今も']
                has_current_indicator = any(indicator in context for indicator in current_indicators)
                if has_current_indicator:
                    # 逆接表現がない場合のみ続行
                    if 'ですが' not in context and 'がありますが' not in context:
                        continue
                    else:
                        return False
                return False
        
        # 2. 正規表現パターンで既往歴表現をチェック
        for pattern in medical_history_patterns:
            # 診断名の前後30文字以内でパターンを検索
            pattern_start = max(0, index - 30)
            pattern_end = min(len(text), index + len(diagnosis) + 30)
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
        '双極性障害', '躁うつ病', '躁鬱病', 'うつ状態', '抑うつ',
        
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
    
    # 診断名の検出（精神疾患）
    for diagnosis in mental_health_diagnoses:
        if check_diagnosis_with_context(diagnosis, text, exclusion_context_words):
            return (True, 'mental_health', {
                'message': f'「{diagnosis}」は診断名であり、具体的な症状ではありません。\n\n'
                          f'市販薬での対応が難しい可能性があります。以下のいずれかをお試しください：\n'
                          f'1. 具体的な症状（例：不眠、不安、イライラ、倦怠感など）を教えてください\n'
                          f'2. 医師や薬剤師にご相談ください\n\n'
                          f'※精神疾患の治療は専門医の診断と処方薬が必要な場合があります。',
                'escalation_required': True,
                'escalation_reason': f'診断名「{diagnosis}」が検出されました。専門医への相談を推奨します。'
            })
    
    # 診断名の検出（悪性腫瘍）
    for diagnosis in cancer_diagnoses:
        if check_diagnosis_with_context(diagnosis, text, exclusion_context_words):
            return (True, 'serious', {
                'message': f'「{diagnosis}」は診断名であり、具体的な症状ではありません。\n\n'
                          f'悪性腫瘍の治療は医師の診断と処方薬が必須です。\n'
                          f'市販薬での対応は困難ですので、必ずかかりつけの医師や専門医にご相談ください。\n\n'
                          f'※現在の症状について教えていただけますと、より適切なご案内ができます。',
                'escalation_required': True,
                'escalation_reason': f'診断名「{diagnosis}」が検出されました。専門医への相談を強く推奨します。'
            })
    
    # 診断名の検出（慢性疾患・重篤な疾患）
    for diagnosis in chronic_serious_diagnoses:
        if check_diagnosis_with_context(diagnosis, text, exclusion_context_words):
            return (True, 'chronic', {
                'message': f'「{diagnosis}」は診断名であり、具体的な症状ではありません。\n\n'
                          f'慢性疾患や重篤な疾患の場合は、医師の診断と処方薬が必要です。\n'
                          f'市販薬での対応が難しい可能性がありますので、以下のいずれかをお試しください：\n'
                          f'1. 具体的な症状（例：頭痛、発熱、痛みなど）を教えてください\n'
                          f'2. かかりつけの医師や薬剤師にご相談ください',
                'escalation_required': True,
                'escalation_reason': f'診断名「{diagnosis}」が検出されました。医師への相談を推奨します。'
            })
    
    # 診断名の検出（その他の重篤な疾患）
    for diagnosis in other_serious_diagnoses:
        if check_diagnosis_with_context(diagnosis, text, exclusion_context_words):
            return (True, 'other', {
                'message': f'「{diagnosis}」は診断名であり、具体的な症状ではありません。\n\n'
                          f'市販薬での対応が難しい可能性があります。以下のいずれかをお試しください：\n'
                          f'1. 具体的な症状（例：痛み、発熱、不調など）を教えてください\n'
                          f'2. かかりつけの医師や薬剤師にご相談ください',
                'escalation_required': True,
                'escalation_reason': f'診断名「{diagnosis}」が検出されました。医師への相談を推奨します。'
            })
    
    return (False, None, None)

def create_multilingual_attribute_extraction_prompt(user_text, language, user_info=None):
    """
    言語に応じたユーザー属性抽出プロンプトを作成
    
    Args:
        user_text (str): ユーザーの入力テキスト
        language (str): 検出された言語コード
        user_info (dict): 既存のユーザー情報
    
    Returns:
        str: プロンプトテキスト
    """
    prompts = {
        'ja': f"""
あなたは医薬品推奨システムです。ユーザーのメッセージから以下の属性情報を抽出してください。

【ユーザーのメッセージ】
{user_text}

【既存のユーザー情報】
{user_info if user_info else 'なし'}

【抽出すべき属性】
- age: 年齢（数値）
- gender: 性別（男性/女性）
- pregnant: 妊娠中かどうか（true/false）
- breastfeeding: 授乳中かどうか（true/false）
- allergies: アレルギー（リスト）
- current_medications: 服用中の薬（リスト）
- medical_history: 既往症（リスト）
- symptom_duration_days: 症状の期間（日数）
- other_info: その他の情報（文字列）

【回答形式】
以下のJSON形式で回答してください：
{{
    "age": 30,
    "gender": "男性",
    "pregnant": false,
    "breastfeeding": false,
    "allergies": ["なし"],
    "current_medications": [],
    "medical_history": [],
    "symptom_duration_days": 3,
    "other_info": "その他の情報があれば"
}}

情報が不明な場合は null を返してください。
""",
        
        'en': f"""
You are a medicine recommendation system. Extract the following attribute information from the user's message.

【User's Message】
{user_text}

【Existing User Information】
{user_info if user_info else 'None'}

【Attributes to Extract】
- age: Age (number)
- gender: Gender (Male/Female)
- pregnant: Whether pregnant (true/false)
- breastfeeding: Whether breastfeeding (true/false)
- allergies: Allergies (list)
- current_medications: Current medications (list)
- medical_history: Medical history (list)
- symptom_duration_days: Duration of symptoms (days)
- other_info: Other information (string)

【Response Format】
Please respond in the following JSON format:
{{
    "age": 30,
    "gender": "Male",
    "pregnant": false,
    "breastfeeding": false,
    "allergies": ["None"],
    "current_medications": [],
    "medical_history": [],
    "symptom_duration_days": 3,
    "other_info": "Other information if any"
}}

Return null for unknown information.
""",
        
        'ko': f"""
당신은 의약품 추천 시스템입니다. 사용자의 메시지에서 다음 속성 정보를 추출해주세요.

【사용자의 메시지】
{user_text}

【기존 사용자 정보】
{user_info if user_info else '없음'}

【추출해야 할 속성】
- age: 나이 (숫자)
- gender: 성별 (남성/여성)
- pregnant: 임신 여부 (true/false)
- breastfeeding: 수유 여부 (true/false)
- allergies: 알레르기 (목록)
- current_medications: 복용 중인 약 (목록)
- medical_history: 병력 (목록)
- symptom_duration_days: 증상 지속 기간 (일수)
- other_info: 기타 정보 (문자열)

【응답 형식】
다음 JSON 형식으로 응답해주세요:
{{
    "age": 30,
    "gender": "남성",
    "pregnant": false,
    "breastfeeding": false,
    "allergies": ["없음"],
    "current_medications": [],
    "medical_history": [],
    "symptom_duration_days": 3,
    "other_info": "기타 정보가 있다면"
}}

정보를 모르는 경우 null을 반환하세요.
""",
        
        'zh': f"""
您是药品推荐系统。请从用户消息中提取以下属性信息。

【用户消息】
{user_text}

【现有用户信息】
{user_info if user_info else '无'}

【要提取的属性】
- age: 年龄（数字）
- gender: 性别（男性/女性）
- pregnant: 是否怀孕（true/false）
- breastfeeding: 是否哺乳（true/false）
- allergies: 过敏（列表）
- current_medications: 正在服用的药物（列表）
- medical_history: 病史（列表）
- symptom_duration_days: 症状持续时间（天数）
- other_info: 其他信息（字符串）

【回答格式】
请以以下JSON格式回答：
{{
    "age": 30,
    "gender": "男性",
    "pregnant": false,
    "breastfeeding": false,
    "allergies": ["无"],
    "current_medications": [],
    "medical_history": [],
    "symptom_duration_days": 3,
    "other_info": "如有其他信息"
}}

未知信息请返回null。
"""
    }
    
    return prompts.get(language, prompts['ja'])

def extract_user_attributes_multilingual(user_text, client=None, user_info=None):
    """
    多言語対応のユーザー属性抽出
    
    Args:
        user_text (str): ユーザーの入力テキスト
        client: OpenAIクライアント
        user_info (dict): 既存のユーザー情報
    
    Returns:
        dict: 抽出された属性情報
    """
    if client is None:
        from openai import OpenAI
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            return {}
        client = OpenAI(api_key=api_key)
    
    # 言語を自動検出
    detected_language = detect_language(user_text)
    
    # 言語に応じたプロンプトを作成
    prompt = create_multilingual_attribute_extraction_prompt(user_text, detected_language, user_info)
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a medical AI assistant that extracts user attributes from text."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=1000
        )
        
        result = response.choices[0].message.content
        if os.getenv('DEBUG_MODE', 'false').lower() == 'true' or logger.level <= logging.DEBUG:
            logger.debug(f"ChatGPT属性抽出応答 ({detected_language}): {result}")
        
        # JSON形式の回答を解析
        import json
        try:
            json_start = result.find('{') if result else -1
            json_end = result.rfind('}') + 1 if result else -1
            if json_start != -1 and json_end != -1:
                json_str = result[json_start:json_end]
                parsed_result = json.loads(json_str)
                
                # 言語情報を追加
                parsed_result['detected_language'] = detected_language
                
                return parsed_result
            else:
                return {"detected_language": detected_language}
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析エラー: {e}")
            return {"detected_language": detected_language}
            
    except Exception as e:
        logger.error(f"ChatGPT API呼び出しエラー: {e}")
        return {"detected_language": detected_language}

# 翻訳キャッシュ（グローバル）
_translation_cache_global = {}
_max_translation_cache_size = 200

def get_cached_translation(text: str, target_language: str):
    """翻訳キャッシュから結果を取得"""
    cache_key = f"{target_language}:{hash(text)}"
    return _translation_cache_global.get(cache_key)

def set_cached_translation(text: str, target_language: str, translated_text: str):
    """翻訳キャッシュに結果を保存"""
    global _translation_cache_global
    
    # キャッシュサイズ制限
    if len(_translation_cache_global) >= _max_translation_cache_size:
        # 古いエントリを削除（FIFO）
        oldest_key = next(iter(_translation_cache_global))
        del _translation_cache_global[oldest_key]
    
    cache_key = f"{target_language}:{hash(text)}"
    _translation_cache_global[cache_key] = translated_text

def translate_medicine_recommendation(text, target_language, client=None):
    """
    AI応答（医薬品推奨）を翻訳（DeepL API使用、キャッシュ機能付き）
    
    Args:
        text (str): 翻訳対象のテキスト
        target_language (str): 翻訳先言語コード ('en', 'ko', 'zh')
        client: 後方互換性のためのパラメータ（使用されません）
    
    Returns:
        str: 翻訳されたテキスト
    """
    if not text or target_language == 'ja':
        return text  # 日本語の場合は翻訳不要
    
    # キャッシュをチェック
    cached_result = get_cached_translation(text, target_language)
    if cached_result:
        logger.debug(f"翻訳キャッシュヒット: {target_language}, テキスト長: {len(text)}")
        return cached_result
    
    # .envファイルから環境変数を読み込む（念のため）
    try:
        from dotenv import load_dotenv
        env_path = os.path.join(BASE_DIR, '.env')
        if os.path.exists(env_path):
            load_dotenv(env_path, override=True)
    except ImportError:
        pass  # python-dotenvがインストールされていない場合はスキップ
    except Exception:
        pass  # エラーが発生した場合はスキップ
    
    try:
        import deepl
    except ImportError:
        logger.error("deeplライブラリがインストールされていません。'pip install deepl'でインストールしてください。")
        return text
    
    api_key = os.getenv('DEEPL_API_KEY')
    if not api_key:
        logger.error("DEEPL_API_KEYが設定されていません。.envファイルにDEEPL_API_KEYを設定してください。")
        return text
    
    try:
        translator = deepl.Translator(api_key)
        
        # DeepLの言語コードに変換（ENは非推奨のためEN-USを使用）
        deepl_lang_map = {
            'en': 'EN-US',  # EN-GB（イギリス英語）またはEN-US（アメリカ英語）を指定
            'ko': 'KO',
            'zh': 'ZH'
        }
        deepl_target = deepl_lang_map.get(target_language, 'EN-US')
        
        # HTMLタグを保護して翻訳
        start_time = time.time()
        result = translator.translate_text(
            text,
            source_lang='JA',
            target_lang=deepl_target,
            tag_handling='html'  # HTMLタグを保護
        )
        elapsed_time = time.time() - start_time
        
        translated_text = result.text
        
        # 翻訳結果を検証：重要なセクションが含まれているか確認
        important_keywords = ['医師', '受診', '質問', '追加', 'お伺い', 'doctor', 'consultation', 'question', 'additional']
        has_important_sections = any(keyword in translated_text for keyword in important_keywords)
        
        if not has_important_sections and len(translated_text) < len(text) * 0.5:
            # 翻訳結果が短すぎる、または重要なセクションが欠けている場合は警告
            logger.warning(f"⚠️ 翻訳結果が不完全の可能性があります。元のテキスト長: {len(text)}, 翻訳後: {len(translated_text)}")
        
        logger.info(f"✅ DeepL翻訳完了 ({target_language}): {elapsed_time:.2f}秒, {len(translated_text)}文字")
        
        # キャッシュに保存
        set_cached_translation(text, target_language, translated_text)
        
        return translated_text
        
    except deepl.exceptions.QuotaExceededException:
        logger.error("❌ DeepL APIのクォータを超過しました。")
        return text
    except deepl.exceptions.AuthorizationException:
        logger.error("❌ DeepL APIキーが無効です。")
        return text
    except Exception as e:
        logger.error(f"❌ DeepL翻訳エラー: {e}")
        return text  # 翻訳に失敗した場合は元のテキストを返す

# Markdown太文字をHTML太文字に変換する関数
def convert_markdown_bold(text):
    """Markdown形式の太文字（**文字**）をHTML太文字タグに変換"""
    if text is None:
        return ""
    # **文字** を <strong>文字</strong> に変換
    result = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
    # ### で始まる行を除去
    result = re.sub(r'^###+\s*', '', result, flags=re.MULTILINE)
    # ## で始まる行を除去
    result = re.sub(r'^##+\s*', '', result, flags=re.MULTILINE)
    # # で始まる行を除去
    result = re.sub(r'^#+\s*', '', result, flags=re.MULTILINE)
    # 行頭の余分な空白を除去
    result = re.sub(r'^\s+', '', result, flags=re.MULTILINE)
    return result

# 使用上の注意生成のキャッシュ
_usage_notes_cache = {}

def generate_usage_notes(medicine_name: str, medicine_info: dict, user_info: dict = None) -> str:
    """
    ChatGPTを使用して医薬品の使用上の注意を自動生成（キャッシュ機能付き）
    
    Args:
        medicine_name: 医薬品名
        medicine_info: 医薬品情報（成分、効能、年齢制限など）
        user_info: ユーザー情報（年齢、妊娠状態など）
    
    Returns:
        str: 生成された使用上の注意
    """
    try:
        # キャッシュキーの生成（医薬品名とユーザー情報の組み合わせ）
        cache_key = f"{medicine_name}_{hash(str(user_info))}"
        
        # キャッシュから取得を試行
        if cache_key in _usage_notes_cache:
            if os.getenv('DEBUG_MODE', 'false').lower() == 'true' or logger.level <= logging.DEBUG:
                logger.debug(f"📋 使用上の注意をキャッシュから取得: {medicine_name}")
            return _usage_notes_cache[cache_key]
        
        # ユーザー情報の準備
        user_context = ""
        if user_info:
            if user_info.get('age'):
                user_context += f"年齢: {user_info['age']}歳\n"
            if user_info.get('pregnant'):
                user_context += "妊娠中\n"
            if user_info.get('breastfeeding'):
                user_context += "授乳中\n"
            if user_info.get('allergies'):
                user_context += f"アレルギー: {', '.join(user_info['allergies'])}\n"
        
        # ドーピング禁止物質の情報を追加
        doping_info = ""
        if medicine_info.get('doping_prohibited') == '禁止物質あり':
            doping_info = f"""
ドーピング禁止物質情報:
- 禁止物質あり: {medicine_info.get('doping_prohibited', 'なし')}
- 競技会区分: {medicine_info.get('competition_category', '情報なし')}
- 条件: {medicine_info.get('conditions', '情報なし')}
"""
        
        # プロンプトの構築
        prompt = f"""
以下の医薬品について、使用上の注意を生成してください。

医薬品名: {medicine_name}
成分: {medicine_info.get('ingredients', '情報なし')}
効能・効果: {medicine_info.get('efficacy', '情報なし')}
年齢制限: {medicine_info.get('age_restriction', '情報なし')}
用法・用量: {medicine_info.get('usage', '情報なし')}
{doping_info}

ユーザー情報:
{user_context if user_context else '情報なし'}

以下の形式で使用上の注意を生成してください：
1. 基本的な使用上の注意
2. 年齢・性別による注意点（年齢制限の詳細を含む）
3. 妊娠・授乳中の注意点
4. アレルギーに関する注意点
5. 副作用について
6. 他の薬との相互作用
7. 保存方法・保管上の注意
8. ドーピング禁止物質に関する注意（該当する場合）

各項目は簡潔で分かりやすく、実際の使用場面で役立つ内容にしてください。
特に年齢制限とドーピング禁止物質については、具体的で明確な注意事項を含めてください。
"""
        
        # ChatGPT APIを呼び出し
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "あなたは医薬品の専門家です。症状に適した医薬品を推奨し、使用上の注意を説明してください。効能・効果が限定された特殊用途の医薬品（例：「食あたり等」「便秘」など）は、ユーザーの症状がその限定用途と完全に一致する場合のみ推奨してください。一般的な症状に対して特殊用途の医薬品を無理に推奨することは避けてください。"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1200,
            temperature=0.7
        )
        
        usage_notes = response.choices[0].message.content.strip()
        
        # HTMLタグを適切に処理
        usage_notes = convert_markdown_bold(usage_notes)
        
        # キャッシュに保存（最大100件まで）
        if len(_usage_notes_cache) < 100:
            _usage_notes_cache[cache_key] = usage_notes
            if os.getenv('DEBUG_MODE', 'false').lower() == 'true' or logger.level <= logging.DEBUG:
                logger.debug(f"💾 使用上の注意をキャッシュに保存: {medicine_name}")
        
        return usage_notes
        
    except Exception as e:
        logger.error(f"使用上の注意生成エラー: {e}")
        return "使用上の注意の生成に失敗しました。薬剤師または登録販売者にご相談ください。"

# テキストを整形して見やすくする関数
def format_text_for_display(text):
    """テキストを整形して見やすくする"""
    if text is None:
        return ""
    
    # ①、②、③などの丸数字の後に改行を追加
    text = re.sub(r'([①②③④⑤⑥⑦⑧⑨⑩])\s*', r'\1<br>', text)
    
    # 1.、2.、3.などの数字の後に改行を追加
    text = re.sub(r'(\d+\.)\s*', r'\1<br>', text)
    
    # - で始まる行の前に改行を追加
    text = re.sub(r'\n\s*-\s*', r'<br>- ', text)
    
    # ・ で始まる行の前に改行を追加
    text = re.sub(r'\n\s*・\s*', r'<br>・ ', text)
    
    # 改行を適切に処理（最初に改行を処理）
    text = text.replace('\n\n', '<br><br>')
    text = text.replace('\n', '<br>')
    
    # 丸数字の後の改行を再度確認
    text = re.sub(r'([①②③④⑤⑥⑦⑧⑨⑩])(?!<br>)', r'\1<br>', text)
    
    # 数字の後の改行を再度確認
    text = re.sub(r'(\d+\.)(?!<br>)', r'\1<br>', text)
    
    # Markdown太文字をHTML太文字に変換
    text = convert_markdown_bold(text)
    
    return text

# .envファイルから環境変数を読み込み（オプショナル）
# load_dotenv関数をグローバルスコープで利用できるようにする
load_dotenv_func = None
try:
    from dotenv import load_dotenv
    load_dotenv_func = load_dotenv  # グローバル変数として保存
    # スクリプトのディレクトリを基準に.envファイルを読み込む（BASE_DIRはプロジェクトルート）
    env_path = os.path.join(BASE_DIR, '.env')
    
    # デバッグ情報（DEBUG_MODE時のみ）
    if os.getenv('DEBUG_MODE', 'false').lower() == 'true':
        logger.debug(f"[DEBUG] BASE_DIR: {BASE_DIR}")
        logger.debug(f"[DEBUG] 現在の作業ディレクトリ: {os.getcwd()}")
        logger.debug(f"[DEBUG] .envファイルのパス（BASE_DIR）: {env_path}")
        logger.debug(f"[DEBUG] .envファイル存在確認（BASE_DIR）: {os.path.exists(env_path)}")
    
    # まず引数なしでload_dotenvを呼び出し、現在の作業ディレクトリから上位ディレクトリを自動検索
    loaded = load_dotenv(override=True)  # override=Trueで確実に読み込む
    if os.getenv('DEBUG_MODE', 'false').lower() == 'true':
        logger.debug(f"[DEBUG] load_dotenv() (引数なし) 結果: {loaded}")
    
    # 明示的なパスも試す（存在する場合は読み込む）
    env_loaded = False
    if os.path.exists(env_path):
        env_loaded = load_dotenv(env_path, override=True)  # override=Trueで確実に読み込む
        if os.getenv('DEBUG_MODE', 'false').lower() == 'true':
            logger.debug(f"[DEBUG] load_dotenv({env_path}) 結果: {env_loaded}")
    else:
        # 現在の作業ディレクトリから.envファイルを確認
        cwd_env = os.path.join(os.getcwd(), '.env')
        if os.getenv('DEBUG_MODE', 'false').lower() == 'true':
            logger.debug(f"[DEBUG] .envファイルのパス（現在の作業ディレクトリ）: {cwd_env}")
            logger.debug(f"[DEBUG] .envファイル存在確認（CWD）: {os.path.exists(cwd_env)}")
        if os.path.exists(cwd_env):
            env_loaded = load_dotenv(cwd_env, override=True)  # override=Trueで確実に読み込む
            if os.getenv('DEBUG_MODE', 'false').lower() == 'true':
                logger.debug(f"[DEBUG] load_dotenv({cwd_env}) 結果: {env_loaded}")
    
    logger.info("dotenvを使用して.envファイルから環境変数を読み込みました。")
except ImportError:
    logger.info("python-dotenvがインストールされていません。環境変数のみを使用します。")

# --- OpenAI APIキー設定 ---
# 環境変数からAPIキーを取得
api_key = os.getenv('OPENAI_API_KEY')

# デバッグ用: 環境変数の確認（値の一部のみ表示）
if api_key:
    if os.getenv('DEBUG_MODE', 'false').lower() == 'true':
        logger.debug(f"APIキーが読み込まれました（長さ: {len(api_key)}文字）")
else:
    logger.warning("WARNING: OpenAI API keyが環境変数に設定されていません。")
    logger.warning("環境変数 OPENAI_API_KEY を設定してください。")

# --- OpenAIクライアント初期化 ---
client = None
if api_key:
    try:
        client = OpenAI(api_key=api_key)
        if os.getenv('DEBUG_MODE', 'false').lower() == 'true':
            logger.debug("OpenAI client initialized successfully.")
    except Exception as e:
        logger.error(f"Error initializing OpenAI client: {e}")
else:
    logger.error("Error: OpenAI API key not found. Please set it in environment variables or .env file.")

# --- CSVファイルの読み込み ---
def clean_csv_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    CSVデータのクリーニング: 成分名の表記ゆれの統一、欠損値の補完、効能効果の正規化
    
    Args:
        df: クリーニング前のDataFrame
    
    Returns:
        クリーニング後のDataFrame
    """
    if df is None or df.empty:
        logger.warning("CSVデータが空です。クリーニングをスキップします。")
        return df
    
    logger.info("CSVデータのクリーニングを開始します...")
    df_cleaned = df.copy()
    
    # 1. 成分名の表記ゆれの統一
    if '成分' in df_cleaned.columns:
        # INGREDIENT_DICTIONARYから正規化マッピングを作成
        try:
            from rule_based_recommendation import INGREDIENT_DICTIONARY
            ingredient_mapping = {}
            for canonical_name, info in INGREDIENT_DICTIONARY.items():
                synonyms = info.get('synonyms', [])
                for synonym in synonyms:
                    ingredient_mapping[synonym.lower()] = canonical_name
            
            def normalize_ingredient_name(ingredients_str):
                """成分名を正規化"""
                if pd.isna(ingredients_str) or not isinstance(ingredients_str, str):
                    return ingredients_str
                
                # 改行や区切り文字で分割
                parts = re.split(r'[\n、,/，／・]+', ingredients_str)
                normalized_parts = []
                
                for part in parts:
                    part = part.strip()
                    if not part:
                        continue
                    
                    # 正規化マッピングを適用
                    part_lower = part.lower()
                    if part_lower in ingredient_mapping:
                        normalized_parts.append(ingredient_mapping[part_lower])
                    else:
                        # マッピングにない場合はそのまま（既に正規化されている可能性）
                        normalized_parts.append(part)
                
                # 重複を除去して結合
                unique_parts = list(dict.fromkeys(normalized_parts))  # 順序を保持しながら重複除去
                return '\n'.join(unique_parts)
            
            df_cleaned['成分'] = df_cleaned['成分'].apply(normalize_ingredient_name)
            logger.info("成分名の表記ゆれを統一しました。")
        except ImportError:
            logger.warning("INGREDIENT_DICTIONARYをインポートできませんでした。成分名の正規化をスキップします。")
    
    # 2. 欠損値の補完
    # 効能効果が空の場合は、医薬品の種類から推測（簡易的な補完）
    if '効能効果' in df_cleaned.columns:
        missing_efficacy_count = df_cleaned['効能効果'].isna().sum()
        if missing_efficacy_count > 0:
            # 医薬品の種類に基づいてデフォルト効能効果を設定（簡易的）
            default_efficacy_map = {
                '解熱鎮痛薬': '発熱、頭痛、生理痛',
                '風邪薬': '風邪の諸症状',
                '胃腸薬': '胃腸の不調',
                '漢方薬': '体質改善',
                '外用薬（のど）': 'のどの痛み',
                '外用薬（皮膚）': '皮膚の炎症'
            }
            
            if '医薬品の種類' in df_cleaned.columns:
                for idx, row in df_cleaned.iterrows():
                    if pd.isna(row['効能効果']):
                        medicine_type = row.get('医薬品の種類', '')
                        if medicine_type in default_efficacy_map:
                            df_cleaned.at[idx, '効能効果'] = default_efficacy_map[medicine_type]
            
            logger.info(f"効能効果の欠損値を補完しました（{missing_efficacy_count}件）。")
    
    # 成分が空の場合は、医薬品の種類から推測（簡易的な補完）
    if '成分' in df_cleaned.columns:
        missing_ingredient_count = df_cleaned['成分'].isna().sum()
        if missing_ingredient_count > 0:
            # 成分が空の場合は空文字列に統一（後続処理で扱いやすくする）
            df_cleaned['成分'] = df_cleaned['成分'].fillna('')
            logger.info(f"成分の欠損値を補完しました（{missing_ingredient_count}件）。")
    
    # 3. 効能効果の正規化
    if '効能効果' in df_cleaned.columns:
        # 症状名の正規化マッピング（「生理不順」→「月経不順」など）
        efficacy_normalization_map = {
            '生理不順': '月経不順',
            '生理異常': '月経不順',
            '生理痛': '月経痛',
            '生理の痛み': '月経痛',
            '血の道症': '月経不順',  # より広義な表現を月経不順に統一
            '血の道': '月経不順'
        }
        
        def normalize_efficacy(efficacy_str):
            """効能効果を正規化"""
            if pd.isna(efficacy_str) or not isinstance(efficacy_str, str):
                return efficacy_str
            
            normalized = efficacy_str
            for old_term, new_term in efficacy_normalization_map.items():
                # 単語境界を考慮した置換
                pattern = r'\b' + re.escape(old_term) + r'\b'
                normalized = re.sub(pattern, new_term, normalized)
            
            return normalized
        
        df_cleaned['効能効果'] = df_cleaned['効能効果'].apply(normalize_efficacy)
        logger.info("効能効果の正規化を完了しました。")
    
    logger.info("CSVデータのクリーニングが完了しました。")
    return df_cleaned

df = None
csv_load_status = {
    "success": False,
    "encoding": None,
    "error": None,
    "row_count": 0,
    "col_count": 0,
    "columns": [],
    "path": CSV_PATH
}
encodings = ['utf-8', 'shift_jis', 'cp932', 'euc-jp']

for encoding in encodings:
    try:
        df = pd.read_csv(CSV_PATH, encoding=encoding)
        # CSVデータのクリーニングを実行
        df = clean_csv_data(df)
        csv_load_status["success"] = True
        csv_load_status["encoding"] = encoding
        csv_load_status["row_count"] = len(df)
        csv_load_status["col_count"] = len(df.columns)
        csv_load_status["columns"] = list(df.columns)
        logger.info(f"CSVファイルを正常に読み込みました（エンコーディング: {encoding}）。")
        break
    except UnicodeDecodeError:
        if os.getenv('DEBUG_MODE', 'false').lower() == 'true':
            logger.debug(f"エンコーディング {encoding} で読み込みに失敗しました。")
        continue
    except FileNotFoundError:
        csv_load_status["error"] = "FileNotFoundError"
        logger.error("エラー: otc_medicine_data.csvファイルが見つかりません。")
        break
    except Exception as e:
        csv_load_status["error"] = str(e)
        logger.error(f"CSVファイルの読み込みエラー: {e}")
        break

if not csv_load_status["success"]:
    logger.error("すべてのエンコーディングでCSVファイルの読み込みに失敗しました。")

def get_medicines_by_symptom(symptom_text, df=None):
    if df is None:
        try:
            from medicine_logic import df as global_df
            df = global_df
        except ImportError:
            return ["データが読み込まれていません"]
    if df is None:
        return ["データが読み込まれていません"]
    if '効能効果' not in df.columns:
        return ["CSVに効能効果カラムがありません"]
    # 症状テキストが効能効果に部分一致する行を抽出
    matched = df[df['効能効果'].astype(str).str.contains(symptom_text, na=False)]
    if matched.empty:
        return ["該当する市販薬情報が見つかりませんでした。"]
    # 製品名・メーカー名・分類・効能効果・成分をまとめて返す
    result = []
    for _, row in matched.iterrows():
        info = f"製品名: {row['製品名']} / メーカー: {row['メーカー名']} / 分類: {row['分類']}\n効能効果: {row['効能効果']}\n成分: {row['成分']}"
        result.append(info)
    return result

def gpt_guess_symptom(user_text, symptom_list, client=None):
    """
    ChatGPTで症状リストから最も近い症状名を1～3個推定
    """
    if client is None:
        client = OpenAI(api_key=api_key)
    prompt = (
        "あなたは医薬品推奨システムです。\n"
        "以下は症状リストです。\n"
        "ユーザーの症状文から最も近い症状名を日本語で返してください。(複数選択可)\n\n"
        "【症状リスト】\n" +
        "\n".join(f"{i+1}. {s}" for i, s in enumerate(symptom_list)) +
        f"\nユーザーの症状: {user_text}"
    )
    messages = [
        {"role": "system", "content": prompt}
    ]
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        temperature=0
    )
    content = response.choices[0].message.content if response.choices[0].message.content else ""
    if os.getenv('DEBUG_MODE', 'false').lower() == 'true' or logger.level <= logging.DEBUG:
        logger.debug(f"ChatGPT返答:\n{content.strip()}")
    # 改行やカンマ区切りで分割
    symptoms = [s.strip() for s in re.split(r'[\n,、]', content) if s.strip()]
    return symptoms

def find_otc_candidates(symptoms, df_otc, max_candidates=20):
    """
    症状名リストのいずれかが効能効果に含まれる市販薬を抽出
    """
    mask = df_otc['効能効果'].astype(str).apply(lambda x: any(s in x for s in symptoms))
    return df_otc[mask].head(max_candidates)

def gpt_select_best_otc(user_text, candidates, client=None):
    """
    ChatGPTで候補リストから最適な市販薬3つを選ばせる
    """
    if client is None:
        client = OpenAI(api_key=api_key)
    prompt = (
        f"あなたは医薬品推奨システムです。ユーザーの症状「{user_text}」に最も適した市販薬を3つ選び、理由も簡単に説明してください。(市販薬の重複は避けてください)\n\n"
        "【候補リスト】\n" +
        "\n".join(
            f"{i+1}. 製品名: {row['製品名']} / 効能効果: {row['効能効果']} / 成分: {row['成分']}"
            for i, (_, row) in enumerate(candidates.iterrows())
        )
    )
    messages = [
        {"role": "system", "content": prompt}
    ]
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        temperature=0
    )
    content = response.choices[0].message.content if response.choices[0].message.content else ""
    if os.getenv('DEBUG_MODE', 'false').lower() == 'true' or logger.level <= logging.DEBUG:
        logger.debug(f"ChatGPT返答:\n{content.strip()}")
    return content.strip()

def recommend_otc_medicines_via_gpt(user_text, symptom_csv_path=None, otc_csv_path=None, max_candidates=20, client=None):
    """
    ユーザー症状文→ChatGPTで症状名推定→候補薬抽出→ChatGPTで最適薬3つ選定
    """
    import pandas as pd
    import os
    # CSV読み込み
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, "data")
    symptom_csv = symptom_csv_path or os.path.join(data_dir, "症状-薬.csv")
    otc_csv = otc_csv_path or os.path.join(data_dir, "otc_medicine_data.csv")
    df_symptom = pd.read_csv(symptom_csv)
    df_otc = pd.read_csv(otc_csv)
    
    # NaN値を適切に処理
    df_otc = df_otc.fillna("")
    # 症状リスト作成
    symptom_list = df_symptom["症状"].dropna().unique().tolist()
    # 1. ChatGPTで症状名推定
    symptoms = gpt_guess_symptom(user_text, symptom_list, client=client)
    # 2. 候補薬抽出
    candidates = find_otc_candidates(symptoms, df_otc, max_candidates=max_candidates)
    if candidates.empty:
        return "該当する市販薬情報が見つかりませんでした。"
    # 3. ChatGPTで最適薬3つ選定
    result = gpt_select_best_otc(user_text, candidates, client=client)
    if os.getenv('DEBUG_MODE', 'false').lower() == 'true' or logger.level <= logging.DEBUG:
        logger.debug(f"ChatGPT返答:\n{result}")
    return result

def recommend_otc_medicines_from_summarized(user_text, summarized_csv_path=None, max_candidates=20, client=None):
    """
    summarized_efficacy_data.csvを用いて、
    1. 症状語リストを自動抽出
    2. ChatGPTで症状名推定（表記ゆれ・複数症状対応）
    3. 候補薬リストを抽出
    4. ChatGPTに候補リスト＋症状文を渡し、最適な3つを選ばせる
    """
    import pandas as pd
    import os
    import re
    # CSV読み込み
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, "data")
    summarized_csv = summarized_csv_path or os.path.join(data_dir, "summarized_efficacy_data.csv")
    df = pd.read_csv(summarized_csv)
    
    # NaN値を適切に処理
    df = df.fillna("")
    # --- 症状語リストを抽出 ---
    symptom_set = set()
    for eff in df["Summarized Efficacy"].dropna():
        # かっこ内の症状語を抽出
        m = re.search(r'（(.+?)）', eff)
        if m:
            for s in re.split(r'[、,]', m.group(1)):
                s = s.strip()
                if s:
                    symptom_set.add(s)
    # 類義語・表記ゆれ対応（例: 咳/せき, 鼻水/鼻みず など）
    synonym_map = {
        "咳": ["咳", "せき"],
        "鼻水": ["鼻水", "鼻みず"],
        "痰": ["痰", "たん"],
        "悪寒": ["悪寒", "さむけ"],
        "関節の痛み": ["関節の痛み", "関節痛"],
        "筋肉の痛み": ["筋肉の痛み", "筋肉痛"],
        # 必要に応じて追加
    }
    # 症状語リストを展開
    expanded_symptom_set = set()
    for s in symptom_set:
        expanded_symptom_set.add(s)
        for syns in synonym_map.values():
            if s in syns:
                expanded_symptom_set.update(syns)
    symptom_list = sorted(expanded_symptom_set)
    # --- 1. ChatGPTで症状名推定 ---
    symptoms = gpt_guess_symptom(user_text, symptom_list, client=client)
    # --- 2. 類義語も含めて候補薬抽出 ---
    # 入力症状の類義語も展開
    all_symptoms = set(symptoms)
    for s in symptoms:
        for key, syns in synonym_map.items():
            if s in syns:
                all_symptoms.update(syns)
    # 候補薬抽出（すべての症状語のいずれかを含むもの）
    mask = df["Summarized Efficacy"].astype(str).apply(lambda x: any(s in x for s in all_symptoms))
    candidates = df[mask].copy()
    # カバー症状数でソート（多くカバーする薬を上位に）
    def count_covered(eff):
        return sum(s in eff for s in all_symptoms)
    candidates["_cover_count"] = candidates["Summarized Efficacy"].astype(str).apply(count_covered)
    candidates = candidates.sort_values("_cover_count", ascending=False).head(max_candidates)
    if candidates.empty:
        return "該当する市販薬情報が見つかりませんでした。"
    # --- 3. ChatGPTで最適薬3つ選定 ---
    # プロンプト工夫: 症状文・推定症状語・候補リストを明示
    prompt = (
        f"あなたは医薬品推奨システムです。ユーザーの症状:『{user_text}』\n"
        f"推定された症状語: {', '.join(symptoms)}\n"
        "以下の候補リストから、症状に最も適した市販薬を3つ選び、それぞれの医薬品の特徴を効果効能から要約して日本語で説明してください。\n"
        "【候補リスト】\n" +
        "\n".join(
            f"{i+1}. 製品名: {row['製品名']} / 効能効果: {row['Summarized Efficacy']}"
            for i, (_, row) in enumerate(candidates.iterrows())
        )
    )
    messages = [
        {"role": "system", "content": prompt}
    ]
    if client is None:
        client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        temperature=0
    )
    content = response.choices[0].message.content if response.choices[0].message.content else ""
    if os.getenv('DEBUG_MODE', 'false').lower() == 'true' or logger.level <= logging.DEBUG:
        logger.debug(f"ChatGPT返答:\n{content.strip()}")
    return content.strip() 

def gpt_select_efficacy_candidates(user_text, summarized_csv_path=None, max_candidates=30, client=None):
    """
    ChatGPTにsummarized_efficacy_data.csvの効能効果リストを渡し、
    ユーザー症状に最も近い効能効果（複数可）を選ばせる
    """
    import pandas as pd
    import os
    base_dir = os.path.dirname(os.path.abspath(__file__))
    summarized_csv = summarized_csv_path or os.path.join(base_dir, "summarized_efficacy_data.csv")
    df = pd.read_csv(summarized_csv)
    
    # NaN値を適切に処理
    df = df.fillna("")
    efficacy_list = df["Summarized Efficacy"].dropna().unique().tolist()
    # 候補数が多すぎる場合はランダムサンプリング
    import random
    if len(efficacy_list) > max_candidates:
        efficacy_list = random.sample(efficacy_list, max_candidates)
    prompt = (
        f"あなたは医薬品推奨システムです。下記は市販薬の効能効果リストです。\n"
        f"ユーザーの症状:『{user_text}』\n"
        "この中から症状に最も近い効能効果をすべて選び、日本語でリスト形式で出力してください。\n"
        "【効能効果リスト】\n" +
        "\n".join(f"{i+1}. {e}" for i, e in enumerate(efficacy_list))
    )
    messages = [
        {"role": "system", "content": prompt}
    ]
    if client is None:
        client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        temperature=0
    )
    content = response.choices[0].message.content if response.choices[0].message.content else ""
    if os.getenv('DEBUG_MODE', 'false').lower() == 'true' or logger.level <= logging.DEBUG:
        logger.debug(f"ChatGPT返答:\n{content.strip()}")
    # リスト形式で返す
    selected = [line.strip(" ・-0123456789.") for line in content.splitlines() if line.strip()]
    # 元の効能効果リストと突合して正規化
    selected_set = set(selected)
    matched_efficacy = [e for e in efficacy_list if any(s in e or e in s for s in selected_set)]
    return matched_efficacy

def select_symptoms_via_gpt(user_text, symptoms_csv_path=None, client=None, max_symptoms=250):
    """
    ユーザーの症状文からChatGPTを使って適切な症状を抽出する
    """
    import pandas as pd
    import os
    import re
    
    # より包括的な症状リストを作成
    comprehensive_symptom_list = [
        # 風邪・インフルエンザ関連
        "頭痛", "発熱", "咳", "鼻水", "鼻づまり", "のどの痛み", "くしゃみ", "寒気", "悪寒",
        # 消化器系
        "腹痛", "下痢", "便秘", "吐き気", "嘔吐", "胃痛", "胸やけ", "胃もたれ",
        # 神経系・全身症状
        "めまい", "疲労感", "倦怠感", "だるさ", "むくみ", "筋肉痛", "関節痛", "肩こり", "腰痛",
        # 皮膚系
        "かゆみ", "発疹", "湿疹", "蕁麻疹", "皮膚の乾燥",
        # 睡眠・精神系
        "不眠", "眠気", "イライラ", "不安", "ストレス",
        # 女性特有
        "生理痛", "月経不順", "更年期症状",
        # その他
        "口内炎", "目の疲れ", "目のかゆみ", "目の充血", "耳鳴り", "動悸"
    ]
    
    # 一般的な表現から典型的な症状を推測する前処理
    user_text_lower = user_text.lower()
    inferred_symptoms = []
    
    # 風邪関連のキーワード検出
    cold_keywords = ["風邪", "かぜ", "風邪をひ", "風邪気味", "風邪っぽい", "風邪の症状"]
    if any(kw in user_text_lower for kw in cold_keywords):
        # 風邪の典型的な症状を追加
        inferred_symptoms.extend(["頭痛", "発熱", "咳", "鼻水", "のどの痛み"])
    
    # インフルエンザ関連のキーワード検出
    flu_keywords = ["インフルエンザ", "インフル", "インフルエンザの症状", "インフルエンザっぽい"]
    if any(kw in user_text_lower for kw in flu_keywords):
        # インフルエンザの典型的な症状を追加
        inferred_symptoms.extend(["発熱", "頭痛", "関節痛", "筋肉痛", "悪寒", "咳"])
    
    # 胃腸炎関連のキーワード検出
    gastroenteritis_keywords = ["胃腸炎", "胃腸の調子", "お腹の調子", "お腹を壊"]
    if any(kw in user_text_lower for kw in gastroenteritis_keywords):
        # 胃腸炎の典型的な症状を追加
        inferred_symptoms.extend(["腹痛", "下痢", "吐き気"])
    
    # 症状抽出のプロンプトを改善
    prompt = f"""
あなたは医薬品推奨システムです。ユーザーの症状文から該当する症状を正確に抽出してください。

【ユーザーの症状文】
{user_text}

【抽出すべき症状リスト】
{', '.join(comprehensive_symptom_list)}

【重要な指示】
1. ユーザーの症状文から該当する症状を抽出してください
2. **一般的な表現から典型的な症状を推測してください**：
   - 「風邪をひいています」→ 頭痛、発熱、咳、鼻水、のどの痛みなどの典型的な風邪症状を推測
   - 「インフルエンザです」→ 発熱、頭痛、関節痛、筋肉痛、悪寒などの典型的なインフルエンザ症状を推測
   - 「胃腸炎です」→ 腹痛、下痢、吐き気などの典型的な胃腸炎症状を推測
3. 症状文に明示的に書かれていない症状でも、一般的な表現から推測できる典型的な症状は含めてください
4. ただし、症状文が「こんにちは」などの挨拶のみの場合は、症状なしとして空のリストを返してください

【回答形式】
該当する症状を以下の形式で出力してください：
症状1, 症状2, 症状3

該当する症状がない場合は「なし」と出力してください。
"""
    
    messages = [
        {"role": "system", "content": """あなたは医薬品推奨システムです。ユーザーの症状文から正確に症状を抽出してください。

重要な注意事項：
- 「風邪をひいています」のような一般的な表現からも、典型的な症状（頭痛、発熱、咳、鼻水、のどの痛みなど）を推測して抽出してください
- 「インフルエンザです」のような表現からも、典型的な症状（発熱、頭痛、関節痛、筋肉痛、悪寒など）を推測して抽出してください
- 症状文に明示的に書かれていない症状でも、一般的な表現から推測できる典型的な症状は含めてください"""},
        {"role": "user", "content": prompt}
    ]
    
    # クライアントが指定されていない場合、api_keyから初期化
    if client is None:
        # まず環境変数から直接取得を試みる（最新の値を取得）
        current_api_key = os.getenv('OPENAI_API_KEY')
        
        # 環境変数にない場合、.envファイルを再読み込みしてから再取得
        if current_api_key is None:
            print("[DEBUG] api_keyがNoneのため、環境変数から再取得を試みます...")
            # .envファイルを再読み込み（明示的なパスを指定）
            env_path = os.path.join(BASE_DIR, '.env')
            print(f"[DEBUG] .envファイル再読み込み試行: {env_path}")
            
            # グローバル変数として保存されたload_dotenv_funcを使用、または直接インポート
            try:
                # まずグローバル変数を試す
                dotenv_func = load_dotenv_func
                if dotenv_func is None:
                    # グローバル変数がNoneの場合、直接インポートを試みる
                    print("[DEBUG] load_dotenv_funcがNoneのため、直接インポートを試みます...")
                    from dotenv import load_dotenv
                    dotenv_func = load_dotenv
                    print("[DEBUG] load_dotenvの直接インポートに成功しました")
                
                # BASE_DIRの.envファイルを試す
                if os.path.exists(env_path):
                    loaded = dotenv_func(env_path, override=True)  # override=Trueで強制的に読み込む
                    print(f"[DEBUG] .envファイル再読み込み結果: {loaded}")
                else:
                    # 現在の作業ディレクトリからも試す
                    cwd_env = os.path.join(os.getcwd(), '.env')
                    print(f"[DEBUG] .envファイル再読み込み試行（CWD）: {cwd_env}")
                    if os.path.exists(cwd_env):
                        loaded = dotenv_func(cwd_env, override=True)
                        print(f"[DEBUG] .envファイル再読み込み結果（CWD）: {loaded}")
                    # 引数なしでも試す（自動検索）
                    dotenv_func(override=True)
                
                # 再読み込み後に環境変数から再取得
                current_api_key = os.getenv('OPENAI_API_KEY')
            except ImportError as e:
                print(f"[DEBUG] python-dotenvのインポートに失敗: {e}")
                # .envファイルを直接読み込む方法を試す
                if os.path.exists(env_path):
                    print("[DEBUG] .envファイルを直接読み込みます...")
                    try:
                        with open(env_path, 'r', encoding='utf-8') as f:
                            for line in f:
                                line = line.strip()
                                if line and not line.startswith('#') and '=' in line:
                                    key, value = line.split('=', 1)
                                    key = key.strip()
                                    value = value.strip().strip('"').strip("'")
                                    if key == 'OPENAI_API_KEY':
                                        os.environ[key] = value
                                        current_api_key = value
                                        print(f"[DEBUG] .envファイルから直接環境変数を設定しました（長さ: {len(value)}文字）")
                                        break
                    except Exception as file_error:
                        print(f"[DEBUG] .envファイル直接読み込みエラー: {file_error}")
            except Exception as e:
                print(f"[DEBUG] .envファイル読み込みエラー: {e}")
                import traceback
                traceback.print_exc()
                # エラーが発生しても環境変数から再取得を試みる
                current_api_key = os.getenv('OPENAI_API_KEY')
            
            if current_api_key:
                print(f"[DEBUG] APIキー再取得成功（長さ: {len(current_api_key)}文字）")
            else:
                print("[DEBUG] APIキー再取得失敗")
                # 最後の手段として、グローバル変数のapi_keyも確認
                if api_key:
                    current_api_key = api_key
                    print(f"[DEBUG] グローバル変数api_keyを使用（長さ: {len(current_api_key)}文字）")
        
        if current_api_key is None:
            error_msg = "OPENAI_API_KEYが環境変数に設定されていません。.envファイルまたは環境変数を確認してください。"
            print(f"❌ {error_msg}")
            print(f"[DEBUG] BASE_DIR: {BASE_DIR}")
            print(f"[DEBUG] 現在の作業ディレクトリ: {os.getcwd()}")
            env_check_path = os.path.join(BASE_DIR, '.env')
            print(f"[DEBUG] .envファイル存在確認: {os.path.exists(env_check_path)}")
            # .envファイルの内容を確認（最初の1行のみ、セキュリティのため）
            if os.path.exists(env_check_path):
                try:
                    with open(env_check_path, 'r', encoding='utf-8') as f:
                        first_line = f.readline().strip()
                        if 'OPENAI_API_KEY' in first_line:
                            print(f"[DEBUG] .envファイルにOPENAI_API_KEYが含まれています: {first_line[:20]}...")
                        else:
                            print("[DEBUG] .envファイルの最初の行にOPENAI_API_KEYが含まれていません")
                except Exception as e:
                    print(f"[DEBUG] .envファイル読み込みエラー: {e}")
            return {
                'status': 'error',
                'symptoms': [],
                'message': error_msg
            }
        
        client = OpenAI(api_key=current_api_key)
    
    print("ユーザー入力:", user_text)
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.1,
            max_tokens=500
        )
        content = response.choices[0].message.content if response.choices[0].message.content else ""
    except Exception as e:
        logger.error(f"ChatGPT API エラー: {e}")
        return {
            'status': 'error',
            'symptoms': [],
            'message': f'ChatGPT API エラー: {e}'
        }
    if os.getenv('DEBUG_MODE', 'false').lower() == 'true' or logger.level <= logging.DEBUG:
        logger.debug(f"ChatGPT返答:\n{content.strip()}")
    
    # 症状抽出の結果を処理
    symptoms = []
    if "なし" in content or "症状なし" in content or not content.strip():
        # ChatGPTが「なし」と返答した場合でも、前処理で推測した症状があれば使用
        if inferred_symptoms:
            symptoms = inferred_symptoms
            print(f"前処理で推測した症状を使用: {symptoms}")
        else:
            return {
                'status': 'success',
                'symptoms': [],
                'message': 'No symptoms detected'
            }
    else:
        # カンマ区切りで症状を抽出
        if "," in content:
            symptoms = [s.strip() for s in content.split(",") if s.strip()]
        else:
            # 改行区切りの場合
            symptoms = [line.strip(" ・-0123456789.") for line in content.splitlines() if line.strip()]
        
        # 前処理で推測した症状とマージ（重複を除去）
        all_symptoms = list(set(symptoms + inferred_symptoms))
        symptoms = all_symptoms
    
    # 症状リストと照合して正規化
    matched_symptoms = []
    for symptom in symptoms:
        # 完全一致を探す
        if symptom in comprehensive_symptom_list:
            matched_symptoms.append(symptom)
        else:
            # 部分一致を探す
            for ref_symptom in comprehensive_symptom_list:
                if symptom in ref_symptom or ref_symptom in symptom:
                    matched_symptoms.append(ref_symptom)
                    break
    
    # 重複を除去
    matched_symptoms = list(set(matched_symptoms))
    
    return {
        'status': 'success',
        'symptoms': matched_symptoms,
        'message': f'Extracted {len(matched_symptoms)} symptoms'
    } 

def analyze_symptoms_and_medicine_type(user_text, client=None):
    """
    症状文と症状リスト、医薬品の種類のデータをChatGPTに渡して
    症状（複数選択可）と適する医薬品の種類を返す
    
    診断名が検出された場合は、適切な返信を返す
    """
    if client is None:
        client = OpenAI(api_key=api_key)
    
    # 診断名の検出（先にチェック）
    is_diagnosis, diagnosis_type, diagnosis_response = is_diagnosis_term(user_text)
    if is_diagnosis:
        logger.info(f"🏥 診断名が検出されました（analyze_symptoms_and_medicine_type）: {diagnosis_type} - {user_text}")
        return {
            'symptoms': [],
            'medicine_type': 'その他',
            'is_diagnosis': True,
            'diagnosis_type': diagnosis_type,
            'diagnosis_response': diagnosis_response
        }
    
    # 医薬品の種類リスト（CSVファイルの実際の内容に基づく）
    medicine_types = [
        "筋肉痛", "睡眠障害", "精神症状", "その他", "胃腸薬", 
        "解熱鎮痛薬", "外用薬（皮膚）", "抗アレルギー薬", "禁煙補助薬", 
        "鼻炎用薬", "風邪薬", "目薬", "更年期障害"
    ]
    
    # 症状リスト（包括的なリストを使用）
    symptoms_list = [
        "頭痛", "発熱", "咳", "鼻水", "鼻づまり", "のどの痛み", "くしゃみ", "寒気", "悪寒",
        "腹痛", "下痢", "便秘", "吐き気", "嘔吐", "胃痛", "胸やけ", "胃もたれ",
        "めまい", "疲労感", "倦怠感", "筋肉痛", "関節痛", "肩こり", "腰痛",
        "かゆみ", "発疹", "湿疹", "蕁麻疹", "皮膚の乾燥",
        "不眠", "眠気", "イライラ", "不安", "ストレス",
        "生理痛", "月経不順", "更年期症状",
        "口内炎", "目の疲れ", "目のかゆみ", "目の充血", "耳鳴り", "動悸"
    ]
    
    # 二日酔いのキーワードを検出
    hangover_keywords = ["二日酔い", "2日酔い", "二日酔", "2日酔", "飲みすぎ", "飲み過ぎ", "深酒", "アルコール"]
    is_hangover = any(keyword in user_text for keyword in hangover_keywords)
    
    prompt = f"""
あなたは医薬品推奨システムです。ユーザーの症状文を分析して、該当する症状と適する医薬品の種類を選択してください。

【ユーザーの症状文】
{user_text}

【選択可能な症状リスト】
{', '.join(symptoms_list)}

【医薬品の種類】
{', '.join(medicine_types)}

【重要な判断ルール】
- 「二日酔い」「2日酔い」「飲みすぎ」などのキーワードが含まれている場合は、「胃腸薬」を選択してください（最優先）
- 「目が痒い」「目のかゆみ」「目の痒み」などの目の症状は「目のかゆみ」として抽出し、医薬品の種類は「目薬」を選択してください
- 「目がかゆい」は皮膚のかゆみ（「かゆみ」）ではなく、「目のかゆみ」として分類してください
- 目の症状（目のかゆみ、目の充血、目の疲れ）がある場合は、必ず「目薬」を選択してください（最優先）
- 皮膚のかゆみ（「かゆみ」「かゆい」）は「目のかゆみ」とは区別し、「外用薬（皮膚）」を選択してください
- 鼻症状（鼻水、鼻づまり、くしゃみ）のみで発熱・のどの痛み・咳がない場合は「鼻炎用薬」を選択してください
- 「月経不順」「生理不順」「生理が遅れている」などの症状がある場合は、「解熱鎮痛薬」を選択してください
- 「生理痛」「月経痛」などの症状がある場合は、「解熱鎮痛薬」を選択してください
- 複数症状がある場合は、以下の優先順位で医薬品の種類を選択してください：
  1. 二日酔い → 胃腸薬（最優先）
  2. 目の症状 → 目薬
  3. 皮膚症状 → 外用薬（皮膚）
  4. 消化器症状 → 胃腸薬
  5. 生理痛・月経不順・生理不順 → 解熱鎮痛薬（女性特有症状を優先）
  6. 筋肉痛・関節痛・肩こり・腰痛 → 解熱鎮痛薬 または 筋肉痛
  7. 鼻症状のみ → 鼻炎用薬
  8. その他の風邪症状 → 風邪薬
  9. 頭痛 → 解熱鎮痛薬

【指示】
1. 症状文から該当する症状のみを抽出してください
2. 症状文に明示的に書かれていない症状は含めないでください
3. 症状文が曖昧で、医療関連のキーワードが含まれていない場合は、症状なしとして空のリストを返してください
4. 「決まりたい」「治したい」「良くなりたい」などの一般的な表現のみの場合は、具体的な症状が含まれていないため、症状なしとして扱ってください
5. 推測や憶測による症状の検出は避け、明確に記述された症状のみを抽出してください
6. 「こんにちは」などの挨拶のみの場合は、症状なしとして空のリストを返してください
7. 医薬品の種類は1つ選択してください

【回答形式】
以下のJSON形式で回答してください：
{{
    "symptoms": ["症状1", "症状2"],
    "medicine_type": "適する医薬品の種類"
}}

該当する症状がない場合は：
{{
    "symptoms": [],
    "medicine_type": "その他"
}}
"""

    print(f"=== 症状分析開始 ===")
    print(f"症状文: {user_text}")
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "あなたは医薬品の専門家です。症状に適した医薬品を推奨し、使用上の注意を説明してください。効能・効果が限定された特殊用途の医薬品（例：「食あたり等」「便秘」など）は、ユーザーの症状がその限定用途と完全に一致する場合のみ推奨してください。一般的な症状に対して特殊用途の医薬品を無理に推奨することは避けてください。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=500
        )
        
        result = response.choices[0].message.content
        print(f"ChatGPT応答: {result}")
        if not result:
            print("ChatGPTからの応答が空です")
            return {"symptoms": [], "medicine_type": None}
        # JSON形式の回答を解析
        import json
        try:
            # JSON部分を抽出
            json_start = result.find('{') if result else -1
            json_end = result.rfind('}') + 1 if result else -1
            if json_start != -1 and json_end != -1:
                json_str = result[json_start:json_end]
                parsed_result = json.loads(json_str)
                print(f"解析結果: {parsed_result}")
                # 二日酔いのキーワードが含まれている場合、医薬品種類を「胃腸薬」に強制変更
                if is_hangover:
                    parsed_result['medicine_type'] = '胃腸薬'
                    print(f"二日酔いキーワード検出: 医薬品種類を「胃腸薬」に変更")
                # 医薬品種類が「その他」の場合はNoneに変換
                if parsed_result.get('medicine_type') == 'その他':
                    parsed_result['medicine_type'] = None
                return parsed_result
            else:
                print("JSON形式が見つかりませんでした")
                return {"symptoms": [], "medicine_type": None}
        except json.JSONDecodeError as e:
            print(f"JSON解析エラー: {e}")
            return {"symptoms": [], "medicine_type": None}
            
    except Exception as e:
        print(f"ChatGPT API呼び出しエラー: {e}")
        print("フォールバック: 簡易症状検出を使用します")
        return simple_symptom_and_type_detection(user_text)

def simple_symptom_and_type_detection(user_text):
    """
    簡易的な症状と医薬品種類の検出（APIフォールバック用）
    """
    import re
    
    # 症状キーワードマッピング（目の症状を優先的に検出するため、先に定義）
    # rule_based_recommendation.pyのSYMPTOM_DICTIONARYと整合性を保つ
    symptom_keywords = {
        # 目薬関連症状（最優先）
        "目のかゆみ": ["目が痒", "目がかゆ", "目の痒", "目のかゆ", "目痒", "目かゆ", "目のかゆみ"],
        "目の充血": ["目の充血", "目が赤い", "目赤", "充血", "目の血走り"],
        "目の疲れ": ["目の疲れ", "目が疲", "眼精疲労", "目の重い感じ"],
        # 風邪関連症状
        "頭痛": ["頭痛", "頭が痛い", "ズキズキ", "偏頭痛", "頭が重い"],
        "発熱": ["熱", "発熱", "熱っぽい", "高熱", "微熱", "体温が高い"],
        "のどの痛み": ["のどが痛い", "喉が痛い", "のどの痛み", "咽頭痛", "喉痛", "のど痛", "喉の腫れ"],
        "咳": ["咳", "せき", "咳が出る", "咳込む", "空咳"],
        "鼻水": ["鼻水", "鼻みず", "鼻汁", "鼻が出る", "水っぽい鼻水"],
        "鼻づまり": ["鼻づまり", "鼻詰まり", "鼻が詰まる", "鼻閉"],
        "くしゃみ": ["くしゃみ", "クシャミ", "くしゃみが出る"],
        "寒気": ["寒気", "さむけ", "悪寒", "ゾクゾクする", "悪寒がする"],
        "悪寒": ["悪寒", "寒気", "さむけ", "ゾクゾクする", "悪寒がする"],
        # 消化器症状
        "胃痛": ["胃痛", "胃が痛い", "胃の痛み", "胃部痛", "みぞおちの痛み", "胃が痛む"],
        "腹痛": ["腹痛", "お腹が痛い", "腹部痛", "おなかが痛い", "腹が痛い", "腹痛が続く"],
        "下痢": ["下痢", "軟便", "水様便", "便がゆるい", "便が緩い", "下痢が続く"],
        "便秘": ["便秘", "便が出ない", "便通がない", "便が硬い", "便秘が続く"],
        "吐き気": ["吐き気", "嘔吐", "むかつき", "気持ち悪い", "嘔吐感", "吐きそう"],
        "胸やけ": ["胸やけ", "胸焼け", "胃の重い感じ", "酸が上がる", "胸が苦い"],
        "胃もたれ": ["胃もたれ", "もたれる", "消化不良", "胃の重い感じ", "消化が悪い", "胃の不快感"],
        # 皮膚症状
        "かゆみ": ["かゆい", "痒み", "かゆみ", "皮膚のかゆみ", "皮膚が痒い"],
        "発疹": ["発疹", "ブツブツ", "赤い斑点", "皮膚の異常", "皮膚に赤い斑点が出る"],
        "湿疹": ["湿疹", "皮膚炎", "かぶれ", "皮膚の炎症"],
        "蕁麻疹": ["蕁麻疹", "じんましん", "じん麻疹", "蕁麻疹が出る"],
        # 筋肉・関節症状
        "筋肉痛": ["筋肉痛", "筋肉の痛み", "体が痛い", "筋肉が痛い", "筋肉が痛む"],
        "関節痛": ["関節痛", "関節の痛み", "節々が痛い", "関節が痛い", "関節が痛む"],
        "肩こり": ["肩こり", "肩の凝り", "肩の痛み", "首肩の痛み", "肩が凝る"],
        "腰痛": ["腰痛", "腰が痛い", "腰の痛み", "腰が痛む"],
        # その他の症状
        "生理痛": ["生理痛", "月経痛", "生理", "生理の痛み", "下腹部痛", "生理痛が続く"],
        "めまい": ["めまい", "眩暈", "ふらつき", "立ちくらみ", "めまいが続く"],
        "疲労感": ["疲労感", "疲れ", "倦怠感", "だるい", "疲労感が続く"],
        "倦怠感": ["倦怠感", "疲労感", "疲れ", "だるい", "倦怠感が続く"],
        "不眠": ["不眠", "眠れない", "睡眠不足", "寝つきが悪い", "不眠が続く"],
    }
    
    detected_symptoms = []
    for symptom, keywords in symptom_keywords.items():
        for keyword in keywords:
            if keyword in user_text:
                detected_symptoms.append(symptom)
                break
    
    # 重複を除去
    detected_symptoms = list(set(detected_symptoms))
    
    # 医薬品種類の推定（優先順位に注意）
    medicine_type = "その他"
    
    # 1. 目の症状（最優先）
    eye_symptoms = ["目のかゆみ", "目の充血", "目の疲れ"]
    if any(s in detected_symptoms for s in eye_symptoms):
        medicine_type = "目薬"
    # 2. 皮膚症状 → 外用薬（皮膚）
    elif any(s in detected_symptoms for s in ["かゆみ", "発疹", "湿疹", "蕁麻疹"]):
        medicine_type = "外用薬（皮膚）"
    # 3. 消化器症状 → 胃腸薬
    elif any(s in detected_symptoms for s in ["胃痛", "腹痛", "下痢", "便秘", "吐き気", "胸やけ", "胃もたれ"]):
        medicine_type = "胃腸薬"
    # 4. 筋肉痛・関節痛・肩こり・腰痛 → 解熱鎮痛薬 または 筋肉痛
    elif any(s in detected_symptoms for s in ["筋肉痛", "関節痛", "肩こり", "腰痛"]):
        # 筋肉痛がある場合は「筋肉痛」、それ以外は「解熱鎮痛薬」
        if "筋肉痛" in detected_symptoms:
            medicine_type = "筋肉痛"
        else:
            medicine_type = "解熱鎮痛薬"
    # 5. 鼻炎用薬の判定（鼻症状のみで発熱・喉・咳がない場合）
    elif any(s in detected_symptoms for s in ["鼻水", "鼻づまり", "くしゃみ"]):
        nose_symptoms = ["鼻水", "鼻づまり", "くしゃみ"]
        other_cold_symptoms = ["発熱", "のどの痛み", "咳"]
        # 鼻症状のみで他の風邪症状がない場合は鼻炎用薬
        if not any(s in detected_symptoms for s in other_cold_symptoms):
            medicine_type = "鼻炎用薬"
        # 鼻症状+他の風邪症状がある場合は風邪薬
        else:
            medicine_type = "風邪薬"
    # 6. 風邪薬の判定（鼻症状以外の風邪症状）
    elif any(s in detected_symptoms for s in ["発熱", "のどの痛み", "咳"]):
        medicine_type = "風邪薬"
    # 7. 解熱鎮痛薬の判定（頭痛・生理痛）
    elif any(s in detected_symptoms for s in ["頭痛", "生理痛"]):
        medicine_type = "解熱鎮痛薬"
    
    print(f"=== 簡易検出結果 ===")
    print(f"検出された症状: {detected_symptoms}")
    print(f"推定された医薬品の種類: {medicine_type}")
    
    return {
        "symptoms": detected_symptoms,
        "medicine_type": medicine_type
    }

def get_medicines_by_type(medicine_type, df=None):
    """
    医薬品の種類に基づいてotc_medicine_dataから医薬品リストを取得
    """
    if df is None:
        df = globals().get('df')
    
    if df is None:
        print("データフレームが読み込まれていません")
        return []
    
    # 医薬品の種類カラムから該当する医薬品を抽出
    if '医薬品の種類' in df.columns:
        matched = df[df['医薬品の種類'].astype(str).str.contains(medicine_type, na=False)]
        medicines = []
        for _, row in matched.iterrows():
            medicine_info = {
                '製品名': row.get('製品名', ''),
                'メーカー名': row.get('メーカー名', ''),
                '分類': row.get('分類', ''),
                '医薬品の種類': row.get('医薬品の種類', ''),
                '効能効果': row.get('効能効果', ''),
                '成分': row.get('成分', ''),
                '使用上の注意': row.get('使用上の注意', '')
            }
            medicines.append(medicine_info)
        
        print(f"医薬品の種類 '{medicine_type}' で {len(medicines)} 件の医薬品を抽出しました")
        return medicines
    else:
        print("CSVに医薬品の種類カラムがありません")
        return []

def recommend_medicines_with_retry(user_text, symptoms, medicine_list, user_info=None, client=None, max_retries=3):
    """
    症状と医薬品リストをChatGPTに渡して推奨医薬品を3つ選び、
    使用上の注意を要約して返す。適した医薬品が返ってこなければ再試行
    """
    # セキュリティ検証の追加
    from security_validator import validate_user_input
    from security_config import should_block_input, get_current_phase
    from security_logger import log_input_validation
    
    # 入力検証
    is_safe, risk_score, warnings, sanitized_text = validate_user_input(
        user_text, context='medicine_recommendation'
    )
    
    # ログ記録
    log_input_validation(
        user_id='medicine_recommendation',
        input_text=user_text,
        risk_score=risk_score,
        is_safe=is_safe,
        warnings=warnings,
        sanitized_text=sanitized_text
    )
    
    # ブロック判定
    if should_block_input(risk_score):
        print(f"⚠️ 医薬品推奨がブロックされました: リスクスコア {risk_score}")
        return {
            "recommended_medicines": [],
            "usage_notes": "入力内容に問題が検出されました。症状や質問を自然な文章で入力してください。",
            "doctor_consultation": "医師にご相談ください。"
        }
    
    # 高リスク入力の場合は医薬品推奨を停止
    if risk_score >= 80:
        print(f"⚠️ 高リスク入力のため医薬品推奨を停止: リスクスコア {risk_score}")
        return {
            "recommended_medicines": [],
            "usage_notes": "入力内容に不審なパターンが検出されました。症状や質問を自然な文章で入力してください。",
            "doctor_consultation": "医師にご相談ください。"
        }
    
    if client is None:
        client = OpenAI(api_key=api_key)
    
    # 医薬品リストを文字列に変換（使用上の注意も含める）
    medicine_text = ""
    for i, medicine in enumerate(medicine_list[:20]):  # 最初の20個のみ使用
        usage_notes = medicine.get('使用上の注意', '')
        medicine_text += f"{i+1}. {medicine['製品名']} ({medicine['メーカー名']})\n"
        medicine_text += f"   効能効果: {medicine['効能効果']}\n"
        medicine_text += f"   成分: {medicine['成分']}\n"
        medicine_text += f"   使用上の注意: {usage_notes}\n\n"
    
    user_context = user_info if user_info else {}

    for attempt in range(max_retries):
        print(f"=== 医薬品推奨試行 {attempt + 1}/{max_retries} ===")
        
        prompt = f"""
以下の症状と医薬品リストから、最も適切な3つの医薬品を選んでください。

【症状】
{', '.join(symptoms)}

【症状文】
{sanitized_text}

【ユーザー情報】
{user_context if user_context else '情報なし'}

【選択可能な医薬品】
{medicine_text}

【回答形式】
以下のJSON形式で回答してください：
{{
    "recommended_medicines": [
        {{
            "number": 1,
            "product_name": "製品名",
            "manufacturer": "メーカー名",
            "reason": "推奨理由",
            "usage_notes": "この医薬品の使用上の注意点の要約"
        }},
        {{
            "number": 2,
            "product_name": "製品名",
            "manufacturer": "メーカー名",
            "reason": "推奨理由",
            "usage_notes": "この医薬品の使用上の注意点の要約"
        }},
        {{
            "number": 3,
            "product_name": "製品名",
            "manufacturer": "メーカー名",
            "reason": "推奨理由",
            "usage_notes": "この医薬品の使用上の注意点の要約"
        }}
    ],
    "doctor_consultation": "医師の受診が必要な場合について"
}}

注意：
- 症状に最も適した医薬品を3つ選んでください
- 製品名とメーカー名が同じものは重複として、同じものを複数回推奨しないでください
- 番号は1つ目、2つ目、3つ目の順で出力してください（例："number": 1, "number": 2, "number": 3）
- 製品名とメーカー名は正確に記載してください
- 各医薬品の「使用上の注意」欄の内容を参考に、必ず各医薬品ごとに使用上の注意点を要約してください
- 医師の受診が必要な場合についても記載してください
- 効能・効果が限定された特殊用途の医薬品（例：「食あたり等」「便秘のみ」「腸内容物の急速な排除」など）は、ユーザーの症状がその限定用途と完全に一致する場合のみ推奨してください
- 一般的な症状に対して特殊用途の医薬品を無理に推奨することは避けてください
- リスク成分（ヒマシ油、センナ、アロエエキス、ビサコジル、アスピリン、トラマドールなど）が含まれる医薬品は、詳細な症状情報がない場合は推奨を避けてください
- インフルエンザの可能性がある場合（高熱38.5度以上+複数の風邪症状）は、アスピリンを含む医薬品は絶対に推奨しないでください
- 単一症状（例：発熱のみ）の場合は、総合感冒薬よりも特化した医薬品（例：解熱鎮痛薬）を優先してください
"""

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": """あなたは医薬品の専門家です。症状に適した医薬品を推奨し、使用上の注意を説明してください。

重要な推奨ルール：
- 効能効果が限定された特殊用途の医薬品（「食あたり等」「便秘のみ」「腸内容物の急速な排除」など）は、ユーザーの症状がその限定用途と完全に一致する場合のみ推奨してください
- 一般的な症状に対して特殊用途の医薬品を無理に推奨することは避けてください
- リスク成分（ヒマシ油、センナ、アロエエキス、ビサコジル、アスピリン、トラマドールなど）が含まれる医薬品は、詳細な症状情報がない場合は推奨を避けてください
- インフルエンザの可能性がある場合（高熱38.5度以上+複数の風邪症状）は、アスピリンを含む医薬品は絶対に推奨しないでください
- 単一症状（例：発熱のみ）の場合は、総合感冒薬よりも特化した医薬品（例：解熱鎮痛薬）を優先してください
- 症状に最も適した医薬品を3つ選び、製品名とメーカー名は正確に記載してください"""},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=800
            )
            
            result = response.choices[0].message.content
            print(f"ChatGPT応答 (試行 {attempt + 1}): {result}")
            if not result:
                print("ChatGPTからの応答が空です。再試行します。")
                continue
            
            # ChatGPTの応答から```json```マークダウンブロックを除去
            if result.startswith('```json'):
                result = result[7:]  # ```jsonを除去
            if result.endswith('```'):
                result = result[:-3]  # ```を除去
            result = result.strip()
            
            # 安全なJSON解析
            from json_validator import safe_json_parse
            try:
                parsed_result = safe_json_parse(result, schema='medicine_recommendation')
                
                # 推奨医薬品が3つあるかチェック＋重複除去
                if (parsed_result.get('recommended_medicines')):
                    # 製品名・メーカー名の重複を除去
                    seen = set()
                    unique_meds = []
                    for med in parsed_result['recommended_medicines']:
                        key = (med.get('product_name', ''), med.get('manufacturer', ''))
                        if key not in seen:
                            seen.add(key)
                            unique_meds.append(med)
                        if len(unique_meds) == 3:
                            break
                    parsed_result['recommended_medicines'] = unique_meds
                    if len(unique_meds) >= 3:
                        print(f"適切な推奨医薬品が見つかりました（重複除去済み）")
                        return parsed_result
                    else:
                        print(f"推奨医薬品が不足しています（重複除去後）。再試行します。")
                else:
                    print(f"推奨医薬品が不足しています。再試行します。")
            except Exception as e:
                print(f"JSON解析エラー: {e}。再試行します。")
                
        except Exception as e:
            print(f"ChatGPT API呼び出しエラー: {e}")
    
    print("最大試行回数に達しました。デフォルトの推奨を返します。")
    return {
        "recommended_medicines": [],
        "usage_notes": "適切な医薬品が見つかりませんでした。医師にご相談ください。",
        "doctor_consultation": "症状が改善しない場合は医師にご相談ください。"
    }

def get_medicine_details(recommended_medicines, medicine_list):
    """
    推奨医薬品の詳細情報（使用上の注意など）を取得
    """
    detailed_medicines = []
    
    for rec in recommended_medicines:
        product_name = rec.get('product_name', '')
        manufacturer = rec.get('manufacturer', '')
        
        # NaN値を適切に処理
        if product_name is None or str(product_name) == 'nan':
            product_name = ''
        if manufacturer is None or str(manufacturer) == 'nan':
            manufacturer = ''

        # まず完全一致で検索
        matched_medicine = None
        for medicine in medicine_list:
            csv_product = medicine.get('製品名', '')
            csv_manufacturer = medicine.get('メーカー名', '')
            
            # NaN値を適切に処理
            if csv_product is None or str(csv_product) == 'nan':
                csv_product = ''
            if csv_manufacturer is None or str(csv_manufacturer) == 'nan':
                csv_manufacturer = ''
            
            if product_name == csv_product and manufacturer == csv_manufacturer:
                matched_medicine = medicine
                break
        # 完全一致が見つからない場合は製品名のみで検索
        if not matched_medicine:
            for medicine in medicine_list:
                csv_product = medicine.get('製品名', '')
                
                # NaN値を適切に処理
                if csv_product is None or str(csv_product) == 'nan':
                    csv_product = ''
                
                if product_name == csv_product:
                    matched_medicine = medicine
                    break
        
        if matched_medicine:
            # usage_notesはChatGPT返答を優先、なければDB内容
            usage_notes = rec.get('usage_notes')
            if not usage_notes:
                usage_notes = matched_medicine.get('使用上の注意', '')
            # NaN値を適切に処理して医薬品詳細情報を構築
            def safe_get(value):
                if value is None or str(value) == 'nan':
                    return ''
                return value
            
            # スコアリング計算（管理者画面用）
            def calculate_medicine_score(medicine_data, rec_data, notes):
                score = 0
                max_score = 100
                
                # 基本スコア（順位による）
                rank_score = max(0, 30 - (rec_data.get('number', 1) - 1) * 5)
                score += rank_score
                
                # 効能効果の充実度
                efficacy = safe_get(medicine_data.get('効能効果', ''))
                if efficacy and len(efficacy) > 50:
                    score += 20
                elif efficacy and len(efficacy) > 20:
                    score += 10
                
                # 成分情報の充実度
                ingredients = safe_get(medicine_data.get('成分', ''))
                if ingredients and len(ingredients) > 30:
                    score += 15
                elif ingredients and len(ingredients) > 10:
                    score += 8
                
                # 使用上の注意の充実度
                usage_notes_safe = safe_get(notes)
                if usage_notes_safe and len(usage_notes_safe) > 50:
                    score += 15
                elif usage_notes_safe and len(usage_notes_safe) > 20:
                    score += 8
                
                # ドーピング情報の有無
                doping = safe_get(medicine_data.get('禁止物質あり', ''))
                if doping and doping != '':
                    score += 10
                
                # 推奨理由の充実度
                reason = safe_get(rec_data.get('reason', ''))
                if reason and len(reason) > 30:
                    score += 10
                elif reason and len(reason) > 10:
                    score += 5
                
                return min(score, max_score)
            
            medicine_score = calculate_medicine_score(matched_medicine, rec, usage_notes)
            
            detailed_medicine = {
                'number': rec.get('number', 0),
                'product_name': safe_get(matched_medicine.get('製品名', product_name)),
                'manufacturer': safe_get(matched_medicine.get('メーカー名', manufacturer)),
                'reason': safe_get(rec.get('reason', '')),
                'efficacy': safe_get(matched_medicine.get('効能効果', '')),
                'ingredients': safe_get(matched_medicine.get('成分', '')),
                'usage_notes': safe_get(usage_notes),
                'doping_prohibited': safe_get(matched_medicine.get('禁止物質あり', '')),
                'competition_category': safe_get(matched_medicine.get('競技会区分', '')),
                'doping_conditions': safe_get(matched_medicine.get('条件', '')),
                # 管理画面表示に合わせて 0-1 の範囲に正規化
                'score': (medicine_score / 100.0)  # スコアリング情報を追加（正規化）
            }
            detailed_medicines.append(detailed_medicine)
            print(f"医薬品詳細情報取得: {product_name} ({manufacturer}) -> {matched_medicine.get('製品名', '')} ({matched_medicine.get('メーカー名', '')})")
        else:
            print(f"医薬品詳細情報が見つかりません: {product_name} ({manufacturer})")
            # 詳細情報が見つからない場合でも、ChatGPTのusage_notesを優先
            usage_notes = rec.get('usage_notes')
            if not usage_notes:
                usage_notes = '詳細情報が見つかりませんでした'
            # NaN値を適切に処理して医薬品詳細情報を構築
            def safe_get(value):
                if value is None or str(value) == 'nan':
                    return ''
                return value
            
            # 詳細情報が見つからない場合のスコアリング
            def calculate_fallback_score(rec_data):
                score = 0
                # 基本スコア（順位による）
                rank_score = max(0, 30 - (rec_data.get('number', 1) - 1) * 5)
                score += rank_score
                
                # 推奨理由の充実度
                reason = safe_get(rec_data.get('reason', ''))
                if reason and len(reason) > 30:
                    score += 20
                elif reason and len(reason) > 10:
                    score += 10
                
                return min(score, 50)  # 詳細情報がない場合は最大50点
            
            fallback_score = calculate_fallback_score(rec)
            
            detailed_medicine = {
                'number': rec.get('number', 0),
                'product_name': safe_get(product_name),
                'manufacturer': safe_get(manufacturer),
                'reason': safe_get(rec.get('reason', '')),
                'efficacy': '詳細情報が見つかりませんでした',
                'ingredients': '詳細情報が見つかりませんでした',
                'usage_notes': safe_get(usage_notes),
                'doping_prohibited': '詳細情報が見つかりませんでした',
                'competition_category': '詳細情報が見つかりませんでした',
                'doping_conditions': '詳細情報が見つかりませんでした',
                # 管理画面表示に合わせて 0-1 の範囲に正規化
                'score': (fallback_score / 100.0)  # スコアリング情報を追加（正規化）
            }
            detailed_medicines.append(detailed_medicine)
    
    return detailed_medicines

def comprehensive_medicine_recommendation(user_text, user_info=None, client=None):
    """
    包括的な医薬品推奨システムのメイン関数
    """
    print(f"=== 包括的医薬品推奨システム開始 ===")
    print(f"症状文: {user_text}")
    
    # ステップ1: 症状と医薬品の種類を分析
    analysis_result = analyze_symptoms_and_medicine_type(user_text, client)
    symptoms = analysis_result.get('symptoms', [])
    medicine_type = analysis_result.get('medicine_type', 'その他')
    
    print(f"分析結果 - 症状: {symptoms}")
    print(f"分析結果 - 医薬品の種類: {medicine_type}")
    
    # ステップ2: 医薬品の種類に基づいて医薬品リストを取得
    medicine_list = get_medicines_by_type(medicine_type)
    
    if not medicine_list:
        print("該当する医薬品が見つかりませんでした")
        return {
            'symptoms': symptoms,
            'medicine_type': medicine_type,
            'recommended_medicines': [],
            'usage_notes': '該当する医薬品が見つかりませんでした。医師にご相談ください。',
            'doctor_consultation': '症状が改善しない場合は医師にご相談ください。'
        }
    
    # ステップ3: ChatGPTに推奨医薬品を選択させる
    recommendation_result = recommend_medicines_with_retry(
        user_text, symptoms, medicine_list, user_info=user_info, client=client
    )
    
    # ステップ4: 推奨医薬品の詳細情報を取得
    detailed_medicines = get_medicine_details(
        recommendation_result.get('recommended_medicines', []), 
        medicine_list
    )
    
    # スコア順にソート（降順：スコアが高い順）
    detailed_medicines.sort(key=lambda x: x.get('score', 0), reverse=True)
    
    # ソート後の順位を更新
    for i, medicine in enumerate(detailed_medicines, 1):
        medicine['number'] = i
    
    # 最終結果を構築
    final_result = {
        'symptoms': symptoms,
        'medicine_type': medicine_type,
        'recommended_medicines': detailed_medicines,
        'usage_notes': recommendation_result.get('usage_notes', ''),
        'doctor_consultation': recommendation_result.get('doctor_consultation', '')
    }
    
    print(f"=== 推奨結果 ===")
    print(f"症状: {symptoms}")
    print(f"医薬品の種類: {medicine_type}")
    print(f"推奨医薬品数: {len(detailed_medicines)}")
    
    return final_result 

# ================================================================================
# ルールベース推奨システム（新規追加）
# ================================================================================

def rule_based_medicine_recommendation(user_text, user_info, client=None):
    """
    ルールベース医薬品推奨システムのラッパー関数
    風邪薬、解熱鎮痛薬、鼻炎用薬に限定
    
    Args:
        user_text: ユーザーの症状入力
        user_info: ユーザー情報（年齢、妊娠など）
        client: OpenAIクライアント
    
    Returns:
        推奨結果
    """
    if client is None:
        client = OpenAI(api_key=api_key)
    
    # ルールベース推奨モジュールをインポート
    try:
        from rule_based_recommendation import rule_based_recommendation, log_recommendation_session
        
        # グローバルdfを使用
        global df
        if df is None:
            return {
                "status": "error",
                "reason": "医薬品データが読み込まれていません"
            }
        
        # ルールベース推奨を実行
        result = rule_based_recommendation(
            user_text=user_text,
            user_info=user_info,
            medicine_df=df,
            client=client,
            top_n=3
        )
        
        # ログ保存
        log_recommendation_session(user_text, user_info, result)
        
        return result
        
    except Exception as e:
        print(f"ルールベース推奨エラー: {e}")
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "reason": f"システムエラー({str(e)})"
        }

def detect_medicine_name_in_query(user_message, medicine_df):
    """
    ユーザーの質問から医薬品名を検出する
    
    Args:
        user_message: ユーザーの質問
        medicine_df: 医薬品データフレーム
    
    Returns:
        list: 検出された医薬品のリスト
    """
    if medicine_df is None or medicine_df.empty:
        return []
    
    detected_medicines = []
    user_message_lower = user_message.lower()
    
    # 成分名での検索を優先（ビタミンC、イブプロフェンなど）
    for _, row in medicine_df.iterrows():
        ingredients = str(row.get('成分', '')).lower()
        if ingredients:
            ingredient_list = [ing.strip() for ing in ingredients.split(',')]
            for ingredient in ingredient_list:
                if ingredient and ingredient in user_message_lower:
                    detected_medicines.append({
                        'product_name': row.get('製品名', ''),
                        'manufacturer': row.get('メーカー名', ''),
                        'efficacy': row.get('効能効果', ''),
                        'usage': row.get('用法用量', ''),
                        'age_restriction': row.get('年齢制限', ''),
                        'ingredients': row.get('成分', ''),
                        'doping_prohibited': row.get('禁止物質あり', ''),
                        'medicine_type': row.get('医薬品の種類', '')
                    })
                    break  # 重複を避ける
    
    # 効能効果での検索を追加（「風邪薬」「頭痛薬」など）
    efficacy_keywords = {'風邪': '風邪', 'ビタミン': 'ビタミン', '頭痛': '頭痛', '胃痛': '胃', '胃薬': '胃', 'かぜ': '風邪'}
    for keyword, search_term in efficacy_keywords.items():
        if keyword in user_message_lower:
            matched = medicine_df[medicine_df['効能効果'].str.contains(search_term, na=False)]
            for _, row in matched.head(5).iterrows():  # 最大5件
                detected_medicines.append({
                    'product_name': row.get('製品名', ''),
                    'manufacturer': row.get('メーカー名', ''),
                    'efficacy': row.get('効能効果', ''),
                    'usage': row.get('用法用量', ''),
                    'age_restriction': row.get('年齢制限', ''),
                    'ingredients': row.get('成分', ''),
                    'doping_prohibited': row.get('禁止物質あり', ''),
                    'medicine_type': row.get('医薬品の種類', '')
                })
    
    # 医薬品名で検索（部分一致）
    for _, row in medicine_df.iterrows():
        product_name = str(row.get('製品名', '')).lower()
        if product_name and any(word in product_name for word in user_message_lower.split() if len(word) > 2):
            detected_medicines.append({
                'product_name': row.get('製品名', ''),
                'manufacturer': row.get('メーカー名', ''),
                'efficacy': row.get('効能効果', ''),
                'usage': row.get('用法用量', ''),
                'age_restriction': row.get('年齢制限', ''),
                'ingredients': row.get('成分', ''),
                'doping_prohibited': row.get('禁止物質あり', ''),
                'medicine_type': row.get('医薬品の種類', '')
            })
    
    # 重複を除去
    unique_medicines = []
    seen_names = set()
    for med in detected_medicines:
        if med['product_name'] not in seen_names:
            unique_medicines.append(med)
            seen_names.add(med['product_name'])
    
    return unique_medicines[:10]  # 最大10件に制限

def chat_with_medicine_context(user_message, conversation_history, recommended_medicines, client=None):
    """
    会話履歴と推奨医薬品の情報をChatGPTに渡して、医薬品に関する質問に回答する
    
    Args:
        user_message: ユーザーの質問
        conversation_history: 会話履歴（最新の5件程度）
        recommended_medicines: 推奨医薬品のリスト
        client: OpenAIクライアント
    
    Returns:
        dict: ChatGPTの回答
    """
    if client is None:
        client = OpenAI(api_key=api_key)
    
    # システム紹介質問を検出
    system_intro_keywords = ['あなたについて', 'あなたは', 'システムについて', 'どんなシステム', '何ができる', '機能','自己紹介','自己紹介して','自己紹介してください']
    is_system_intro = any(keyword in user_message for keyword in system_intro_keywords)
    
    if is_system_intro and not recommended_medicines:
        # HTMLではなく、テキストで簡潔に回答を返す（他システムへの影響を避ける）
        answer_text = (
            "🏥 医薬品推奨システムについて\n"
            "このシステムは、症状に基づいて適切な市販薬（OTC医薬品）を提示するサポートを行います。\n\n"
            "📋 主な機能\n"
            "・症状に基づく医薬品の推奨\n"
            "・効能や用法用量などの基本情報の提示\n"
            "・相互作用や副作用に関する注意喚起\n"
            "・競技者向けのドーピング観点の補足\n\n"
            "🔍 できること\n"
            "・「頭痛がする」「のどが痛い」などの症状で検索\n"
            "・医薬品名での検索や質問\n"
            "・推奨結果についての追加質問\n\n"
            "⚠️ ご注意\n"
            "本システムは参考情報の提供を目的としており、最終判断は登録販売者・薬剤師などの専門家にご相談ください。"
        )
        return {
            "answer": answer_text,
            "medicine_details": "",
            "interactions": "",
            "doping_check": "",
            "side_effects": "",
            "consultation_advice": ""
        }
    
    # 推奨医薬品が空の場合でも、まず会話履歴から復元を試みる
    if not recommended_medicines and conversation_history:
        try:
            for hist in reversed(conversation_history):
                diag = hist.get('diagnosis') if isinstance(hist, dict) else None
                if isinstance(diag, dict) and diag.get('recommended_medicines'):
                    recommended_medicines = diag.get('recommended_medicines') or []
                    if recommended_medicines:
                        print(f"会話履歴から推奨医薬品を復元: {len(recommended_medicines)}件")
                        break
        except Exception as e:
            print(f"履歴復元エラー: {e}")

    # それでも推奨医薬品がない場合、医薬品名での直接検索を試行（成功時のみ早期return）
    if not recommended_medicines:
        try:
            import pandas as pd
            base_dir = os.path.dirname(os.path.abspath(__file__))
            data_dir = os.path.join(base_dir, "data")
            df = pd.read_csv(os.path.join(data_dir, 'otc_medicine_data.csv'))
            detected_medicines = detect_medicine_name_in_query(user_message, df)
            if detected_medicines:
                medicine_info = ""
                for i, med in enumerate(detected_medicines[:3], 1):
                    medicine_info += f"\n💊 **{i}つ目: {med['product_name']}** ({med['manufacturer']})\n"
                    medicine_info += f"**効能効果:** {med['efficacy']}\n"
                    medicine_info += f"**成分:** {med['ingredients']}\n"
                    if med['age_restriction']:
                        medicine_info += f"**年齢制限:** {med['age_restriction']}\n"
                    if med['usage']:
                        medicine_info += f"**用法用量:** {med['usage']}\n"
                    medicine_info += "\n"
                return {
                    "answer": f"🔍 **医薬品検索結果**\n\n{medicine_info}\n⚠️ **ご注意**\n・医薬品の使用前には必ず登録販売者や薬剤師にご相談ください\n・アレルギー体質の方は成分を確認してください\n・用法用量を守ってご使用ください",
                    "medicine_details": "検出された医薬品の情報",
                    "interactions": "医薬品の相互作用については登録販売者にご相談ください",
                    "doping_check": "ドーピング検査については各競技団体にご確認ください",
                    "side_effects": "副作用については登録販売者にご相談ください",
                    "consultation_advice": "お近くの登録販売者にご相談ください"
                }
        except Exception as e:
            print(f"医薬品検索エラー: {e}")
        # 検索でも見つからない場合は、会話履歴を踏まえた一般回答にフォールバック（以降の処理で生成）
    
    # 会話履歴を整形（最新の5件程度）
    history_text = ""
    if conversation_history is not None:
        recent_messages = conversation_history[-5:]  # 最新5件
        for msg in recent_messages:
            if msg.get('type') == 'user':
                history_text += f"ユーザー: {msg.get('content', '')}\n"
            elif msg.get('type') == 'bot':
                # botメッセージから診断結果を抽出
                diagnosis = msg.get('diagnosis')
                if diagnosis is not None and diagnosis.get('recommended_medicines'):
                    medicines = diagnosis.get('recommended_medicines', [])
                    history_text += f"AI: 推奨医薬品: {', '.join([m.get('product_name', '') for m in medicines])}\n"
                else:
                    history_text += f"AI: {msg.get('content', '')}\n"
    
    # 推奨医薬品の詳細情報を整形
    medicines_text = ""
    if recommended_medicines:
        for i, medicine in enumerate(recommended_medicines, 1):
            medicines_text += f"""
{i}つ目: {medicine.get('product_name', '')}
- メーカー: {medicine.get('manufacturer', '')}
- 効能効果: {medicine.get('efficacy', '')}
- 成分: {medicine.get('ingredients', '')}
- 使用上の注意: {medicine.get('usage_notes', '')}
- ドーピング禁止物質: {medicine.get('doping_prohibited', '')}
- 競技会区分: {medicine.get('competition_category', '')}
- ドーピング条件: {medicine.get('doping_conditions', '')}
"""
    
    prompt = f"""
あなたは医薬品推奨システムです。ユーザーの医薬品に関する質問に、推奨医薬品の情報を基に回答してください。

【会話履歴】
{history_text}

【推奨医薬品の詳細情報】
{medicines_text}

【ユーザーの質問】
{user_message}

以下の点について回答してください：
1. 医薬品の詳細説明（効能効果、成分、使用方法）
2. 他の医薬品との飲み合わせ（相互作用）
3. スポーツ競技でのドーピング規制対象かどうか
4. 副作用や注意点
5. 医師に相談すべき場合

回答は以下の形式で構造化してください：
{{
    "answer": "ユーザーへの直接的な回答",
    "medicine_details": "医薬品の詳細説明",
    "interactions": "飲み合わせ・相互作用の説明",
    "doping_check": "ドーピング規制の確認結果",
    "side_effects": "副作用・注意点",
    "consultation_advice": "医師相談のアドバイス"
}}

注意：
- 推奨医薬品の情報を基に具体的に回答してください
- 飲み合わせについては、一般的な相互作用を説明してください
- ドーピングについては、WADA（世界アンチ・ドーピング機関）の規制を参考にしてください
- 安全性を最優先に考え、不明な点がある場合は医師相談を推奨してください
- 質問の内容が推奨医薬品の情報では回答できない場合は、「お近くの登録販売者にご相談ください」と回答してください
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "あなたは医薬品推奨システムです。医薬品の安全性と効果について正確な情報を提供してください。推奨医薬品の情報で回答できない質問については、お近くの登録販売者にご相談するよう推奨してください。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=1000
        )
        
        result = response.choices[0].message.content
        print(f"ChatGPT応答: {result}")
        
        # JSON形式の回答を解析
        import json
        try:
            # JSON部分を抽出
            json_start = result.find('{') if result else -1
            json_end = result.rfind('}') + 1 if result else -1
            if json_start != -1 and json_end != -1:
                json_str = result[json_start:json_end]
                parsed_result = json.loads(json_str)
                
                # 回答が不十分な場合や「分からない」系の回答の場合は登録販売者相談を推奨
                answer = parsed_result.get('answer', '')
                if any(keyword in answer.lower() for keyword in ['分からない', '不明', '確認できません', '情報がありません', '回答できません']):
                    return {
                        "answer": "申し訳ございません。この質問については推奨医薬品の情報では回答できません。お近くの登録販売者にご相談ください。",
                        "medicine_details": "推奨医薬品の情報では回答できません",
                        "interactions": "推奨医薬品の情報では回答できません",
                        "doping_check": "推奨医薬品の情報では回答できません",
                        "side_effects": "推奨医薬品の情報では回答できません",
                        "consultation_advice": "お近くの登録販売者にご相談ください"
                    }
                
                return parsed_result
            else:
                # JSON形式でない場合は直接回答として返す
                return {
                    "answer": result,
                    "medicine_details": "詳細情報を取得できませんでした",
                    "interactions": "飲み合わせ情報を取得できませんでした",
                    "doping_check": "ドーピング規制の確認ができませんでした",
                    "side_effects": "副作用情報を取得できませんでした",
                    "consultation_advice": "お近くの登録販売者にご相談ください"
                }
        except json.JSONDecodeError as e:
            print(f"JSON解析エラー: {e}")
            return {
                "answer": result,
                "medicine_details": "詳細情報を取得できませんでした",
                "interactions": "飲み合わせ情報を取得できませんでした",
                "doping_check": "ドーピング規制の確認ができませんでした",
                "side_effects": "副作用情報を取得できませんでした",
                "consultation_advice": "お近くの登録販売者にご相談ください"
            }
        
    except Exception as e:
        print(f"ChatGPT API呼び出しエラー: {e}")
        return {
            "answer": "申し訳ございません。システムエラーが発生しました。お近くの登録販売者にご相談ください。",
            "medicine_details": "詳細情報を取得できませんでした",
            "interactions": "飲み合わせ情報を取得できませんでした",
            "doping_check": "ドーピング規制の確認ができませんでした",
            "side_effects": "副作用情報を取得できませんでした",
            "consultation_advice": "お近くの登録販売者にご相談ください"
        }

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
        if keyword.lower() in user_message_lower:
            # 「苦しい」は身体的症状の文脈では検出しない
            if keyword == '苦しい':
                # 身体的症状の文脈または恋愛文脈の場合は検出しない
                if has_physical_context or has_romantic_context:
                    continue
            detected_keywords.append(keyword)
    
    return len(detected_keywords) > 0, detected_keywords

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

def detect_severity_escalation(user_message: str, nlu_result: dict, user_info: dict) -> dict:
    """
    症状の重症度による受診勧奨の判定
    
    Args:
        user_message: ユーザーの入力メッセージ
        nlu_result: NLU解析結果
        user_info: ユーザー情報
    
    Returns:
        {
            "needs_escalation": True/False,
            "reason": "受診勧奨理由",
            "urgency": "high/medium/low",
            "message": "受診勧奨メッセージ"
        }
    """
    needs_escalation = False
    reason = ""
    urgency = "low"
    message = ""
    
    user_message_lower = user_message.lower() if user_message else ""
    
    # 「生理痛が年々ひどくなっている」の検出
    # パターンマッチング
    temporal_keywords = ['年々', '徐々に', 'だんだん', '次第に', '段々', 'だんだんと', '徐々', '年を追うごとに', '年を重ねるごとに']
    severity_keywords = ['ひどくなっている', '悪化', '悪化している', 'ひどくなった', '強くなっている', '強くなった', 'つらくなっている', 'つらくなった']
    pain_keywords = ['生理痛', '月経痛', '腹痛', 'お腹の痛み', '下腹部痛', '下腹部の痛み']
    
    # 時間的キーワードと重症度キーワードの組み合わせ
    has_temporal = any(kw in user_message_lower for kw in temporal_keywords)
    has_severity = any(kw in user_message_lower for kw in severity_keywords)
    has_pain = any(kw in user_message_lower for kw in pain_keywords)
    
    if has_temporal and has_severity and has_pain:
        needs_escalation = True
        reason = "生理痛が年々ひどくなっている"
        urgency = "high"
        message = "生理痛が年々ひどくなっている場合、子宮内膜症などの疾患が隠れている可能性があります。婦人科での受診をお勧めします。"
        logger.info(f"🚨 受診勧奨: {reason} (緊急度: {urgency})")
        return {
            "needs_escalation": needs_escalation,
            "reason": reason,
            "urgency": urgency,
            "message": message
        }
    
    # NLUで症状の進行パターンを分析
    if nlu_result:
        symptoms = nlu_result.get("symptoms", [])
        for symptom in symptoms:
            symptom_name = symptom.get("name", "")
            # 症状の進行パターンをチェック（NLU結果に進行情報が含まれている場合）
            if "進行" in str(symptom) or "悪化" in str(symptom):
                if "生理痛" in symptom_name or "月経痛" in symptom_name:
                    needs_escalation = True
                    reason = "生理痛の進行パターンが検出されました"
                    urgency = "high"
                    message = "生理痛が進行している場合、子宮内膜症などの疾患が隠れている可能性があります。婦人科での受診をお勧めします。"
                    logger.info(f"🚨 受診勧奨: {reason} (緊急度: {urgency})")
                    return {
                        "needs_escalation": needs_escalation,
                        "reason": reason,
                        "urgency": urgency,
                        "message": message
                    }
    
    # 「出血量が異常に多い（過多月経）」の検出
    # 明示的なキーワード
    excessive_bleeding_keywords = [
        '出血量が多い', '過多月経', 'ナプキンがすぐにいっぱいになる',
        '出血が多い', '経血量が多い', '出血が異常に多い', '出血量が異常',
        '大量出血', '出血が止まらない', '出血が長引く'
    ]
    
    # 重症度キーワードと「出血」「経血」の組み合わせ
    severity_modifiers = ['異常に', '非常に', '大量に', 'すごく', 'とても', 'かなり', 'めちゃくちゃ']
    bleeding_keywords = ['出血', '経血', '生理の出血', '月経の出血']
    
    # 明示的なキーワードをチェック
    if any(kw in user_message_lower for kw in excessive_bleeding_keywords):
        needs_escalation = True
        reason = "過多月経の可能性"
        urgency = "high"
        message = "出血量が異常に多い場合、子宮筋腫や子宮内膜症などの疾患が隠れている可能性があります。婦人科での受診をお勧めします。"
        logger.info(f"🚨 受診勧奨: {reason} (緊急度: {urgency})")
        return {
            "needs_escalation": needs_escalation,
            "reason": reason,
            "urgency": urgency,
            "message": message
        }
    
    # 重症度キーワードと出血キーワードの組み合わせ
    has_severity_modifier = any(kw in user_message_lower for kw in severity_modifiers)
    has_bleeding = any(kw in user_message_lower for kw in bleeding_keywords)
    
    if has_severity_modifier and has_bleeding:
        needs_escalation = True
        reason = "異常な出血量の可能性"
        urgency = "high"
        message = "出血量が異常に多い場合、子宮筋腫や子宮内膜症などの疾患が隠れている可能性があります。婦人科での受診をお勧めします。"
        logger.info(f"🚨 受診勧奨: {reason} (緊急度: {urgency})")
        return {
            "needs_escalation": needs_escalation,
            "reason": reason,
            "urgency": urgency,
            "message": message
        }
    
    # NLUで過多月経の症状を抽出
    if nlu_result:
        symptoms = nlu_result.get("symptoms", [])
        for symptom in symptoms:
            symptom_name = symptom.get("name", "")
            if "過多月経" in symptom_name or "出血量" in symptom_name:
                needs_escalation = True
                reason = "過多月経の症状が検出されました"
                urgency = "high"
                message = "出血量が異常に多い場合、子宮筋腫や子宮内膜症などの疾患が隠れている可能性があります。婦人科での受診をお勧めします。"
                logger.info(f"🚨 受診勧奨: {reason} (緊急度: {urgency})")
                return {
                    "needs_escalation": needs_escalation,
                    "reason": reason,
                    "urgency": urgency,
                    "message": message
                }
    
    return {
        "needs_escalation": False,
        "reason": "",
        "urgency": "",
        "message": ""
    }

def generate_doctor_referral_message(escalation_info: dict) -> dict:
    """
    受診勧奨メッセージの生成
    
    Args:
        escalation_info: detect_severity_escalationの結果
    
    Returns:
        構造化された受診勧奨メッセージ
    """
    if not escalation_info.get("needs_escalation", False):
        return {}
    
    reason = escalation_info.get("reason", "")
    urgency = escalation_info.get("urgency", "medium")
    message = escalation_info.get("message", "")
    
    # 推奨される診療科を決定
    recommended_department = "婦人科"
    
    # 緊急度に応じたメッセージの調整
    if urgency == "high":
        urgency_message = "早めに"
    elif urgency == "medium":
        urgency_message = "なるべく早く"
    else:
        urgency_message = "可能な限り"
    
    structured_message = {
        "title": "受診をお勧めします",
        "reason": reason,
        "recommended_department": recommended_department,
        "urgency": urgency,
        "urgency_message": urgency_message,
        "message": message,
        "additional_info": "市販薬で対応できない症状の可能性があります。専門医の診察を受けることをお勧めします。"
    }
    
    return structured_message

def determine_pain_urgency(user_message: str, nlu_result: dict) -> dict:
    """
    痛みの緊急性判定（痛みが主訴か随伴症状かを判定）
    
    Args:
        user_message: ユーザーの入力メッセージ
        nlu_result: NLU解析結果
    
    Returns:
        {
            "is_primary": True/False,
            "pain_level": "severe/moderate/mild",
            "keywords": ["検出されたキーワード"]
        }
    """
    user_message_lower = user_message.lower() if user_message else ""
    detected_keywords = []
    
    # キーワードの優先度判定
    primary_pain_keywords = ['痛い', '激痛', '痛くて辛い', '痛くてつらい', '痛みが強い', '痛みがひどい', '痛みで', '痛みのため']
    secondary_pain_keywords = ['たまに痛む', '時々痛む', '痛むことがある', '痛みがある', '痛みを感じる']
    
    # 文の構造判定
    # 「痛くて辛い」などの主訴パターン
    primary_patterns = [
        r'痛くて\s*辛い',
        r'痛くて\s*つらい',
        r'痛みが\s*強い',
        r'痛みが\s*ひどい',
        r'激痛',
        r'痛みで\s*',
        r'痛みのため\s*'
    ]
    
    # 「たまに痛む」などの随伴症状パターン
    secondary_patterns = [
        r'たまに\s*痛む',
        r'時々\s*痛む',
        r'痛む\s*ことが\s*ある',
        r'痛みが\s*ある',
        r'痛みを\s*感じる'
    ]
    
    # キーワードの優先度チェック
    has_primary_keyword = False
    has_secondary_keyword = False
    
    for keyword in primary_pain_keywords:
        if keyword in user_message_lower:
            has_primary_keyword = True
            detected_keywords.append(keyword)
            break
    
    if not has_primary_keyword:
        for keyword in secondary_pain_keywords:
            if keyword in user_message_lower:
                has_secondary_keyword = True
                detected_keywords.append(keyword)
                break
    
    # 文の構造チェック
    import re
    has_primary_pattern = False
    has_secondary_pattern = False
    
    for pattern in primary_patterns:
        if re.search(pattern, user_message_lower):
            has_primary_pattern = True
            break
    
    if not has_primary_pattern:
        for pattern in secondary_patterns:
            if re.search(pattern, user_message_lower):
                has_secondary_pattern = True
                break
    
    # NLUで症状の重要度を分析
    nlu_primary = False
    if nlu_result:
        symptoms = nlu_result.get("symptoms", [])
        # 症状の順序や重要度フラグをチェック（NLU結果に含まれている場合）
        for i, symptom in enumerate(symptoms):
            symptom_name = symptom.get("name", "")
            if "痛" in symptom_name or "痛み" in symptom_name:
                # 最初の症状または重要度が高い場合は主訴の可能性が高い
                if i == 0 or symptom.get("priority", 0) > 0.7:
                    nlu_primary = True
                    break
    
    # 判定結果の統合
    is_primary = has_primary_keyword or has_primary_pattern or nlu_primary
    
    # 痛みのレベル判定
    pain_level = "mild"
    if any(kw in user_message_lower for kw in ['激痛', '激しい痛み', '強い痛み', 'ひどい痛み']):
        pain_level = "severe"
    elif any(kw in user_message_lower for kw in ['痛い', '痛み', '痛む']):
        pain_level = "moderate"
    
    logger.info(f"🔍 痛みの緊急性判定: is_primary={is_primary}, pain_level={pain_level}, keywords={detected_keywords}")
    
    return {
        "is_primary": is_primary,
        "pain_level": pain_level,
        "keywords": detected_keywords
    }

def detect_digestive_sensitivity(user_message: str, nlu_result: dict, user_info: dict) -> dict:
    """
    消化器症状の検出（お腹を壊しやすい、下痢しやすいなど）
    
    Args:
        user_message: ユーザーの入力メッセージ
        nlu_result: NLU解析結果
        user_info: ユーザー情報
    
    Returns:
        {
            "has_digestive_sensitivity": True/False,
            "reason": "検出理由"
        }
    """
    has_digestive_sensitivity = False
    reason = ""
    
    user_message_lower = user_message.lower() if user_message else ""
    
    # 明示的なキーワードを検出
    digestive_keywords = ['お腹を壊しやすい', '下痢しやすい', 'お腹が弱い', '胃腸が弱い', '下痢をしやすい', 'お腹を下しやすい']
    if any(kw in user_message_lower for kw in digestive_keywords):
        has_digestive_sensitivity = True
        reason = "明示的なキーワード検出"
    
    # NLUで「消化器症状」や「下痢」の既往歴を抽出
    if not has_digestive_sensitivity and nlu_result:
        symptoms = nlu_result.get("symptoms", [])
        for symptom in symptoms:
            symptom_name = symptom.get("name", "")
            if "下痢" in symptom_name or "消化器" in symptom_name:
                has_digestive_sensitivity = True
                reason = "NLU解析による検出"
                break
    
    # ユーザー属性（user_info）から判定
    if not has_digestive_sensitivity:
        if user_info.get('digestive_sensitivity') is True:
            has_digestive_sensitivity = True
            reason = "ユーザー属性による検出"
    
    return {
        "has_digestive_sensitivity": has_digestive_sensitivity,
        "reason": reason
    }

def extract_user_preferences(user_message: str, nlu_result: dict = None, user_info: dict = None) -> dict:
    """
    ユーザー要望を抽出（成分・バランス、飲みやすさ、随伴症状など）
    
    Args:
        user_message: ユーザーのメッセージ
        nlu_result: NLU解析結果（オプション）
        user_info: ユーザー情報（オプション）
    
    Returns:
        {
            "ingredient_balance": True/False,  # 成分・バランス重視
            "ease_of_taking": True/False,      # 飲みやすさ重視
            "accompanying_symptoms": True/False,  # 随伴症状対応
            "confidence": 0.0-1.0,            # 確信度
            "reasons": List[str]               # 判定理由
        }
    """
    if not user_message:
        return {
            "ingredient_balance": False,
            "ease_of_taking": False,
            "accompanying_symptoms": False,
            "confidence": 0.0,
            "reasons": []
        }
    
    user_message_lower = user_message.lower()
    reasons = []
    confidence = 0.0
    
    # 成分・バランス重視のキーワード（計画要件: ユーザー要望抽出の改善）
    ingredient_balance_keywords = [
        "成分", "バランス", "配合", "ビタミン", "栄養", "総合", "複合",
        "成分重視", "バランス重視", "配合成分", "成分のバランス",
        "ビタミン配合", "栄養補給", "総合的な", "複合的な",
        "成分・バランス", "成分・バランス重視", "成分バランス",  # 追加
        "生薬重視", "漢方重視", "複合成分"  # 追加
    ]
    
    # 飲みやすさ重視のキーワード（計画要件: ユーザー要望抽出の改善）
    ease_of_taking_keywords = [
        "飲みやすい", "飲みやすさ", "錠剤", "カプセル", "顆粒", "顆粒が苦手",
        "味が苦手", "漢方の味", "苦い", "飲みにくい", "服用しやすい",
        "簡単に", "手軽に", "1日1回", "1日2回", "服用回数が少ない",
        "飲みやすさ重視", "服用しやすさ", "手軽に飲める",
        "錠剤タイプ", "錠剤タイプが", "錠剤が", "カプセルタイプ",  # 追加
        "顆粒苦手", "味が苦手", "携帯しやすい"  # 追加
    ]
    
    # 随伴症状対応のキーワード（計画要件: ユーザー要望抽出の改善）
    accompanying_symptoms_keywords = [
        "随伴症状", "併発", "一緒に", "同時に", "複数の症状", "いろいろな症状",
        "ニキビ", "肌荒れ", "腰痛", "頭痛", "めまい", "冷え症", "むくみ",
        "複数の悩み", "様々な症状", "多様な症状", "幅広い症状",
        "あれこれ", "あれこれ気になる", "色々気になる", "色々な症状",  # 追加
        "複合的な症状", "全体的に", "まとめて", "随伴症状対応"  # 追加
    ]
    
    # 成分・バランス重視の判定
    ingredient_balance = False
    ingredient_balance_count = 0
    for keyword in ingredient_balance_keywords:
        if keyword in user_message_lower:
            ingredient_balance = True
            ingredient_balance_count += 1
            reasons.append(f"成分・バランス重視: '{keyword}'を検出")
    
    # 飲みやすさ重視の判定
    ease_of_taking = False
    ease_of_taking_count = 0
    for keyword in ease_of_taking_keywords:
        if keyword in user_message_lower:
            ease_of_taking = True
            ease_of_taking_count += 1
            reasons.append(f"飲みやすさ重視: '{keyword}'を検出")
    
    # 随伴症状対応の判定
    accompanying_symptoms = False
    accompanying_symptoms_count = 0
    
    # 明示的なキーワード
    for keyword in accompanying_symptoms_keywords:
        if keyword in user_message_lower:
            accompanying_symptoms = True
            accompanying_symptoms_count += 1
            reasons.append(f"随伴症状対応: '{keyword}'を検出")
    
    # NLU結果から複数の症状が検出されている場合、随伴症状対応と推測
    if nlu_result:
        symptoms = nlu_result.get("symptoms", [])
        if len(symptoms) >= 2:
            accompanying_symptoms = True
            accompanying_symptoms_count += 1
            reasons.append(f"随伴症状対応: 複数の症状が検出されました（{len(symptoms)}個）")
    
    # 確信度の計算
    total_keywords = ingredient_balance_count + ease_of_taking_count + accompanying_symptoms_count
    if total_keywords >= 3:
        confidence = min(1.0, 0.7 + (total_keywords - 3) * 0.1)
    elif total_keywords >= 2:
        confidence = 0.5 + (total_keywords - 2) * 0.1
    elif total_keywords >= 1:
        confidence = 0.3 + (total_keywords - 1) * 0.1
    else:
        confidence = 0.0
    
    # 症状から推測（明示的な指定がない場合）
    if not ingredient_balance and not ease_of_taking and not accompanying_symptoms:
        # ビタミンや総合的な表現がある場合、成分・バランス重視と推測
        if any(kw in user_message_lower for kw in ["ビタミン", "総合", "複合", "配合"]):
            ingredient_balance = True
            confidence = max(confidence, 0.2)
            reasons.append("成分・バランス重視: ビタミンや総合的な表現から推測")
        
        # 錠剤や服用回数に関する言及がある場合、飲みやすさ重視と推測
        if any(kw in user_message_lower for kw in ["錠剤", "カプセル", "1日1回", "1日2回", "服用回数"]):
            ease_of_taking = True
            confidence = max(confidence, 0.2)
            reasons.append("飲みやすさ重視: 錠剤や服用回数に関する言及から推測")
        
        # 複数の症状が検出されている場合、随伴症状対応と推測
        if nlu_result and len(nlu_result.get("symptoms", [])) >= 2:
            accompanying_symptoms = True
            confidence = max(confidence, 0.2)
            reasons.append("随伴症状対応: 複数の症状から推測")
    
    logger.info(f"📋 ユーザー要望抽出: 成分・バランス={ingredient_balance}, 飲みやすさ={ease_of_taking}, 随伴症状={accompanying_symptoms}, 確信度={confidence:.2f}")
    if reasons:
        logger.debug(f"ユーザー要望抽出の詳細: {reasons}")
    
    return {
        "ingredient_balance": ingredient_balance,
        "ease_of_taking": ease_of_taking,
        "accompanying_symptoms": accompanying_symptoms,
        "confidence": confidence,
        "reasons": reasons
    }

def detect_postpartum_breastfeeding(user_message: str, nlu_result: dict, user_info: dict) -> dict:
    """
    産後・授乳中の判定
    
    Args:
        user_message: ユーザーの入力メッセージ
        nlu_result: NLU解析結果
        user_info: ユーザー情報
    
    Returns:
        {
            "is_postpartum": True/False,
            "is_breastfeeding": True/False,
            "reason": "検出理由"
        }
    """
    is_postpartum = False
    is_breastfeeding = False
    reason = ""
    
    user_message_lower = user_message.lower() if user_message else ""
    
    # 明示的キーワード: 「産後」「授乳中」「授乳」などのキーワードを検出
    postpartum_keywords = ['産後', '出産後', '分娩後']
    breastfeeding_keywords = ['授乳中', '授乳', '母乳', '授乳している', '授乳期間中']
    
    if any(kw in user_message_lower for kw in postpartum_keywords):
        is_postpartum = True
        reason = "明示的なキーワード検出（産後）"
    
    if any(kw in user_message_lower for kw in breastfeeding_keywords):
        is_breastfeeding = True
        if not reason:
            reason = "明示的なキーワード検出（授乳中）"
        else:
            reason += "、授乳中"
    
    # NLP抽出: NLUで「産後」「授乳」などの状態を抽出
    if nlu_result:
        # NLU結果から産後・授乳関連の情報を抽出（必要に応じて実装）
        # 現時点では明示的なキーワードとuser_infoを確認
        pass
    
    # ユーザー属性（user_info）から判定
    if not is_postpartum:
        if user_info.get('postpartum') is True:
            is_postpartum = True
            if not reason:
                reason = "ユーザー属性による検出（産後）"
    
    if not is_breastfeeding:
        if user_info.get('breastfeeding') is True:
            is_breastfeeding = True
            if not reason:
                reason = "ユーザー属性による検出（授乳中）"
            else:
                reason += "、授乳中"
    
    return {
        "is_postpartum": is_postpartum,
        "is_breastfeeding": is_breastfeeding,
        "reason": reason
    }


# ================================================================================
# 不足情報による減点システム
# ================================================================================

# 不足情報フィールドと減点値のマッピング
PENALTY_MAP = {
    "age": 0.15,  # Critical
    "allergies": 0.15,  # Critical
    "pregnancy_status": 0.15,  # Critical
    "gender": 0.05,  # Important
    "current_medications": 0.05,  # Important
    "symptom_duration": 0.02,  # Optional
    "symptoms": 0.0  # 症状が検出されない場合は推奨を中断するため減点なし
}

def calculate_completeness_penalty(missing_info_result: Dict) -> Dict:
    """
    不足情報による減点を計算
    
    Args:
        missing_info_result: check_missing_informationの戻り値
            {
                "has_missing_info": bool,
                "missing_fields": List[str],
                "priority": str
            }
    
    Returns:
        {
            "completeness_penalty": float,  # 累積減点（最大-0.3でキャップ）
            "missing_fields_detail": Dict[str, float],  # 各フィールドの減点内訳
            "max_penalty_reached": bool  # 最大減点に達したかどうか
        }
    """
    if not missing_info_result.get("has_missing_info", False):
        return {
            "completeness_penalty": 0.0,
            "missing_fields_detail": {},
            "max_penalty_reached": False
        }
    
    missing_fields = missing_info_result.get("missing_fields", [])
    if not missing_fields:
        return {
            "completeness_penalty": 0.0,
            "missing_fields_detail": {},
            "max_penalty_reached": False
        }
    
    # 各フィールドの減点を計算
    missing_fields_detail = {}
    total_penalty = 0.0
    max_penalty = 0.15  # 最大減点（30%から15%に変更）
    
    for field in missing_fields:
        penalty = PENALTY_MAP.get(field, 0.0)
        if penalty > 0:
            missing_fields_detail[field] = penalty
            total_penalty += penalty
    
    # 最大減点でキャップ
    max_penalty_reached = total_penalty >= max_penalty
    completeness_penalty = min(total_penalty, max_penalty)
    
    if logger.level <= logging.DEBUG:
        logger.debug(f"不足情報減点計算: missing_fields={missing_fields}, total_penalty={total_penalty:.3f}, capped_penalty={completeness_penalty:.3f}, max_reached={max_penalty_reached}")
    
    return {
        "completeness_penalty": completeness_penalty,
        "missing_fields_detail": missing_fields_detail,
        "max_penalty_reached": max_penalty_reached
    }
