import re
import unicodedata

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
