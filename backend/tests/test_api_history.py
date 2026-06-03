from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app import models  # noqa: F401


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)


def _payload(history_id: str, anonymous_id: str = "anon_a", accuracy: int = 80):
    return {
        "anonymousId": anonymous_id,
        "historyId": history_id,
        "sourceContent": "费曼学习法强调复述、暴露漏洞和迁移应用。",
        "quiz": {
            "quizId": history_id,
            "title": "关于费曼学习法的闯关",
            "questionCount": 3,
            "questions": [{"id": "q1", "answer": "A"}],
            "modelProvider": "mock",
        },
        "answers": [{"questionId": "q1", "selectedOption": "A", "isCorrect": True, "duration": 3}],
        "report": {"reportId": f"report_{history_id}", "quizId": history_id, "accuracy": accuracy, "score": accuracy},
        "provider": "mock",
        "questionCount": 3,
        "accuracy": accuracy,
        "score": accuracy,
    }


def test_save_history_success(client: TestClient):
    response = client.post("/api/v1/history", json=_payload("quiz_1"))

    body = response.json()
    assert response.status_code == 200
    assert body["success"] is True
    record = body["data"]["record"]
    assert record["historyId"] == "quiz_1"
    assert record["provider"] == "mock"
    assert record["accuracy"] == 80
    assert record["quiz"]["quizId"] == "quiz_1"


def test_list_history_is_scoped_by_anonymous_id(client: TestClient):
    client.post("/api/v1/history", json=_payload("quiz_a", "anon_a"))
    client.post("/api/v1/history", json=_payload("quiz_b", "anon_b"))

    response = client.get("/api/v1/history", params={"anonymousId": "anon_a"})

    records = response.json()["data"]["records"]
    assert response.status_code == 200
    assert [record["historyId"] for record in records] == ["quiz_a"]


def test_list_history_returns_recent_ten_in_updated_order(client: TestClient):
    for index in range(12):
        client.post("/api/v1/history", json=_payload(f"quiz_{index}", "anon_a", accuracy=50 + index))

    response = client.get("/api/v1/history", params={"anonymousId": "anon_a"})

    records = response.json()["data"]["records"]
    assert response.status_code == 200
    assert len(records) == 10
    assert [record["historyId"] for record in records][:3] == ["quiz_11", "quiz_10", "quiz_9"]
    assert "quiz_0" not in {record["historyId"] for record in records}


def test_delete_history_hides_record(client: TestClient):
    client.post("/api/v1/history", json=_payload("quiz_delete", "anon_a"))

    delete_response = client.delete("/api/v1/history/quiz_delete", params={"anonymousId": "anon_a"})
    list_response = client.get("/api/v1/history", params={"anonymousId": "anon_a"})

    assert delete_response.status_code == 200
    assert list_response.json()["data"]["records"] == []


def test_clear_history_only_affects_current_anonymous_id(client: TestClient):
    client.post("/api/v1/history", json=_payload("quiz_a", "anon_a"))
    client.post("/api/v1/history", json=_payload("quiz_b", "anon_b"))

    response = client.delete("/api/v1/history", params={"anonymousId": "anon_a"})

    assert response.status_code == 200
    assert response.json()["data"]["deleted"] == 1
    assert client.get("/api/v1/history", params={"anonymousId": "anon_a"}).json()["data"]["records"] == []
    records_b = client.get("/api/v1/history", params={"anonymousId": "anon_b"}).json()["data"]["records"]
    assert [record["historyId"] for record in records_b] == ["quiz_b"]
