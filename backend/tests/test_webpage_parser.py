from __future__ import annotations

import pytest

from app.errors import AppError
from app.services import webpage_parser


def test_extract_text_prefers_article_content():
    html = """
    <html>
      <head><title>测试文章</title></head>
      <body>
        <nav>导航内容</nav>
          <article>
            <h1>检索增强生成</h1>
            <p>RAG 会先检索相关资料，再把资料交给大模型生成回答。</p>
            <p>这种方式可以减少幻觉，并让回答更容易追溯来源。</p>
            <p>在学习场景中，用户可以把网页内容转成问题，用答题来检查自己是否真正理解文章中的关键概念。</p>
          </article>
      </body>
    </html>
    """

    page = webpage_parser._extract_text("https://example.com/rag", html)

    assert page.title == "测试文章"
    assert "RAG 会先检索相关资料" in page.content
    assert "导航内容" not in page.content


def test_extract_text_rejects_too_short_content():
    with pytest.raises(AppError) as exc:
        webpage_parser._extract_text("https://example.com/empty", "<html><body><p>太短</p></body></html>")

    assert exc.value.code == "URL_CONTENT_TOO_SHORT"


def test_validate_url_rejects_non_http_url():
    with pytest.raises(AppError) as exc:
        webpage_parser._validate_url("file:///etc/passwd")

    assert exc.value.code == "URL_INVALID"
