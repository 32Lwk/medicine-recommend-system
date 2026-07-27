"""looks_like_inquiry — 口語・省略形の問い合わせ検出"""
import pytest

from src.services.concierge_intent import looks_like_inquiry, looks_like_user_question


@pytest.mark.parametrize(
    "text,expect_inquiry",
    [
        ("ロキソニンの副作用は？", True),
        ("風邪薬教えて", True),
        ("ポケモンの最新アップデート教えて", True),
        ("頭痛がする", False),
        ("うん", False),
        ("了解", False),
        ("陸上競技でも使える？", True),
        ("暇だから話相手になって", True),
        ("寂しいから誰か話聞いて", True),
        ("頭痛", False),
    ],
)
def test_looks_like_inquiry(text, expect_inquiry):
    assert looks_like_inquiry(text) is expect_inquiry


def test_looks_like_user_question_subset_of_inquiry():
    samples = ["副作用は？", "教えて", "頭痛"]
    for s in samples:
        if looks_like_user_question(s):
            assert looks_like_inquiry(s)
