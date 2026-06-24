"""非同期属性抽出のマージロジック"""
from src.utils.allergen_attributes import merge_list_attribute


def test_merge_list_attribute_unions_without_overwrite():
    merged, changed = merge_list_attribute(["糖尿病"], ["花粉症"])
    assert changed is True
    assert merged == ["糖尿病", "花粉症"]


def test_merge_list_attribute_no_duplicate():
    merged, changed = merge_list_attribute(["花粉症"], ["花粉症"])
    assert changed is False
    assert merged == ["花粉症"]


def test_merge_list_attribute_from_string():
    merged, changed = merge_list_attribute([], "ペニシリン、卵")
    assert changed is True
    assert merged == ["ペニシリン", "卵"]
