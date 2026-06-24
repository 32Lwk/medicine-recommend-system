"""counseling_processor が generate_counseling_response を解決できること"""


def test_counseling_processor_exports_generate_counseling_response():
    from src.services.counseling import counseling_processor

    assert callable(counseling_processor.generate_counseling_response)
