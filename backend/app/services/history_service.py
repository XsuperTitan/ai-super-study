from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.errors import AppError
from app.models import StudyHistoryRecord
from app.schemas import HistoryRecordResponse, SaveHistoryRequest

MAX_HISTORY_COUNT = 10


def save_history(db: Session, payload: SaveHistoryRequest) -> HistoryRecordResponse:
    history_id = _history_id(payload)
    existing = db.execute(
        select(StudyHistoryRecord).where(
            StudyHistoryRecord.anonymous_id == payload.anonymousId,
            StudyHistoryRecord.history_id == history_id,
        )
    ).scalar_one_or_none()

    now = datetime.now(timezone.utc)
    if existing is None:
        record = StudyHistoryRecord(
            history_id=history_id,
            anonymous_id=payload.anonymousId,
            created_at=now,
        )
        db.add(record)
    else:
        record = existing

    record.source_content = payload.sourceContent or ""
    record.source_preview = _preview(record.source_content)
    record.quiz_json = payload.quiz
    record.answers_json = payload.answers
    record.report_json = payload.report
    record.provider = _provider_from_quiz(payload.quiz) if payload.provider == "unknown" else payload.provider
    record.question_count = payload.questionCount or _question_count_from_quiz(payload.quiz)
    record.accuracy = payload.accuracy or int(payload.report.get("accuracy") or 0)
    record.score = payload.score or int(payload.report.get("score") or 0)
    record.updated_at = now

    db.commit()
    db.refresh(record)
    _prune_history(db, payload.anonymousId)
    return to_response(record)


def list_history(db: Session, anonymous_id: str, limit: int = MAX_HISTORY_COUNT) -> list[HistoryRecordResponse]:
    records = db.execute(
        select(StudyHistoryRecord)
        .where(StudyHistoryRecord.anonymous_id == anonymous_id)
        .order_by(StudyHistoryRecord.updated_at.desc(), StudyHistoryRecord.id.desc())
        .limit(min(max(limit, 1), MAX_HISTORY_COUNT))
    ).scalars()
    return [to_response(record) for record in records]


def get_history(db: Session, anonymous_id: str, history_id: str) -> HistoryRecordResponse:
    record = db.execute(
        select(StudyHistoryRecord).where(
            StudyHistoryRecord.anonymous_id == anonymous_id,
            StudyHistoryRecord.history_id == history_id,
        )
    ).scalar_one_or_none()
    if record is None:
        raise AppError("HISTORY_NOT_FOUND", "学习记录不存在", 404)
    return to_response(record)


def delete_history(db: Session, anonymous_id: str, history_id: str) -> None:
    result = db.execute(
        delete(StudyHistoryRecord).where(
            StudyHistoryRecord.anonymous_id == anonymous_id,
            StudyHistoryRecord.history_id == history_id,
        )
    )
    db.commit()
    if result.rowcount == 0:
        raise AppError("HISTORY_NOT_FOUND", "学习记录不存在", 404)


def clear_history(db: Session, anonymous_id: str) -> int:
    result = db.execute(delete(StudyHistoryRecord).where(StudyHistoryRecord.anonymous_id == anonymous_id))
    db.commit()
    return int(result.rowcount or 0)


def to_response(record: StudyHistoryRecord) -> HistoryRecordResponse:
    return HistoryRecordResponse(
        historyId=record.history_id,
        sourceContent=record.source_content,
        sourcePreview=record.source_preview,
        quiz=record.quiz_json,
        answers=record.answers_json,
        report=record.report_json,
        provider=record.provider,
        questionCount=record.question_count,
        accuracy=record.accuracy,
        score=record.score,
        createdAt=_iso(record.created_at),
        updatedAt=_iso(record.updated_at),
    )


def _history_id(payload: SaveHistoryRequest) -> str:
    history_id = payload.historyId or str(payload.quiz.get("quizId") or payload.report.get("quizId") or "")
    if not history_id:
        raise AppError("HISTORY_ID_REQUIRED", "学习记录缺少 historyId 或 quizId", 422)
    return history_id


def _preview(text: str, size: int = 80) -> str:
    value = " ".join(str(text or "").split())
    return value[:size] + ("..." if len(value) > size else "")


def _provider_from_quiz(quiz: dict) -> str:
    return str(quiz.get("modelProvider") or "unknown")


def _question_count_from_quiz(quiz: dict) -> int:
    questions = quiz.get("questions")
    if isinstance(questions, list):
        return len(questions)
    return int(quiz.get("questionCount") or 0)


def _prune_history(db: Session, anonymous_id: str) -> None:
    extra_ids = [
        record_id
        for record_id in db.execute(
            select(StudyHistoryRecord.id)
            .where(StudyHistoryRecord.anonymous_id == anonymous_id)
            .order_by(StudyHistoryRecord.updated_at.desc(), StudyHistoryRecord.id.desc())
            .offset(MAX_HISTORY_COUNT)
        ).scalars()
    ]
    if extra_ids:
        db.execute(delete(StudyHistoryRecord).where(StudyHistoryRecord.id.in_(extra_ids)))
        db.commit()


def _iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()
