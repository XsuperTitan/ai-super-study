from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class StudyHistoryRecord(Base):
    __tablename__ = "study_history_records"
    __table_args__ = (UniqueConstraint("anonymous_id", "history_id", name="uq_history_anonymous_history"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    history_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    anonymous_id: Mapped[str] = mapped_column(String(96), nullable=False, index=True)
    source_content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    source_preview: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    quiz_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    answers_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    report_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False, default="unknown")
    question_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    accuracy: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)
