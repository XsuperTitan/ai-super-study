from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from app.adapters.factory import create_adapter
from app.config import Settings
from app.errors import AppError
from app.schemas import GenerateQuizRequest, JobError, JobStatusResponse
from app.services.quiz_service import QuizService

JOB_TTL_SECONDS = 30 * 60


@dataclass
class JobState:
    job_id: str
    payload: GenerateQuizRequest
    status: str = "queued"
    progress: int = 0
    message: str = "任务已创建"
    result: dict[str, Any] | None = None
    error: JobError | None = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


class JobStore:
    def __init__(self):
        self._jobs: dict[str, JobState] = {}
        self._lock = threading.Lock()

    def create(self, payload: GenerateQuizRequest) -> JobState:
        self.prune()
        job = JobState(job_id=f"job_{uuid.uuid4().hex}", payload=payload)
        with self._lock:
            self._jobs[job.job_id] = job
        return job

    def get(self, job_id: str) -> JobState:
        self.prune()
        with self._lock:
            job = self._jobs.get(job_id)
        if job is None:
            raise AppError("JOB_NOT_FOUND", "任务不存在或已过期", 404)
        return job

    def update(self, job_id: str, **changes: Any) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            for key, value in changes.items():
                setattr(job, key, value)
            job.updated_at = time.time()

    def clear(self) -> None:
        with self._lock:
            self._jobs.clear()

    def prune(self) -> None:
        now = time.time()
        with self._lock:
            expired = [job_id for job_id, job in self._jobs.items() if now - job.updated_at > JOB_TTL_SECONDS]
            for job_id in expired:
                self._jobs.pop(job_id, None)


job_store = JobStore()


def start_quiz_job(payload: GenerateQuizRequest, settings: Settings) -> JobState:
    job = job_store.create(payload)
    thread = threading.Thread(target=_run_quiz_job, args=(job.job_id, payload, settings), daemon=True)
    thread.start()
    return job


def get_job_response(job_id: str) -> JobStatusResponse:
    return to_response(job_store.get(job_id))


def to_response(job: JobState) -> JobStatusResponse:
    return JobStatusResponse(
        jobId=job.job_id,
        status=job.status,  # type: ignore[arg-type]
        progress=job.progress,
        message=job.message,
        result=job.result,
        error=job.error,
    )


def _run_quiz_job(job_id: str, payload: GenerateQuizRequest, settings: Settings) -> None:
    try:
        job_store.update(job_id, status="running", progress=18, message="正在识别输入内容")
        selection = create_adapter(settings)
        service = QuizService(selection.adapter, selection.fallback_reason)
        job_store.update(job_id, progress=42, message="正在提炼关键考点")
        result = service.generate_quiz(payload)
        job_store.update(job_id, progress=82, message="正在校验题目结构")
        job_store.update(
            job_id,
            status="succeeded",
            progress=100,
            message="题目生成完成",
            result={
                "quiz": result.quiz.model_dump(mode="json"),
                "provider": result.provider,
                "fallbackReason": result.fallback_reason,
            },
        )
    except AppError as exc:
        job_store.update(
            job_id,
            status="failed",
            progress=100,
            message=exc.message,
            error=JobError(code=exc.code, message=exc.message),
        )
    except Exception as exc:
        job_store.update(
            job_id,
            status="failed",
            progress=100,
            message="题目生成失败",
            error=JobError(code="QUIZ_JOB_FAILED", message=str(exc) or "题目生成失败"),
        )
