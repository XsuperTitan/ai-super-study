from __future__ import annotations

from dataclasses import dataclass

from pydantic import ValidationError

from app.adapters.base import ModelAdapter
from app.adapters.mock import MockModelAdapter
from app.schemas import Question
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
            quiz = _validate_relevance(quiz, source)
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


def _validate_relevance(quiz: Quiz, source: NormalizedSource) -> Quiz:
    source_text = source.content.strip()
    topic = source.title.replace("...", "").strip()
    repaired_questions: list[Question] = []
    for question in quiz.questions:
        if not question.stem.strip():
            raise ValueError("question stem is empty")
        if not question.explanation.strip():
            raise ValueError("question explanation is empty")
        if not question.knowledgePoint.strip():
            raise ValueError("question knowledgePoint is empty")
        if not question.relevanceReason.strip():
            raise ValueError("question relevanceReason is empty")

        if source.input_mode == "topic":
            if not question.sourceTrace.strip():
                raise ValueError("question sourceTrace is empty")
            combined = f"{question.stem} {question.sourceTrace} {question.knowledgePoint} {question.relevanceReason}"
            if topic and topic.lower() not in combined.lower():
                raise ValueError("topic question does not reference user topic")
            repaired_questions.append(question)
        else:
            repaired_questions.append(_repair_source_trace(question, source_text))
    return quiz.model_copy(update={"questions": repaired_questions})


def _repair_source_trace(question: Question, source_text: str) -> Question:
    trace = question.sourceTrace.strip()
    if trace and trace in source_text:
        return question
    return question.model_copy(update={"sourceTrace": _source_excerpt(source_text)})


def _source_excerpt(source_text: str, length: int = 100) -> str:
    text = " ".join(source_text.split())
    return text[:length]
