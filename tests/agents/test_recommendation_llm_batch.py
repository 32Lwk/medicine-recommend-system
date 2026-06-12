"""recommendation_llm_batch の並列 LLM 呼び出しテスト。"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.handlers.chat.recommendation_llm_batch import (
    generate_usage_notes_parallel,
    run_nlu_and_symptom_analysis_parallel,
)


def test_run_nlu_and_symptom_analysis_parallel_merges_results():
    client = MagicMock()
    nlu = {"symptoms": ["頭痛"], "gender_detected": {"detected": False}}
    analysis = {"medicine_type": "解熱鎮痛剤", "symptoms": ["頭痛"]}

    with (
        patch(
            "src.handlers.chat.recommendation_llm_batch.resolve_nlu_for_recommendation",
            return_value=nlu,
        ),
        patch(
            "src.handlers.chat.recommendation_llm_batch.analyze_symptoms_and_medicine_type",
            return_value=analysis,
        ),
    ):
        batch = run_nlu_and_symptom_analysis_parallel("頭が痛い", {}, client, session_id="s1")

    assert batch.nlu_result["symptoms"] == ["頭痛"]
    assert batch.analysis_result["medicine_type"] == "解熱鎮痛剤"


def test_generate_usage_notes_parallel_preserves_order():
    meds = [
        {"name": "A", "product_name": "A"},
        {"name": "B", "product_name": "B"},
        {"name": "C", "product_name": "C"},
    ]

    def _fake_notes(name, *_args, **_kwargs):
        return f"note-{name}"

    with patch(
        "src.core.medicine_logic.generate_usage_notes",
        side_effect=_fake_notes,
    ):
        notes = generate_usage_notes_parallel(
            meds,
            user_info={},
            nlu_result={"symptoms": ["頭痛"]},
        )

    assert len(notes) == 3
    assert notes[0].startswith("<strong>A:</strong>")
    assert notes[1].startswith("<strong>B:</strong>")
    assert notes[2].startswith("<strong>C:</strong>")


def test_run_nlu_and_symptom_analysis_parallel_nlu_fallback():
    client = MagicMock()
    analysis = {"medicine_type": "解熱鎮痛剤", "symptoms": []}

    with (
        patch(
            "src.handlers.chat.recommendation_llm_batch.resolve_nlu_for_recommendation",
            side_effect=RuntimeError("nlu fail"),
        ),
        patch(
            "src.handlers.chat.recommendation_llm_batch.analyze_symptoms_and_medicine_type",
            return_value=analysis,
        ),
    ):
        batch = run_nlu_and_symptom_analysis_parallel("頭が痛い", {}, client)

    assert batch.nlu_result["gender_detected"]["detected"] is False
    assert batch.analysis_result["medicine_type"] == "解熱鎮痛剤"


def test_run_nlu_and_symptom_analysis_parallel_symptom_fallback():
    client = MagicMock()
    nlu = {"symptoms": ["頭痛"], "gender_detected": {"detected": False}, "pregnancy_possible": {"detected": False}}

    with (
        patch(
            "src.handlers.chat.recommendation_llm_batch.resolve_nlu_for_recommendation",
            return_value=nlu,
        ),
        patch(
            "src.handlers.chat.recommendation_llm_batch.analyze_symptoms_and_medicine_type",
            side_effect=RuntimeError("sym fail"),
        ),
    ):
        batch = run_nlu_and_symptom_analysis_parallel("頭が痛い", {}, client)

    assert batch.nlu_result["symptoms"] == ["頭痛"]
    assert batch.analysis_result == {}


def test_run_nlu_and_symptom_analysis_parallel_tasks_start_together():
    import threading
    import time

    client = MagicMock()
    barrier = threading.Barrier(2, timeout=2)
    started = []

    def _slow_nlu(*_args, **_kwargs):
        started.append("nlu")
        barrier.wait()
        return {"gender_detected": {"detected": False}, "pregnancy_possible": {"detected": False}}

    def _slow_sym(*_args, **_kwargs):
        started.append("sym")
        barrier.wait()
        return {"medicine_type": "解熱鎮痛剤", "symptoms": []}

    with (
        patch(
            "src.handlers.chat.recommendation_llm_batch.resolve_nlu_for_recommendation",
            side_effect=_slow_nlu,
        ),
        patch(
            "src.handlers.chat.recommendation_llm_batch.analyze_symptoms_and_medicine_type",
            side_effect=_slow_sym,
        ),
    ):
        t0 = time.perf_counter()
        batch = run_nlu_and_symptom_analysis_parallel("頭が痛い", {}, client)
        elapsed = time.perf_counter() - t0

    assert set(started) == {"nlu", "sym"}
    assert elapsed < 1.5
    assert batch.analysis_result["medicine_type"] == "解熱鎮痛剤"


def test_generate_usage_notes_parallel_faster_than_serial(monkeypatch):
    import time

    meds = [{"name": "A"}, {"name": "B"}, {"name": "C"}]

    def _slow_notes(name, *_a, **_k):
        time.sleep(0.05)
        return f"note-{name}"

    monkeypatch.setattr(
        "src.core.medicine_logic.generate_usage_notes",
        _slow_notes,
    )
    t0 = time.perf_counter()
    notes = generate_usage_notes_parallel(meds, user_info={}, nlu_result={})
    parallel_elapsed = time.perf_counter() - t0

    assert len(notes) == 3
    assert parallel_elapsed < 0.14


def test_generate_usage_notes_parallel_faster_than_serial_with_200ms(monkeypatch):
    """p1-un-03: sleep(0.2)x3 の並列が直列より短いこと。"""
    import time

    meds = [{"name": "A"}, {"name": "B"}, {"name": "C"}]

    def _slow_notes(name, *_a, **_k):
        time.sleep(0.2)
        return f"note-{name}"

    monkeypatch.setattr(
        "src.core.medicine_logic.generate_usage_notes",
        _slow_notes,
    )
    t0 = time.perf_counter()
    notes = generate_usage_notes_parallel(meds, user_info={}, nlu_result={})
    parallel_elapsed = time.perf_counter() - t0

    t1 = time.perf_counter()
    for m in meds:
        _slow_notes(m.get("name"), m, {}, {})
    serial_elapsed = time.perf_counter() - t1

    assert len(notes) == 3
    assert parallel_elapsed < serial_elapsed * 0.8


def test_generate_usage_notes_parallel_matches_serial_html(monkeypatch):
    meds = [
        {"name": "A", "product_name": "A"},
        {"name": "B", "product_name": "B"},
    ]

    def _fake_notes(name, *_a, **_k):
        return f"note-{name}"

    monkeypatch.setattr(
        "src.core.medicine_logic.generate_usage_notes",
        _fake_notes,
    )
    parallel = generate_usage_notes_parallel(meds, user_info={}, nlu_result={})
    serial = []
    for medicine in meds[:3]:
        name = medicine.get("name") or ""
        text = _fake_notes(name, medicine, {}, {})
        serial.append(f"<strong>{name}:</strong><br>{text}")
    assert parallel == serial
