import os
import sys
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import main  # noqa: E402


def run():
    c = TestClient(main.app)
    r = c.post(
        "/api/submit_feedback",
        json={"report_type": "bug_report", "user_message": "u", "ai_response": "a"},
    )
    print("status", r.status_code)
    print("content-type", r.headers.get("content-type"))
    print("body", r.text)


if __name__ == "__main__":
    run()

