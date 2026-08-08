"""non_human_patient_guard の単体テスト。"""
from src.services.non_human_patient_guard import is_non_human_patient_query
from src.services.store_emergency_handler import detect_store_emergency


def test_pet_medicine_query_detected():
    assert is_non_human_patient_query(
        "うちの犬が咳してるんですが、人間の風邪薬あげていい？"
    )


def test_human_allergy_not_pet_redirect():
    assert not is_non_human_patient_query("犬アレルギーで目がかゆい")


def test_insulin_not_theft_emergency():
    assert detect_store_emergency(
        "インスリン打ってるんですが、風邪薬飲んでも大丈夫？"
    ) is None
