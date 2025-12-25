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
    'spring': {
        'period': [(3, 1, 5, 31)],
        'images': {
            # 将来的に追加
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
ZODIAC_LIST = ['Cow', 'Tiger', 'Rabbit', 'Dragon', 'Snake', 
               'Horse', 'Goat', 'Monkey', 'Rooster', 'Dog', 'Pig', 'Rat']

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
    'Horse.png': 'うま',
    'Goat.png': 'ひつじ',
    'Monkey.png': 'さる',
    'Rooster.png': 'とり',
    'Dog.png': 'いぬ',
    'Pig.png': 'いのしし',
    'Rat.png': 'ねずみ',
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
        str: シーズンタイプ（'christmas', 'newyear', 'spring', 'summer', 'autumn', None）
    """
    # 優先順位の高い順にチェック（クリスマスと正月が重複する可能性があるため）
    priority_seasons = ['christmas', 'newyear', 'spring', 'summer', 'autumn']
    
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
                session[session_key] = random.choice(config['images']['left'])
            left_img = session[session_key]
        else:
            # セッションが利用できない場合は最初の画像を使用
            left_img = config['images']['left'][0]
        
        images.append({
            'path': f"img/{config['base_path']}/{left_img}",
            'alt': get_image_alt(left_img),
            'position_class': 'position-left'
        })
    
    return images

