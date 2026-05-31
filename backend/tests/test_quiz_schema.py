from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas import Option, Question, Quiz


def test_question_answer_must_match_option():
    with pytest.raises(ValidationError):
        Question(
            id="q1",
            type="single_choice",
            stem="题干",
            options=[
                Option(id="A", text="A"),
                Option(id="B", text="B"),
                Option(id="C", text="C"),
                Option(id="D", text="D"),
            ],
            answer="Z",
            explanation="解析",
        )


def test_single_choice_requires_four_options():
    with pytest.raises(ValidationError):
        Question(
            id="q1",
            type="single_choice",
            stem="题干",
            options=[Option(id="A", text="A"), Option(id="B", text="B")],
            answer="A",
            explanation="解析",
        )


def test_quiz_question_count_must_match_questions():
    question = Question(
        id="q1",
        type="true_false",
        stem="判断题",
        options=[Option(id="A", text="正确"), Option(id="B", text="错误")],
        answer="A",
        explanation="解析",
    )
    with pytest.raises(ValidationError):
        Quiz(quizId="quiz_1", title="标题", summary="摘要", questionCount=3, questions=[question])


def test_question_accepts_relevance_metadata():
    question = Question(
        id="q1",
        type="true_false",
        stem="判断题",
        options=[Option(id="A", text="正确"), Option(id="B", text="错误")],
        answer="A",
        explanation="解析",
        sourceTrace="基于用户输入主题：AI",
        knowledgePoint="AI 的基础概念",
        relevanceReason="本题用于确认用户是否理解 AI 主题。",
    )
    assert question.knowledgePoint == "AI 的基础概念"
    assert "AI" in question.relevanceReason
