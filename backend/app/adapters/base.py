from __future__ import annotations

from abc import ABC, abstractmethod

from app.schemas import GenerateQuizRequest, Quiz, Report, AnswerRecord, Question
from app.services.text_normalizer import NormalizedSource


class ModelAdapter(ABC):
    provider_name = "unknown"

    @abstractmethod
    def generate_quiz(self, source: NormalizedSource, request: GenerateQuizRequest) -> Quiz:
        raise NotImplementedError

    @abstractmethod
    def generate_report(self, quiz_id: str, questions: list[Question], answers: list[AnswerRecord], duration: int) -> Report:
        raise NotImplementedError
