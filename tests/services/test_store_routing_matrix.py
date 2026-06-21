"""店舗案内系フレーズのルーティング優先度マトリクス"""
import pytest

from src.agents.concierge_agent import should_concierge_handle
from src.services.store_inquiry_handler import is_probable_store_inquiry

_TRIAGE_OTHER = {"category": "Other", "confidence": 0.8, "subcategory": "general_other"}


@pytest.mark.parametrize(
    "text",
    [
        "トイレどこ？",
        "お手洗いは？",
        "レジどこ",
        "忘れ物拾いました",
        "落とし物を拾った",
        "営業時間は？",
        "駐車場はありますか",
        "免税できますか",
        "歯ブラシはどこ？",
        "コンビニはどこ？",
        "店内の売場案内",
        "近くのコンビニはどこ？",
    ],
)
def test_store_phrases_skip_concierge(text: str):
    assert is_probable_store_inquiry(text, _TRIAGE_OTHER) is True
    assert should_concierge_handle(text, _TRIAGE_OTHER) is False


@pytest.mark.parametrize(
    "text",
    [
        "大学はどこ？",
        "こんにちは",
        "頭が痛い",
    ],
)
def test_non_store_phrases_not_probable_store(text: str):
    assert is_probable_store_inquiry(text, _TRIAGE_OTHER) is False
