from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _quiz_payload():
    return {
        "sourceType": "text",
        "content": "碎片化学习需要及时复盘和自测，否则知识容易停留在看过但不会用的状态。",
        "questionCount": 3,
        "questionTypes": ["single_choice", "true_false"],
        "difficulty": "normal",
    }


def test_generate_report_success():
    quiz = client.post("/api/v1/quiz/generate", json=_quiz_payload()).json()["data"]["quiz"]
    answers = [
        {
            "questionId": question["id"],
            "selectedOption": question["answer"],
            "isCorrect": False,
            "duration": 3,
        }
        for question in quiz["questions"]
    ]
    response = client.post(
        "/api/v1/reports/generate",
        json={"quizId": quiz["quizId"], "questions": quiz["questions"], "answers": answers, "duration": 9},
    )
    body = response.json()
    assert response.status_code == 200
    assert body["success"] is True
    report = body["data"]["report"]
    assert report["accuracy"] == 100
    assert report["correctCount"] == 3
    assert report["total"] == 3
    assert report["reviewAdvice"]


def test_generate_report_with_empty_answers():
    quiz = client.post("/api/v1/quiz/generate", json=_quiz_payload()).json()["data"]["quiz"]
    response = client.post(
        "/api/v1/reports/generate",
        json={"quizId": quiz["quizId"], "questions": quiz["questions"], "answers": [], "duration": 0},
    )
    report = response.json()["data"]["report"]
    assert response.status_code == 200
    assert report["accuracy"] == 0
    assert report["wrongCount"] == 3
