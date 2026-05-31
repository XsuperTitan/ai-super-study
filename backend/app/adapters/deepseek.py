from __future__ import annotations

import json

from openai import OpenAI

from app.adapters.base import ModelAdapter
from app.config import Settings
from app.errors import ModelAdapterError
from app.schemas import AnswerRecord, GenerateQuizRequest, Question, Quiz, Report
from app.services.text_normalizer import NormalizedSource


class DeepSeekAdapter(ModelAdapter):
    def __init__(self, settings: Settings):
        if not settings.deepseek_api_key:
            raise ModelAdapterError("DEEPSEEK_API_KEY is not configured")
        self._client = OpenAI(api_key=settings.deepseek_api_key, base_url=settings.deepseek_base_url)
        self._model = settings.deepseek_model

    def generate_quiz(self, source: NormalizedSource, request: GenerateQuizRequest) -> Quiz:
        instruction = (
            "用户输入是一个想学习的知识主题。请围绕该主题生成入门自测题，可以补充通用定义、关键概念和常见误区，但不要编造具体来源。"
            if source.input_mode == "topic"
            else "用户输入是一段学习内容。请严格基于这段内容提炼考点，不要编造输入中不存在的事实。"
        )
        payload = self._json_chat(
            system_prompt=_quiz_system_prompt(request.questionCount, request.questionTypes, source.input_mode),
            user_prompt=f"{instruction}\n\n用户输入：\n{source.content}",
            max_tokens=2600,
        )
        return Quiz.model_validate(_normalize_quiz_payload(payload, source, request))

    def generate_report(self, quiz_id: str, questions: list[Question], answers: list[AnswerRecord], duration: int) -> Report:
        compact = {
            "quizId": quiz_id,
            "questions": [question.model_dump(mode="json") for question in questions],
            "answers": [answer.model_dump(mode="json") for answer in answers],
            "duration": duration,
        }
        payload = self._json_chat(
            system_prompt=_report_system_prompt(),
            user_prompt=json.dumps(compact, ensure_ascii=False),
            max_tokens=1600,
        )
        return Report.model_validate(payload)

    def _json_chat(self, system_prompt: str, user_prompt: str, max_tokens: int) -> dict:
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
                max_tokens=max_tokens,
            )
            content = response.choices[0].message.content or "{}"
            return json.loads(content)
        except Exception as exc:
            raise ModelAdapterError(str(exc)) from exc


def _quiz_system_prompt(question_count: int, question_types: list[str], input_mode: str) -> str:
    source_rule = (
        "用户输入可能只是一个短主题；可以围绕主题生成基础概念题，但必须避免杜撰专有出处、数据或原文片段。"
        if input_mode == "topic"
        else "请只基于用户输入内容生成题目，不要编造输入中不存在的事实。"
    )
    return f"""
你是一个严谨的中文微学习出题助手。{source_rule}
输出必须是 JSON object，结构如下：
{{
  "quizId": "quiz_xxx",
  "title": "关于...的闯关",
  "summary": "一句话总结",
  "sourceType": "text",
  "questionCount": {question_count},
  "questions": [
    {{
      "id": "q1",
      "type": "single_choice 或 true_false",
      "stem": "题干",
      "options": [{{"id": "A", "text": "选项"}}],
      "answer": "A",
      "explanation": "解析",
      "sourceTrace": "原文追溯片段",
      "difficulty": "normal"
    }}
  ],
  "createdAt": "ISO 时间字符串"
}}
要求：
- 必须生成 {question_count} 道题。
- 题型只能来自：{", ".join(question_types)}。
- single_choice 必须有 A/B/C/D 四个选项。
- true_false 必须有 A=正确、B=错误两个选项。
- answer 必须命中某个 options.id。
- explanation 和 sourceTrace 不能为空。
"""


def _report_system_prompt() -> str:
    return """
你是一个严谨的中文学习报告助手。根据题目、答案和耗时生成 JSON object。
必须输出字段：
reportId, quizId, grade(A/B/C), score, accuracy, correctCount, total, wrongCount, duration,
weakPoints(string array), knowledgeMap(array: topic/mastery/value), reviewAdvice(string array),
shareText, summary, createdAt。
统计数字必须与输入答案一致，不要夸大效果。
"""


def _normalize_quiz_payload(payload: dict, source: NormalizedSource, request: GenerateQuizRequest) -> dict:
    payload = dict(payload or {})
    payload.setdefault("quizId", "quiz_deepseek")
    payload.setdefault("title", f"关于「{source.title}」的闯关")
    payload.setdefault("summary", f"AI 已生成 {request.questionCount} 道闯关题。")
    payload["sourceType"] = source.source_type
    payload["questionCount"] = request.questionCount
    payload["questions"] = list(payload.get("questions") or [])[: request.questionCount]
    return payload
