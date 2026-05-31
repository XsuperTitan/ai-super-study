from __future__ import annotations

from app.adapters.mock import MockModelAdapter
from app.schemas import AnswerRecord, GenerateReportRequest, Option, Question
from app.services.report_service import ReportService


def _questions():
    return [
        Question(
            id="q1",
            type="true_false",
            stem="判断一",
            options=[Option(id="A", text="正确"), Option(id="B", text="错误")],
            answer="A",
            explanation="解析",
        ),
        Question(
            id="q2",
            type="true_false",
            stem="判断二",
            options=[Option(id="A", text="正确"), Option(id="B", text="错误")],
            answer="B",
            explanation="解析",
        ),
    ]


def test_report_service_recomputes_accuracy_from_answers():
    service = ReportService(MockModelAdapter())
    report = service.generate_report(
        GenerateReportRequest(
            quizId="quiz_1",
            questions=_questions(),
            answers=[
                AnswerRecord(questionId="q1", selectedOption="A", isCorrect=False, duration=3),
                AnswerRecord(questionId="q2", selectedOption="A", isCorrect=True, duration=4),
            ],
            duration=7,
        )
    )
    assert report.correctCount == 1
    assert report.accuracy == 50
    assert report.grade == "C"
    assert report.duration == 7
    assert report.weakPoints
