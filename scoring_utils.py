"""
スコアリング関連のユーティリティ関数
効能特異性、副作用リスク、相互作用リスク、用法簡便性のスコア計算
"""

import pandas as pd
import re
import os
import unicodedata
import logging
from typing import Dict, List, Optional, Tuple, Any, Set

# Aho-Corasickアルゴリズムのインポート（オプション）
try:
    import ahocorasick
    AHO_CORASICK_AVAILABLE = True
except ImportError:
    AHO_CORASICK_AVAILABLE = False
    import logging
    _logger = logging.getLogger(__name__)
    _logger.warning("pyahocorasickがインストールされていません。通常の正規表現を使用します。")

logger = logging.getLogger(__name__)

# DEBUG_MODEはrule_based_recommendation.pyから取得（グローバル変数として定義されていない場合はFalse）
try:
    from rule_based_recommendation import DEBUG_MODE
except ImportError:
    DEBUG_MODE = False

# CSVファイルのパス
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
SIDE_EFFECTS_CSV = os.path.join(DATA_DIR, "medicine_side_effects.csv")
INTERACTIONS_CSV = os.path.join(DATA_DIR, "medicine_interactions.csv")

# 副作用・相互作用データのキャッシュ
_side_effects_df = None
_interactions_df = None


def normalize_text(text: str) -> str:
    """文字列をNFKC正規化・小文字化し、空白や記号を除去"""
    if not text or not isinstance(text, str):
        return ""

    normalized = unicodedata.normalize('NFKC', text)
    normalized = normalized.lower()
    # 空白と記号を除去（数字・アルファベット・日本語は残す）
    normalized = re.sub(r'[\s\u3000]+', '', normalized)
    normalized = re.sub(r"[^\wぁ-んァ-ン一-龥]+", '', normalized)
    return normalized


def basic_normalize_text(text: str) -> str:
    """
    基本正規化（Unicode正規化、大文字小文字・半角全角の統一、長音削除）
    方言変換の前に実行する
    
    Args:
        text: 正規化前のテキスト
    
    Returns:
        基本正規化されたテキスト
    """
    if not text or not isinstance(text, str):
        return ""
    
    # Unicode正規化（NFKC）
    normalized = unicodedata.normalize('NFKC', text)
    
    # 全角半角の統一（数字・アルファベット）
    normalized = normalized.translate(str.maketrans(
        '０１２３４５６７８９ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚ',
        '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
    ))
    
    # カタカナをひらがなに統一（濁点・半濁点も含む）
    # 全角カタカナの範囲を変換
    katakana_to_hiragana_map = {}
    for i in range(0x30A1, 0x30F7):  # ァ～ヲ
        katakana = chr(i)
        hiragana = chr(i - 0x60)  # カタカナとひらがなの差は0x60
        katakana_to_hiragana_map[katakana] = hiragana
    
    # 特殊な文字のマッピング
    katakana_to_hiragana_map['ヲ'] = 'を'
    katakana_to_hiragana_map['ヴ'] = 'う'
    katakana_to_hiragana_map['ヰ'] = 'ゐ'
    katakana_to_hiragana_map['ヱ'] = 'ゑ'
    
    # 濁点・半濁点付きカタカナ
    for base_kata, base_hira in [
        ('ガ', 'が'), ('ギ', 'ぎ'), ('グ', 'ぐ'), ('ゲ', 'げ'), ('ゴ', 'ご'),
        ('ザ', 'ざ'), ('ジ', 'じ'), ('ズ', 'ず'), ('ゼ', 'ぜ'), ('ゾ', 'ぞ'),
        ('ダ', 'だ'), ('ヂ', 'ぢ'), ('ヅ', 'づ'), ('デ', 'で'), ('ド', 'ど'),
        ('バ', 'ば'), ('ビ', 'び'), ('ブ', 'ぶ'), ('ベ', 'べ'), ('ボ', 'ぼ'),
        ('パ', 'ぱ'), ('ピ', 'ぴ'), ('プ', 'ぷ'), ('ペ', 'ぺ'), ('ポ', 'ぽ')
    ]:
        katakana_to_hiragana_map[base_kata] = base_hira
    
    # 変換テーブルを作成
    katakana_chars = ''.join(katakana_to_hiragana_map.keys())
    hiragana_chars = ''.join(katakana_to_hiragana_map.values())
    normalized = normalized.translate(str.maketrans(katakana_chars, hiragana_chars))
    
    # 長音の削除（「えらーい」→「えらい」）
    normalized = re.sub(r'[ー〜～]', '', normalized)
    
    return normalized


# 「たん」の誤検知防止用ブラックリスト
TANN_FALSE_POSITIVE_BLACKLIST = [
    "簡単", "かんたん", "カンタン",
    "負担", "ふたん", "フタン",
    "短期間", "たんきかん", "タンキカン",
    "ビタン", "ビタミン",
    "タンパク質", "たんぱく質", "タンパク",
    "担当", "たんとう", "タントウ",
    "単独", "たんどく", "タンドク",
    "単純", "たんじゅん", "タンジュン",
    "短縮", "たんしゅく", "タンシュク"
]

# キャッシュ用の辞書
_synonym_cache = {}
_blacklist_cache = {}


def is_word_match(token: str, text: str, blacklist: List[str] = None) -> bool:
    """
    単語境界を考慮したマッチング（ブラックリストチェック統合版・局所判定）
    
    Args:
        token: 検索する単語
        text: 検索対象のテキスト
        blacklist: 誤検知防止用ブラックリスト
    
    Returns:
        マッチした場合True
    """
    if not token or not text:
        return False
    
    normalized_text = normalize_text(text)
    normalized_token = normalize_text(token)
    
    # トークンが見つからない場合は即False
    if normalized_token not in normalized_text:
        return False
    
    # トークンの出現位置をすべて取得（str.find()を繰り返し使用）
    start_positions = []
    start = 0
    while True:
        pos = normalized_text.find(normalized_token, start)
        if pos == -1:
            break
        start_positions.append(pos)
        start = pos + 1
    
    if not start_positions:
        return False
    
    # ブラックリストチェック（短単語の場合・局所判定・座標計算のみで判定）
    if blacklist and len(normalized_token) <= 2:
        valid_match_found = False
        
        for start_idx in start_positions:
            is_part_of_blacklist = False
            
            for bl_word in blacklist:
                normalized_bl = normalize_text(bl_word)
                
                # ブラックリスト語の中にトークンが含まれていないならスキップ
                if normalized_token not in normalized_bl:
                    continue
                
                # トークンがブラックリスト語内の「どこ」にあるか特定（複数ある場合も考慮）
                # 例: bl_word="カンタン", token="タン" -> 相対位置 2
                bl_token_start = 0
                while True:
                    rel_start = normalized_bl.find(normalized_token, bl_token_start)
                    if rel_start == -1:
                        break
                    
                    # テキスト上の「ブラックリスト語の開始位置」と推測される座標
                    # text上の token_start (start_idx) から、相対位置 (rel_start) を引く
                    suspected_bl_start = start_idx - rel_start
                    suspected_bl_end = suspected_bl_start + len(normalized_bl)
                    
                    # 範囲チェック：テキストの範囲外なら無視
                    if suspected_bl_start < 0 or suspected_bl_end > len(normalized_text):
                        bl_token_start = rel_start + 1
                        continue
                    
                    # 実際にその範囲のテキストがブラックリスト語と一致するか？
                    if normalized_text[suspected_bl_start:suspected_bl_end] == normalized_bl:
                        is_part_of_blacklist = True
                        break  # この start_idx はブラックリストの一部だと確定
                    
                    bl_token_start = rel_start + 1
                
                if is_part_of_blacklist:
                    break  # 次のブラックリスト語を見るまでもなくNG
            
            if not is_part_of_blacklist:
                valid_match_found = True
                break  # 有効なマッチが1つでもあればOK
        
        # すべての出現がブラックリストに含まれている場合はFalse
        if not valid_match_found:
            return False
    
    # 以下、既存の単語境界チェック処理
    # 日本語文字の判定関数（助詞・記号を除く）
    def is_japanese_word_char(c: str) -> bool:
        if not c:
            return False
        # 漢字、カタカナのみを単語文字とみなす（ひらがな助詞は境界）
        return ('\u30A0' <= c <= '\u30FF' or  # カタカナ
                '\u4E00' <= c <= '\u9FFF')    # 漢字
    
    # 各出現位置で、前後が日本語文字でないことを確認
    for pos in start_positions:
        # 前の文字（存在する場合）
        prev_char = normalized_text[pos - 1] if pos > 0 else ''
        # 後の文字（存在する場合）
        next_pos = pos + len(normalized_token)
        next_char = normalized_text[next_pos] if next_pos < len(normalized_text) else ''
        
        # 前後が日本語単語文字でないことを確認
        # （前が文の始まりまたは非単語文字）AND（後が文の終わりまたは非単語文字）
        # ひらがな助詞（の、が、を、に、は、など）や記号（、。）は境界とみなす
        is_valid_start = (pos == 0) or not is_japanese_word_char(prev_char)
        is_valid_end = (next_pos >= len(normalized_text)) or not is_japanese_word_char(next_char)
        
        if is_valid_start and is_valid_end:
            return True
    
    return False

def get_synonym_expansion(symptom_name: str) -> set:
    """同義語展開をキャッシュ付きで取得"""
    if symptom_name in _synonym_cache:
        return _synonym_cache[symptom_name]
    
    # 同義語展開処理（symptom_synonyms辞書から取得）
    expanded = set()
    # この関数は後でcalculate_efficacy_specificity_score関数内で使用される
    # 実際の展開処理はcalculate_efficacy_specificity_score関数内で行う
    
    _synonym_cache[symptom_name] = expanded
    return expanded

BROAD_EFFICACY_KEYWORDS = {
    "滋養強壮": {
        "require_any": {"倦怠感", "疲労感", "虚弱体質", "肉体疲労", "病後"},
        "penalty": 0.45
    },
    "栄養補給": {
        "require_any": {"栄養障害", "食欲不振", "病後", "産前産後"},
        "penalty": 0.35
    },
    "疲労回復": {
        "require_any": {"疲労感", "倦怠感", "肉体疲労"},
        "penalty": 0.3
    }
}

def load_side_effects_data():
    """副作用データを読み込み"""
    global _side_effects_df
    if _side_effects_df is None:
        try:
            _side_effects_df = pd.read_csv(SIDE_EFFECTS_CSV, encoding='utf-8')
        except FileNotFoundError:
            print(f"警告: {SIDE_EFFECTS_CSV} が見つかりません")
            _side_effects_df = pd.DataFrame()
    return _side_effects_df

def load_interactions_data():
    """相互作用データを読み込み"""
    global _interactions_df
    if _interactions_df is None:
        try:
            _interactions_df = pd.read_csv(INTERACTIONS_CSV, encoding='utf-8')
        except FileNotFoundError:
            print(f"警告: {INTERACTIONS_CSV} が見つかりません")
            _interactions_df = pd.DataFrame()
    return _interactions_df

def calculate_efficacy_specificity_score(candidate: Dict, nlu_result: Dict) -> float:
    """
    効能特異性スコアを計算
    医薬品の効能効果が症状に特化しているほど高スコア
    
    Args:
        candidate: 候補医薬品の情報
        nlu_result: NLU結果（症状リスト）
    
    Returns:
        効能特異性スコア (0.0-1.0)
    """
    try:
        efficacy_text = candidate.get('efficacy', '')
        if not efficacy_text:
            return 0.0
        
        symptoms = nlu_result.get("symptoms", [])
        if not symptoms:
            return 0.0
        
        # 症状名のリストを作成
        symptom_names = [s.get('name', '') for s in symptoms if s.get('name')]
        if not symptom_names:
            return 0.0

        # 二日酔い特別処理：効能に「二日酔」が明記されている場合
        efficacy_lower = efficacy_text.lower()
        hangover_keywords_in_efficacy = ["二日酔", "宿酔", "悪酔"]
        has_hangover_efficacy = any(kw in efficacy_lower for kw in hangover_keywords_in_efficacy)
        has_hangover_symptom = any("二日酔" in str(name) for name in symptom_names)
        
        # 二日酔い症状と二日酔い効能が一致する場合、高スコアを付与
        if has_hangover_symptom and has_hangover_efficacy:
            return 0.95  # 二日酔い特化医薬品には高い効能特異性スコア

        normalized_symptoms = [normalize_text(name) for name in symptom_names]
        normalized_symptom_set = {name for name in normalized_symptoms if name}

        if not normalized_symptom_set:
            return 0.0
        
        # 症状名の同義語マッピング（月経不順と生理不順を同義語として扱う）
        symptom_synonyms = {
        "生理不順": ["月経不順", "生理不順", "月経異常", "生理異常"],
        "月経不順": ["月経不順", "生理不順", "月経異常", "生理異常"],
        "イライラ": ["イライラ", "いらいら", "イラつき", "いらつき", "いらだち"],
        # 新規追加（拡張版）
        "たん": [
            "たん", "痰", "タン", 
            "たんが出る", "痰が出る", 
            "喀痰", "咳痰",
            "のどにからむ", "喉に絡む"
        ],
        "痰": [
            "たん", "痰", "タン", 
            "たんが出る", "痰が出る", 
            "喀痰", "咳痰",
            "のどにからむ", "喉に絡む"
        ],
        "せき": ["せき", "咳", "セキ", "せきが出る", "咳が出る", "咳嗽", "咳込む", "空咳", "咳が止まらない", "咳がでる"],
        "咳": ["せき", "咳", "セキ", "せきが出る", "咳が出る", "咳嗽", "咳込む", "空咳", "咳が止まらない", "咳がでる"],
        # その他の一般的な症状
        "頭痛": ["頭痛", "頭が痛い", "頭がズキズキ", "偏頭痛", "緊張性頭痛", "頭が重い", "頭痛がする", "ずきずき"],
        "発熱": ["発熱", "熱", "熱がある", "高熱", "微熱", "体温上昇", "熱っぽい", "熱が出る", "熱が出た", "熱がでる", "悪寒", "寒気", "さむけ", "解熱", "熱感", "発熱感", "熱症状", "熱性"],
        "悪寒": ["悪寒", "寒気", "さむけ", "ゾクゾクする", "悪寒がする", "発熱", "熱", "震え"],
        "震え": ["震え", "ふるえ", "震える", "悪寒", "寒気"],
        "鼻水": ["鼻水", "鼻みず", "鼻汁", "鼻が出る", "水っぽい鼻水", "はなみず", "鼻がでる", "鼻炎", "鼻汁過多", "鼻水が多い", "鼻水がとまらない"],
        "鼻炎": ["鼻炎", "鼻水", "鼻づまり", "鼻汁過多"],
        "鼻汁過多": ["鼻汁過多", "鼻水が多い", "鼻水がとまらない", "鼻水"],
        "鼻づまり": ["鼻づまり", "鼻詰まり", "鼻が詰まる", "鼻閉", "鼻がつまる", "鼻が詰まってる", "鼻がつまってる"],
        "のどの痛み": ["のどの痛み", "喉の痛み", "咽頭痛", "のど痛", "喉が痛い", "のどが痛い", "声がかすれる", "声がかれる", "咽喉痛", "咽頭部痛", "のどの炎症", "喉の炎症", "咽頭炎", "咽喉炎"],
        "声がかすれる": ["声がかすれる", "声がかれる", "のどの痛み", "喉の痛み"],
        "腹痛": ["腹痛", "お腹が痛い", "腹が痛い", "腹部痛", "おなかが痛い", "はらが痛い", "胃痛", "胃が痛い"],
        "下痢": ["下痢", "軟便", "水様便", "便がゆるい", "便が緩い", "おなかを下す", "お腹を下す", "下す", "下痢をする", "げり"],
        "便秘": ["便秘", "便が出ない", "便通がない", "便が硬い", "お通じがない", "便がでない", "うんちが出ない", "ウンチが出ない"],
        # 胃腸関連症状
        "吐き気": ["吐き気", "むかつき", "気持ち悪い", "嘔吐感", "吐きそう", "はきけ", "むかむか", "つわり"],
        "胸やけ": ["胸やけ", "胸焼け", "むねやけ", "胃もたれ"],
        "胃もたれ": ["胃もたれ", "胃の重い感じ", "消化が悪い", "胃の不快感", "いもたれ", "胸やけ", "胸焼け", "消化不良"],
        "消化不良": ["消化不良", "消化が悪い", "胃もたれ", "胃の重い感じ"],
        "胃痛": ["胃痛", "胃が痛い", "胃の痛み", "胃部痛", "みぞおちの痛み"],
        "つわり": ["つわり", "悪阻", "吐き気", "嘔吐", "匂いに敏感", "匂いが気になる"],
        "頻尿": ["頻尿", "トイレが近い", "おしっこが近い", "尿が近い", "トイレに行く回数が多い"],
        # めまい・疲労関連
        "めまい": ["めまい", "眩暈", "ふらつき", "立ちくらみ", "くらくら", "平衡感覚の異常"],
        "疲労感": ["疲労感", "疲れ", "だるい", "倦怠感", "体が重い", "つかれた", "疲れた", "だるさ"],
        "だるさ": ["だるさ", "だるい", "体がだるい", "全身倦怠感", "倦怠感", "疲労感", "疲れ"],
        # 睡眠関連
        "不眠": ["不眠", "眠れない", "睡眠不足", "寝つきが悪い", "浅い眠り", "ねむれない"],
        # 皮膚関連
        "かゆみ": ["かゆみ", "痒み", "かゆい", "皮膚のかゆみ", "全身のかゆみ"],
        "発疹": ["発疹", "ブツブツ", "赤い斑点", "皮膚の異常", "湿疹"],
        "湿疹": ["湿疹", "皮膚炎", "かぶれ", "皮膚の炎症", "発疹"],
        "水虫": ["水虫", "白癬", "足の水虫", "指の間のかゆみ"],
        "打撲": ["打撲", "打ち身", "青あざ", "あおたん", "内出血", "あざ"],
        "打ち身": ["打ち身", "打撲", "青あざ", "あおたん", "内出血", "あざ"],
        "炎症": ["炎症", "炎症している", "炎症する", "にえる", "にえている"],
        "捻挫": ["捻挫", "くじいた", "関節の痛み", "靭帯損傷"],
        "くしゃみ": ["くしゃみ", "クシャミ", "くしゃみがでる", "くしゃみが出る"],
        # その他
        "むくみ": ["むくみ", "浮腫", "腫れぼったい", "パンパン", "顔のむくみ", "足のむくみ"],
        "二日酔い": ["二日酔い", "二日酔", "宿酔", "悪酔い", "悪酔", "飲み過ぎ", "飲みすぎ"],
        "肩こり": ["肩こり", "肩の凝り", "肩の痛み", "首肩の痛み", "かたこり", "首の痛み"],
        "腰痛": ["腰痛", "腰が痛い", "こしがいたい", "背中の痛み"],
        "背中の痛み": ["背中の痛み", "背中が痛い", "せなかがいたい"],
        "首の痛み": ["首の痛み", "首が痛い", "くびがいたい", "肩こり"],
        "関節痛": ["関節痛", "関節が痛い", "かんせつがいたい", "節々が痛い", "関節の痛み", "筋肉痛"],
        "筋肉痛": ["筋肉痛", "筋肉の痛み", "体が痛い", "筋肉が痛い", "関節痛"],
        "目の疲れ": ["目の疲れ", "眼精疲労", "目が疲れる", "目の重い感じ", "めがつかれる"],
        "目のかゆみ": ["目のかゆみ", "目がかゆい", "目の痒み", "めがかゆい", "結膜炎"],
        "目の充血": ["目の充血", "目が赤い", "充血", "目の血走り"],
        "なみだ目": ["なみだ目", "涙目", "目が涙でる", "涙が出る"],
        "結膜炎": ["結膜炎", "目のかゆみ", "目がかゆい", "目の充血"],
        "眠気": ["眠気", "眠い", "だるい", "眠たい", "眠気が強い", "いつも眠い", "寝てしまう", "眠くて寝てしまう", "居眠り", "眠くてたまらない"],
        "乗り物酔い": ["乗り物酔い", "車酔い", "船酔い", "バス酔い", "酔い", "乗り物に酔う", "車に乗ると気持ち悪い", "船に乗ると気持ち悪い", "乗物酔い", "乗物に酔う"],
        "冷え性": ["冷え性", "冷え", "手足が冷える", "体が冷える", "冷え症"],
        "動悸": ["動悸", "心臓がドキドキ", "ドキドキする", "心拍が速い", "脈が速い", "心臓がバクバク"],
        "息切れ": ["息切れ", "息が切れる", "息切れがする", "呼吸困難", "呼吸が苦しい", "息苦しい"],
        "呼吸困難": ["呼吸困難", "呼吸が苦しい", "息苦しい", "息ができない", "息切れ"],
        "生理痛": ["生理痛", "月経痛", "生理の痛み", "下腹部痛", "下腹部が痛い"],
        "下腹部痛": ["下腹部痛", "下腹部が痛い", "生理痛", "月経痛"],
        "歯痛": ["歯痛", "歯が痛い", "歯の痛み", "はがいたい"],
        "口内炎": ["口内炎", "口の痛み", "口が痛い", "口の中が痛い", "くちがいたい"],
        "口の痛み": ["口の痛み", "口が痛い", "口の中が痛い", "口内炎"],
        "耳鳴り": ["耳鳴り", "みみなり", "耳が鳴る"],
        "耳の痛み": ["耳の痛み", "耳が痛い", "みみがいたい"],
        "胸の張り": ["胸の張り", "胸が張る", "乳房の張り", "胸が痛い", "胸が敏感", "乳房が痛い"]
        }
        
        # 症状名の同義語を展開（キャッシュ対応）
        expanded_symptom_set = set(normalized_symptom_set)
        for symptom in normalized_symptom_set:
            # キャッシュをチェック
            cache_key = symptom
            if cache_key in _synonym_cache:
                expanded_symptom_set.update(_synonym_cache[cache_key])
            else:
                # キャッシュにない場合は展開処理を実行
                symptom_expanded = set()
                if symptom in symptom_synonyms:
                    for synonym in symptom_synonyms[symptom]:
                        normalized_synonym = normalize_text(synonym)
                        symptom_expanded.add(normalized_synonym)
                        expanded_symptom_set.add(normalized_synonym)
                # 「月経不順」と「生理不順」を相互にマッピング
                if normalize_text('月経不順') in symptom or normalize_text('生理不順') in symptom:
                    symptom_expanded.add(normalize_text('月経不順'))
                    symptom_expanded.add(normalize_text('生理不順'))
                    expanded_symptom_set.add(normalize_text('月経不順'))
                    expanded_symptom_set.add(normalize_text('生理不順'))
                # キャッシュに保存
                _synonym_cache[cache_key] = symptom_expanded
        
        normalized_symptom_set = expanded_symptom_set
        
        # 効能テキストを句読点で分割してから正規化
        # より柔軟な分割方法を採用（句読点だけでなく、長いテキストの場合は適切に分割）
        import re
        # 句読点で分割
        efficacy_parts_raw = re.split(r'[、。，．,.]', efficacy_text)
        # さらに、長いテキストの場合は適切に分割（効能効果の表現の多様性に対応）
        # 例：「発熱、さむけ、頭痛」と「発熱・さむけ・頭痛」と「発熱、さむけ及び頭痛」など
        additional_parts = []
        for part in efficacy_parts_raw:
            # 「及び」「並びに」「または」などの接続詞で分割
            if '及び' in part or '並びに' in part or 'または' in part or '又は' in part:
                additional_parts.extend(re.split(r'[及び並びにまたは又は]', part))
            # 「・」で分割（ただし、短い場合はそのまま）
            elif '・' in part and len(part) > 10:
                additional_parts.extend(part.split('・'))
            else:
                additional_parts.append(part)
        efficacy_parts_raw = additional_parts
        
        efficacy_parts = [normalize_text(p) for p in efficacy_parts_raw if p.strip()]
        efficacy_parts = [p for p in efficacy_parts if p]
        
        if not efficacy_parts:
            return 0.0
        
        # 効能効果欄の専門用語マッピング（月経不順関連）
        efficacy_lower = efficacy_text.lower()
        menstrual_efficacy_keywords = ["月経不順", "生理不順", "血の道症", "血の道", "月経異常", "生理異常"]
        has_menstrual_efficacy = any(kw in efficacy_lower for kw in menstrual_efficacy_keywords)

        # 単語境界を考慮したマッチング関数（モジュールレベルのis_word_match関数を使用）
        
        # キーワードの重み付けシステム
        def get_keyword_weight(keyword: str, symptom_name: str) -> float:
            """
            キーワードの重みを取得（コンテキストによる重み調整）
            
            Args:
                keyword: 効能テキスト内のキーワード
                symptom_name: 症状名
            
            Returns:
                重み (0.0-1.0)
            """
            keyword_lower = keyword.lower()
            symptom_name_lower = symptom_name.lower()
            
            # 「生理不順」→「月経不順」: weight: 1.0（直接的な表現）
            if (normalize_text('生理不順') in symptom_name_lower or normalize_text('月経不順') in symptom_name_lower) and normalize_text('月経不順') in keyword_lower:
                return 1.0
            if (normalize_text('月経不順') in symptom_name_lower or normalize_text('生理不順') in symptom_name_lower) and normalize_text('生理不順') in keyword_lower:
                return 1.0
            
            # 「血の道症」: weight: 0.8（より広義な表現）
            if normalize_text('血の道症') in keyword_lower or normalize_text('血の道') in keyword_lower:
                return 0.8
            
            # 「月経異常」「生理異常」: weight: 0.9（直接的な表現に近い）
            if normalize_text('月経異常') in keyword_lower or normalize_text('生理異常') in keyword_lower:
                return 0.9
            
            # 「産前産後」「更年期」: weight: コンテキスト依存（ユーザーの年齢や症状に応じて0.85-0.95）
            if normalize_text('産前産後') in keyword_lower or normalize_text('更年期') in keyword_lower:
                # デフォルトは0.9（年齢情報があれば調整可能）
                return 0.9
            
            # デフォルトの重み
            return 1.0
        
        # 各効能パート内でマッチングをカウント（重み付け対応）
        weighted_match_score = 0.0
        matched_symptoms = set()  # 既にマッチした症状を記録（重複カウントを防ぐ）
        
        for name in normalized_symptom_set:
            if name in matched_symptoms:
                continue  # 既にマッチした症状はスキップ
            
            matched = False
            match_weight = 1.0
            
            for part in efficacy_parts:
                # 直接マッチング
                if is_word_match(name, part):
                    # キーワードの重みを取得
                    match_weight = get_keyword_weight(part, name)
                    weighted_match_score += match_weight
                    matched_symptoms.add(name)
                    matched = True
                    if DEBUG_MODE or logger.level <= logging.DEBUG:
                        logger.debug(f"効能効果マッチング: {name} × {part} = weight {match_weight:.2f}")
                    break
                # 同義語マッチング（月経不順と生理不順を同義語として扱う）
                if name in symptom_synonyms:
                    for synonym in symptom_synonyms[name]:
                        normalized_synonym = normalize_text(synonym)
                        if normalized_synonym and is_word_match(normalized_synonym, part):
                            # キーワードの重みを取得
                            match_weight = get_keyword_weight(part, name)
                            weighted_match_score += match_weight
                            matched_symptoms.add(name)
                            matched = True
                            if DEBUG_MODE or logger.level <= logging.DEBUG:
                                logger.debug(f"効能効果マッチング（同義語）: {name} × {part} = weight {match_weight:.2f}")
                            break
                    if matched:
                        break
            
            # 効能テキストに「月経不順」や「生理不順」が含まれている場合、症状が「月経不順」または「生理不順」ならマッチ
            if not matched:
                # 症状名が「月経不順」または「生理不順」に関連する場合
                is_menstrual_symptom = (
                    normalize_text('月経不順') in name or 
                    normalize_text('生理不順') in name or
                    name == normalize_text('月経不順') or
                    name == normalize_text('生理不順')
                )
                
                if is_menstrual_symptom:
                    # 効能テキスト全体で月経不順関連キーワードをチェック（重み付け対応）
                    if has_menstrual_efficacy:
                        # 最も適切なキーワードの重みを取得
                        best_weight = 0.0
                        for kw in menstrual_efficacy_keywords:
                            if kw in efficacy_lower:
                                weight = get_keyword_weight(kw, name)
                                best_weight = max(best_weight, weight)
                        weighted_match_score += best_weight
                        matched_symptoms.add(name)
                        matched = True
                        if DEBUG_MODE or logger.level <= logging.DEBUG:
                            logger.debug(f"効能効果マッチング（月経不順関連）: {name} = weight {best_weight:.2f}")
        
        # 重み付けされたマッチスコアを症状数で正規化
        if len(normalized_symptom_set) > 0:
            match_count = weighted_match_score  # 重み付けされたスコアを使用
        else:
            match_count = 0.0
        
        # 効能特異性が0.0（イプシロン比較）の場合のフォールバック処理
        EPSILON = 0.0001  # 浮動小数点比較用イプシロン
        
        # 症状が効能に全く含まれていない場合の処理（強化版：ペナルティを強化）
        if match_count == 0:
            # 効能テキスト全体で症状が含まれているかを直接チェック（2段階）
            normalized_efficacy_full = normalize_text(efficacy_text)
            
            # 第1段階: 単純包含チェック（高速）
            has_simple_match = False
            for symptom_name in normalized_symptom_set:
                if symptom_name in normalized_efficacy_full:
                    has_simple_match = True
                    break
            
            # 第2段階: 単語境界チェック（正確性重視）
            if has_simple_match:
                for symptom_name in normalized_symptom_set:
                    # ブラックリストチェック（「たん」の場合）
                    blacklist = TANN_FALSE_POSITIVE_BLACKLIST if symptom_name == "たん" else None
                    if is_word_match(symptom_name, normalized_efficacy_full, blacklist=blacklist):
                        # 効能に症状が含まれている場合は、効能特異性スコアを0.5に底上げ
                        if DEBUG_MODE or logger.level <= logging.DEBUG:
                            logger.debug(f"効能特異性フォールバック: {candidate.get('product_name', '')} - "
                                        f"症状: {symptom_name}, 効能特異性: 0.5（底上げ）")
                        return 0.5
        
        # 解熱鎮痛薬の場合、発熱やのどの痛みなどの症状に対して一定のスコアを付与
        medicine_type = candidate.get("medicine_type", "")
        if "解熱鎮痛薬" in medicine_type:
            # 解熱鎮痛薬は発熱、頭痛、のどの痛みなどに効果がある
            fever_symptoms = ["発熱", "熱", "高熱", "微熱"]
            throat_symptoms = ["のどの痛み", "咽頭痛", "喉の痛み", "のど痛"]
            headache_symptoms = ["頭痛"]
            
            matched_symptom_count = 0
            for name in normalized_symptom_set:
                # 発熱関連症状
                if any(fever in name for fever in fever_symptoms):
                    matched_symptom_count += 1
                # のど痛み関連症状
                elif any(throat in name for throat in throat_symptoms):
                    matched_symptom_count += 1
                # 頭痛関連症状
                elif any(headache in name for headache in headache_symptoms):
                    matched_symptom_count += 1
            
            if matched_symptom_count > 0:
                # 解熱鎮痛薬は発熱、のどの痛み、頭痛に効果があるため、一定のスコアを付与
                specificity_ratio = matched_symptom_count / len(normalized_symptom_set)
                # 解熱鎮痛薬の効能特異性は中程度（0.4-0.5程度）
                return 0.45 * specificity_ratio
        
        # 外用薬（のど）の場合、のどの痛みに対して一定のスコアを付与
        if "外用薬（のど）" in medicine_type or ("外用薬" in medicine_type and "のど" in medicine_type):
            throat_symptoms = ["のどの痛み", "咽頭痛", "喉の痛み", "のど痛"]
            
            for name in normalized_symptom_set:
                if any(throat in name for throat in throat_symptoms):
                    # 外用薬（のど）はのどの痛みに効果があるため、一定のスコアを付与
                    return 0.45
            
            return 0.0
        
        # 重み付けされたスコアを使用して特異性比率を計算
        if len(normalized_symptom_set) > 0:
            # 重み付けされたスコアを症状数で正規化（最大値は症状数）
            specificity_ratio = match_count / len(normalized_symptom_set)
        else:
            specificity_ratio = 0.0
        
        # 効能特異性が非常に低い場合（イプシロン比較）でも、効能テキストに症状が含まれているかを直接チェック
        EPSILON = 0.0001  # 浮動小数点比較用イプシロン
        
        # 効能テキスト全体で症状が含まれているかを直接チェック（2段階）
        normalized_efficacy_full = normalize_text(efficacy_text)
        
        # 第1段階: 単純包含チェック（高速）
        # 同義語も含めてチェック（効能効果の表現の多様性に対応）
        has_simple_match = False
        for symptom_name in normalized_symptom_set:
            # 直接マッチ
            if symptom_name in normalized_efficacy_full:
                has_simple_match = True
                break
            # 同義語マッチ（症状名の同義語を展開してチェック）
            if symptom_name in symptom_synonyms:
                for synonym in symptom_synonyms[symptom_name]:
                    normalized_synonym = normalize_text(synonym)
                    if normalized_synonym and normalized_synonym in normalized_efficacy_full:
                        has_simple_match = True
                        break
                if has_simple_match:
                    break
        
        # 第2段階: 単語境界チェック（正確性重視）
        if has_simple_match:
            for symptom_name in normalized_symptom_set:
                # ブラックリストチェック（「たん」の場合）
                blacklist = TANN_FALSE_POSITIVE_BLACKLIST if symptom_name == "たん" else None
                if is_word_match(symptom_name, normalized_efficacy_full, blacklist=blacklist):
                    # 効能に症状が含まれている場合、かつスコアが0.5未満の場合は0.5に底上げ
                    # ただし、すでに0.5以上の場合はそのまま返す
                    if specificity_ratio < EPSILON:
                        # 効能に症状が含まれている場合は、効能特異性スコアを0.5に底上げ
                        if DEBUG_MODE or logger.level <= logging.DEBUG:
                            logger.debug(f"効能特異性フォールバック（低スコア）: {candidate.get('product_name', '')} - "
                                        f"症状: {symptom_name}, 効能特異性: 0.5（底上げ）")
                        return 0.5
                    # スコアが0.5未満の場合も底上げ（効能に明記されている場合は最低0.5を保証）
                    elif specificity_ratio < 0.5:
                        if DEBUG_MODE or logger.level <= logging.DEBUG:
                            logger.debug(f"効能特異性底上げ: {candidate.get('product_name', '')} - "
                                        f"症状: {symptom_name}, 効能特異性: {specificity_ratio:.2f} → 0.5（底上げ）")
                        return 0.5
                # 同義語マッチ（症状名の同義語を展開してチェック）
                if symptom_name in symptom_synonyms:
                    for synonym in symptom_synonyms[symptom_name]:
                        normalized_synonym = normalize_text(synonym)
                        if normalized_synonym and is_word_match(normalized_synonym, normalized_efficacy_full, blacklist=blacklist):
                            # 効能に症状が含まれている場合、かつスコアが0.5未満の場合は0.5に底上げ
                            if specificity_ratio < EPSILON:
                                if DEBUG_MODE or logger.level <= logging.DEBUG:
                                    logger.debug(f"効能特異性フォールバック（低スコア・同義語）: {candidate.get('product_name', '')} - "
                                                f"症状: {symptom_name} (同義語: {synonym}), 効能特異性: 0.5（底上げ）")
                                return 0.5
                            elif specificity_ratio < 0.5:
                                if DEBUG_MODE or logger.level <= logging.DEBUG:
                                    logger.debug(f"効能特異性底上げ（同義語）: {candidate.get('product_name', '')} - "
                                                f"症状: {symptom_name} (同義語: {synonym}), 効能特異性: {specificity_ratio:.2f} → 0.5（底上げ）")
                                return 0.5
        
        # 月経不順関連症状と効能のマッチング強化
        if has_menstrual_efficacy:
            # 効能効果欄に月経不順関連のキーワードが含まれている場合、症状とのマッチングを強化
            menstrual_symptom_keywords = ["月経不順", "生理不順", "月経異常", "生理異常", "血の道症", "生理が遅れ", "月経が遅れ"]
            symptom_names = [s.get("name", "") for s in nlu_result.get("symptoms", [])]
            has_menstrual_symptom = any(
                any(keyword in symptom_name or keyword in normalize_text(symptom_name) 
                    for keyword in menstrual_symptom_keywords)
                for symptom_name in symptom_names
            )
            if has_menstrual_symptom:
                # 月経不順関連症状と効能が一致する場合、特異性スコアを底上げ
                specificity_ratio = max(specificity_ratio, 0.7)  # 最低0.7を保証

        # 効能効果の長さによる調整（短いほど特化している）
        # 全パートを結合して長さを計算
        combined_efficacy = ''.join(efficacy_parts)
        efficacy_length = len(combined_efficacy)
        length_penalty = min(1.0, efficacy_length / 120)  # 正規化後のテキスト長を基準

        final_score = specificity_ratio * (1.0 - length_penalty * 0.25)

        # 広域効能（滋養強壮など）の場合は症状との整合性を確認
        penalty_factor = 1.0
        for keyword, rule in BROAD_EFFICACY_KEYWORDS.items():
            normalized_keyword = normalize_text(keyword)
            if normalized_keyword and normalized_keyword in combined_efficacy:
                required_set = {normalize_text(req) for req in rule.get("require_any", set())}
                if required_set and not any(req in normalized_symptom_set for req in required_set):
                    penalty = max(0.0, min(1.0, rule.get("penalty", 0.2)))
                    penalty_factor *= (1.0 - penalty)

        final_score *= penalty_factor

        return min(1.0, max(0.0, final_score))
    except Exception as e:
        logger.warning(f"効能特異性計算エラー: {e}")
        if DEBUG_MODE or logger.level <= logging.DEBUG:
            import traceback
            logger.debug(f"詳細: {traceback.format_exc()}")
        return 0.0  # デフォルト値

def calculate_side_effect_risk_score(candidate: Dict, user_info: Dict) -> float:
    """
    副作用リスクスコアを計算
    副作用リスクが高いほど負のスコア
    
    Args:
        candidate: 候補医薬品の情報
        user_info: ユーザー情報
    
    Returns:
        副作用リスクスコア (-1.0-0.0、負の値)
    """
    ingredients = candidate.get('ingredients', '')
    if not ingredients:
        return 0.0
    
    # 副作用データを読み込み
    side_effects_df = load_side_effects_data()
    if side_effects_df.empty:
        return 0.0
    
    # 成分リストを抽出（改行区切り）
    ingredient_list = [ing.strip() for ing in ingredients.split('\n') if ing.strip()]
    
    total_risk = 0.0
    risk_count = 0
    
    for ingredient in ingredient_list:
        # 副作用データから該当成分を検索
        matching_rows = side_effects_df[
            side_effects_df['成分名'].str.contains(ingredient, na=False, case=False)
        ]
        
        for _, row in matching_rows.iterrows():
            side_effect_level = row.get('副作用レベル', '')
            contraindications = row.get('禁忌条件', '')
            
            # 副作用レベルを数値に変換
            level_score = 0.0
            if side_effect_level == '高':
                level_score = -0.8
            elif side_effect_level == '中':
                level_score = -0.5
            elif side_effect_level == '低':
                level_score = -0.2
            
            # 禁忌条件のチェック
            if contraindications and user_info:
                # ユーザーの既往症や状態をチェック
                if any(condition in str(user_info) for condition in contraindications.split(',')):
                    level_score *= 2  # 禁忌条件に該当する場合はリスクを倍増
            
            # 妊娠中・授乳中の場合は追加減点
            if user_info.get('pregnant') or user_info.get('breastfeeding'):
                level_score *= 1.5
            
            total_risk += level_score
            risk_count += 1
    
    # 平均リスクスコアを計算
    if risk_count == 0:
        return 0.0
    
    avg_risk = total_risk / risk_count
    return max(-1.0, min(0.0, avg_risk))

def calculate_interaction_risk_score(candidate: Dict, user_info: Dict) -> float:
    """
    相互作用リスクスコアを計算
    相互作用リスクが高いほど負のスコア
    
    Args:
        candidate: 候補医薬品の情報
        user_info: ユーザー情報
    
    Returns:
        相互作用リスクスコア (-1.0-0.0、負の値)
    """
    ingredients = candidate.get('ingredients', '')
    current_medications = user_info.get('current_medications', [])
    
    if not ingredients or not current_medications:
        return 0.0
    
    # 相互作用データを読み込み
    interactions_df = load_interactions_data()
    if interactions_df.empty:
        return 0.0
    
    # 候補医薬品の成分リスト
    candidate_ingredients = [ing.strip() for ing in ingredients.split('\n') if ing.strip()]
    
    total_risk = 0.0
    interaction_count = 0
    
    # 現在服用中の薬との相互作用をチェック
    for medication in current_medications:
        for candidate_ingredient in candidate_ingredients:
            # 相互作用データから該当する組み合わせを検索
            matching_rows = interactions_df[
                (interactions_df['成分A'].str.contains(candidate_ingredient, na=False, case=False) |
                 interactions_df['成分B'].str.contains(candidate_ingredient, na=False, case=False)) &
                (interactions_df['成分A'].str.contains(medication, na=False, case=False) |
                 interactions_df['成分B'].str.contains(medication, na=False, case=False))
            ]
            
            for _, row in matching_rows.iterrows():
                interaction_level = row.get('相互作用レベル', '')
                
                # 相互作用レベルを数値に変換
                level_score = 0.0
                if interaction_level == '高':
                    level_score = -0.8
                elif interaction_level == '中':
                    level_score = -0.5
                elif interaction_level == '低':
                    level_score = -0.2
                
                total_risk += level_score
                interaction_count += 1
    
    # 平均相互作用リスクスコアを計算
    if interaction_count == 0:
        return 0.0
    
    avg_risk = total_risk / interaction_count
    return max(-1.0, min(0.0, avg_risk))

def calculate_usage_convenience_score(candidate: Dict) -> float:
    """
    用法簡便性スコアを計算
    1日の服用回数が少ないほど高スコア
    
    Args:
        candidate: 候補医薬品の情報
    
    Returns:
        用法簡便性スコア (0.0-1.0)
    """
    usage_text = candidate.get('usage', '')
    if not usage_text:
        return 0.5  # デフォルトスコア
    
    # 1日の服用回数を抽出する正規表現
    patterns = [
        r'1日(\d+)回',
        r'(\d+)回服用',
        r'(\d+)回に分けて',
        r'(\d+)回服用'
    ]
    
    daily_frequency = None
    for pattern in patterns:
        match = re.search(pattern, usage_text)
        if match:
            daily_frequency = int(match.group(1))
            break
    
    # 服用回数が見つからない場合はデフォルト
    if daily_frequency is None:
        return 0.5
    
    # 服用回数によるスコア計算
    if daily_frequency == 1:
        return 1.0
    elif daily_frequency == 2:
        return 0.8
    elif daily_frequency == 3:
        return 0.6
    elif daily_frequency == 4:
        return 0.4
    else:
        return 0.2

# 成分名の正規化辞書
INGREDIENT_NORMALIZATION = {
    "アスピリン": ["アセチルサリチル酸", "ASA", "アスピリン", "aspirin"],
    "イブプロフェン": ["イブ", "ブルフェン", "イブプロフェン", "ibuprofen"],
    "アセトアミノフェン": ["パラセタモール", "タイレノール", "アセトアミノフェン", "acetaminophen"],
    "ロキソプロフェン": ["ロキソニン", "ロキソプロフェン", "loxoprofen"],
    "ジクロフェナク": ["ボルタレン", "ジクロフェナク", "diclofenac"],
    "メフェナム酸": ["ポンタール", "メフェナム酸", "mefenamic acid"],
    "インドメタシン": ["インダシン", "インドメタシン", "indomethacin"],
    "ケトプロフェン": ["モーラス", "ケトプロフェン", "ketoprofen"],
    "ナプロキセン": ["ナイキサン", "ナプロキセン", "naproxen"],
    "セレコキシブ": ["セレコックス", "セレコキシブ", "celecoxib"]
}

def normalize_ingredient_name(ingredient: str) -> str:
    """
    成分名を正規化
    
    Args:
        ingredient: 元の成分名
    
    Returns:
        正規化された成分名
    """
    ingredient_lower = ingredient.lower().strip()
    
    # 正規化辞書から検索
    for normalized_name, variations in INGREDIENT_NORMALIZATION.items():
        for variation in variations:
            if variation.lower() in ingredient_lower:
                return normalized_name
    
    return ingredient.strip()

def check_allergy_contraindication(candidate: Dict, user_info: Dict) -> Tuple[bool, str]:
    """
    アレルギー成分照合を実行（強化版）
    
    Args:
        candidate: 候補医薬品の情報
        user_info: ユーザー情報
    
    Returns:
        (is_allergic: bool, allergy_ingredient: str)
    """
    ingredients = candidate.get('ingredients', '')
    allergies = user_info.get('allergies', [])
    
    if not ingredients or not allergies or allergies == ['なし']:
        return False, ""
    
    # 成分リストを抽出（改行とカンマの両方に対応）
    ingredient_list = []
    for separator in ['\n', ',', '、']:
        if separator in ingredients:
            ingredient_list.extend([ing.strip() for ing in ingredients.split(separator) if ing.strip()])
            break
    else:
        ingredient_list = [ingredients.strip()]
    
    # アレルギー成分との照合（正規化版）
    for allergy in allergies:
        allergy_normalized = normalize_ingredient_name(allergy)
        
        for ingredient in ingredient_list:
            ingredient_normalized = normalize_ingredient_name(ingredient)
            
            # 完全一致チェック
            if allergy_normalized == ingredient_normalized:
                return True, allergy
            
            # 部分一致チェック（より厳密）
            if (allergy_normalized in ingredient_normalized or 
                ingredient_normalized in allergy_normalized):
                return True, allergy
    
    return False, ""

def check_drug_interactions(candidate: Dict, user_info: Dict) -> Tuple[bool, List[str]]:
    """
    薬物相互作用チェックを実行（強化版）
    
    Args:
        candidate: 候補医薬品の情報
        user_info: ユーザー情報
    
    Returns:
        (has_interaction: bool, interaction_warnings: List[str])
    """
    ingredients = candidate.get('ingredients', '')
    current_medications = user_info.get('current_medications', [])
    
    if not ingredients or not current_medications:
        return False, []
    
    # 相互作用データを読み込み
    interactions_df = load_interactions_data()
    if interactions_df.empty:
        return False, []
    
    warnings = []
    candidate_ingredients = [ing.strip() for ing in ingredients.split('\n') if ing.strip()]
    
    # 現在服用中の薬との相互作用をチェック（正規化版）
    for medication in current_medications:
        medication_normalized = normalize_ingredient_name(medication)
        
        for candidate_ingredient in candidate_ingredients:
            candidate_normalized = normalize_ingredient_name(candidate_ingredient)
            
            matching_rows = interactions_df[
                (interactions_df['成分A'].str.contains(candidate_normalized, na=False, case=False) |
                 interactions_df['成分B'].str.contains(candidate_normalized, na=False, case=False)) &
                (interactions_df['成分A'].str.contains(medication_normalized, na=False, case=False) |
                 interactions_df['成分B'].str.contains(medication_normalized, na=False, case=False))
            ]
            
            for _, row in matching_rows.iterrows():
                interaction_level = row.get('相互作用レベル', '')
                description = row.get('説明', '')
                
                # リスクレベルに応じた警告メッセージ
                if interaction_level == '高':
                    warning_msg = f"🚨 禁忌レベル: {candidate_ingredient}と{medication}の併用は避けてください。{description}"
                elif interaction_level == '中':
                    warning_msg = f"⚠️ 注意レベル: {candidate_ingredient}と{medication}の併用時は医師に相談してください。{description}"
                else:
                    warning_msg = f"ℹ️ 情報レベル: {candidate_ingredient}と{medication}について。{description}"
                
                warnings.append(warning_msg)
    
    return len(warnings) > 0, warnings

def _contains_ingredient(ingredients_text: str, ingredient_keywords: List[str]) -> bool:
    """
    成分テキストに指定された成分が含まれているかチェック
    
    Args:
        ingredients_text: 成分テキスト
        ingredient_keywords: 検索する成分キーワードのリスト
    
    Returns:
        含まれている場合True
    """
    if not ingredients_text:
        return False
    
    ingredients_lower = str(ingredients_text).lower()
    for keyword in ingredient_keywords:
        if keyword.lower() in ingredients_lower:
            return True
    return False

def _is_kampo_or_herbal_medicine(candidate: Dict) -> bool:
    """
    漢方薬または生薬製剤かどうかを判定
    
    Args:
        candidate: 候補医薬品の情報
    
    Returns:
        漢方薬または生薬製剤の場合True
    """
    product_name = str(candidate.get('product_name', '')).lower()
    ingredients = str(candidate.get('ingredients', '')).lower()
    medicine_type = str(candidate.get('medicine_type', '')).lower()
    
    # 漢方・生薬のキーワード（拡張版）
    kampo_keywords = ["漢方", "生薬", "エキス", "湯", "散", "丸", "膏", "桂枝", "茯苓", "釣藤", "葛根",
                     "カッコン", "カンゾウ", "ケイヒ", "タイソウ", "ショウキョウ", "シャクヤク", "マオウ"]
    
    # 製品名または医薬品の種類に漢方のキーワードが含まれているか
    if any(kw in product_name or kw in medicine_type for kw in kampo_keywords):
        return True
    
    # 成分に生薬エキスが含まれているか
    herbal_keywords = ["エキス", "乾燥エキス", "エキス末", "エキス顆粒"]
    if any(kw in ingredients for kw in herbal_keywords):
        return True
    
    return False

def _is_goreisan(candidate: Dict) -> bool:
    """
    五苓散かどうかを判定
    
    Args:
        candidate: 候補医薬品の情報
    
    Returns:
        五苓散の場合True
    """
    product_name = str(candidate.get('product_name', '')).lower()
    ingredients = str(candidate.get('ingredients', '')).lower()
    
    return "五苓散" in product_name or "五苓散" in ingredients

def _contains_l_cysteine(candidate: Dict) -> bool:
    """
    L-システインを含む医薬品かどうかを判定
    
    Args:
        candidate: 候補医薬品の情報
    
    Returns:
        L-システインを含む場合True
    """
    ingredients = str(candidate.get('ingredients', '')).lower()
    
    return "l-システイン" in ingredients or "システイン" in ingredients

def _is_herbal_stomach_medicine(candidate: Dict) -> bool:
    """
    生薬配合の胃腸薬かどうかを判定
    
    Args:
        candidate: 候補医薬品の情報
    
    Returns:
        生薬配合の胃腸薬の場合True
    """
    medicine_type = str(candidate.get('medicine_type', '')).lower()
    ingredients = str(candidate.get('ingredients', '')).lower()
    
    if '胃腸薬' not in medicine_type:
        return False
    
    # 生薬成分のキーワード
    herbal_ingredients = ["ショウキョウ", "オウバク", "サンショウ", "カンゾウ", "ケイヒ", "ニンジン", "ブクリョウ"]
    return any(herb.lower() in ingredients for herb in herbal_ingredients)

def _parse_kampo_efficacy(efficacy_text: str) -> Dict[str, Any]:
    """
    漢方薬の効能効果を解析（柔軟性向上版）
    証の条件、主要適応症状、条件付き症状を抽出
    
    Args:
        efficacy_text: 効能効果テキスト
    
    Returns:
        {
            "has_sho_condition": bool,  # 証の条件があるか
            "sho_condition": str,      # 証の条件テキスト
            "primary_symptoms": List[str],  # 主要適応症状
            "conditional_symptoms": List[str],  # 条件付き症状（例：「高血圧に伴う随伴症状」）
            "is_conditional": bool,  # 条件付きの効能かどうか
            "is_robust_type": bool,  # 実証向け（体力充実）か
            "requires_constipation": bool  # 便秘が前提か
        }
    """
    result = {
        "has_sho_condition": False,
        "sho_condition": "",
        "primary_symptoms": [],
        "conditional_symptoms": [],
        "is_conditional": False,
        "is_robust_type": False,
        "requires_constipation": False,
        "age_restriction": None  # "middle_aged_or_older", "elderly", "young", None
    }
    
    if not efficacy_text:
        return result
    
    # 1. 証（Sho）の抽出
    # パターンを拡張し、句読点までの長さを制限して誤爆を防ぐ
    sho_patterns = [
        r'^体力[^、。]{2,20}[、。][^。]*もの',
        r'^比較的体力[^、。]{2,20}[、。][^。]*もの',
        r'^虚弱体質[^、。]*もの',
        r'^胃腸[^、。]*もの',
    ]
    
    for pattern in sho_patterns:
        match = re.search(pattern, efficacy_text)
        if match:
            result["has_sho_condition"] = True
            result["sho_condition"] = match.group(0)
            
            # 実証（体力充実）判定
            if "充実" in result["sho_condition"] or "比較的体力があり" in result["sho_condition"]:
                result["is_robust_type"] = True
            # 便秘前提判定
            if "便秘" in result["sho_condition"]:
                result["requires_constipation"] = True
            break
    
    # 2. 主要適応症状の抽出（フォールバック付き）
    symptoms_source = ""
    
    # パターンA: 明示的な区切りがある場合
    split_keywords = [r'次の諸症[：:]', r'次の症状[：:]', r'に伴う次の諸症', r'適応症']
    for kw in split_keywords:
        parts = re.split(kw, efficacy_text)
        if len(parts) > 1:
            symptoms_source = parts[-1]
            break
    
    # パターンB: 区切りがない場合、「証」の部分を除去した残りを症状とする
    if not symptoms_source and result["has_sho_condition"]:
        symptoms_source = efficacy_text.replace(result["sho_condition"], "")
        # 先頭の「の」「、」などを掃除
        symptoms_source = re.sub(r'^[の、,：\s]+', '', symptoms_source)
    
    # 症状テキストをリスト化
    if symptoms_source:
        # カッコ書き（例：「...痛み（...を除く）」）の処理などは簡易的に無視
        clean_text = re.sub(r'（[^）]*）', '', symptoms_source)
        # 区切り文字で分割
        symptoms = re.split(r'[、,，。]', clean_text)
        result["primary_symptoms"] = [s.strip() for s in symptoms if s.strip()]
    
    # 3. 条件付き症状（原因）の抽出
    # 「高血圧に伴う」「更年期障害による」など
    conditional_patterns = [
        r'([^、。]+)に伴う',
        r'([^、。]+)による',
    ]
    for pattern in conditional_patterns:
        matches = re.findall(pattern, efficacy_text)
        if matches:
            result["is_conditional"] = True
            # 「～の～」などの修飾語を掃除してシンプルにする処理を入れるとベター
            result["conditional_symptoms"].extend(matches)
    
    # 4. 年齢条件の検出
    age_patterns = [
        (r'中年以降', "middle_aged_or_older"),
        (r'中年', "middle_aged_or_older"),
        (r'高齢', "elderly"),
        (r'若年', "young"),
        (r'(\d+)歳以上', "age_min"),  # 将来の拡張用
        (r'(\d+)歳未満', "age_max"),  # 将来の拡張用
    ]
    
    for pattern, restriction_type in age_patterns:
        match = re.search(pattern, efficacy_text)
        if match:
            if restriction_type in ["middle_aged_or_older", "elderly", "young"]:
                result["age_restriction"] = restriction_type
            # 数値パターンの場合は将来の拡張用（今回は実装しない）
            break
    
    # 補完的な年齢条件の検出（「高血圧の傾向のあるもの」なども中年以降の可能性が高い）
    if result["age_restriction"] is None:
        # 釣藤散など、「高血圧の傾向」や「慢性頭痛で中年以降」のような表現を検出
        if "高血圧の傾向" in efficacy_text and "慢性" in efficacy_text:
            # 慢性頭痛で高血圧の傾向があるものは、実質的に中年以降向け
            result["age_restriction"] = "middle_aged_or_older"
    
    return result

def _check_kampo_symptom_match(candidate: Dict, symptom_names: List[str], user_info: Dict) -> Tuple[bool, float]:
    """
    漢方薬の適合性判定（胃腸虚弱チェック追加版）
    証の条件と適応症状を考慮して、適切な使用かどうかを判定
    
    Args:
        candidate: 候補医薬品
        symptom_names: ユーザーの症状名リスト
        user_info: ユーザー情報
    
    Returns:
        (is_appropriate: bool, penalty: float)
        is_appropriate: 適切な使用かどうか
        penalty: ペナルティ値（0.0-1.0、不適切な場合は正の値）
    """
    efficacy = str(candidate.get('efficacy', ''))
    if not efficacy:
        return True, 0.0
    
    # 漢方薬でない場合はスキップ
    if not _is_kampo_or_herbal_medicine(candidate):
        return True, 0.0
    
    parsed = _parse_kampo_efficacy(efficacy)
    user_symptoms_str = " ".join(symptom_names)
    user_age = user_info.get('age')
    
    # --- 年齢条件のチェック ---
    if user_age is not None and parsed.get("age_restriction"):
        age_restriction = parsed["age_restriction"]
        # 40歳未満のユーザーに対して「中年以降」向け漢方にペナルティ
        if age_restriction == "middle_aged_or_older" and user_age < 40:
            return False, 0.35  # 若年層への中年向け漢方のペナルティ（0.25から0.35に強化）
        # 将来の拡張: 65歳以上のユーザーに対して「若年」向け漢方にペナルティ
        # if age_restriction == "young" and user_age >= 65:
        #     return False, 0.25
    
    # --- 安全装置: 胃腸虚弱ユーザーへの実証薬チェック ---
    # ユーザーが「胃が弱い」「下痢」などを訴えている場合
    weak_stomach_keywords = ["胃が弱", "胃腸が弱", "下痢", "軟便", "食欲不振"]
    is_user_weak_stomach = any(kw in user_symptoms_str for kw in weak_stomach_keywords)
    
    if is_user_weak_stomach:
        # 「体力充実」「便秘しがち（＝瀉下作用あり）」な薬は危険
        if parsed["is_robust_type"] or parsed["requires_constipation"] or "桃核承気湯" in candidate.get('product_name', ''):
            return False, 0.5  # 強いペナルティ（使用非推奨レベル）
    
    # --- 証・随伴症状のマッチング ---
    if parsed["has_sho_condition"]:
        # A. 必須条件（便秘）のチェック
        if parsed["requires_constipation"] and "便秘" not in user_symptoms_str:
            return False, 0.3  # 便秘がないのに便秘向け漢方は不適切
        
        # B. 主要適応症状のマッチング
        if parsed["primary_symptoms"]:
            # 症状リストのいずれかが、主要症状に含まれているか（部分一致許容）
            # 例: User「肩こり」 vs Primary「肩こり、頭痛」 -> OK
            has_match = any(
                any(ps in us or us in ps for ps in parsed["primary_symptoms"])
                for us in symptom_names
            )
            
            if not has_match:
                # 全くかすっていない場合
                return False, 0.3
        
        # C. 条件付き症状（高血圧など）のチェック
        if parsed["is_conditional"]:
            # 条件（原因）がユーザー入力にあるか、または主症状がマッチしているか
            # 通常、OTCでは原因（高血圧）まで入力しないことも多いので、
            # 「主症状がマッチしていれば条件は不問」とするのが現実的かもしれません。
            # ここでは「主症状も条件もマッチしない」場合のみペナルティとします。
            
            has_condition_match = any(
                any(cs in us or us in cs for cs in parsed["conditional_symptoms"])
                for us in symptom_names
            )
            
            # 主症状マッチ判定（上記Bの結果を利用、なければ再計算）
            has_match = any(
                any(ps in us or us in ps for ps in parsed["primary_symptoms"])
                for us in symptom_names
            ) if parsed["primary_symptoms"] else False
            
            # 条件も主症状も一致しないなら不適切
            if not has_match and not has_condition_match:
                return False, 0.4
    
    return True, 0.0

def calculate_inappropriate_kampo_penalty(candidate: Dict, symptom_names: List[str], user_info: Dict) -> float:
    """
    不適切な漢方薬の使用に対するペナルティを計算
    
    Args:
        candidate: 候補医薬品
        symptom_names: ユーザーの症状名リスト
        user_info: ユーザー情報
    
    Returns:
        ペナルティ値（0.0-1.0、負の値として使用）
    """
    product_name = str(candidate.get('product_name', ''))
    efficacy = str(candidate.get('efficacy', ''))
    
    # 特定の漢方薬に対する特別なルール（kanpo_medicine.csvより統合）
    inappropriate_kampo_rules = {
        # --- 風邪・呼吸器系 ---
        "葛根湯": {
            "primary_symptoms": ["感冒の初期", "鼻かぜ", "鼻炎", "頭痛", "肩こり", "筋肉痛", "手や肩の痛み"],
            "inappropriate_symptoms": ["発汗", "著しい虚弱", "体力が弱い"],  # 「汗をかいていないもの」という規定に反するため
            "penalty": 0.3
        },
        "麻黄湯": {
            "primary_symptoms": ["感冒", "鼻かぜ", "気管支炎", "鼻づまり"],
            "inappropriate_symptoms": ["発汗", "虚弱体質", "微熱"],  # 「体力充実」「汗が出ていない」規定に反するため
            "penalty": 0.4
        },
        "小青竜湯": {
            "primary_symptoms": ["気管支炎", "気管支ぜんそく", "鼻炎", "アレルギー性鼻炎", "むくみ", "感冒", "花粉症"],
            "inappropriate_symptoms": ["黄色い痰", "濃い鼻汁"],  # 「うすい水様のたん」という規定に反するため（熱証には不適）
            "penalty": 0.3
        },
        "麦門冬湯": {
            "primary_symptoms": ["からぜき", "気管支炎", "気管支ぜんそく", "咽頭炎", "しわがれ声"],
            "inappropriate_symptoms": ["多量の痰", "水っぽい鼻水"],  # 乾燥感（燥証）に対応する薬のため湿証には不適
            "penalty": 0.2
        },
        "五虎湯": {
            "primary_symptoms": ["せき", "気管支ぜんそく", "気管支炎", "小児ぜんそく", "感冒", "痔の痛み"],
            "inappropriate_symptoms": ["虚弱体質", "湿性の咳"],
            "penalty": 0.3
        },
        "参蘇飲": {
            "primary_symptoms": ["感冒", "せき"],
            "inappropriate_symptoms": ["体力充実", "高熱"],
            "penalty": 0.2
        },
        
        # --- 消化器系 ---
        "安中散": {
            "primary_symptoms": ["神経性胃炎", "慢性胃炎", "胃腸虚弱"],
            "inappropriate_symptoms": ["胃熱", "炎症性の激しい痛み"],
            "penalty": 0.2
        },
        "六君子湯": {
            "primary_symptoms": ["胃炎", "胃腸虚弱", "胃下垂", "消化不良", "食欲不振", "胃痛", "嘔吐"],
            "inappropriate_symptoms": ["体力充実", "のぼせ"],
            "penalty": 0.2
        },
        "半夏瀉心湯": {
            "primary_symptoms": ["急・慢性胃腸炎", "下痢・軟便", "消化不良", "胃下垂", "神経性胃炎", "胃弱", "二日酔", "げっぷ", "胸やけ", "口内炎", "神経症"],
            "inappropriate_symptoms": ["便秘", "腹痛（冷えによるもの）"],
            "penalty": 0.3
        },
        "大建中湯": {
            "primary_symptoms": ["下腹部痛", "腹部膨満感"],
            "inappropriate_symptoms": ["発熱", "炎症性の腹痛", "暑がり"],
            "penalty": 0.3
        },
        "平胃散": {
            "primary_symptoms": ["食べ過ぎによる胃のもたれ", "急・慢性胃炎", "消化不良", "食欲不振"],
            "inappropriate_symptoms": ["著しい虚弱", "空腹時の胃痛"],
            "penalty": 0.2
        },
        "五苓散": {
            "primary_symptoms": ["水様性下痢", "急性胃腸炎", "暑気あたり", "頭痛", "むくみ", "二日酔"],
            "inappropriate_symptoms": ["しぶり腹", "尿量が多い"],  # 文中で明確に「しぶり腹のものには使用しないこと」とあるため
            "penalty": 0.5
        },
        
        # --- 婦人科・血の道症 ---
        "当帰芍薬散": {
            "primary_symptoms": ["月経不順", "月経異常", "月経痛", "更年期障害", "産前産後あるいは流産による障害", "めまい・立ちくらみ", "頭重", "肩こり", "腰痛", "足腰の冷え症", "しもやけ", "むくみ", "しみ", "耳鳴り"],
            "inappropriate_symptoms": ["胃腸虚弱（著しい）", "のぼせ"],
            "penalty": 0.2
        },
        "加味逍遙散": {
            "primary_symptoms": ["冷え症", "虚弱体質", "月経不順", "月経困難", "更年期障害", "血の道症", "不眠症"],
            "inappropriate_symptoms": ["無気力（うつ状態）", "著しい冷え"],
            "penalty": 0.2
        },
        "桂枝茯苓丸": {
            "primary_symptoms": ["月経不順", "月経異常", "月経痛", "更年期障害", "血の道症", "肩こり", "めまい", "頭重", "打ち身", "しもやけ", "しみ", "湿疹・皮膚炎", "にきび"],
            "inappropriate_symptoms": ["著しい虚弱", "出血傾向"],
            "penalty": 0.3
        },
        "桃核承気湯": {
            "primary_symptoms": ["月経不順", "月経困難症", "月経痛", "月経時や産後の精神不安", "腰痛", "便秘", "高血圧の随伴症状", "痔疾", "打撲症"],
            "inappropriate_symptoms": ["下痢", "胃腸虚弱", "体力がない", "肩こり", "筋肉痛"],  # 単独では不適切
            "penalty": 0.3
        },
        "当帰四逆加呉茱萸生姜湯": {
            "required_symptoms": ["冷え", "手足", "しもやけ", "冷え性", "手足の冷え", "下肢の冷え"],  # 必須症状
            "primary_symptoms": ["冷え症", "しもやけ", "頭痛", "下腹部痛", "腰痛", "下痢", "月経痛"],
            "inappropriate_symptoms": ["頭痛", "のぼせ", "ほてり"],  # 単独では不適切（冷え性の症状がない場合）
            "penalty": 0.4  # 強いペナルティ（一般的な頭痛には不適切）
        },
        
        # --- 精神・神経系 ---
        "半夏厚朴湯": {
            "primary_symptoms": ["不安神経症", "神経性胃炎", "つわり", "せき", "しわがれ声", "のどのつかえ感"],
            "inappropriate_symptoms": ["高熱", "脱水"],
            "penalty": 0.2
        },
        "抑肝散": {
            "primary_symptoms": ["神経症", "不眠症", "小児夜泣き", "小児疳症", "歯ぎしり", "更年期障害", "血の道症"],
            "inappropriate_symptoms": ["無気力", "抑うつ"],
            "penalty": 0.3
        },
        "柴胡加竜骨牡蛎湯": {
            "primary_symptoms": ["高血圧の随伴症状", "神経症", "更年期神経症", "小児夜泣き", "便秘"],
            "inappropriate_symptoms": ["下痢", "虚弱体質"],  # 便秘などを伴うとあるため下痢は不適
            "penalty": 0.3
        },
        "酸棗仁湯": {
            "primary_symptoms": ["不眠症", "神経症"],
            "inappropriate_symptoms": ["体力充実", "日中の眠気"],
            "penalty": 0.2
        },
        "釣藤散": {
            "primary_symptoms": ["慢性頭痛", "神経症", "高血圧の傾向のあるもの"],
            "inappropriate_symptoms": ["急性頭痛", "冷えによる頭痛"],  # 「慢性に経過する」とあるため
            "age_restriction": "middle_aged_or_older",  # 中年以降向け
            "inappropriate_for_young": True,  # 若年層には不適切
            "penalty": 0.35  # 若年層（40歳未満）へのペナルティ
        },
        
        # --- 痛み・こむらがえり・泌尿器 ---
        "芍薬甘草湯": {
            "primary_symptoms": ["こむらがえり", "筋肉のけいれん", "腹痛", "腰痛"],
            "inappropriate_symptoms": ["慢性の鈍痛", "むくみ"],  # 甘草による副作用リスク考慮（長期連用不適）
            "penalty": 0.5
        },
        "八味地黄丸": {
            "primary_symptoms": ["下肢痛", "腰痛", "しびれ", "高齢者のかすみ目", "かゆみ", "排尿困難", "残尿感", "夜間尿", "頻尿", "むくみ", "高血圧に伴う随伴症状", "軽い尿漏れ"],
            "inappropriate_symptoms": ["胃腸虚弱", "下痢", "のぼせ"],  # 地黄を含むため胃腸障害に注意
            "penalty": 0.3
        },
        "牛車腎気丸": {
            "primary_symptoms": ["下肢痛", "腰痛", "しびれ", "高齢者のかすみ目", "かゆみ", "排尿困難", "頻尿", "むくみ", "高血圧に伴う随伴症状"],
            "inappropriate_symptoms": ["胃腸虚弱", "下痢"],
            "penalty": 0.3
        },
        "猪苓湯": {
            "primary_symptoms": ["排尿困難", "排尿痛", "残尿感", "頻尿", "むくみ"],
            "inappropriate_symptoms": ["尿量過多"],
            "penalty": 0.2
        },
        "疎経活血湯": {
            "primary_symptoms": ["関節痛", "神経痛", "腰痛", "筋肉痛"],
            "inappropriate_symptoms": ["胃腸虚弱", "食欲不振"],
            "penalty": 0.3
        },
        
        # --- 皮膚 ---
        "十味敗毒湯": {
            "primary_symptoms": ["化膿性皮膚疾患", "急性皮膚疾患の初期", "じんましん", "湿疹・皮膚炎", "水虫"],
            "inappropriate_symptoms": ["陰性の皮膚疾患", "慢性化膿症"],
            "penalty": 0.2
        },
        "防風通聖散": {
            "primary_symptoms": ["高血圧や肥満に伴う動悸・肩こり・のぼせ・むくみ・便秘", "蓄膿症", "湿疹・皮膚炎", "ふきでもの", "肥満症"],
            "inappropriate_symptoms": ["下痢", "胃腸虚弱", "体力虚弱"],
            "penalty": 0.4
        },
        "黄連解毒湯": {
            "primary_symptoms": ["鼻出血", "不眠症", "神経症", "胃炎", "二日酔", "血の道症", "めまい", "動悸", "更年期障害", "湿疹・皮膚炎", "皮膚のかゆみ", "口内炎"],
            "inappropriate_symptoms": ["冷え症", "低血圧", "虚弱体質"],
            "penalty": 0.3
        },
        "消風散": {
            "primary_symptoms": ["湿疹・皮膚炎", "じんましん", "水虫", "あせも"],
            "inappropriate_symptoms": ["乾燥性の皮膚疾患", "分泌物が少ない"],
            "penalty": 0.2
        },
        
        # --- その他（疲労・全身） ---
        "補中益気湯": {
            "primary_symptoms": ["虚弱体質", "疲労倦怠", "病後・術後の衰弱", "食欲不振", "ねあせ", "感冒"],
            "inappropriate_symptoms": ["発熱（高熱）", "体力充実"],
            "penalty": 0.2
        },
        "十全大補湯": {
            "primary_symptoms": ["病後・術後の体力低下", "疲労倦怠", "食欲不振", "ねあせ", "手足の冷え", "貧血"],
            "inappropriate_symptoms": ["胃腸虚弱（著しい）", "高血圧"],  # 地黄などを含むため
            "penalty": 0.3
        },
        "人参養栄湯": {
            "primary_symptoms": ["病後・術後などの体力低下", "疲労倦怠", "食欲不振", "ねあせ", "手足の冷え", "貧血"],
            "inappropriate_symptoms": ["消化不良", "のぼせ"],
            "penalty": 0.3
        }
    }
    
    # 漢方薬名をチェック
    for kampo_name, rule in inappropriate_kampo_rules.items():
        if kampo_name in product_name:
            # 当帰四逆加呉茱萸生姜湯の特別処理
            if kampo_name == "当帰四逆加呉茱萸生姜湯":
                # 必須症状（冷え、手足、しもやけなど）があるか確認
                user_symptoms_str = " ".join(symptom_names)
                has_required = any(
                    rs in user_symptoms_str for rs in rule.get("required_symptoms", [])
                )
                
                # 必須症状がない場合、不適切な症状（頭痛のみ）がある場合はペナルティ
                if not has_required:
                    has_inappropriate = any(
                        ins in symptom_names for ins in rule.get("inappropriate_symptoms", [])
                    )
                    if has_inappropriate:
                        return rule["penalty"]
            # 釣藤散の特別処理（年齢ペナルティ）
            elif kampo_name == "釣藤散":
                user_age = user_info.get('age')
                if user_age is not None and user_age < 40:
                    # 40歳未満の若年層には不適切
                    if rule.get("inappropriate_for_young", False):
                        return rule["penalty"]
                # 急性頭痛には不適切（慢性頭痛向け）
                if "急性頭痛" in " ".join(symptom_names) or any("急性" in sn and "頭痛" in sn for sn in symptom_names):
                    if any(ins in " ".join(symptom_names) for ins in rule.get("inappropriate_symptoms", [])):
                        return rule["penalty"]
            else:
                # その他の漢方薬の処理
                # required_symptomsがある場合のチェック（当帰四逆加呉茱萸生姜湯と同様の処理）
                if rule.get("required_symptoms"):
                    user_symptoms_str = " ".join(symptom_names)
                    has_required = any(
                        rs in user_symptoms_str for rs in rule.get("required_symptoms", [])
                    )
                    
                    # 必須症状がない場合、不適切な症状がある場合はペナルティ
                    if not has_required:
                        has_inappropriate = any(
                            ins in user_symptoms_str for ins in rule.get("inappropriate_symptoms", [])
                        )
                        if has_inappropriate:
                            return rule["penalty"]
                else:
                    # primary_symptomsとinappropriate_symptomsの組み合わせチェック
                    has_primary = any(
                        any(ps in sn or sn in ps for ps in rule.get("primary_symptoms", []))
                        for sn in symptom_names
                    )
                    
                    # 不適切な症状のみの場合、または主要症状がない場合に不適切な症状がある場合
                    user_symptoms_str = " ".join(symptom_names)
                    has_inappropriate = any(
                        ins in user_symptoms_str for ins in rule.get("inappropriate_symptoms", [])
                    )
                    
                    if has_inappropriate and not has_primary:
                        return rule["penalty"]
    
    # 一般的な漢方薬の判定（証の条件を考慮）
    is_appropriate, penalty = _check_kampo_symptom_match(candidate, symptom_names, user_info)
    if not is_appropriate:
        return penalty
    
    return 0.0

def calculate_symptom_specific_boost(candidate: Dict, nlu_result: Dict, user_info: Dict) -> float:
    """
    症状に特化した医薬品にブーストを付与
    
    Args:
        candidate: 候補医薬品の情報
        nlu_result: NLU解析結果
        user_info: ユーザー情報
    
    Returns:
        ブーストスコア（0.0-1.0の範囲）
    """
    product_name = str(candidate.get('product_name', ''))
    efficacy = str(candidate.get('efficacy', ''))
    medicine_type = str(candidate.get('medicine_type', ''))
    ingredients = str(candidate.get('ingredients', ''))
    target_text = (product_name + efficacy).lower()
    
    symptoms = nlu_result.get("symptoms", [])
    symptom_names = [s.get("name", "") for s in symptoms]
    gender = user_info.get('gender', '')
    
    boost = 0.0
    
    # 喉の痛み特化医薬品（ブースト強化、部分一致も含める）
    if "のどの痛み" in symptom_names:
        throat_specific_keywords = ["ベンザブロック", "ルルアタック", "トラネキサム"]
        # 部分一致も検出（例: "ベンザブロックL" や "ルルアタックEX" など）
        product_name_upper = product_name.upper()
        product_name_normalized = normalize_text(product_name)
        
        # キーワードが製品名に含まれているかチェック（大文字小文字を無視、部分一致）
        for keyword in throat_specific_keywords:
            keyword_normalized = normalize_text(keyword)
            if keyword_normalized in product_name_normalized or keyword.upper() in product_name_upper:
                boost += 0.35  # 0.30から0.35に微調整
                break
        
        # 効能効果に「のどの痛み」が含まれ、かつ製品名に「のど」「喉」が含まれる場合もブースト
        if boost == 0.0:  # まだブーストが適用されていない場合
            efficacy_normalized = normalize_text(efficacy)
            if "のど" in efficacy_normalized or "喉" in efficacy_normalized:
                if "のど" in product_name_normalized or "喉" in product_name_normalized:
                    boost += 0.20  # 0.15から0.20に強化
    
    # 頭痛のみの場合 → 風邪薬にペナルティ、即効性のあるNSAIDsにブースト（重大な改善点）
    # 頭痛のみで他の風邪症状（発熱、のどの痛み、咳、鼻水、鼻づまり、くしゃみ）がない場合
    cold_symptoms = ["発熱", "のどの痛み", "咳", "鼻水", "鼻づまり", "くしゃみ", "悪寒"]
    has_only_headache = "頭痛" in symptom_names and not any(s in symptom_names for s in cold_symptoms)
    
    if has_only_headache:
        # 風邪薬にペナルティを付与（不要な成分による副作用リスクを回避）
        # 製品名に「かぜ」「風邪」が含まれる場合もペナルティ
        if "風邪薬" in medicine_type or "かぜ" in product_name or "風邪" in product_name:
            boost -= 0.50  # 風邪薬への強力なペナルティ（0.35から0.50に強化）
        
        # 即効性のあるNSAIDs成分が含まれる製品に大きなブースト
        fast_acting_nsaids = [
            "アセトアミノフェン", "パラセタモール", "タイレノール",
            "イブプロフェン", "イブ", "ブルフェン",
            "ロキソプロフェン", "ロキソニン"
        ]
        if _contains_ingredient(ingredients, fast_acting_nsaids):
            boost += 0.40  # 即効性のあるNSAIDsへの大幅ブースト
        
        # 漢方・生薬製剤はユーザーが希望しない限り優先度を下げる
        if _is_kampo_or_herbal_medicine(candidate):
            # 漢方希望のフラグがない場合はペナルティ
            if not user_info.get('prefers_kampo', False):
                boost -= 0.25  # 漢方薬へのペナルティ（急性頭痛には即効性が重要）
        
        # 解熱鎮痛薬にブーストを付与（成分によるブーストがない場合）
        elif "解熱鎮痛薬" in medicine_type:
            boost += 0.15  # 解熱鎮痛薬への基本ブースト（成分ブーストがない場合）
    
    # 女性の頭痛 → 胃に優しい医薬品（ブースト強化）
    if "頭痛" in symptom_names and gender == "女性":
        stomach_friendly_keywords = ["イブクイック", "バファリン", "酸化マグネシウム"]
        if any(kw in target_text for kw in stomach_friendly_keywords):
            boost += 0.25  # 0.20から0.25に微調整
    
    # 肩こり → 外用薬（テープ・パップ）（成分ランク付けによるブースト）
    if "肩こり" in symptom_names or "筋肉痛" in symptom_names:
        if "外用" in medicine_type:
            # 最適解の製品名を優先（製品名による判定を最初に行う）
            optimal_topical_keywords = ["フェイタス", "バンテリン", "サロンパス"]
            product_name_normalized = normalize_text(product_name)
            found_optimal_by_name = False
            
            for keyword in optimal_topical_keywords:
                keyword_normalized = normalize_text(keyword)
                if keyword_normalized in product_name_normalized or keyword in product_name:
                    boost += 0.70  # 最適解への大幅ブースト（0.50から0.70に強化）
                    found_optimal_by_name = True
                    break
            
            # 製品名による判定がない場合、成分による判定を行う
            if not found_optimal_by_name:
                # 第2世代鎮痛成分（高ランク）: フェルビナク、インドメタシン、ジクロフェナク
                second_gen_analgesics = [
                    "フェルビナク", "フェルビナクナトリウム", "フェルビナクナトリウム水和物",
                    "インドメタシン", "インダシン", "インドメタシン水和物",
                    "ジクロフェナク", "ジクロフェナクナトリウム", "ボルタレン", "ジクロフェナクナトリウム水和物"
                ]
                if _contains_ingredient(ingredients, second_gen_analgesics):
                    boost += 0.45  # 第2世代鎮痛成分への高ランクボーナス
                
                # サリチル酸メチル（中ランク）: サロンパス等
                elif _contains_ingredient(ingredients, ["サリチル酸メチル", "サリチル酸グリコール"]):
                    boost += 0.30  # サリチル酸メチルへの中ランクボーナス
                
                # 生薬配合のみ（低ランク）: 中黄膏など
                elif _is_kampo_or_herbal_medicine(candidate):
                    boost += 0.10  # 生薬配合のみへの低ランクボーナス
                
                # その他の外用薬
                elif any(kw in product_name for kw in ["ロキソニン", "テープ", "パップ"]):
                    boost += 0.15  # その他の外用薬への基本ブースト
    
    # 乗り物酔い → 乗り物酔い薬（ブースト強化、最適解を優先）
    if "乗り物酔い" in symptom_names:
        # 最適解の乗り物酔い薬を優先（アネロン「ニスキャップ」）
        optimal_motion_sickness_keywords = ["アネロン", "ニスキャップ", "キャップ"]
        product_name_normalized = normalize_text(product_name)
        found_optimal = False
        
        for keyword in optimal_motion_sickness_keywords:
            keyword_normalized = normalize_text(keyword)
            if keyword_normalized in product_name_normalized or keyword in product_name:
                boost += 0.60  # 最適解への大幅ブースト（0.50から0.60に強化）
                found_optimal = True
                
                # 持続性（1日1回）や指定第2類医薬品のキーワードをチェック
                usage = str(candidate.get('usage', '')).lower()
                efficacy_lower = efficacy.lower()
                classification = str(candidate.get('classification', '')).lower()
                if any(kw in usage or kw in efficacy_lower or kw in classification for kw in ["1日1回", "1回", "持続", "長時間", "指定第2類", "第2類"]):
                    boost += 0.20  # 持続性・指定第2類への追加ブースト（0.15から0.20に強化）
                break
        
        # その他の乗り物酔い薬
        if not found_optimal:
            if any(kw in product_name for kw in ["ソラシドン", "センパア", "トリブラ", "トラベルミン"]):
                boost += 0.25  # その他の乗り物酔い薬へのブースト
    
    # 不適切な漢方のペナルティ（改善版）
    penalty = calculate_inappropriate_kampo_penalty(candidate, symptom_names, user_info)
    if penalty > 0:
        boost -= penalty
    
    # 大人（15歳以上）や年齢未入力の場合にシロップ系形状を推奨しないロジック
    user_age = user_info.get('age')
    if user_age is None or user_age >= 15:
        product_name_lower = product_name.lower()
        # シロップ系の形状を検出
        syrup_keywords = ["シロップ", "ドライシロップ"]
        has_syrup = any(kw in product_name_lower for kw in syrup_keywords)
        
        if has_syrup:
            # 小児向けキーワードが含まれていない場合（大人向けシロップ剤の可能性があるが、一般的には小児向け）
            pediatric_keywords_in_name = ["小児", "こども", "子供", "キッズ", "ジュニア", "ベビー"]
            has_pediatric_keyword = any(kw in product_name_lower for kw in pediatric_keywords_in_name)
            
            if not has_pediatric_keyword:
                # 大人向けシロップ剤の可能性もあるが、一般的には小児向けとして認識されるため軽めのペナルティ
                boost -= 0.20  # シロップ系形状へのペナルティ
    
    # 月経不順・生理痛向けの成分ブースト（新規追加）
    menstrual_symptoms = ["月経不順", "生理不順", "生理痛", "月経痛"]
    has_menstrual_symptom = any(symptom in symptom_names for symptom in menstrual_symptoms)
    
    if has_menstrual_symptom:
        ingredients_lower = ingredients.lower()
        product_name_lower = product_name.lower()
        efficacy_lower = efficacy.lower()
        
        # 当帰芍薬散を含む医薬品（最高優先度）
        if "当帰芍薬散" in product_name or "トウキシャクヤクサン" in product_name_lower or "当帰芍薬散" in efficacy:
            boost += 0.25
        else:
            # 当帰と芍薬の両方が含まれる場合（高優先度）
            has_toki = any(kw in ingredients_lower for kw in ["トウキ", "当帰", "とうき"])
            has_shakuyaku = any(kw in ingredients_lower for kw in ["シャクヤク", "芍薬", "しゃくやく"])
            
            if has_toki and has_shakuyaku:
                boost += 0.20
            # 当帰または芍薬単独（中優先度）
            elif has_toki or has_shakuyaku:
                boost += 0.10
        
        # 加味逍遙散（イライラ症状がある場合）
        if "イライラ" in symptom_names:
            if "加味逍遙散" in product_name or "カミショウヨウサン" in product_name_lower or "加味逍遙散" in efficacy:
                boost += 0.15
            # 命の母ホワイト
            if "命の母ホワイト" in product_name or "命の母" in product_name:
                boost += 0.15
        
        # 桂枝茯苓丸（ニキビ症状がある場合）
        if "ニキビ" in symptom_names:
            if "桂枝茯苓丸" in product_name or "ケイシブクリョウガン" in product_name_lower or "桂枝茯苓丸" in efficacy:
                boost += 0.15
            # 桃仁（トウニン）を含む場合
            if "トウニン" in ingredients_lower or "桃仁" in ingredients:
                boost += 0.10
    
    return boost


# ============================================================================
# 方言変換機能（グローバルリソース対応）
# ============================================================================

# グローバル変数（アプリ起動時に一度だけ構築）
GLOBAL_DIALECT_AUTOMATON = None
GLOBAL_DIALECT_INDEX = None
GLOBAL_RE_SCANNER = None


def initialize_dialect_resources():
    """
    方言変換用のリソースを初期化（アプリ起動時に一度だけ実行）
    オートマトン、インデックス、re.Scannerを構築してグローバル変数に保存
    """
    global GLOBAL_DIALECT_AUTOMATON, GLOBAL_DIALECT_INDEX, GLOBAL_RE_SCANNER
    
    try:
        from config.dialect_dictionary import DIALECT_DICTIONARY
        
        # Aho-Corasickオートマトンの構築
        if AHO_CORASICK_AVAILABLE:
            GLOBAL_DIALECT_AUTOMATON = build_aho_corasick_automaton(DIALECT_DICTIONARY)
            logger.info("✅ Aho-Corasickオートマトンの構築が完了しました。")
        else:
            logger.info("⚠️ pyahocorasickが利用できないため、Aho-Corasickオートマトンは構築しません。")
        
        # 方言インデックスの構築
        GLOBAL_DIALECT_INDEX = build_dialect_index(DIALECT_DICTIONARY)
        logger.info("✅ 方言インデックスの構築が完了しました。")
        
        # re.Scannerの構築
        GLOBAL_RE_SCANNER = build_re_scanner(DIALECT_DICTIONARY)
        logger.info("✅ re.Scannerの構築が完了しました。")
        
        logger.info("✅ 方言変換リソースの初期化が完了しました。")
    except Exception as e:
        logger.error(f"❌ 方言変換リソースの初期化エラー: {e}")
        import traceback
        traceback.print_exc()


def create_japanese_word_boundary_pattern(word: str, sentence_end_priority: bool = False, is_emphasis: bool = False, is_symptom: bool = False) -> str:
    """
    日本語の単語境界判定パターンを作成（否定の戻り読み・先読み＋カスタム判定）
    
    Args:
        word: 方言表現
        sentence_end_priority: 文末マッチングを優先するかどうか
        is_emphasis: 強調副詞かどうか（後ろに形容詞・動詞が続くことを許可）
        is_symptom: 症状関連の方言表現かどうか（前にも日本語文字が続くことを許可）
    
    Returns:
        正規表現パターン
    """
    escaped_word = re.escape(word)
    
    if sentence_end_priority:
        # 文末マッチングを優先（「ばい」「たい」など）
        # 文末パターンと通常パターンの両方を生成
        end_pattern = f"({escaped_word})$"
        normal_pattern = f"(?<![ぁ-んァ-ヶー一-龥]){escaped_word}(?![ぁ-んァ-ヶー一-龥])"
        return f"({end_pattern}|{normal_pattern})"
    else:
        # 通常の単語境界判定（否定の戻り読み・先読み）
        # 前後に日本語文字（ひらがな、カタカナ、漢字）がない場合にマッチ
        # ただし、強調副詞や症状関連の場合は前後にも日本語文字が続くことを許可
        if is_emphasis:
            # 強調副詞の場合：前後にも日本語文字が続くことを許可（「でら痛い」「めっちゃしんどい」「でらめっちゃ痛い」など）
            # ただし、「でらきん」のような誤変換を防ぐため、「きん」で始まる語は除外
            return f"{escaped_word}(?!きん)"
        elif is_symptom:
            # 症状関連の場合：前後にも日本語文字が続くことを許可（「今日はしんどい」「頭がえらい」など）
            return f"{escaped_word}"
        else:
            return f"(?<![ぁ-んァ-ヶー一-龥]){escaped_word}(?![ぁ-んァ-ヶー一-龥])"


def check_health_context(text: str, dialect_word: str, dialect_info: Dict) -> bool:
    """
    体調関連の文脈かどうかを判定
    
    Args:
        text: ユーザー入力テキスト
        dialect_word: 方言表現
        dialect_info: 方言情報（context_keywords, exclude_patternsを含む）
    
    Returns:
        True: 体調関連の文脈の場合（変換可能）
        False: 体調関連でない場合（変換しない）
    """
    # 除外パターンのチェック
    exclude_patterns = dialect_info.get("exclude_patterns", [])
    for pattern in exclude_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return False
    
    # 文脈キーワードのチェック
    context_keywords = dialect_info.get("context_keywords", [])
    if not context_keywords:
        # 文脈キーワードが定義されていない場合は変換可能
        return True
    
    # 体調関連キーワードが近くにあるかチェック（前後20文字以内）
    dialect_pos = text.find(dialect_word)
    if dialect_pos == -1:
        return False
    
    context_window = text[max(0, dialect_pos - 20):dialect_pos + len(dialect_word) + 20]
    
    for keyword in context_keywords:
        if keyword in context_window:
            return True
    
    return False


def build_aho_corasick_automaton(dialect_dictionary: Dict) -> Optional[Any]:
    """
    Aho-Corasickオートマトンを構築
    
    Args:
        dialect_dictionary: 方言辞書
    
    Returns:
        Aho-Corasickオートマトン（利用可能な場合）
    """
    if not AHO_CORASICK_AVAILABLE:
        return None
    
    automaton = ahocorasick.Automaton()
    
    for dialect_type, entries in dialect_dictionary.items():
        for dialect_word, info in entries.items():
            # 方言表現をキーとして追加
            automaton.add_word(dialect_word, (dialect_word, info, dialect_type))
    
    automaton.make_automaton()
    return automaton


def find_dialect_matches_aho_corasick(
    text: str,
    automaton: Any
) -> List[Tuple[int, int, Tuple]]:
    """
    Aho-Corasickアルゴリズムで方言表現を検出
    
    Args:
        text: 検索対象テキスト
        automaton: Aho-Corasickオートマトン
    
    Returns:
        マッチした方言表現のリスト（位置、長さ、情報）
    """
    if not automaton:
        return []
    
    matches = []
    for end_index, (dialect_word, info, dialect_type) in automaton.iter(text):
        start_index = end_index - len(dialect_word) + 1
        matches.append((start_index, end_index + 1, (dialect_word, info, dialect_type)))
    
    return matches


def build_dialect_index(dialect_dictionary: Dict) -> Dict[str, Set[str]]:
    """
    方言インデックスを構築（文字ベース＋N-gram）
    
    Args:
        dialect_dictionary: 方言辞書
    
    Returns:
        文字/N-gramから方言表現へのマッピング
    """
    index = {}
    
    for dialect_type, entries in dialect_dictionary.items():
        for dialect_word, info in entries.items():
            # 文字ベースのインデックス
            for char in dialect_word:
                if char not in index:
                    index[char] = set()
                index[char].add(dialect_word)
            
            # N-gramベースのインデックス（2-3文字）
            for n in [2, 3]:
                for i in range(len(dialect_word) - n + 1):
                    ngram = dialect_word[i:i+n]
                    if ngram not in index:
                        index[ngram] = set()
                    index[ngram].add(dialect_word)
    
    return index


def filter_dialects_by_index(
    text: str,
    dialect_index: Dict[str, Set[str]],
    dialect_dictionary: Dict
) -> List[Tuple[str, Dict, str]]:
    """
    方言インデックスを使用してマッチする可能性のある方言を絞り込み
    
    Args:
        text: ユーザー入力テキスト
        dialect_index: 方言インデックス
        dialect_dictionary: 方言辞書
    
    Returns:
        マッチする可能性のある方言のリスト
    """
    candidate_dialects = set()
    
    # テキスト内の文字/N-gramから候補を抽出
    for n in [1, 2, 3]:
        for i in range(len(text) - n + 1):
            ngram = text[i:i+n]
            if ngram in dialect_index:
                candidate_dialects.update(dialect_index[ngram])
    
    # 候補の方言表現を返す
    candidates = []
    for dialect_word in candidate_dialects:
        for dialect_type, entries in dialect_dictionary.items():
            if dialect_word in entries:
                candidates.append((dialect_word, entries[dialect_word], dialect_type))
                break
    
    return candidates


def build_re_scanner(dialect_dictionary: Dict) -> Any:
    """
    re.Scannerを構築（一括スキャン用）
    
    注意: re.ScannerはPython 3.11で非推奨となり、エラーが発生するため使用しない
    
    Args:
        dialect_dictionary: 方言辞書
    
    Returns:
        None（re.Scannerは非推奨のため使用しない）
    """
    # re.ScannerはPython 3.11で非推奨となり、エラーが発生するため使用しない
    # 代わりに通常の正規表現を使用
    logger.warning("⚠️ re.Scannerは非推奨のため使用しません。通常の正規表現を使用します。")
    return None


def scan_text_with_scanner(text: str, scanner: Any) -> List[Tuple[int, int, Tuple]]:
    """
    re.Scannerでテキストを一括スキャン
    
    Args:
        text: スキャン対象テキスト
        scanner: re.Scannerオブジェクト
    
    Returns:
        マッチした方言表現のリスト（位置、長さ、情報）
    """
    matches = []
    tokens, remainder = scanner.scan(text)
    
    current_pos = 0
    for token in tokens:
        if token is not None:
            dialect_word, info, dialect_type = token
            start_pos = text.find(dialect_word, current_pos)
            if start_pos != -1:
                end_pos = start_pos + len(dialect_word)
                matches.append((start_pos, end_pos, (dialect_word, info, dialect_type)))
                current_pos = end_pos
    
    return matches


def calculate_escalation_score(severity_tags: List[str]) -> float:
    """
    escalation_scoreを計算（重み付き加算）
    
    Args:
        severity_tags: 検出された重症度タグのリスト
    
    Returns:
        escalation_score
    """
    from config.dialect_dictionary import ESCALATION_SCORE_WEIGHTS
    
    total_score = 0.0
    for severity_tag in severity_tags:
        weight = ESCALATION_SCORE_WEIGHTS.get(severity_tag, 0.0)
        total_score += weight
    
    return total_score


def check_escalation_threshold(escalation_score: float) -> bool:
    """
    escalation_scoreが閾値を超えているかチェック
    
    Args:
        escalation_score: 計算されたescalation_score
    
    Returns:
        True: 閾値を超えている場合（受診勧奨）
    """
    from config.dialect_dictionary import ESCALATION_THRESHOLD
    
    return escalation_score >= ESCALATION_THRESHOLD


def get_max_severity(severity1: Optional[str], severity2: Optional[str]) -> Optional[str]:
    """
    2つの重症度タグのうち、より高い方を返す
    
    Args:
        severity1: 重症度タグ1
        severity2: 重症度タグ2
    
    Returns:
        より高い重症度タグ
    """
    from config.dialect_dictionary import SEVERITY_LEVELS
    
    level1 = SEVERITY_LEVELS.get(severity1, 0)
    level2 = SEVERITY_LEVELS.get(severity2, 0)
    
    if level1 >= level2:
        return severity1
    else:
        return severity2


def normalize_symptom_weights(
    dialect_word: str,
    dialect_info: Dict,
    original_weight: float = 1.0
) -> Dict[str, float]:
    """
    症状の重みを正規化（総症状エネルギー保存＋正規化）
    
    物理の「確率密度関数の正規化」と同様の保存則を適用：
    Σ(i=1 to n) w_i = W_original
    
    これにより、「にえる」を分解した結果、全体的な「痛みの強さ」の
    期待値が勝手に増幅されるバグを防ぐ。
    
    Args:
        dialect_word: 方言表現
        dialect_info: 方言情報
        original_weight: 元の重み（総症状エネルギー W_original）
    
    Returns:
        正規化された重みの辞書（Σw_i = W_original を満たす）
    """
    if not dialect_info.get("multiple_symptoms", False):
        # 複数症状対応でない場合はそのまま
        standard = dialect_info.get("standard", dialect_word)
        return {standard: original_weight}
    
    standard_tokens = dialect_info.get("standard_tokens", [])
    symptom_weights = dialect_info.get("symptom_weights", {})
    
    # 重み付き配分
    normalized_weights = {}
    total_weight = 0.0
    
    for token in standard_tokens:
        if token in symptom_weights:
            weight = symptom_weights[token]
        else:
            # デフォルトは均等配分
            weight = 1.0 / len(standard_tokens)
        
        normalized_weights[token] = weight
        total_weight += weight
    
    # 正規化（保存則：Σw_i = W_original）
    # 合計がoriginal_weightになるように正規化
    if total_weight > 0:
        for token in normalized_weights:
            # 各重みを正規化して、合計がoriginal_weightになるように調整
            normalized_weights[token] = (normalized_weights[token] / total_weight) * original_weight
    
    # 検証：保存則が満たされているか確認（デバッグ用）
    calculated_total = sum(normalized_weights.values())
    if abs(calculated_total - original_weight) > 0.001:  # 浮動小数点誤差を考慮
        logger.warning(
            f"重みの正規化で保存則が満たされていません: "
            f"original={original_weight}, calculated={calculated_total}"
        )
    
    return normalized_weights


def is_protected_word(word: str) -> bool:
    """
    保護すべき語かどうかを判定（2文字以上の名詞・症状語）
    
    Args:
        word: チェックする語
    
    Returns:
        True: 保護すべき語の場合
    """
    from config.dialect_dictionary import PROTECTED_WORDS
    
    # 2文字以上で、保護リストに含まれているか
    if len(word) >= 2 and word in PROTECTED_WORDS:
        return True
    
    # 症状語のパターンチェック（「痛」「熱」「咳」などが含まれる）
    symptom_keywords = ["痛", "熱", "咳", "下痢", "便秘", "吐", "かゆ", "だる", "疲"]
    if any(keyword in word for keyword in symptom_keywords) and len(word) >= 2:
        return True
    
    return False


def convert_dialect_to_standard(
    text: str,
    extract_severity: bool = False,
    non_destructive: bool = True,
    use_aho_corasick: bool = True,
    use_index: bool = True,
    use_scanner: bool = True
) -> Tuple[str, Optional[str], float, Dict[str, List[str]], Dict[str, float]]:
    """
    方言表現を標準語に変換（最終版：パフォーマンス最適化対応）
    
    Args:
        text: 変換前のテキスト
        extract_severity: 強調副詞の重症度タグを抽出するかどうか
        non_destructive: 非破壊的変換を使用するかどうか
        use_aho_corasick: Aho-Corasickアルゴリズムを使用するかどうか
        use_index: 方言インデックスを使用するかどうか
        use_scanner: re.Scannerを使用するかどうか
    
    Returns:
        (変換後のテキスト, 重症度タグ, escalation_score, 非破壊的変換の候補辞書, 正規化された重み)
    """
    # エラーハンドリング：無効な入力のチェック
    if text is None:
        return None, None, 0.0, {}, {}
    if not isinstance(text, str):
        if DEBUG_MODE:
            logger.debug(f"無効な入力: {type(text)}")
        # 数値やその他の型は文字列に変換
        return str(text), None, 0.0, {}, {}
    if not text:
        return "", None, 0.0, {}, {}
    
    try:
        from config.dialect_dictionary import (
            DIALECT_DICTIONARY,
            CONVERSION_EXCLUSION_LIST,
            SEVERITY_LEVELS
        )
    except ImportError as e:
        logger.error(f"❌ 方言辞書のインポートに失敗: {e}")
        return text, None, 0.0, {}, {}
    except Exception as e:
        logger.error(f"❌ 方言辞書の読み込みエラー: {e}")
        return text, None, 0.0, {}, {}
    
    converted_text = text
    detected_severity = None
    severity_tags = []  # 複数の重症度タグを収集
    escalation_score = 0.0
    non_destructive_candidates = {}
    normalized_weights = {}
    
    # グローバル変数からリソースを取得（構築済みのものを使用）
    global GLOBAL_DIALECT_AUTOMATON, GLOBAL_DIALECT_INDEX, GLOBAL_RE_SCANNER
    
    # グローバルリソースが初期化されていない場合は初期化
    if GLOBAL_DIALECT_INDEX is None:
        initialize_dialect_resources()
    
    # 方言インデックスで候補を絞り込み（パフォーマンス最適化）
    try:
        if use_index and GLOBAL_DIALECT_INDEX:
            candidate_dialects = filter_dialects_by_index(text, GLOBAL_DIALECT_INDEX, DIALECT_DICTIONARY)
        else:
            # インデックスを使用しない場合は全エントリを処理
            candidate_dialects = []
            for dialect_type, entries in DIALECT_DICTIONARY.items():
                for dialect_word, info in entries.items():
                    candidate_dialects.append((dialect_word, info, dialect_type))
    except Exception as e:
        logger.warning(f"⚠️ 方言インデックスの使用でエラー: {e}")
        # フォールバック：全エントリを処理
        candidate_dialects = []
        for dialect_type, entries in DIALECT_DICTIONARY.items():
            for dialect_word, info in entries.items():
                candidate_dialects.append((dialect_word, info, dialect_type))
    
    # Aho-Corasickでマッチング（パフォーマンス最適化）
    try:
        if use_aho_corasick and AHO_CORASICK_AVAILABLE and GLOBAL_DIALECT_AUTOMATON:
            matches = find_dialect_matches_aho_corasick(text, GLOBAL_DIALECT_AUTOMATON)
            # マッチした方言のみを処理
            if matches:
                candidate_dialects = [
                    (word, info, dtype) for _, _, (word, info, dtype) in matches
                ]
    except Exception as e:
        logger.warning(f"⚠️ Aho-Corasickマッチングでエラー: {e}")
        # エラーが発生しても処理を続行（インデックスで絞り込んだ候補を使用）
    
    # 長さの降順でソート（最長一致原則）
    candidate_dialects.sort(key=lambda x: len(x[0]), reverse=True)
    
    # 変換処理
    for dialect_word, dialect_info, dialect_type in candidate_dialects:
        # 変換保留リストのチェック
        if dialect_word in CONVERSION_EXCLUSION_LIST:
            if dialect_info.get("ambiguity_risk") == "high":
                if not check_health_context(converted_text, dialect_word, dialect_info):
                    continue
        
        # 正規表現パターンの取得
        regex_pattern = dialect_info.get("regex_pattern")
        if not regex_pattern:
            # 強調副詞かどうかを判定（severity_tagがある場合は強調副詞）
            is_emphasis = bool(dialect_info.get("severity_tag"))
            # 症状関連かどうかを判定（symptom_relatedがTrueの場合は症状関連）
            is_symptom = bool(dialect_info.get("symptom_related", False))
            regex_pattern = create_japanese_word_boundary_pattern(
                dialect_word,
                dialect_info.get("sentence_end_priority", False),
                is_emphasis=is_emphasis,
                is_symptom=is_symptom
            )
        
        # マッチングと置換
        try:
            matches = list(re.finditer(regex_pattern, converted_text, re.IGNORECASE))
        except re.error as e:
            logger.warning(f"⚠️ 正規表現エラー: {regex_pattern} - {e}")
            continue
        
        if matches:
            # 後ろから置換（インデックスのずれを防ぐ）
            for match in reversed(matches):
                # 文脈判定（多義語の場合）
                if dialect_info.get("ambiguity_risk") == "high":
                    if not check_health_context(converted_text, dialect_word, dialect_info):
                        continue
                
                # 非破壊的変換
                if non_destructive and dialect_info.get("standard_tokens"):
                    standard_tokens = dialect_info.get("standard_tokens", [])
                    non_destructive_candidates[dialect_word] = standard_tokens
                    
                    # 重みの正規化
                    weights = normalize_symptom_weights(dialect_word, dialect_info)
                    normalized_weights.update(weights)
                    
                    # 主要な変換先で置換
                    standard_word = dialect_info.get("standard", dialect_word)
                else:
                    standard_word = dialect_info.get("standard", dialect_word)
                
                # 置換（動詞の活用形を考慮）
                # 「にえる」→「打ち身」のように、名詞の場合は「になっている」などの表現に変換
                matched_text = match.group()
                replacement = standard_word
                
                # 動詞の活用形を考慮（「にえています」→「打ち身になっています」など）
                # 正規表現パターンが「にえ(?:ています|ている|て|た|る)」の場合、
                # 「にえています」全体がマッチするが、「にえる」の基本形は「にえ」+「る」
                # なので、活用部分を抽出する際は「にえ」を除いた部分を取得
                # 注意：「にえた」の場合、matched_textとdialect_wordの長さが同じ（3文字）なので、
                # len(matched_text) != len(dialect_word) または matched_text != dialect_word で判定
                if matched_text != dialect_word:
                    # 活用形が含まれている場合（「にえています」など）
                    # 「にえる」の基本形は「にえ」+「る」なので、「にえ」を除いた部分を取得
                    base_form = dialect_word[:-1]  # 「にえる」→「にえ」
                    if matched_text.startswith(base_form):
                        verb_suffix = matched_text[len(base_form):]  # 「にえています」→「ています」
                    else:
                        # フォールバック：通常の方法
                        verb_suffix = matched_text[len(dialect_word):]
                    
                    # 標準語が動詞（「する」で終わる）か名詞かを判定
                    if standard_word.endswith("する"):
                        # 動詞の場合：「する」動詞の活用形に変換
                        if verb_suffix:
                            # 「ている」「ています」などの活用形を保持
                            if verb_suffix.startswith("て"):
                                replacement = standard_word[:-2] + "し" + verb_suffix
                            elif verb_suffix.startswith("た"):
                                replacement = standard_word[:-2] + "し" + verb_suffix
                            elif verb_suffix.startswith("る"):
                                replacement = standard_word
                            else:
                                replacement = standard_word[:-2] + "し" + verb_suffix
                        else:
                            replacement = standard_word
                    else:
                        # 名詞の場合：「になっている」「になった」などの表現に変換
                        if verb_suffix:
                            if verb_suffix.startswith("て"):
                                # 「ている」「ています」→「になっている」「になっています」
                                if "ます" in verb_suffix:
                                    replacement = standard_word + "になっています"
                                else:
                                    replacement = standard_word + "になっている"
                            elif verb_suffix.startswith("た"):
                                # 「た」→「になった」
                                replacement = standard_word + "になった"
                            elif verb_suffix.startswith("る"):
                                # 「る」→「になる」
                                replacement = standard_word + "になる"
                            else:
                                # その他の活用形は「になっている」に統一
                                replacement = standard_word + "になっている"
                        else:
                            replacement = standard_word
                else:
                    replacement = standard_word
                
                converted_text = (
                    converted_text[:match.start()] +
                    replacement +
                    converted_text[match.end():]
                )
                
                # 強調副詞の重症度タグ抽出（最大値を取得＋escalation_score加算）
                if extract_severity and dialect_info.get("severity_tag"):
                    new_severity = dialect_info.get("severity_tag")
                    severity_tags.append(new_severity)
                    detected_severity = get_max_severity(detected_severity, new_severity)
    
    # escalation_scoreを計算
    if severity_tags:
        escalation_score = calculate_escalation_score(severity_tags)
    
    # デバッグモード時のログ記録（変換前後のテキスト記録）
    if DEBUG_MODE or logger.level <= logging.DEBUG:
        if converted_text != text:
            logger.debug(
                f"方言変換: '{text[:50]}...' → '{converted_text[:50]}...' "
                f"(重症度: {detected_severity}, escalation_score: {escalation_score:.1f})"
            )
    
    # 自動学習基盤：変換結果のログ記録（誤変換パターンの分析用）
    try:
        log_conversion_result(
            original_text=text,
            converted_text=converted_text,
            severity_tag=detected_severity,
            escalation_score=escalation_score,
            non_destructive_candidates=non_destructive_candidates,
            normalized_weights=normalized_weights
        )
    except Exception as e:
        # ログ記録のエラーは無視（メイン処理に影響を与えない）
        if DEBUG_MODE:
            logger.debug(f"変換結果のログ記録でエラー: {e}")
    
    return converted_text, detected_severity, escalation_score, non_destructive_candidates, normalized_weights


def log_conversion_result(
    original_text: str,
    converted_text: str,
    severity_tag: Optional[str],
    escalation_score: float,
    non_destructive_candidates: Dict[str, List[str]],
    normalized_weights: Dict[str, float]
):
    """
    自動学習機能の基盤：変換結果をログ記録（誤変換パターンの分析用）
    
    Args:
        original_text: 変換前のテキスト
        converted_text: 変換後のテキスト
        severity_tag: 検出された重症度タグ
        escalation_score: escalation_score
        non_destructive_candidates: 非破壊的変換の候補
        normalized_weights: 正規化された重み
    """
    import json
    from datetime import datetime
    
    # ログディレクトリの確認
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'log')
    os.makedirs(log_dir, exist_ok=True)
    
    # 変換結果をJSON形式で記録
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "original_text": original_text,
        "converted_text": converted_text,
        "severity_tag": severity_tag,
        "escalation_score": escalation_score,
        "non_destructive_candidates": non_destructive_candidates,
        "normalized_weights": normalized_weights,
        "conversion_applied": original_text != converted_text
    }
    
    # JSONL形式でログファイルに追記
    log_file = os.path.join(log_dir, 'dialect_conversion_log.jsonl')
    try:
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
    except Exception as e:
        # ログ記録のエラーは無視
        if DEBUG_MODE:
            logger.debug(f"変換結果のログ記録でエラー: {e}")
