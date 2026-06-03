from __future__ import annotations

import pytest

from app.adapters.base import ModelAdapter
from app.schemas import GenerateQuizRequest, Option, Question, Quiz
from app.services import quiz_service
from app.services.quiz_service import QuizService
from app.services.text_normalizer import NormalizedSource


SOURCE_TEXT = "RAG 会先检索相关资料，再把资料交给大模型生成回答。这种方式可以减少幻觉，并让回答更容易追溯来源。"


class FixedAdapter(ModelAdapter):
    provider_name = "deepseek"

    def __init__(self, quiz: Quiz):
        self.quiz = quiz

    def generate_quiz(self, source, request):
        return self.quiz

    def generate_report(self, quiz_id, questions, answers, duration):
        raise NotImplementedError


def _request(source_type: str = "url", content: str = "https://example.com/rag") -> GenerateQuizRequest:
    return GenerateQuizRequest(
        sourceType=source_type,
        content=content,
        questionCount=3,
        questionTypes=["single_choice", "true_false"],
        difficulty="normal",
    )


def _quiz(source_trace: str = "模型改写后的追溯片段，不会精确出现在原文里", question_count: int = 3) -> Quiz:
    questions = [
        Question(
            id="q1",
            type="single_choice",
            stem="RAG 的基本流程是什么？",
            options=[
                Option(id="A", text="先检索资料再生成回答"),
                Option(id="B", text="只生成回答"),
                Option(id="C", text="只保存数据"),
                Option(id="D", text="只做翻译"),
            ],
            answer="A",
            explanation="RAG 的核心是检索增强生成。",
            sourceTrace=source_trace,
            knowledgePoint="RAG 的基本流程",
            relevanceReason="题目来自网页中对 RAG 流程的说明。",
        ),
        Question(
            id="q2",
            type="true_false",
            stem="RAG 可以帮助减少幻觉。",
            options=[Option(id="A", text="正确"), Option(id="B", text="错误")],
            answer="A",
            explanation="检索资料可以给模型提供依据。",
            sourceTrace=source_trace,
            knowledgePoint="RAG 的价值",
            relevanceReason="题目对应网页中减少幻觉的描述。",
        ),
        Question(
            id="q3",
            type="single_choice",
            stem="RAG 为什么更容易追溯来源？",
            options=[
                Option(id="A", text="因为回答依据来自检索资料"),
                Option(id="B", text="因为完全不使用资料"),
                Option(id="C", text="因为只依赖记忆"),
                Option(id="D", text="因为跳过生成过程"),
            ],
            answer="A",
            explanation="检索资料可以作为回答依据。",
            sourceTrace=source_trace,
            knowledgePoint="来源追溯",
            relevanceReason="题目对应网页中追溯来源的描述。",
        ),
    ]
    return Quiz(
        quizId="quiz_deepseek",
        title="RAG 网页闯关",
        summary="RAG 网页内容生成的题目。",
        sourceType="url",
        questionCount=question_count,
        questions=questions[:question_count],
    )


def test_url_trace_mismatch_keeps_real_provider(monkeypatch):
    monkeypatch.setattr(
        quiz_service,
        "normalize_text",
        lambda content, source_type: NormalizedSource(
            source_type="url",
            content=SOURCE_TEXT,
            title="RAG 网页",
            length=len(SOURCE_TEXT),
            input_mode="content",
        ),
    )

    result = QuizService(FixedAdapter(_quiz())).generate_quiz(_request())

    assert result.provider == "deepseek"
    assert result.fallback_reason == ""
    assert result.quiz.questions[0].sourceTrace == SOURCE_TEXT[:100]


def test_url_empty_trace_is_repaired(monkeypatch):
    monkeypatch.setattr(
        quiz_service,
        "normalize_text",
        lambda content, source_type: NormalizedSource(
            source_type="url",
            content=SOURCE_TEXT,
            title="RAG 网页",
            length=len(SOURCE_TEXT),
            input_mode="content",
        ),
    )

    result = QuizService(FixedAdapter(_quiz(source_trace=""))).generate_quiz(_request())

    assert result.provider == "deepseek"
    assert result.quiz.questions[0].sourceTrace == SOURCE_TEXT[:100]


def test_question_count_mismatch_still_falls_back(monkeypatch):
    monkeypatch.setattr(
        quiz_service,
        "normalize_text",
        lambda content, source_type: NormalizedSource(
            source_type="url",
            content=SOURCE_TEXT,
            title="RAG 网页",
            length=len(SOURCE_TEXT),
            input_mode="content",
        ),
    )

    result = QuizService(FixedAdapter(_quiz(question_count=2))).generate_quiz(_request())

    assert result.provider == "mock"
    assert "question count mismatch" in result.fallback_reason


def test_topic_drift_still_falls_back(monkeypatch):
    monkeypatch.setattr(
        quiz_service,
        "normalize_text",
        lambda content, source_type: NormalizedSource(
            source_type="text",
            content="RAG",
            title="RAG",
            length=3,
            input_mode="topic",
        ),
    )

    drift_quiz = _quiz(source_trace="基于用户输入主题：经济学").model_copy(
        update={
            "questions": [
                question.model_copy(
                    update={
                        "stem": "供给曲线通常表示什么？",
                        "knowledgePoint": "供给曲线",
                        "relevanceReason": "本题用于确认经济学基础概念。",
                    }
                )
                for question in _quiz(source_trace="基于用户输入主题：经济学").questions
            ]
        }
    )
    result = QuizService(FixedAdapter(drift_quiz)).generate_quiz(_request(source_type="text", content="RAG"))

    assert result.provider == "mock"
    assert "topic question does not reference user topic" in result.fallback_reason
