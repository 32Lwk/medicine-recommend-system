"""ExplanationAgent parallel"""
from unittest.mock import MagicMock, patch


@patch("src.core.explanation_generator.generate_usage_notes_and_consultation_with_gpt", return_value={})
@patch("src.core.explanation_generator.generate_explanation", return_value="説明")
def test_parallel_explanations(_exp, _notes):
    from src.agents.explanation_agent import generate_explanations_for_recommendation

    meds = [{"product_name": f"M{i}"} for i in range(3)]
    out = generate_explanations_for_recommendation(meds, {}, {}, MagicMock())
    assert len(out["explanations"]) == 3
    assert out["explanations"][0] == "説明"
