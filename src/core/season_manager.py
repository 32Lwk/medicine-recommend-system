#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
シーズン管理モジュール
日時からシーズンを判定し、適切な装飾画像のパスを生成する
"""

import copy
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
        'period': [(2, 10, 2, 18)],  # 周辺含む。2/14 のみ get_particle_profile で density high
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
    'tanabata': {
        'period': [(7, 6, 7, 8)],
        'images': {
            'right': ['tanabata-streamer.png'],
            'left': ['tanabata-bamboo.png']
        },
        'base_path': 'events/tanabata'
    },
    'summer': {
        'period': [(6, 1, 8, 31)],
        'images': {},
        'base_path': 'summer'
    },
    'autumn': {
        'period': [(9, 1, 11, 30)],
        'images': {},
        'base_path': 'autumn'
    },
    'keiro': {
        'period': [(9, 15, 9, 21)],
        'images': {
            'right': ['keiro-carnation-soft.png'],
            'left': ['keiro-gift-soft.png']
        },
        'base_path': 'events/keiro'
    },
    'halloween': {
        'period': [(10, 28, 10, 31)],
        'images': {
            'right': ['halloween-moon-soft.png'],
            'left': ['halloween-star-soft.png']
        },
        'base_path': 'events/halloween'
    },
    'shichigosan': {
        'period': [(11, 14, 11, 16)],
        'images': {
            'right': ['shichigosan-chouchin-soft.png'],
            'left': ['shichigosan-motif-soft.png']
        },
        'base_path': 'events/shichigosan'
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
    # チャット粒子スプライト（img/particles/）
    'heart-glow.png': '淡色のハート装飾（粒子）',
    'pumpkin-soft.png': '淡色のかぼちゃ装飾（粒子）',
    'soybean-soft.png': '節分・豆を連想する淡色粒子',
    'car-soft.png': 'GW・車を連想する淡色粒子',
    'plane-soft.png': 'GW・飛行機を連想する淡色粒子',
    'carp-streamer-soft.png': 'こいのぼりを連想する淡色粒子',
    'kabuto-soft.png': '兜を連想する淡色粒子',
    'tanzaku-soft.png': '七夕・短冊を連想する淡色粒子',
    'bamboo-soft.png': '七夕・竹を連想する淡色粒子',
    'firework-soft.png': '夏・花火を連想する淡色粒子',
    'hina-doll-soft.png': 'ひな祭りを連想する淡色粒子',
    'gift-soft.png': 'ホワイトデー・贈り物を連想する淡色粒子',
    'cap-soft.png': '卒業・角帽を連想する淡色粒子',
    'bag-soft.png': '入学・ランドセルを連想する淡色粒子',
    'petal-soft.png': '花見・桜の花びらを連想する淡色粒子',
    'butterfly-soft.png': '春・蝶を連想する淡色粒子',
    'carnation-particle-soft.png': '敬老の日・カーネーションを連想する淡色粒子',
    'fan-soft.png': '七五三・扇子を連想する淡色粒子',
    'kadomatsu-soft.png': '正月・門松を連想する淡色粒子',
    'ornament-soft.png': 'クリスマス・オーナメントを連想する淡色粒子',
    'maple-soft.png': '秋・もみじを連想する淡色粒子',
    'tulip-soft.png': '母の日・チューリップを連想する淡色粒子',
    # 行事装飾（img/events/）
    'tanabata-bamboo.png': '七夕・竹を連想する淡色装飾',
    'tanabata-streamer.png': '七夕・短冊を連想する淡色装飾',
    'keiro-carnation-soft.png': '敬老の日・花を連想する淡色装飾',
    'keiro-gift-soft.png': '敬老の日・贈り物を連想する淡色装飾',
    'halloween-moon-soft.png': 'ハロウィン・月を連想する淡色装飾',
    'halloween-star-soft.png': 'ハロウィン・星を連想する淡色装飾',
    'shichigosan-chouchin-soft.png': '七五三・提灯を連想する淡色装飾',
    'shichigosan-motif-soft.png': '七五三・和柄を連想する淡色装飾',
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


def is_in_period(dt, period_list):
    """
    日時が期間リスト内に含まれるか判定

    Args:
        dt: datetime オブジェクト（tz 付き可。日付のみ比較）
        period_list: [(開始月, 開始日, 終了月, 終了日), ...] の形式。
            同年にまたがる複数月（例: 6/1〜8/31）と、年末→年始の跨ぎ（例: 12/26〜1/7）を扱う。

    Returns:
        bool: 期間内であれば True
    """
    month = dt.month
    day = dt.day

    for start_month, start_day, end_month, end_day in period_list:
        if start_month == end_month:
            if month == start_month and start_day <= day <= end_day:
                return True
            continue

        # 年末→年始（終了月 < 開始月、例: 12/26〜1/7）
        if end_month < start_month or (end_month == start_month and end_day < start_day):
            if (month == start_month and day >= start_day) or (month == end_month and day <= end_day):
                return True
            continue

        # 同年の複数月（例: 6/1〜8/31、3/1〜5/31）
        if month < start_month or month > end_month:
            continue
        if month == start_month and day < start_day:
            continue
        if month == end_month and day > end_day:
            continue
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
             'spring', 'tanabata', 'summer', 'keiro', 'halloween', 'shichigosan', 'autumn', None）
    """
    # 優先順位の高い順にチェック（イベント日が重複する可能性があるため）
    # valentine は winter より前（2/10–18 は valentine）。tanabata は summer より前（7/6–8）。
    # keiro / halloween / shichigosan は autumn より前。
    priority_seasons = [
        'christmas', 'newyear', 'valentine', 'setubun', 'winter',
        'hinamatsuri', 'whiteday', 'graduation', 'enrollment', 'hanami', 'gw', 'kodomonomi', 'mothersday',
        'spring', 'tanabata', 'summer', 'keiro', 'halloween', 'shichigosan', 'autumn'
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


def _particle_profile(
    glyphs,
    particle_color,
    density='medium',
    *,
    angle_deg_min=-18,
    angle_deg_max=18,
    drift_px_min=-55,
    drift_px_max=55,
    duration_sec_min=9,
    duration_sec_max=26,
    delay_sec_max=5,
    sprites=None,
    enabled=True,
):
    """
    チャット欄パーティクル用プロファイル（クライアント JSON）。
    色は #000 禁止・チャット背景 rgba(192,192,192) 上で視認できる明るめトーンを想定。
    """
    return {
        'enabled': bool(enabled),
        'density': density,
        'glyphs': list(glyphs),
        'sprites': list(sprites or []),
        'particleColor': particle_color,
        'angleDegMin': angle_deg_min,
        'angleDegMax': angle_deg_max,
        'driftPxMin': drift_px_min,
        'driftPxMax': drift_px_max,
        'durationSecMin': duration_sec_min,
        'durationSecMax': duration_sec_max,
        'delaySecMax': delay_sec_max,
    }


def _fallback_particle_key(month):
    """get_current_season が None のときの暦月バケット。"""
    if month in (12, 1, 2):
        return 'fallback_winter'
    if month in (3, 4, 5):
        return 'fallback_spring'
    if month in (6, 7, 8):
        return 'fallback_summer'
    return 'fallback_autumn'


# キーは get_current_season の戻り値 + fallback_*（None 時）
PARTICLE_PROFILES = {
    'fallback_winter': _particle_profile(['❄', '❅', '❆'], '#ffffff', 'low'),
    'fallback_spring': _particle_profile(['🌸', '✨', '🦋'], '#fff8e1', 'low'),
    'fallback_summer': _particle_profile(['✨', '☀', '·'], '#fff9c4', 'low'),
    'fallback_autumn': _particle_profile(['🍂', '✨'], '#ffe0b2', 'low'),
    'christmas': _particle_profile(
        ['❄', '❅', '❆', '✨'],
        '#ffffff',
        'high',
        sprites=[{'path': 'img/particles/christmas/ornament-soft.png', 'weight': 1}],
    ),
    'newyear': _particle_profile(
        ['✨', '⭐', '❄'],
        '#fffde7',
        'high',
        sprites=[{'path': 'img/particles/newyear/kadomatsu-soft.png', 'weight': 1}],
    ),
    'winter': _particle_profile(
        ['❄', '❅', '❆'],
        '#ffffff',
        'medium',
    ),
    'setubun': _particle_profile(
        ['·', '✨'],
        '#efebe9',
        'medium',
        sprites=[{'path': 'img/particles/setubun/soybean-soft.png', 'weight': 1}],
    ),
    'valentine': _particle_profile(
        ['💕', '🤍', '💗'],
        '#fce4ec',
        'medium',
        sprites=[
            {'path': 'img/particles/valentine/heart-glow.png', 'weight': 2},
        ],
    ),
    'hinamatsuri': _particle_profile(
        ['🌸', '✨'],
        '#fce4ec',
        'medium',
        sprites=[{'path': 'img/particles/hinamatsuri/hina-doll-soft.png', 'weight': 1}],
    ),
    'whiteday': _particle_profile(
        ['🤍', '✨'],
        '#f5f5f5',
        'medium',
        sprites=[{'path': 'img/particles/whiteday/gift-soft.png', 'weight': 1}],
    ),
    'graduation': _particle_profile(
        ['🌸', '✨', '🎓'],
        '#f3e5f5',
        'high',
        sprites=[{'path': 'img/particles/graduation/cap-soft.png', 'weight': 1}],
    ),
    'enrollment': _particle_profile(
        ['🌸', '✨'],
        '#e8f5e9',
        'high',
        sprites=[{'path': 'img/particles/enrollment/bag-soft.png', 'weight': 1}],
    ),
    'hanami': _particle_profile(
        ['🌸', '🍃'],
        '#ffecb3',
        'high',
        sprites=[{'path': 'img/particles/hanami/petal-soft.png', 'weight': 1}],
    ),
    'gw': _particle_profile(
        ['✨', '·'],
        '#e3f2fd',
        'medium',
        sprites=[
            {'path': 'img/particles/gw/car-soft.png', 'weight': 1},
            {'path': 'img/particles/gw/plane-soft.png', 'weight': 1},
        ],
    ),
    'kodomonomi': _particle_profile(
        ['✨', '·'],
        '#e3f2fd',
        'high',
        sprites=[
            {'path': 'img/particles/kodomonomi/carp-streamer-soft.png', 'weight': 1},
            {'path': 'img/particles/kodomonomi/kabuto-soft.png', 'weight': 1},
        ],
    ),
    'mothersday': _particle_profile(
        ['🌷', '✨'],
        '#fce4ec',
        'high',
        sprites=[{'path': 'img/particles/mothersday/tulip-soft.png', 'weight': 1}],
    ),
    'spring': _particle_profile(
        ['🌸', '✨', '🦋'],
        '#fff8e1',
        'medium',
        sprites=[{'path': 'img/particles/spring/butterfly-soft.png', 'weight': 1}],
    ),
    'tanabata': _particle_profile(
        ['✨', '⭐'],
        '#e3f2fd',
        'high',
        sprites=[
            {'path': 'img/particles/tanabata/tanzaku-soft.png', 'weight': 1},
            {'path': 'img/particles/tanabata/bamboo-soft.png', 'weight': 1},
        ],
    ),
    'summer': _particle_profile(
        ['✨', '☀', '·'],
        '#fff9c4',
        'medium',
        sprites=[{'path': 'img/particles/summer/firework-soft.png', 'weight': 1}],
    ),
    'keiro': _particle_profile(
        ['✨', '🌸'],
        '#fff3e0',
        'medium',
        sprites=[{'path': 'img/particles/keiro/carnation-particle-soft.png', 'weight': 1}],
    ),
    'halloween': _particle_profile(
        ['✨', '·'],
        '#f3e5f5',
        'high',
        sprites=[
            {'path': 'img/particles/halloween/pumpkin-soft.png', 'weight': 1},
        ],
    ),
    'shichigosan': _particle_profile(
        ['✨', '🌸'],
        '#fff8e1',
        'medium',
        sprites=[{'path': 'img/particles/shichigosan/fan-soft.png', 'weight': 1}],
    ),
    'autumn': _particle_profile(
        ['🍂', '✨'],
        '#ffe0b2',
        'medium',
        sprites=[{'path': 'img/particles/autumn/maple-soft.png', 'weight': 1}],
    ),
}


def get_particle_profile(season_type, date):
    """
    チャット欄パーティクル設定を返す（JST の date を想定）。

    Args:
        season_type: get_current_season の戻り値、または None
        date: datetime（tz 付き JST 推奨）

    Returns:
        dict: JSON 化可能なプロファイル（enabled, density, glyphs, sprites, particleColor, …）。
            sprites は `{"path": "img/.../file.png", "weight": 1}` の配列（weight は任意、既定 1）。
    """
    if season_type is None:
        key = _fallback_particle_key(date.month)
        profile = copy.deepcopy(PARTICLE_PROFILES[key])
    else:
        profile = copy.deepcopy(
            PARTICLE_PROFILES.get(season_type, PARTICLE_PROFILES['spring'])
        )

    if season_type == 'valentine':
        if date.month == 2 and date.day == 14:
            profile['density'] = 'high'
        else:
            profile['density'] = 'medium'

    if season_type == 'summer':
        if date.month == 8:
            profile['density'] = 'high'
        else:
            profile['density'] = 'medium'

    return profile


def _left_pool_avoiding_right(left_options, right_img, weights_map):
    """
    左装飾の候補から right_img と同一ファイルを除く（別候補が残る場合のみ）。
    weights_map があれば候補に対応する重みリストも返す。
    """
    if right_img is None:
        filtered = list(left_options)
    else:
        filtered = [x for x in left_options if x != right_img]
        if not filtered:
            filtered = list(left_options)
    if not weights_map:
        return filtered, None
    wlist = [weights_map.get(x, 1) for x in filtered]
    return filtered, wlist


def _pick_left_decoration(left_options, right_img, weights_map):
    """左装飾画像を1件選ぶ（右と同じファイルは避ける）。"""
    choices, wlist = _left_pool_avoiding_right(left_options, right_img, weights_map)
    if wlist is not None:
        return random.choices(choices, weights=wlist, k=1)[0]
    return random.choice(choices)


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
    right_filename_for_dedup = None

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
        
        right_filename_for_dedup = right_img
        images.append({
            'path': f"img/{config['base_path']}/{right_img}",
            'alt': get_image_alt(right_img, year),
            'position_class': 'position-right'
        })
    
    # 左側画像（ランダム選択、セッション固定。右と同一画像は避ける）
    if 'left' in config['images'] and config['images']['left']:
        left_options = config['images']['left']
        weights_map = config['images'].get('left_weights') or None
        if session is not None:
            session_key = f'decoration_left_{season_type}'
            if session_key not in session:
                session[session_key] = _pick_left_decoration(
                    left_options, right_filename_for_dedup, weights_map
                )
            left_img = session[session_key]
            if (
                right_filename_for_dedup is not None
                and left_img == right_filename_for_dedup
                and any(x != right_filename_for_dedup for x in left_options)
            ):
                session[session_key] = _pick_left_decoration(
                    left_options, right_filename_for_dedup, weights_map
                )
                left_img = session[session_key]
        else:
            left_img = _pick_left_decoration(
                left_options, right_filename_for_dedup, weights_map
            )
        
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

