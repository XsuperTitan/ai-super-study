from __future__ import annotations

import httpx
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


def test_extract_text_falls_back_to_body_when_no_article_or_main():
    html = """
    <html>
      <head><meta property="og:title" content="正文回退测试"></head>
      <body>
        <header>页头导航</header>
        <section>
          <div>网页没有 article 或 main 标签，但 body 中仍然有足够正文内容用于提炼学习问题。</div>
          <div>这里补充第二段正文，说明解析器需要在结构不理想时继续保留可读文本，而不是直接失败。</div>
        </section>
      </body>
    </html>
    """

    page = webpage_parser._extract_text("https://example.com/body", html)

    assert page.title == "正文回退测试"
    assert "没有 article 或 main 标签" in page.content
    assert "页头导航" not in page.content


def test_extract_text_deduplicates_repeated_paragraphs():
    paragraph = "RAG 会先检索相关资料，再把资料交给大模型生成回答，这样能减少幻觉并提高可追溯性。"
    html = f"""
    <html><body><article>
      <p>{paragraph}</p>
      <p>{paragraph}</p>
      <p>学习者可以把网页转成题目，并通过答题发现自己没有理解稳固的概念，再根据解析回到原文复盘关键证据。</p>
    </article></body></html>
    """

    page = webpage_parser._extract_text("https://example.com/dedupe", html)

    assert page.content.count(paragraph) == 1


def test_extract_text_truncates_long_content_with_warning(monkeypatch):
    monkeypatch.setattr(webpage_parser, "MAX_EXTRACTED_TEXT_LENGTH", 120)
    long_text = "RAG 可以帮助回答追溯来源。" * 30
    html = f"<html><body><article><p>{long_text}</p></article></body></html>"

    page = webpage_parser._extract_text("https://example.com/long", html)

    assert len(page.content) == 120
    assert page.warnings == ["WEBPAGE_CONTENT_TRUNCATED"]


def test_validate_url_rejects_non_http_url():
    with pytest.raises(AppError) as exc:
        webpage_parser._validate_url("file:///etc/passwd")

    assert exc.value.code == "URL_INVALID"


def test_validate_url_rejects_private_host():
    with pytest.raises(AppError) as exc:
        webpage_parser._validate_url("http://127.0.0.1/admin")

    assert exc.value.code == "URL_PRIVATE_HOST_BLOCKED"


def test_fetch_html_rejects_non_html_response():
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, headers={"content-type": "application/json"}, json={"ok": True})
    )

    with pytest.raises(AppError) as exc:
        webpage_parser._fetch_html("https://example.com/data", transport=transport)

    assert exc.value.code == "URL_NOT_HTML"


def test_fetch_html_follows_redirect_to_public_html(monkeypatch):
    monkeypatch.setattr(webpage_parser, "_reject_private_host", lambda host: None)

    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == "https://example.com/start":
            return httpx.Response(302, headers={"location": "/final"})
        return httpx.Response(
            200,
            headers={"content-type": "text/html; charset=utf-8"},
            content="<html><body><p>重定向后的公开网页正文可以被正常读取并进入后续解析流程。</p></body></html>",
        )

    html = webpage_parser._fetch_html("https://example.com/start", transport=httpx.MockTransport(handler))

    assert "重定向后的公开网页正文" in html


def test_fetch_html_rejects_redirect_to_private_host():
    transport = httpx.MockTransport(
        lambda request: httpx.Response(302, headers={"location": "http://127.0.0.1/private"})
    )

    with pytest.raises(AppError) as exc:
        webpage_parser._fetch_html("https://example.com/start", transport=transport)

    assert exc.value.code == "URL_PRIVATE_HOST_BLOCKED"


def test_fetch_html_rejects_too_many_redirects(monkeypatch):
    monkeypatch.setattr(webpage_parser, "_reject_private_host", lambda host: None)
    transport = httpx.MockTransport(lambda request: httpx.Response(302, headers={"location": "/again"}))

    with pytest.raises(AppError) as exc:
        webpage_parser._fetch_html("https://example.com/start", transport=transport)

    assert exc.value.code == "URL_REDIRECT_TOO_MANY"


def test_fetch_html_limits_download_size(monkeypatch):
    monkeypatch.setattr(webpage_parser, "MAX_FETCH_BYTES", 24)
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            headers={"content-type": "text/html; charset=utf-8"},
            content=b"<html><body>" + b"x" * 100,
        )
    )

    html = webpage_parser._fetch_html("https://example.com/large", transport=transport)

    assert len(html.encode("utf-8")) == 24


def test_is_wechat_article_url_detects_mp_weixin_host():
    assert webpage_parser._is_wechat_article_url("https://mp.weixin.qq.com/s/example") is True
    assert webpage_parser._is_wechat_article_url("https://example.com/s/example") is False


def test_extract_wechat_text_prefers_activity_name_and_js_content():
    html = """
    <html>
      <head>
        <title>备用标题</title>
        <meta property="og:title" content="OG 标题">
      </head>
      <body>
        <header>顶部导航</header>
        <h1 id="activity-name">  RAG 公众号深度文章  </h1>
        <div id="js_content">
          <script>window.noise = true</script>
          <p>RAG 会先检索相关资料，再把资料交给大模型生成回答。</p>
          <section><span>这种方式可以减少幻觉，并让回答更容易追溯来源。</span></section>
          <p>学习者可以把公众号文章转成题目，通过答题检查自己是否真正理解其中的关键概念。</p>
        </div>
        <footer>底部广告</footer>
      </body>
    </html>
    """

    page = webpage_parser._extract_wechat_text("https://mp.weixin.qq.com/s/example", html)

    assert page.title == "RAG 公众号深度文章"
    assert "RAG 会先检索相关资料" in page.content
    assert "可以减少幻觉" in page.content
    assert "顶部导航" not in page.content
    assert "底部广告" not in page.content
    assert "window.noise" not in page.content


def test_extract_wechat_text_uses_rich_media_content_fallback():
    html = """
    <html><body>
      <div class="rich_media_content">
        <p>这篇文章介绍如何把碎片化知识转成自测题，帮助学习者从被动阅读转向主动回忆。</p>
        <p>它强调先提炼核心观点，再通过单选题和判断题检查理解是否稳固，并在答错时回到原文重新定位证据。</p>
      </div>
    </body></html>
    """

    page = webpage_parser._extract_wechat_text("https://mp.weixin.qq.com/s/fallback", html)

    assert "碎片化知识转成自测题" in page.content


def test_extract_wechat_text_rejects_too_short_content():
    html = "<html><body><h1 id='activity-name'>短文</h1><div id='js_content'>太短</div></body></html>"

    with pytest.raises(AppError) as exc:
        webpage_parser._extract_wechat_text("https://mp.weixin.qq.com/s/short", html)

    assert exc.value.code == "URL_CONTENT_TOO_SHORT"


def test_extract_wechat_text_truncates_long_content_with_warning(monkeypatch):
    monkeypatch.setattr(webpage_parser, "MAX_EXTRACTED_TEXT_LENGTH", 100)
    long_text = "公众号文章可以被解析为学习正文，并进一步生成互动题目。" * 20
    html = f"<html><body><div id='js_content'>{long_text}</div></body></html>"

    page = webpage_parser._extract_wechat_text("https://mp.weixin.qq.com/s/long", html)

    assert len(page.content) == 100
    assert page.warnings == ["WEBPAGE_CONTENT_TRUNCATED"]


def test_parse_url_source_routes_final_wechat_url(monkeypatch):
    html = """
    <html><body>
      <h1 id="activity-name">公众号最终链接</h1>
      <div id="js_content">
        <p>即使初始链接经过跳转，只要最终地址是公众号文章，也应使用公众号正文抽取规则。</p>
        <p>这个规则可以保留文章主体，过滤页面周边噪声，并继续进入现有出题流程，帮助用户把阅读内容转成可反馈的测验。</p>
      </div>
    </body></html>
    """

    monkeypatch.setattr(webpage_parser, "_reject_private_host", lambda host: None)
    monkeypatch.setattr(
        webpage_parser,
        "_fetch_html_page",
        lambda url, transport=None: webpage_parser.FetchedHtml(url="https://mp.weixin.qq.com/s/final", html=html),
    )

    page = webpage_parser.parse_url_source("https://example.com/redirect")

    assert page.url == "https://mp.weixin.qq.com/s/final"
    assert page.title == "公众号最终链接"
    assert "最终地址是公众号文章" in page.content
