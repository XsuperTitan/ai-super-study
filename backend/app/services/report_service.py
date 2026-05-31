from __future__ import annotations

from pydantic import ValidationError

from app.adapters.base import ModelAdapter
from app.adapters.mock import MockModelAdapter
from app.schemas import AnswerRecord, GenerateReportRequest, Report


class ReportService:
    def __init__(self, adapter: ModelAdapter):
        self._adapter = adapter

    def generate_report(self, request: GenerateReportRequest) -> Report:
        answers = _recompute_answers(request)
        duration = request.duration or sum(answer.duration for answer in answers)
        try:
            report = self._adapter.generate_report(request.quizId, request.questions, answers, duration)
            return _override_stats(report, request, answers, duration)
        except (Exception, ValidationError):
            return MockModelAdapter().generate_report(request.quizId, request.questions, answers, duration)


def _recompute_answers(request: GenerateReportRequest) -> list[AnswerRecord]:
    answer_by_question = {answer.questionId: answer for answer in request.answers}
    result: list[AnswerRecord] = []
    for question in request.questions:
        existing = answer_by_question.get(question.id)
        if existing is None:
            continue
        result.append(
            AnswerRecord(
                questionId=question.id,
                selectedOption=existing.selectedOption,
                isCorrect=existing.selectedOption == question.answer,
                duration=existing.duration,
            )
        )
    return result


def _override_stats(report: Report, request: GenerateReportRequest, answers: list[AnswerRecord], duration: int) -> Report:
    correct_count = sum(1 for answer in answers if answer.isCorrect)
    total = len(request.questions)
    accuracy = round((correct_count / total) * 100) if total else 0
    grade = "A" if accuracy >= 80 else "B" if accuracy >= 60 else "C"
    return report.model_copy(
        update={
            "quizId": request.quizId,
            "grade": grade,
            "score": accuracy,
            "accuracy": accuracy,
            "correctCount": correct_count,
            "total": total,
            "wrongCount": max(total - correct_count, 0),
            "duration": duration,
        }
    )
