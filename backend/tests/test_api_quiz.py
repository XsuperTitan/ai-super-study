from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_generate_quiz_success():
    response = client.post(
        "/api/v1/quiz/generate",
        json={
            "sourceType": "text",
            "content": "费曼学习法强调用自己的话解释一个概念，通过简单表达暴露理解漏洞，再回到资料中修正。",
            "questionCount": 3,
            "questionTypes": ["single_choice", "true_false"],
            "difficulty": "normal",
        },
    )
    body = response.json()
    assert response.status_code == 200
    assert body["success"] is True
    quiz = body["data"]["quiz"]
    assert quiz["questionCount"] == 3
    assert len(quiz["questions"]) == 3
    for question in quiz["questions"]:
        assert question["answer"] in {option["id"] for option in question["options"]}


def test_generate_quiz_accepts_short_topic():
    response = client.post(
        "/api/v1/quiz/generate",
        json={
            "sourceType": "text",
            "content": "RAG",
            "questionCount": 3,
            "questionTypes": ["single_choice", "true_false"],
            "difficulty": "normal",
        },
    )
    body = response.json()
    assert response.status_code == 200
    assert body["success"] is True
    assert body["data"]["quiz"]["questionCount"] == 3


def test_generate_quiz_rejects_too_short_content():
    response = client.post(
        "/api/v1/quiz/generate",
        json={"sourceType": "text", "content": "A", "questionCount": 3, "questionTypes": ["single_choice"], "difficulty": "normal"},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "CONTENT_TOO_SHORT"


def test_generate_quiz_rejects_illegal_question_count():
    response = client.post(
        "/api/v1/quiz/generate",
        json={"sourceType": "text", "content": "这是一段足够长的学习内容，用于测试非法题量。", "questionCount": 4},
    )
    assert response.status_code == 422
