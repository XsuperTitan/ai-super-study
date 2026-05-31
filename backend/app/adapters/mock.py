from __future__ import annotations

from datetime import datetime, timezone

from app.adapters.base import ModelAdapter
from app.schemas import AnswerRecord, GenerateQuizRequest, KnowledgeMapItem, Option, Question, Quiz, Report
from app.services.text_normalizer import NormalizedSource


def _now_id(prefix: str) -> str:
    return f"{prefix}_{int(datetime.now(timezone.utc).timestamp() * 1000)}"


def _excerpt(text: str, size: int = 64) -> str:
    return text[:size] + ("..." if len(text) > size else "")


def _trace(source: NormalizedSource) -> str:
    return f"基于用户输入主题：{source.content}" if source.input_mode == "topic" else _excerpt(source.content)


class MockModelAdapter(ModelAdapter):
    provider_name = "mock"

    def generate_quiz(self, source: NormalizedSource, request: GenerateQuizRequest) -> Quiz:
        trace = _trace(source)
        concept = source.title.replace("...", "")
        is_topic = source.input_mode == "topic"
        reason = (
            f"题目围绕用户想学习的「{concept}」展开，用于确认基础概念和应用边界。"
            if is_topic
            else "题目从用户输入内容中提炼考点，用于检查是否理解原文核心观点。"
        )
        templates = [
            Question(
                id="q1",
                type="single_choice",
                stem=f"学习「{concept}」时，最应该先确认什么？" if is_topic else "这段内容最适合用来训练哪一种学习能力？",
                options=[
                    Option(id="A", text="只记住几个相关关键词"),
                    Option(id="B", text="理解核心概念并能用自己的话解释"),
                    Option(id="C", text="跳过细节，直接背答案"),
                    Option(id="D", text="只关注排版是否整齐"),
                ],
                answer="B",
                explanation="本题考察对输入内容的整体理解。真正目标是帮助你发现自己是否理解。",
                sourceTrace=trace,
                knowledgePoint=f"{concept}的核心概念",
                relevanceReason=reason,
                difficulty=request.difficulty,
            ),
            Question(
                id="q2",
                type="true_false",
                stem=(
                    f"判断：学习「{concept}」时，只记住名称就足够，不需要了解它的应用场景和边界。"
                    if is_topic
                    else "判断：如果能把一个概念讲清楚，通常说明你对它的理解更稳定。"
                ),
                options=[Option(id="A", text="正确"), Option(id="B", text="错误")],
                answer="B" if is_topic else "A",
                explanation=(
                    f"学习「{concept}」不能停在名称层面，还需要理解它解决什么问题、适合什么场景以及有什么限制。"
                    if is_topic
                    else "表达是检验理解的一种方式。讲不清楚的地方，往往就是知识漏洞。"
                ),
                sourceTrace=trace,
                knowledgePoint=f"{concept}的理解检验",
                relevanceReason=reason,
                difficulty=request.difficulty,
            ),
            Question(
                id="q3",
                type="single_choice",
                stem=f"如果想确认自己真的理解「{concept}」，最有效的自测问题是什么？" if is_topic else "完成这段内容的学习后，最推荐的复习动作是什么？",
                options=[
                    Option(id="A", text=f"我能否说明「{concept}」是什么、能做什么和不能做什么" if is_topic else "立刻关闭页面，等待下次再看"),
                    Option(id="B", text="只记住这个词的拼写" if is_topic else "把核心观点改写成自己的例子"),
                    Option(id="C", text="只看别人给出的结论，不尝试解释" if is_topic else "只重复阅读第一句话"),
                    Option(id="D", text="完全不关心它的实际使用场景" if is_topic else "只收藏，不进行任何输出"),
                ],
                answer="A" if is_topic else "B",
                explanation=(
                    f"能解释「{concept}」的定义、能力边界和使用场景，才说明你不是只记住了词。"
                    if is_topic
                    else "将知识迁移到自己的例子里，可以从“看懂”推进到“会用”。"
                ),
                sourceTrace=trace,
                knowledgePoint=f"{concept}的复习迁移",
                relevanceReason=reason,
                difficulty=request.difficulty,
            ),
            Question(
                id="q4",
                type="true_false",
                stem=(
                    f"判断：学习「{concept}」时，结合例子理解通常比只背抽象定义更可靠。"
                    if is_topic
                    else "判断：AI 生成的题目只需要看分数，不需要阅读解析。"
                ),
                options=[Option(id="A", text="正确"), Option(id="B", text="错误")],
                answer="A" if is_topic else "B",
                explanation=(
                    f"例子能帮助你把「{concept}」从名词变成可理解、可判断、可应用的知识。"
                    if is_topic
                    else "解析用于补齐理解链路。答对也值得看解析，因为它能帮助你确认思路是否稳定。"
                ),
                sourceTrace=trace,
                knowledgePoint=f"{concept}的错题复盘",
                relevanceReason=reason,
                difficulty=request.difficulty,
            ),
            Question(
                id="q5",
                type="single_choice",
                stem=f"如果你想进一步掌握「{concept}」，下一步最有效的是？",
                options=[
                    Option(id="A", text="找一个真实场景尝试解释或应用"),
                    Option(id="B", text="只看标题，不看内容"),
                    Option(id="C", text="把错误选项全部背下来"),
                    Option(id="D", text="完全依赖系统自动判断"),
                ],
                answer="A",
                explanation="真实场景会逼迫你重新组织知识，能更快发现概念边界和误区。",
                sourceTrace=trace,
                knowledgePoint=f"{concept}的应用场景",
                relevanceReason=reason,
                difficulty=request.difficulty,
            ),
        ]
        questions = templates[: request.questionCount]
        return Quiz(
            quizId=_now_id("quiz"),
            title=f"关于「{source.title}」的闯关",
            summary=(
                f"AI 已围绕「{source.title}」生成 {len(questions)} 道入门自测题。"
                if is_topic
                else f"AI 已从输入内容中提炼出核心观点，并生成 {len(questions)} 道闯关题。"
            ),
            sourceType=source.source_type,
            questionCount=len(questions),
            questions=questions,
        )

    def generate_report(self, quiz_id: str, questions: list[Question], answers: list[AnswerRecord], duration: int) -> Report:
        correct_count = sum(1 for question in questions if _answer_for(question.id, answers) == question.answer)
        total = len(questions)
        accuracy = round((correct_count / total) * 100) if total else 0
        wrong_questions = [question for question in questions if _answer_for(question.id, answers) != question.answer]
        grade = "A" if accuracy >= 80 else "B" if accuracy >= 60 else "C"
        weak_points = [question.stem[:18] for question in wrong_questions] or ["继续练习迁移应用"]
        advice = (
            "你已经掌握主要内容。下一步请尝试用一个自己的例子解释它，完成从理解到应用的跃迁。"
            if accuracy >= 80
            else "建议回看错题解析，把每道错题对应的原文片段重新读一遍，再用自己的话复述一次。"
        )
        return Report(
            reportId=_now_id("report"),
            quizId=quiz_id,
            grade=grade,
            score=accuracy,
            accuracy=accuracy,
            correctCount=correct_count,
            total=total,
            wrongCount=max(total - correct_count, 0),
            duration=duration or sum(answer.duration for answer in answers),
            weakPoints=weak_points,
            knowledgeMap=[
                KnowledgeMapItem(topic="核心观点识别", mastery="good" if accuracy >= 80 else "normal", value=max(accuracy, 66)),
                KnowledgeMapItem(topic="概念复述", mastery="good" if accuracy >= 70 else "weak", value=max(accuracy - 6, 42)),
                KnowledgeMapItem(topic="举例迁移", mastery="good" if accuracy >= 90 else "normal", value=max(accuracy - 18, 38)),
            ],
            reviewAdvice=[advice],
            shareText=f"我刚完成一次 AI 知识闯关，正确率 {accuracy}%。 ",
            summary=f"本次完成 {total} 道题，正确率 {accuracy}%。",
        )


def _answer_for(question_id: str, answers: list[AnswerRecord]) -> str | None:
    for answer in answers:
        if answer.questionId == question_id:
            return answer.selectedOption
    return None
