from __future__ import annotations

from pydantic import ValidationError

from app.adapters.base import ModelAdapter
from app.adapters.mock import MockModelAdapter
from app.schemas import GenerateQuizRequest, Quiz
from app.services.text_normalizer import normalize_text


class QuizService:
    def __init__(self, adapter: ModelAdapter):
        self._adapter = adapter

    def generate_quiz(self, request: GenerateQuizRequest) -> Quiz:
        source = normalize_text(request.content, request.sourceType)
        try:
            quiz = self._adapter.generate_quiz(source, request)
            if quiz.questionCount != request.questionCount:
                raise ValueError("question count mismatch")
            return quiz
        except (Exception, ValidationError):
            return MockModelAdapter().generate_quiz(source, request)
