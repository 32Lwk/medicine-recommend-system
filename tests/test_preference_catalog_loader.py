"""嗜好キーワードカタログの読み込み"""
from src.core.dictionary_loader import (
    clear_cache,
    load_preference_keyword_catalog,
)


class TestPreferenceCatalogLoader:
    def setup_method(self):
        clear_cache()

    def test_loads_categories_and_safety(self):
        catalog = load_preference_keyword_catalog()
        assert catalog.get("version") == 1
        assert catalog.get("score_apply_min_confidence") == 0.5
        assert catalog.get("exclude_apply_min_confidence") == 0.8
        fields = {c["preference_field"] for c in catalog.get("categories", [])}
        assert "avoid_drowsiness" in fields
        assert "avoid_nasal_route" in fields
        assert "運転" in catalog.get("safety_hard_keywords", [])

    def test_risk_exclude_rules_present(self):
        catalog = load_preference_keyword_catalog()
        rules = catalog.get("risk_exclude_rules") or []
        assert any(r.get("when", {}).get("field") == "avoid_drowsiness" for r in rules)
        assert catalog.get("ingredient_groups", {}).get("first_gen_antihistamine")

    def test_cached_second_load(self):
        a = load_preference_keyword_catalog()
        b = load_preference_keyword_catalog()
        assert a is b
