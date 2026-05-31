from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.errors import AppError

MIN_CONTENT_LENGTH = 2
MAX_CONTENT_LENGTH = 6000
TOPIC_MODE_MAX_LENGTH = 30


@dataclass(frozen=True)
class NormalizedSource:
    source_type: str
    content: str
    title: str
    length: int
    input_mode: str = "content"
    warnings: list[str] = field(default_factory=list)


def normalize_text(content: str, source_type: str = "text") -> NormalizedSource:
    text = str(content or "").strip()
    if len(text) < MIN_CONTENT_LENGTH:
        raise AppError("CONTENT_TOO_SHORT", "至少输入 2 个有效字符后再生成题目", 400)

    warnings: list[str] = []
    if len(text) > MAX_CONTENT_LENGTH:
        text = text[:MAX_CONTENT_LENGTH]
        warnings.append("CONTENT_TRUNCATED")

    title = text[:18] + ("..." if len(text) > 18 else "")
    input_mode = "topic" if _looks_like_topic(text) else "content"
    return NormalizedSource(
        source_type=source_type,
        content=text,
        title=title,
        length=len(text),
        input_mode=input_mode,
        warnings=warnings,
    )


def _looks_like_topic(text: str) -> bool:
    if len(text) > TOPIC_MODE_MAX_LENGTH:
        return False
    return not re.search(r"[。！？.!?；;：:\n]", text)
