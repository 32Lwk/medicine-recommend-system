# -*- coding: utf-8 -*-
"""season_manager: 季節判定・パーティクルプロファイルの境界テスト（JST）"""

from datetime import datetime, timedelta
from pathlib import Path

import pytest
import pytz

from src.core.season_manager import (
    PARTICLE_PROFILES,
    SEASON_CONFIG,
    get_current_season,
    get_particle_profile,
    is_in_period,
)

JST = pytz.timezone("Asia/Tokyo")
REPO_ROOT = Path(__file__).resolve().parents[1]


def _dt(year, month, day, hour=12):
    return JST.localize(__import__("datetime").datetime(year, month, day, hour, 0, 0))


def test_valentine_window_and_peak_density():
    assert get_current_season(_dt(2026, 2, 9)) == "winter"
    assert get_current_season(_dt(2026, 2, 10)) == "valentine"
    assert get_current_season(_dt(2026, 2, 18)) == "valentine"
    assert get_current_season(_dt(2026, 2, 19)) == "winter"

    p13 = get_particle_profile("valentine", _dt(2026, 2, 13))
    p14 = get_particle_profile("valentine", _dt(2026, 2, 14))
    p15 = get_particle_profile("valentine", _dt(2026, 2, 15))
    assert p13["density"] == "medium"
    assert p14["density"] == "high"
    assert p15["density"] == "medium"


def test_summer_august_density():
    p7 = get_particle_profile("summer", _dt(2026, 7, 31))
    p8 = get_particle_profile("summer", _dt(2026, 8, 1))
    assert p7["density"] == "medium"
    assert p8["density"] == "high"


def test_tanabata_before_summer_bucket():
    assert get_current_season(_dt(2026, 7, 7)) == "tanabata"
    assert get_current_season(_dt(2026, 7, 5)) == "summer"


def test_autumn_events_priority():
    assert get_current_season(_dt(2026, 9, 18)) == "keiro"
    assert get_current_season(_dt(2026, 10, 30)) == "halloween"
    assert get_current_season(_dt(2026, 11, 15)) == "shichigosan"
    assert get_current_season(_dt(2026, 9, 10)) == "autumn"


def test_none_season_fallback_keys():
    p_dec = get_particle_profile(None, _dt(2026, 12, 15))
    p_feb = get_particle_profile(None, _dt(2026, 2, 1))
    p_apr = get_particle_profile(None, _dt(2026, 4, 1))
    p_jul = get_particle_profile(None, _dt(2026, 7, 1))
    p_oct = get_particle_profile(None, _dt(2026, 10, 1))
    assert p_dec["density"] == "low"
    assert p_feb["density"] == "low"
    assert p_apr["density"] == "low"
    assert p_jul["density"] == "low"
    assert p_oct["density"] == "low"


def test_particle_color_not_black():
    p = get_particle_profile("christmas", _dt(2026, 12, 15))
    c = (p.get("particleColor") or "").strip().lower()
    assert c != "#000"
    assert c != "rgb(0,0,0)"


def test_profile_json_serializable_keys():
    p = get_particle_profile("mothersday", _dt(2026, 5, 10))
    for k in (
        "enabled",
        "density",
        "glyphs",
        "sprites",
        "particleColor",
        "angleDegMin",
        "angleDegMax",
        "driftPxMin",
        "driftPxMax",
        "durationSecMin",
        "durationSecMax",
        "delaySecMax",
    ):
        assert k in p


def _srgb_channel_to_linear(c):
    c /= 255.0
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def relative_luminance_hex(hex_color: str) -> float:
    h = hex_color.strip().lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return 0.2126 * _srgb_channel_to_linear(r) + 0.7152 * _srgb_channel_to_linear(
        g
    ) + 0.0722 * _srgb_channel_to_linear(b)


# PARTICLE_COLOR_POLICY: 輝度スナップショット（意図的な配色変更時のみ更新）
EXPECTED_PARTICLE_LUMINANCE = {
    "autumn": 0.778,
    "christmas": 1.0,
    "enrollment": 0.883,
    "fallback_autumn": 0.778,
    "fallback_spring": 0.938,
    "fallback_summer": 0.93,
    "fallback_winter": 1.0,
    "graduation": 0.817,
    "gw": 0.869,
    "halloween": 0.817,
    "hanami": 0.845,
    "hinamatsuri": 0.822,
    "keiro": 0.907,
    "kodomonomi": 0.869,
    "mothersday": 0.822,
    "newyear": 0.973,
    "setubun": 0.837,
    "shichigosan": 0.938,
    "spring": 0.938,
    "summer": 0.93,
    "tanabata": 0.869,
    "valentine": 0.822,
    "whiteday": 0.913,
    "winter": 1.0,
}


def test_particle_colors_luminance_floor():
    floor = 0.55
    for key, prof in PARTICLE_PROFILES.items():
        col = prof.get("particleColor") or ""
        lum = relative_luminance_hex(col)
        assert lum >= floor, f"{key} {col} L={lum}"


def test_particle_luminance_snapshot():
    for key, expected in EXPECTED_PARTICLE_LUMINANCE.items():
        col = PARTICLE_PROFILES[key]["particleColor"]
        got = round(relative_luminance_hex(col), 3)
        assert got == expected, f"{key}: got {got} expected {expected}"


@pytest.mark.parametrize(
    "y,m,d,expected",
    [
        (2026, 1, 1, "newyear"),
        (2026, 1, 8, "winter"),
        (2026, 2, 2, "setubun"),
        (2026, 2, 5, "winter"),
        (2026, 2, 11, "valentine"),
        (2026, 2, 14, "valentine"),
        (2026, 3, 3, "hinamatsuri"),
        (2026, 3, 10, "spring"),
        (2026, 3, 14, "whiteday"),
        (2026, 3, 25, "graduation"),
        (2026, 4, 5, "enrollment"),
        (2026, 4, 20, "hanami"),
        (2026, 5, 2, "gw"),
        (2026, 5, 5, "kodomonomi"),
        (2026, 5, 12, "mothersday"),
        (2026, 5, 20, "spring"),
        (2026, 6, 15, "summer"),
        (2026, 7, 7, "tanabata"),
        (2026, 7, 20, "summer"),
        (2026, 9, 14, "autumn"),
        (2026, 9, 18, "keiro"),
        (2026, 10, 30, "halloween"),
        (2026, 11, 15, "shichigosan"),
        (2026, 11, 22, "autumn"),
        (2026, 12, 15, "christmas"),
        (2026, 12, 28, "newyear"),
    ],
)
def test_get_current_season_calendar_samples(y, m, d, expected):
    assert get_current_season(_dt(y, m, d)) == expected


def _collect_sprite_paths():
    paths = []
    for prof in PARTICLE_PROFILES.values():
        for s in prof.get("sprites") or []:
            if isinstance(s, dict) and s.get("path"):
                paths.append(s["path"])
            elif isinstance(s, str):
                paths.append(s)
    return paths


def test_particle_sprite_files_exist_on_disk():
    for rel in _collect_sprite_paths():
        assert rel.startswith("img/")
        full = REPO_ROOT / "static" / rel
        assert full.is_file(), str(full)


def test_admin_chat_template_has_no_seasonal_particle_init():
    """管理用チャットでは季節粒子を初期化しない（index 専用）。"""
    html = (REPO_ROOT / "templates" / "admin_chat.html").read_text(encoding="utf-8")
    assert "particle-profile" not in html
    assert "snowContainer" not in html
    assert "createSeasonalParticles" not in html


def test_admin_chat_js_has_no_seasonal_particle_init():
    js = (REPO_ROOT / "static" / "js" / "admin_chat.js").read_text(encoding="utf-8")
    assert "particle-profile" not in js
    assert "snowContainer" not in js
    assert "createSeasonalParticles" not in js


def test_chat_messages_background_unchanged_in_css_and_index():
    """計画: .chat-messages の背景は季節ロジックで変えない（固定灰）。"""
    css = (REPO_ROOT / "static" / "css" / "main.css").read_text(encoding="utf-8")
    assert "rgba(192, 192, 192, 1)" in css
    idx = (REPO_ROOT / "templates" / "index.html").read_text(encoding="utf-8")
    assert "background: rgba(192, 192, 192, 1)" in idx


def test_is_in_period_each_period_start_end_and_outside():
    """各 SEASON_CONFIG 期間について、境界の前日・翌日は単一期間リストでは False。"""
    for _season, cfg in SEASON_CONFIG.items():
        for p in cfg["period"]:
            sm, sd, em, ed = p
            wraps_new_year = (em < sm) or (em == sm and ed < sd)
            start = JST.localize(datetime(2026, sm, sd, 12, 0, 0))
            if wraps_new_year:
                end = JST.localize(datetime(2027, em, ed, 12, 0, 0))
            else:
                end = JST.localize(datetime(2026, em, ed, 12, 0, 0))
            assert is_in_period(start, [p]), (_season, p, "start")
            assert is_in_period(end, [p]), (_season, p, "end")
            prev = start - timedelta(days=1)
            nxt = end + timedelta(days=1)
            assert not is_in_period(prev, [p]), (_season, p, "prev", prev)
            assert not is_in_period(nxt, [p]), (_season, p, "next", nxt)


def _contrast_ratio_vs_chat_bg(hex_color: str) -> float:
    """#c0c0c0 固定チャット背景に対するコントラスト比（WCAG）。"""
    chat = (192, 192, 192)

    def lum_rgb(rgb):
        def lin(c):
            c /= 255.0
            return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

        r, g, b = rgb
        return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)

    h = hex_color.strip().lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    l1 = lum_rgb((r, g, b))
    l2 = lum_rgb(chat)
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


# docs/ui/PARTICLE_CONTRAST_VERIFICATION.md と整合（配色変更時のみ更新）
EXPECTED_PARTICLE_CONTRAST_VS_CHAT_BG = {
    "autumn": 1.43,
    "christmas": 1.82,
    "enrollment": 1.62,
    "fallback_autumn": 1.43,
    "fallback_spring": 1.71,
    "fallback_summer": 1.7,
    "fallback_winter": 1.82,
    "graduation": 1.5,
    "gw": 1.59,
    "halloween": 1.5,
    "hanami": 1.55,
    "hinamatsuri": 1.51,
    "keiro": 1.66,
    "kodomonomi": 1.59,
    "mothersday": 1.51,
    "newyear": 1.77,
    "setubun": 1.54,
    "shichigosan": 1.71,
    "spring": 1.71,
    "summer": 1.7,
    "tanabata": 1.59,
    "valentine": 1.51,
    "whiteday": 1.67,
    "winter": 1.82,
}


def test_particle_contrast_ratio_snapshot_vs_chat_bg():
    for key, expected in EXPECTED_PARTICLE_CONTRAST_VS_CHAT_BG.items():
        col = PARTICLE_PROFILES[key]["particleColor"]
        got = round(_contrast_ratio_vs_chat_bg(col), 2)
        assert got == expected, f"{key}: got {got} expected {expected}"


def test_event_decoration_pngs_exist():
    """七夕・敬老・HW・七五三の装飾 PNG（img/events/）が実在すること。"""
    rels = [
        "img/events/tanabata/tanabata-bamboo.png",
        "img/events/tanabata/tanabata-streamer.png",
        "img/events/keiro/keiro-carnation-soft.png",
        "img/events/keiro/keiro-gift-soft.png",
        "img/events/halloween/halloween-moon-soft.png",
        "img/events/halloween/halloween-star-soft.png",
        "img/events/shichigosan/shichigosan-chouchin-soft.png",
        "img/events/shichigosan/shichigosan-motif-soft.png",
    ]
    for rel in rels:
        assert (REPO_ROOT / "static" / rel).is_file(), rel
