from __future__ import annotations

import ipaddress
import re
import socket
from dataclasses import dataclass, field
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from app.errors import AppError

MAX_FETCH_BYTES = 1_000_000
MAX_EXTRACTED_TEXT_LENGTH = 6000
MIN_EXTRACTED_TEXT_LENGTH = 80
FETCH_TIMEOUT_SECONDS = 12.0


@dataclass(frozen=True)
class ParsedWebPage:
    url: str
    title: str
    content: str
    warnings: list[str] = field(default_factory=list)


def parse_url_source(url: str) -> ParsedWebPage:
    safe_url = _validate_url(url)
    html = _fetch_html(safe_url)
    return _extract_text(safe_url, html)


def _validate_url(url: str) -> str:
    value = str(url or "").strip()
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise AppError("URL_INVALID", "请输入有效的 http 或 https 网页链接", 400)
    host = parsed.hostname
    if not host:
        raise AppError("URL_INVALID", "请输入有效的网页链接", 400)
    _reject_private_host(host)
    return value


def _reject_private_host(host: str) -> None:
    try:
        addresses = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise AppError("URL_RESOLVE_FAILED", "无法解析该网页域名", 400) from exc

    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved:
            raise AppError("URL_PRIVATE_HOST_BLOCKED", "暂不支持解析内网或本机地址", 400)


def _fetch_html(url: str) -> str:
    headers = {
        "User-Agent": "AI-Super-Questions/0.1 (+https://example.local) Mozilla/5.0",
        "Accept": "text/html,application/xhtml+xml",
    }
    try:
        with httpx.Client(follow_redirects=True, timeout=FETCH_TIMEOUT_SECONDS, headers=headers) as client:
            response = client.get(url)
            response.raise_for_status()
    except httpx.TimeoutException as exc:
        raise AppError("URL_FETCH_TIMEOUT", "网页读取超时，请复制正文后重试", 504) from exc
    except httpx.HTTPStatusError as exc:
        raise AppError("URL_FETCH_FAILED", f"网页读取失败，HTTP {exc.response.status_code}", 400) from exc
    except httpx.HTTPError as exc:
        raise AppError("URL_FETCH_FAILED", "网页读取失败，请确认链接可公开访问", 400) from exc

    content_type = response.headers.get("content-type", "")
    if "text/html" not in content_type and "application/xhtml+xml" not in content_type:
        raise AppError("URL_NOT_HTML", "该链接不是可解析的普通网页", 400)

    body = response.content[:MAX_FETCH_BYTES]
    return body.decode(response.encoding or "utf-8", errors="ignore")


def _extract_text(url: str, html: str) -> ParsedWebPage:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg", "canvas", "iframe", "nav", "footer", "header", "form"]):
        tag.decompose()

    title = _title(soup, url)
    container = soup.select_one("article") or soup.select_one("main") or soup.body or soup
    pieces = []
    for tag in container.find_all(["h1", "h2", "h3", "p", "li", "blockquote"]):
        text = _clean_text(tag.get_text(" ", strip=True))
        if len(text) >= 8:
            pieces.append(text)

    if not pieces:
        text = _clean_text(container.get_text(" ", strip=True))
    else:
        text = "\n".join(_dedupe_keep_order(pieces))

    warnings: list[str] = []
    if len(text) > MAX_EXTRACTED_TEXT_LENGTH:
        text = text[:MAX_EXTRACTED_TEXT_LENGTH]
        warnings.append("WEBPAGE_CONTENT_TRUNCATED")

    if len(text) < MIN_EXTRACTED_TEXT_LENGTH:
        raise AppError("URL_CONTENT_TOO_SHORT", "网页正文太少，请复制正文后重试", 400)

    return ParsedWebPage(url=url, title=title, content=text, warnings=warnings)


def _title(soup: BeautifulSoup, url: str) -> str:
    candidates = [
        soup.select_one("meta[property='og:title']"),
        soup.select_one("meta[name='twitter:title']"),
        soup.title,
        soup.select_one("h1"),
    ]
    for candidate in candidates:
        if not candidate:
            continue
        text = candidate.get("content") if candidate.name == "meta" else candidate.get_text(" ", strip=True)
        text = _clean_text(text or "")
        if text:
            return text[:80]
    return urlparse(url).netloc or "网页内容"


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _dedupe_keep_order(items: list[str]) -> list[str]:
    seen = set()
    result = []
    for item in items:
        key = item[:120]
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result
