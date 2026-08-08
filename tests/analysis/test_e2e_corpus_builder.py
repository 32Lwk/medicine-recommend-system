"""e2e_corpus_builder — dedupe / bucket / balance."""
from __future__ import annotations

from src.analysis.e2e_corpus_builder import (
    ReplayScenario,
    balance_corpus,
    cluster_dedupe_scenarios,
    infer_e2e_bucket,
    is_valid_user_turn,
    sanitize_user_text,
    scenario_signature,
)


def test_sanitize_user_text_masks_email():
    out = sanitize_user_text("連絡は test@example.com で")
    assert "[EMAIL]" in out
    assert "example.com" not in out


def test_infer_bucket_comparison():
    assert infer_e2e_bucket("どっちがいい？", setup=["頭が痛い"]) == "comparison"


def test_infer_bucket_medicine_thread_followup():
    assert infer_e2e_bucket("家にもある", setup=["ロキソニンの写真見せて"]) == "medicine_thread"


def test_cluster_dedupe_keeps_longer_setup():
    a = ReplayScenario("a", "medicine_thread", [], "うちにも", "t", signature="x")
    b = ReplayScenario(
        "b",
        "medicine_thread",
        ["ロキソニン見せて"],
        "うちにも",
        "t",
        signature="x",
    )
    b.signature = scenario_signature(b.bucket, b.setup, b.input)
    a.signature = b.signature
    out = cluster_dedupe_scenarios([a, b])
    assert len(out) == 1
    assert len(out[0].setup) == 1


def test_rejects_assistant_like_turn():
    assert not is_valid_user_turn("お子さんの体調が心配ですね。特にぐったりしている場合や呼吸が苦しそうなときは、すぐに受診を考えることが重要です。")


def test_accepts_short_user_question():
    assert is_valid_user_turn("ロキソニンの副作用教えて")


def test_balance_generates_fill_when_empty():
    selected, stats = balance_corpus([], quotas={"greeting_short": 2}, total=2)
    assert len(selected) == 2
    assert stats["generated"].get("greeting_short", 0) >= 1
