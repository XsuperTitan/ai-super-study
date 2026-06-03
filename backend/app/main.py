from __future__ import annotations

import json
import time
import uuid
from collections.abc import Iterator

from fastapi import Depends, FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from app.adapters.factory import create_adapter
from app.config import load_settings
from app.database import configure_database, get_db, is_database_enabled
from app.errors import AppError
from app.schemas import GenerateQuizRequest, GenerateReportRequest, SaveHistoryRequest
from app.services import history_service
from app.services import job_service
from app.services.quiz_service import QuizService
from app.services.report_service import ReportService
from sqlalchemy.orm import Session

settings = load_settings()
configure_database(settings.database_url, settings.database_pool_recycle)

app = FastAPI(title="AI Super Study API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request.state.request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
    response = await call_next(request)
    response.headers["x-request-id"] = request.state.request_id
    return response


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return _error(request, exc.status_code, exc.code, exc.message, exc.detail)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    return _error(request, 422, "VALIDATION_ERROR", "请求参数不合法", exc.errors())


@app.get("/health")
def health():
    return {"status": "ok", "aiProvider": settings.ai_provider, "historyDatabase": is_database_enabled()}


@app.post("/api/v1/quiz/generate")
def generate_quiz(payload: GenerateQuizRequest, request: Request):
    selection = create_adapter(settings)
    service = QuizService(selection.adapter, selection.fallback_reason)
    result = service.generate_quiz(payload)
    return _ok(request, _quiz_result_payload(result))


@app.post("/api/v1/quiz/jobs")
def create_quiz_job(payload: GenerateQuizRequest, request: Request):
    job = job_service.start_quiz_job(payload, settings)
    return _ok(request, job_service.to_response(job).model_dump(mode="json"))


@app.get("/api/v1/jobs/{job_id}")
def get_job(job_id: str, request: Request):
    job = job_service.get_job_response(job_id)
    return _ok(request, job.model_dump(mode="json"))


@app.post("/api/v1/quiz/generate/stream")
def generate_quiz_stream(payload: GenerateQuizRequest):
    return StreamingResponse(_quiz_stream_events(payload), media_type="application/x-ndjson")


@app.post("/api/v1/reports/generate")
def generate_report(payload: GenerateReportRequest, request: Request):
    selection = create_adapter(settings)
    service = ReportService(selection.adapter)
    report = service.generate_report(payload)
    return _ok(request, {"report": report.model_dump(mode="json")})


@app.post("/api/v1/history")
def save_history(payload: SaveHistoryRequest, request: Request, db: Session = Depends(get_db)):
    record = history_service.save_history(db, payload)
    return _ok(request, {"record": record.model_dump(mode="json")})


@app.get("/api/v1/history")
def list_history(
    request: Request,
    anonymousId: str = Query(min_length=1),
    limit: int = Query(default=10, ge=1, le=10),
    db: Session = Depends(get_db),
):
    records = history_service.list_history(db, anonymousId, limit)
    return _ok(request, {"records": [record.model_dump(mode="json") for record in records]})


@app.get("/api/v1/history/{history_id}")
def get_history(history_id: str, request: Request, anonymousId: str = Query(min_length=1), db: Session = Depends(get_db)):
    record = history_service.get_history(db, anonymousId, history_id)
    return _ok(request, {"record": record.model_dump(mode="json")})


@app.delete("/api/v1/history/{history_id}")
def delete_history(history_id: str, request: Request, anonymousId: str = Query(min_length=1), db: Session = Depends(get_db)):
    history_service.delete_history(db, anonymousId, history_id)
    return _ok(request, {"deleted": True})


@app.delete("/api/v1/history")
def clear_history(request: Request, anonymousId: str = Query(min_length=1), db: Session = Depends(get_db)):
    deleted_count = history_service.clear_history(db, anonymousId)
    return _ok(request, {"deleted": deleted_count})


def _ok(request: Request, data: object) -> JSONResponse:
    return JSONResponse({"success": True, "data": data, "requestId": request.state.request_id})


def _error(request: Request, status_code: int, code: str, message: str, detail: object | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "error": {"code": code, "message": message, "detail": detail},
            "requestId": getattr(request.state, "request_id", uuid.uuid4().hex),
        },
    )


def _quiz_result_payload(result) -> dict:
    return {
        "quiz": result.quiz.model_dump(mode="json"),
        "provider": result.provider,
        "fallbackReason": result.fallback_reason,
    }


def _quiz_stream_events(payload: GenerateQuizRequest) -> Iterator[str]:
    try:
        yield _ndjson({"type": "progress", "progress": 18, "message": "正在识别输入内容"})
        time.sleep(0.05)
        yield _ndjson({"type": "progress", "progress": 42, "message": "正在提炼关键考点"})
        selection = create_adapter(settings)
        service = QuizService(selection.adapter, selection.fallback_reason)
        time.sleep(0.05)
        yield _ndjson({"type": "progress", "progress": 72, "message": "正在生成题目"})
        result = service.generate_quiz(payload)
        yield _ndjson({"type": "progress", "progress": 92, "message": "正在校验题目结构"})
        yield _ndjson({"type": "done", "progress": 100, "data": _quiz_result_payload(result)})
    except AppError as exc:
        yield _ndjson({"type": "error", "error": {"code": exc.code, "message": exc.message}})
    except Exception as exc:
        yield _ndjson({"type": "error", "error": {"code": "STREAM_GENERATE_FAILED", "message": str(exc) or "题目生成失败"}})


def _ndjson(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False) + "\n"
