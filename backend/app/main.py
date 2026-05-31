from __future__ import annotations

import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.adapters.factory import create_adapter
from app.config import load_settings
from app.errors import AppError
from app.schemas import GenerateQuizRequest, GenerateReportRequest
from app.services.quiz_service import QuizService
from app.services.report_service import ReportService

settings = load_settings()

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
    return {"status": "ok", "aiProvider": settings.ai_provider}


@app.post("/api/v1/quiz/generate")
def generate_quiz(payload: GenerateQuizRequest, request: Request):
    service = QuizService(create_adapter(settings))
    quiz = service.generate_quiz(payload)
    return _ok(request, {"quiz": quiz.model_dump(mode="json")})


@app.post("/api/v1/reports/generate")
def generate_report(payload: GenerateReportRequest, request: Request):
    service = ReportService(create_adapter(settings))
    report = service.generate_report(payload)
    return _ok(request, {"report": report.model_dump(mode="json")})


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
