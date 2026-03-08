#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
シーズン管理モジュール
日時からシーズンを判定し、適切な装飾画像のパスを生成する
"""

import random
from datetime import datetime
import pytz

# シーズン設定辞書
SEASON_CONFIG = {
    'christmas': {
        'period': [(12, 1, 12, 25)],  # (開始月, 開始日, 終了月, 終了日)
        'images': {
            'right': ['christmas_tree.png'],
            'left': ['snowman.png']
        },
        'base_path': 'winter'
    },
    'newyear': {
        'period': [(12, 26, 12, 31), (1, 1, 1, 7)],
        'images': {
            'right': ['zodiac'],  # 年度に応じて動的
            'left': ['Ema.png', 'Kagami-mochi.png']  # ランダム選択
        },
        'base_path': 'winter/HappyNewYear'
    },
    'winter': {
        'period': [(1, 8, 1, 31), (2, 4, 2, 13), (2, 15, 2, 28)],
        'images': {
            'right': ['wintertree.png', 'winter_snow.png'],  # ランダム選択
            'left': ['snowman.png', 'can_coffee.png']  # ランダム選択（snowman.pngはwinter/から参照）
        },
        'base_path': 'winter/general'
    },
    'setubun': {
        'period': [(2, 1, 2, 3)],
        'images': {
            'right': ['oni.png'],
            'left': ['mame.png', 'ehoumaki.png', 'kanabou.png']  # ランダム選択
        },
        'base_path': 'winter/setubun'
    },
    'valentine': {
        'period': [(2, 14, 2, 14)],
        'images': {
            'right': ['choco.png', 'heart.png', 'loveletter.png'],  # ランダム選択
            'left': ['lgbt.png', 'lgbt2.png', 'student.png', 'valentine.png'],  # 重み付きランダム選択
            'left_weights': {'lgbt.png': 1, 'lgbt2.png': 1, 'student.png': 1, 'valentine.png': 1}  # 出現率（デフォルトは均等）
        },
        'base_path': 'winter/valentine'
    },
    # 春イベント（優先順で上から判定）
    'hinamatsuri': {
        'period': [(3, 1, 3, 5)],
        'images': {
            'right': ['ひな祭り(菱餅).png', 'ひな祭り(三色団子).png', 'ひな祭り(提灯).png'],  # ランダム
            'left': ['ひな祭り.png']
        },
        'base_path': 'spring'
    },
    'whiteday': {
        'period': [(3, 12, 3, 15)],
        'images': {
            'right': ['choco.png', 'heart.png', 'loveletter.png'],
            'left': ['lgbt.png', 'lgbt2.png', 'student.png', 'valentine.png']
        },
        'base_path': 'spring/valentine'
    },
    'graduation': {
        'period': [(3, 20, 3, 31)],
        'images': {
            'right': ['卒業式.png'],
            'left': ['卒業証書.png', '桜.png', '桜木.png']
        },
        'base_path': 'spring'
    },
    'enrollment': {
        'period': [(4, 1, 4, 10)],
        'images': {
            'right': ['入学式.png'],
            'left': ['桜.png', '桜木.png', '春.png', '蝶.png']  # くまは出さない
        },
        'base_path': 'spring'
    },
    'hanami': {
        'period': [(4, 11, 4, 25)],
        'images': {
            'right': ['桜木.png', '桜.png'],
            'left': ['ひな祭り(三色団子).png', '蝶.png', '春.png']
        },
        'base_path': 'spring'
    },
    'gw': {
        'period': [(4, 28, 5, 3)],  # こどもの日(5/4-5/7)と被らない
        'images': {
            'right': ['ドライブ.png', 'ドライブ2.png'],  # 片方のみ（セッションで固定）
            'left': ['温泉.png', '飛行機.png']
        },
        'base_path': 'spring'
    },
    'kodomonomi': {
        'period': [(5, 4, 5, 7)],
        'images': {
            'right': ['こいのぼり.png'],
            'left': ['兜.png', '紙かぶと.png', 'こどもの日.png']
        },
        'base_path': 'spring'
    },
    'mothersday': {
        'period': [(5, 8, 5, 14)],  # 5月第2日曜前後
        'images': {
            'right': ['カーネーション.png', '母の日.png'],
            'left': ['プレゼント.png', '母の日.png']
        },
        'base_path': 'spring'
    },
    'spring': {
        'period': [(3, 1, 5, 31)],  # 上記以外の春（くまは左で約1/10、桜・花粉も左に）
        'images': {
            'right': ['桜.png', '桜木.png', '春.png'],
            'left': ['くま.png', '桜.png', '花粉.png', '蝶.png'],
            'left_weights': {'くま.png': 1, '桜.png': 3, '花粉.png': 3, '蝶.png': 3}
        },
        'base_path': 'spring'
    },
    'summer': {
        'period': [(6, 1, 8, 31)],
        'images': {
            # 将来的に追加
        },
        'base_path': 'summer'
    },
    'autumn': {
        'period': [(9, 1, 11, 30)],
        'images': {
            # 将来的に追加
        },
        'base_path': 'autumn'
    },
}

# 干支マッピング辞書（2026年を基準）
ZODIAC_LIST = ['horse', 'Goat', 'Monkey', 'Rooster', 'Dog', 'Pig', 
               'Rat', 'Cow', 'Tiger', 'Rabbit', 'Dragon', 'Snake']

# 画像のalt属性マッピング
IMAGE_ALT_MAPPING = {
    'christmas_tree.png': 'クリスマスツリー',
    'snowman.png': '雪だるま',
    'Ema.png': '絵馬',
    'Kagami-mochi.png': '鏡餅',
    'Sneak.png': 'へび',
    'Cow.png': 'うし',
    'Tiger.png': 'とら',
    'Rabbit.png': 'うさぎ',
    'Dragon.png': 'たつ',
    'Snake.png': 'へび',
    'horse.png': 'うま',
    'Goat.png': 'ひつじ',
    'Monkey.png': 'さる',
    'Rooster.png': 'とり',
    'Dog.png': 'いぬ',
    'Pig.png': 'いのしし',
    'Rat.png': 'ねずみ',
    # 冬の季節
    'wintertree.png': '冬の木',
    'winter_snow.png': '雪景色',
    'can_coffee.png': '温かいコーヒー',
    # 節分
    'oni.png': '鬼',
    'mame.png': '豆',
    'ehoumaki.png': '恵方巻',
    'kanabou.png': '金棒',
    # バレンタイン
    'valentine.png': 'バレンタイン',
    'heart.png': 'ハート',
    'choco.png': 'チョコレート',
    'loveletter.png': 'ラブレター',
    'student.png': '学生',
    'lgbt.png': 'LGBT',
    'lgbt2.png': 'LGBT',
    # 春：ひな祭り
    'ひな祭り.png': 'ひな祭り',
    'ひな祭り(菱餅).png': '菱餅',
    'ひな祭り(三色団子).png': '三色団子',
    'ひな祭り(提灯).png': '提灯',
    # 春：卒業・入学
    '卒業式.png': '卒業式',
    '卒業証書.png': '卒業証書',
    '入学式.png': '入学式',
    # 春：桜・花見・一般
    '桜.png': '桜',
    '桜木.png': '桜の木',
    '春.png': '春',
    '蝶.png': '蝶',
    '花粉.png': '花粉',
    'くま.png': 'くま',
    # 春：GW・行楽
    'ドライブ.png': 'ドライブ',
    'ドライブ2.png': 'ドライブ',
    '飛行機.png': '飛行機',
    '温泉.png': '温泉',
    # 春：こどもの日
    'こいのぼり.png': 'こいのぼり',
    '兜.png': '兜',
    '紙かぶと.png': '紙かぶと',
    'こどもの日.png': 'こどもの日',
    # 春：母の日
    'カーネーション.png': 'カーネーション',
    '母の日.png': '母の日',
    'プレゼント.png': 'プレゼント',
}


def is_in_period(date, period_list):
    """
    日時が期間リスト内に含まれるか判定
    
    Args:
        date: datetimeオブジェクト
        period_list: [(開始月, 開始日, 終了月, 終了日), ...] の形式
    
    Returns:
        bool: 期間内であればTrue
    """
    month = date.month
    day = date.day
    
    for start_month, start_day, end_month, end_day in period_list:
        # 同じ月内の期間
        if start_month == end_month:
            if month == start_month and start_day <= day <= end_day:
                return True
        # 月を跨ぐ期間（例：12月26日～1月7日）
        else:
            if (month == start_month and day >= start_day) or \
               (month == end_month and day <= end_day):
                return True
    
    return False


def get_current_season(date):
    """
    現在の日時からシーズンタイプを判定
    
    Args:
        date: datetimeオブジェクト（JST）
    
    Returns:
        str: シーズンタイプ（'christmas', 'newyear', 'valentine', 'setubun', 'winter',
             'hinamatsuri', 'whiteday', 'graduation', 'enrollment', 'hanami', 'gw', 'kodomonomi', 'mothersday',
             'spring', 'summer', 'autumn', None）
    """
    # 優先順位の高い順にチェック（イベント日が重複する可能性があるため）
    priority_seasons = [
        'christmas', 'newyear', 'valentine', 'setubun', 'winter',
        'hinamatsuri', 'whiteday', 'graduation', 'enrollment', 'hanami', 'gw', 'kodomonomi', 'mothersday',
        'spring', 'summer', 'autumn'
    ]
    
    for season_type in priority_seasons:
        config = SEASON_CONFIG.get(season_type)
        if config and is_in_period(date, config['period']):
            return season_type
    
    return None


def get_zodiac_image(year):
    """
    年度から干支画像名を取得
    
    Args:
        year: 年度（int）
    
    Returns:
        str: 干支画像ファイル名（例：'Cow.png'）
    """
    # 2026年を基準とした干支計算
    base_year = 2026
    index = (year - base_year) % 12
    zodiac_name = ZODIAC_LIST[index]
    return f"{zodiac_name}.png"


def get_image_alt(image_filename, year=None):
    """
    画像ファイル名からalt属性を取得
    
    Args:
        image_filename: 画像ファイル名
        year: 年度（干支判定用、オプション）
    
    Returns:
        str: alt属性のテキスト
    """
    # 干支画像の場合
    if image_filename in [f"{z}.png" for z in ZODIAC_LIST]:
        return IMAGE_ALT_MAPPING.get(image_filename, image_filename.replace('.png', ''))
    
    # その他の画像
    return IMAGE_ALT_MAPPING.get(image_filename, image_filename.replace('.png', ''))


def get_season_images(season_type, year, session):
    """
    シーズンに応じた画像パスリストを生成
    
    Args:
        season_type: シーズンタイプ（'christmas', 'newyear', など）
        year: 年度
        session: Flaskセッションオブジェクト
    
    Returns:
        list: 画像情報の辞書リスト [{'path': '...', 'alt': '...', 'position_class': '...'}, ...]
    """
    config = SEASON_CONFIG.get(season_type)
    if not config:
        return []
    
    images = []
    
    # 右側画像
    if 'right' in config['images'] and config['images']['right']:
        right_img = config['images']['right'][0]
        if right_img == 'zodiac':
            # 2025年はSneak.png、2026年以降は年度に応じた干支画像
            if year <= 2025:
                right_img = 'Sneak.png'
            else:
                right_img = get_zodiac_image(year)
        elif len(config['images']['right']) > 1:
            # 複数の選択肢がある場合はランダム選択（セッション固定）
            if session is not None:
                session_key = f'decoration_right_{season_type}'
                if session_key not in session:
                    session[session_key] = random.choice(config['images']['right'])
                right_img = session[session_key]
            else:
                right_img = random.choice(config['images']['right'])
        
        images.append({
            'path': f"img/{config['base_path']}/{right_img}",
            'alt': get_image_alt(right_img, year),
            'position_class': 'position-right'
        })
    
    # 左側画像（ランダム選択、セッション固定）
    if 'left' in config['images'] and config['images']['left']:
        if session is not None:
            session_key = f'decoration_left_{season_type}'
            if session_key not in session:
                # 重み付きランダム選択が設定されている場合
                if 'left_weights' in config['images'] and config['images']['left_weights']:
                    weights = config['images']['left_weights']
                    # 重みに基づいて選択肢と重みのリストを作成
                    choices = []
                    weights_list = []
                    for img in config['images']['left']:
                        choices.append(img)
                        weights_list.append(weights.get(img, 1))  # 重みが未設定の場合は1
                    # 重み付きランダム選択
                    left_img = random.choices(choices, weights=weights_list, k=1)[0]
                else:
                    # 通常のランダム選択
                    left_img = random.choice(config['images']['left'])
                session[session_key] = left_img
            left_img = session[session_key]
        else:
            # セッションが利用できない場合
            if 'left_weights' in config['images'] and config['images']['left_weights']:
                weights = config['images']['left_weights']
                choices = []
                weights_list = []
                for img in config['images']['left']:
                    choices.append(img)
                    weights_list.append(weights.get(img, 1))
                left_img = random.choices(choices, weights=weights_list, k=1)[0]
            else:
                left_img = config['images']['left'][0]
        
        # snowman.pngはwinter/直下にあるため、winter/general/からは../で参照
        if left_img == 'snowman.png' and config['base_path'] == 'winter/general':
            left_path = f"img/winter/{left_img}"
        else:
            left_path = f"img/{config['base_path']}/{left_img}"
        
        images.append({
            'path': left_path,
            'alt': get_image_alt(left_img),
            'position_class': 'position-left'
        })
    
    return images

