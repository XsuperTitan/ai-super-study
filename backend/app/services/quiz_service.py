from __future__ import annotations

from dataclasses import dataclass

from pydantic import ValidationError

from app.adapters.base import ModelAdapter
from app.adapters.mock import MockModelAdapter
from app.schemas import GenerateQuizRequest, Quiz
from app.services.text_normalizer import NormalizedSource, normalize_text


@dataclass(frozen=True)
class QuizGenerationResult:
    quiz: Quiz
    provider: str
    fallback_reason: str = ""


class QuizService:
    def __init__(self, adapter: ModelAdapter, fallback_reason: str = ""):
        self._adapter = adapter
        self._fallback_reason = fallback_reason

    def generate_quiz(self, request: GenerateQuizRequest) -> QuizGenerationResult:
        source = normalize_text(request.content, request.sourceType)
        try:
            quiz = self._adapter.generate_quiz(source, request)
            if quiz.questionCount != request.questionCount:
                raise ValueError("question count mismatch")
            _validate_relevance(quiz, source)
            return QuizGenerationResult(
                quiz=quiz,
                provider=getattr(self._adapter, "provider_name", "unknown"),
                fallback_reason=self._fallback_reason,
            )
        except (Exception, ValidationError) as exc:
            adapter = MockModelAdapter()
            return QuizGenerationResult(
                quiz=adapter.generate_quiz(source, request),
                provider=adapter.provider_name,
                fallback_reason=f"{getattr(self._adapter, 'provider_name', 'unknown')} failed: {exc}",
            )


def _validate_relevance(quiz: Quiz, source: NormalizedSource) -> None:
    source_text = source.content.strip()
    topic = source.title.replace("...", "").strip()
    for question in quiz.questions:
        if not question.stem.strip():
            raise ValueError("question stem is empty")
        if not question.explanation.strip():
            raise ValueError("question explanation is empty")
        if not question.sourceTrace.strip():
            raise ValueError("question sourceTrace is empty")
        if not question.knowledgePoint.strip():
            raise ValueError("question knowledgePoint is empty")
        if not question.relevanceReason.strip():
            raise ValueError("question relevanceReason is empty")

        if source.input_mode == "topic":
            combined = f"{question.stem} {question.sourceTrace} {question.knowledgePoint} {question.relevanceReason}"
            if topic and topic.lower() not in combined.lower():
                raise ValueError("topic question does not reference user topic")
        elif question.sourceTrace not in source_text and len(question.sourceTrace) > 30:
            raise ValueError("content question sourceTrace is not grounded in source")
