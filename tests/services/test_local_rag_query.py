"""local_rag_query — 口語・言い換えの一般化テスト（fixture 文字列の丸写しは避ける）。"""
from __future__ import annotations

import pytest

from src.services.local_rag_query import (
    expand_concepts,
    extract_brand_tokens,
    extract_coordination_pairs,
    infer_medicine_category,
    _explicit_substance_mention_count,
)
from src.services.local_rag_router import infer_medicine_category as router_infer


@pytest.mark.parametrize(
    "query,expected",
    [
        ("バファリンとイブ、同日にダメ？", "interaction"),
        ("血をサラサラにする薬とロキソ、一緒でいい？", "interaction"),
        (
            "血液をサラサラにする薬とロキソプロフェンを一緒に服用してもよろしいでしょうか？",
            "interaction",
        ),
        ("この解熱剤で眠くなるの普通？", "side_effect"),
        ("この痛み止め飲んだら、めっちゃ眠たくなるわ。", "side_effect"),
        (
            "イブプロフェンを服用した際に、お腹がきつくなった経験をお持ちの方はいらっしゃいますでしょうか。",
            "side_effect",
        ),
        ("イブプロフェン飲んで、お腹張ったことある人おる？", "side_effect"),
        ("この痛み止め飲んだら、めっちゃ眠なるんやけど。", "side_effect"),
        ("ご飯の後に飲む方がマシ？", "usage"),
        ("お水いらずで飲める？", "usage"),
        ("うちの小4、市販薬使える？", "age"),
        ("大会前の点鼻、禁止？", "doping"),
    ],
)
def test_infer_category_colloquial(query: str, expected: str) -> None:
    assert router_infer(query) == expected


def test_brand_not_inside_longer_ingredient_name() -> None:
    assert extract_brand_tokens("イブプロフェン錠") == []


def test_coordination_does_not_split_koto() -> None:
    pairs = extract_coordination_pairs("イブプロフェンでお腹がキツくなったことある？")
    assert not any("こと" in p for p in pairs)


def test_concept_expansion_adds_canonical_terms() -> None:
    expanded = expand_concepts("エナドリと麻黄")
    assert "カフェイン" in expanded
    assert "エフェドリン" in expanded


def test_explicit_count_ignores_usage_phrases() -> None:
    assert _explicit_substance_mention_count("お水なしで飲んでも平気？") == 0


def test_usage_beats_false_interaction_on_interval_question() -> None:
    q = "解熱剤、4時間以内にまた飲んでも平気？"
    assert infer_medicine_category(q) == "usage"
    assert router_infer(q) == "usage"


def test_context_side_effect_followup_beats_usage() -> None:
    history = [
        {"role": "user", "content": "頭痛がひどいです"},
        {"role": "assistant", "content": "ロキソニンをご検討ください"},
        {"role": "user", "content": "この薬、飲むとすごく眠くなるんですが普通ですか？"},
    ]
    q = history[-1]["content"]
    assert (
        router_infer(
            q,
            conversation_history=history,
            recommended_medicines=["ロキソニン"],
        )
        == "side_effect"
    )


def test_context_age_from_prior_turn() -> None:
    history = [
        {"role": "user", "content": "うちの子は小学1年生です"},
        {"role": "assistant", "content": "お子さんの症状を教えてください"},
        {"role": "user", "content": "市販の風邪薬使ってもいい？"},
    ]
    q = history[-1]["content"]
    assert router_infer(q, conversation_history=history) == "age"
