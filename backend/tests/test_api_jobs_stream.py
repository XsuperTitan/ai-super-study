from __future__ import annotations

import json
import time

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.job_service import job_store


@pytest.fixture(autouse=True)
def clear_jobs():
    job_store.clear()
    yield
    job_store.clear()


client = TestClient(app)


def _quiz_payload(content: str = "费曼学习法强调用自己的话解释概念，并通过复述发现理解漏洞。"):
    return {
        "sourceType": "text",
        "content": content,
        "questionCount": 3,
        "questionTypes": ["single_choice", "true_false"],
        "difficulty": "normal",
    }


def test_create_quiz_job_and_poll_success():
    create_response = client.post("/api/v1/quiz/jobs", json=_quiz_payload())
    body = create_response.json()
    assert create_response.status_code == 200
    job_id = body["data"]["jobId"]
    assert body["data"]["status"] in {"queued", "running", "succeeded"}

    final = None
    for _ in range(20):
        poll_response = client.get(f"/api/v1/jobs/{job_id}")
        assert poll_response.status_code == 200
        final = poll_response.json()["data"]
        if final["status"] == "succeeded":
            break
        time.sleep(0.05)

    assert final is not None
    assert final["status"] == "succeeded"
    assert final["progress"] == 100
    assert final["result"]["quiz"]["questionCount"] == 3
    assert final["result"]["provider"] == "mock"


def test_quiz_job_invalid_input_fails():
    create_response = client.post("/api/v1/quiz/jobs", json=_quiz_payload("A"))
    job_id = create_response.json()["data"]["jobId"]

    final = None
    for _ in range(20):
        final = client.get(f"/api/v1/jobs/{job_id}").json()["data"]
        if final["status"] == "failed":
            break
        time.sleep(0.05)

    assert final is not None
    assert final["status"] == "failed"
    assert final["error"]["code"] == "CONTENT_TOO_SHORT"


def test_unknown_job_returns_404():
    response = client.get("/api/v1/jobs/job_missing")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "JOB_NOT_FOUND"


def test_stream_returns_progress_and_done():
    response = client.post("/api/v1/quiz/generate/stream", json=_quiz_payload())
    assert response.status_code == 200
    events = [json.loads(line) for line in response.text.splitlines() if line.strip()]
    assert events[0]["type"] == "progress"
    assert events[-1]["type"] == "done"
    assert events[-1]["data"]["quiz"]["questionCount"] == 3


def test_stream_invalid_input_returns_error_chunk():
    response = client.post("/api/v1/quiz/generate/stream", json=_quiz_payload("A"))
    assert response.status_code == 200
    events = [json.loads(line) for line in response.text.splitlines() if line.strip()]
    assert events[-1]["type"] == "error"
    assert events[-1]["error"]["code"] == "CONTENT_TOO_SHORT"
