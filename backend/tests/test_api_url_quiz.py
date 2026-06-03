from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.services.webpage_parser import ParsedWebPage
from app.services import webpage_parser

client = TestClient(app)


def test_generate_quiz_from_url(monkeypatch):
    def fake_parse_url_source(url: str) -> ParsedWebPage:
        return ParsedWebPage(
            url=url,
            title="RAG 入门文章",
            content="RAG 会先检索相关资料，再把资料交给大模型生成回答。这种方式可以减少幻觉，并让回答更容易追溯来源。",
        )

    monkeypatch.setattr(webpage_parser, "parse_url_source", fake_parse_url_source)

    response = client.post(
        "/api/v1/quiz/generate",
        json={
            "sourceType": "url",
            "content": "https://example.com/rag",
            "questionCount": 3,
            "questionTypes": ["single_choice", "true_false"],
            "difficulty": "normal",
        },
    )

    body = response.json()
    assert response.status_code == 200
    assert body["success"] is True
    quiz = body["data"]["quiz"]
    assert quiz["sourceType"] == "url"
    assert quiz["questionCount"] == 3


def test_generate_quiz_from_invalid_url_returns_error():
    response = client.post(
        "/api/v1/quiz/generate",
        json={
            "sourceType": "url",
            "content": "not-a-url",
            "questionCount": 3,
            "questionTypes": ["single_choice"],
            "difficulty": "normal",
        },
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "URL_INVALID"
