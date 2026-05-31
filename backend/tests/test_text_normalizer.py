from __future__ import annotations

import pytest

from app.errors import AppError
from app.services.text_normalizer import MAX_CONTENT_LENGTH, normalize_text


def test_normalize_text_preserves_user_input_body():
    source = normalize_text("  费曼学习法\n\n强调   用自己的话解释知识点。  ")
    assert source.content == "费曼学习法\n\n强调   用自己的话解释知识点。"
    assert source.length == len(source.content)


def test_normalize_text_rejects_short_input():
    with pytest.raises(AppError) as exc_info:
        normalize_text("A")
    assert exc_info.value.code == "CONTENT_TOO_SHORT"


def test_normalize_text_accepts_short_topic():
    source = normalize_text("RAG")
    assert source.content == "RAG"
    assert source.input_mode == "topic"


def test_normalize_text_truncates_long_input():
    source = normalize_text("学习" * 4000)
    assert source.length == MAX_CONTENT_LENGTH
    assert "CONTENT_TRUNCATED" in source.warnings
