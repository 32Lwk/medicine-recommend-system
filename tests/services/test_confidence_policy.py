"""ConfidencePolicy — Physical/Ask/Emotional 低確信の統一方針"""
from unittest.mock import patch

from src.services.confidence_policy import should_defer_category_routing


@patch("config.routing_config.triage_confidence_threshold", return_value=0.75)
def test_defer_physical_ask_emotional_below_threshold(_thresh):
    session = {}
    assert should_defer_category_routing("Physical", 0.5, session) is True
    assert should_defer_category_routing("Ask", 0.4, session) is True
    assert should_defer_category_routing("Emotional", 0.6, session) is True


@patch("config.routing_config.triage_confidence_threshold", return_value=0.75)
def test_allow_at_or_above_threshold(_thresh):
    assert should_defer_category_routing("Physical", 0.75, {}) is False
    assert should_defer_category_routing("Emotional", 0.9, {}) is False


@patch("config.routing_config.triage_confidence_threshold", return_value=0.75)
def test_defer_when_confidence_gate_concierge_flag(_thresh):
    session = {"_confidence_gate_concierge": True}
    assert should_defer_category_routing("Physical", 0.99, session) is True


@patch("config.routing_config.triage_confidence_threshold", return_value=0.75)
def test_other_category_not_deferred(_thresh):
    assert should_defer_category_routing("Other", 0.1, {}) is False
    assert should_defer_category_routing("Emergency", 0.1, {}) is False
