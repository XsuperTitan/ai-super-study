from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SourceType = Literal["demo", "text", "url", "file"]
QuestionType = Literal["single_choice", "true_false"]
Difficulty = Literal["easy", "normal", "hard"]
Mastery = Literal["good", "normal", "weak"]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ApiError(BaseModel):
    code: str
    message: str
    detail: object | None = None


class ApiResponse(BaseModel):
    success: bool
    data: object | None = None
    error: ApiError | None = None
    requestId: str


class Option(BaseModel):
    id: str = Field(min_length=1, max_length=8)
    text: str = Field(min_length=1)


class Question(BaseModel):
    id: str = Field(min_length=1)
    type: QuestionType
    stem: str = Field(min_length=1)
    options: list[Option] = Field(min_length=2)
    answer: str = Field(min_length=1)
    explanation: str = Field(min_length=1)
    sourceTrace: str = ""
    knowledgePoint: str = ""
    relevanceReason: str = ""
    difficulty: Difficulty = "normal"

    @model_validator(mode="after")
    def answer_must_match_option(self) -> "Question":
        option_ids = {option.id for option in self.options}
        if self.answer not in option_ids:
            raise ValueError("answer must match one option id")
        if self.type == "single_choice" and len(self.options) != 4:
            raise ValueError("single_choice questions must have 4 options")
        if self.type == "true_false" and len(self.options) != 2:
            raise ValueError("true_false questions must have 2 options")
        return self


class Quiz(BaseModel):
    quizId: str = Field(min_length=1)
    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    sourceType: SourceType = "text"
    questionCount: int = Field(ge=1)
    questions: list[Question] = Field(min_length=1)
    createdAt: str = Field(default_factory=utc_now_iso)

    @model_validator(mode="after")
    def count_must_match_questions(self) -> "Quiz":
        if self.questionCount != len(self.questions):
            raise ValueError("questionCount must match questions length")
        return self


class AnswerRecord(BaseModel):
    questionId: str = Field(min_length=1)
    selectedOption: str = Field(min_length=1)
    isCorrect: bool = False
    duration: int = Field(default=1, ge=0)


class KnowledgeMapItem(BaseModel):
    topic: str = Field(min_length=1)
    mastery: Mastery
    value: int = Field(ge=0, le=100)


class Report(BaseModel):
    reportId: str = Field(min_length=1)
    quizId: str = Field(min_length=1)
    grade: Literal["A", "B", "C"]
    score: int = Field(ge=0, le=100)
    accuracy: int = Field(ge=0, le=100)
    correctCount: int = Field(ge=0)
    total: int = Field(ge=0)
    wrongCount: int = Field(ge=0)
    duration: int = Field(ge=0)
    weakPoints: list[str]
    knowledgeMap: list[KnowledgeMapItem]
    reviewAdvice: list[str]
    shareText: str
    summary: str = ""
    createdAt: str = Field(default_factory=utc_now_iso)


class GenerateQuizRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    sourceType: SourceType = "text"
    content: str
    questionCount: Literal[3, 5] = 3
    questionTypes: list[QuestionType] = Field(default_factory=lambda: ["single_choice", "true_false"])
    difficulty: Difficulty = "normal"

    @field_validator("questionTypes")
    @classmethod
    def question_types_not_empty(cls, value: list[QuestionType]) -> list[QuestionType]:
        if not value:
            raise ValueError("questionTypes must not be empty")
        return value


class GenerateQuizResponse(BaseModel):
    quiz: Quiz


class GenerateReportRequest(BaseModel):
    quizId: str = Field(min_length=1)
    questions: list[Question] = Field(min_length=1)
    answers: list[AnswerRecord] = Field(default_factory=list)
    duration: int = Field(default=0, ge=0)


class GenerateReportResponse(BaseModel):
    report: Report
