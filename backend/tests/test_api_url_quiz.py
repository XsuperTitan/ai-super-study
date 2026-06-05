from __future__ import annotations

from fastapi.testclient import TestClient

from app.errors import AppError
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


def test_generate_quiz_from_url_parser_error_returns_clear_code(monkeypatch):
    def fake_parse_url_source(url: str) -> ParsedWebPage:
        raise AppError("URL_NOT_HTML", "该链接不是可解析的普通网页", 400)

    monkeypatch.setattr(webpage_parser, "parse_url_source", fake_parse_url_source)

    response = client.post(
        "/api/v1/quiz/generate",
        json={
            "sourceType": "url",
            "content": "https://example.com/file.pdf",
            "questionCount": 3,
            "questionTypes": ["single_choice"],
            "difficulty": "normal",
        },
    )

    body = response.json()
    assert response.status_code == 400
    assert body["success"] is False
    assert body["error"]["code"] == "URL_NOT_HTML"
    assert "复制正文" in body["error"]["message"] or "普通网页" in body["error"]["message"]


def test_generate_quiz_from_truncated_url_keeps_source_trace_without_model_fallback(monkeypatch):
    content = "RAG 会先检索相关资料，再把资料交给大模型生成回答。这种方式可以减少幻觉，并让回答更容易追溯来源。" * 120

    def fake_parse_url_source(url: str) -> ParsedWebPage:
        return ParsedWebPage(
            url=url,
            title="超长 RAG 文章",
            content=content[:6000],
            warnings=["WEBPAGE_CONTENT_TRUNCATED"],
        )

    monkeypatch.setattr(webpage_parser, "parse_url_source", fake_parse_url_source)

    response = client.post(
        "/api/v1/quiz/generate",
        json={
            "sourceType": "url",
            "content": "https://example.com/long-rag",
            "questionCount": 5,
            "questionTypes": ["single_choice", "true_false"],
            "difficulty": "normal",
        },
    )

    body = response.json()
    assert response.status_code == 200
    quiz = body["data"]["quiz"]
    assert "failed" not in body["data"]["fallbackReason"]
    assert quiz["sourceType"] == "url"
    assert quiz["questionCount"] == 5
    assert all(question["sourceTrace"] for question in quiz["questions"])


def test_generate_quiz_from_wechat_article_html(monkeypatch):
    html = """
    <html><body>
      <h1 id="activity-name">公众号里的 RAG 学习笔记</h1>
      <div id="js_content">
        <p>RAG 会先检索相关资料，再把资料交给大模型生成回答。</p>
        <p>这种方式可以减少幻觉，并让回答更容易追溯来源。</p>
        <p>学习者可以把公众号文章转成题目，通过答题检查自己是否真正理解其中的关键概念。</p>
      </div>
    </body></html>
    """

    monkeypatch.setattr(webpage_parser, "_reject_private_host", lambda host: None)
    monkeypatch.setattr(
        webpage_parser,
        "_fetch_html_page",
        lambda url, transport=None: webpage_parser.FetchedHtml(url="https://mp.weixin.qq.com/s/rag", html=html),
    )

    response = client.post(
        "/api/v1/quiz/generate",
        json={
            "sourceType": "url",
            "content": "https://mp.weixin.qq.com/s/rag",
            "questionCount": 3,
            "questionTypes": ["single_choice", "true_false"],
            "difficulty": "normal",
        },
    )

    body = response.json()
    assert response.status_code == 200
    quiz = body["data"]["quiz"]
    assert quiz["sourceType"] == "url"
    assert quiz["questionCount"] == 3
    assert all(question["sourceTrace"] for question in quiz["questions"])


def test_generate_quiz_from_unparseable_wechat_article_returns_clear_error(monkeypatch):
    html = "<html><body><h1 id='activity-name'>不可解析文章</h1><div id='js_content'>太短</div></body></html>"

    monkeypatch.setattr(webpage_parser, "_reject_private_host", lambda host: None)
    monkeypatch.setattr(
        webpage_parser,
        "_fetch_html_page",
        lambda url, transport=None: webpage_parser.FetchedHtml(url="https://mp.weixin.qq.com/s/short", html=html),
    )

    response = client.post(
        "/api/v1/quiz/generate",
        json={
            "sourceType": "url",
            "content": "https://mp.weixin.qq.com/s/short",
            "questionCount": 3,
            "questionTypes": ["single_choice"],
            "difficulty": "normal",
        },
    )

    body = response.json()
    assert response.status_code == 400
    assert body["success"] is False
    assert body["error"]["code"] == "URL_CONTENT_TOO_SHORT"
    assert "复制正文后重试" in body["error"]["message"]


def test_generate_quiz_from_bilibili_subtitle(monkeypatch):
    html = """
    <html><body>
      <h1 class="video-title">AI 学习路线视频</h1>
      <script>
        window.__playinfo__={"data":{"subtitle":{"subtitles":[{"subtitle_url":"//subtitle.example.com/ai.json"}]}}};
      </script>
    </body></html>
    """
    subtitle = {
        "body": [
            {"content": "学习 AI 时应该先理解机器学习、深度学习和大模型之间的关系。"},
            {"content": "之后通过项目练习提示词设计、数据处理和模型评估，把概念变成可操作能力。"},
            {"content": "最后用输出复盘的方法检查自己是否真正掌握了这些核心知识。"},
        ]
    }

    monkeypatch.setattr(webpage_parser, "_reject_private_host", lambda host: None)
    monkeypatch.setattr(
        webpage_parser,
        "_fetch_html_page",
        lambda url, transport=None: webpage_parser.FetchedHtml(url="https://www.bilibili.com/video/BVAI", html=html),
    )
    monkeypatch.setattr(webpage_parser, "_fetch_json_url", lambda url: subtitle)

    response = client.post(
        "/api/v1/quiz/generate",
        json={
            "sourceType": "url",
            "content": "https://www.bilibili.com/video/BVAI",
            "questionCount": 3,
            "questionTypes": ["single_choice", "true_false"],
            "difficulty": "normal",
        },
    )

    body = response.json()
    assert response.status_code == 200
    quiz = body["data"]["quiz"]
    assert quiz["sourceType"] == "url"
    assert quiz["questionCount"] == 3
    assert all(question["sourceTrace"] for question in quiz["questions"])


def test_generate_quiz_from_bilibili_without_subtitle_uses_description_fallback(monkeypatch):
    html = """
    <html><head><meta name="description" content="这个视频介绍 AI 学习路线，帮助新手理解机器学习、深度学习和大模型之间的关系。"></head><body>
      <h1 class="video-title">无字幕 AI 学习视频</h1>
      <script>
        window.__INITIAL_STATE__={"videoData":{
          "title":"无字幕 AI 学习视频",
          "desc":"视频说明如何从基础概念、项目实践和输出复盘三个阶段学习 AI。",
          "dynamic":"适合把视频简介转成自测题，检查自己是否理解学习路线。"
        }};
      </script>
    </body></html>
    """

    monkeypatch.setattr(webpage_parser, "_reject_private_host", lambda host: None)
    monkeypatch.setattr(
        webpage_parser,
        "_fetch_html_page",
        lambda url, transport=None: webpage_parser.FetchedHtml(url="https://www.bilibili.com/video/BVDESC", html=html),
    )

    response = client.post(
        "/api/v1/quiz/generate",
        json={
            "sourceType": "url",
            "content": "https://www.bilibili.com/video/BVDESC",
            "questionCount": 3,
            "questionTypes": ["single_choice", "true_false"],
            "difficulty": "normal",
        },
    )

    body = response.json()
    assert response.status_code == 200
    quiz = body["data"]["quiz"]
    assert quiz["sourceType"] == "url"
    assert quiz["questionCount"] == 3
    assert all(question["sourceTrace"] for question in quiz["questions"])


def test_generate_quiz_from_bilibili_without_subtitle_and_short_description_returns_clear_error(monkeypatch):
    html = "<html><body><h1 class='video-title'>无字幕视频</h1><script>window.__INITIAL_STATE__={\"videoData\":{\"desc\":\"太短\"}}</script></body></html>"

    monkeypatch.setattr(webpage_parser, "_reject_private_host", lambda host: None)
    monkeypatch.setattr(
        webpage_parser,
        "_fetch_html_page",
        lambda url, transport=None: webpage_parser.FetchedHtml(url="https://www.bilibili.com/video/BV404", html=html),
    )

    response = client.post(
        "/api/v1/quiz/generate",
        json={
            "sourceType": "url",
            "content": "https://www.bilibili.com/video/BV404",
            "questionCount": 3,
            "questionTypes": ["single_choice"],
            "difficulty": "normal",
        },
    )

    body = response.json()
    assert response.status_code == 400
    assert body["success"] is False
    assert body["error"]["code"] == "BILIBILI_SUBTITLE_NOT_FOUND"
    assert "复制字幕" in body["error"]["message"]
