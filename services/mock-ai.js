const QUIZ_KEY = 'm0_current_quiz';
const SOURCE_KEY = 'm0_source';
const ANSWERS_KEY = 'm0_answers';
const REPORT_KEY = 'm0_report';

const FALLBACK_SOURCE =
  '费曼学习法强调用自己的话解释一个概念，通过简单表达暴露理解漏洞，再回到资料中修正，最后用例子迁移应用。';

function normalizeSource(content) {
  const text = String(content || '').replace(/\s+/g, ' ').trim();
  return text || FALLBACK_SOURCE;
}

function getTitle(content) {
  const text = normalizeSource(content);
  if (text.length <= 18) return text;
  return text.slice(0, 18) + '...';
}

function getExcerpt(content, length) {
  const text = normalizeSource(content);
  return text.length > length ? text.slice(0, length) + '...' : text;
}

function createQuestion(id, type, stem, options, answer, explanation, sourceTrace) {
  return {
    id: 'q' + id,
    type,
    stem,
    options,
    answer,
    explanation,
    sourceTrace,
    difficulty: 'normal'
  };
}

function generateQuiz(input) {
  const content = normalizeSource(input && input.content);
  const questionCount = input && input.questionCount === 5 ? 5 : 3;
  const title = '关于「' + getTitle(content) + '」的闯关';
  const excerpt = getExcerpt(content, 56);
  const concept = getTitle(content).replace('...', '');

  const baseQuestions = [
    createQuestion(
      1,
      'single_choice',
      '这段内容最适合用来训练哪一种学习能力？',
      [
        { id: 'A', text: '只记住原文中的关键词' },
        { id: 'B', text: '理解核心观点并能用自己的话复述' },
        { id: 'C', text: '跳过细节，直接背答案' },
        { id: 'D', text: '只关注排版是否整齐' }
      ],
      'B',
      '本题考察对输入内容的整体理解。AI 将原文压缩为可表达、可复述的核心观点，真正目标是帮助你发现自己是否理解。',
      excerpt
    ),
    createQuestion(
      2,
      'true_false',
      '判断：如果能把一个概念讲清楚，通常说明你对它的理解更稳定。',
      [
        { id: 'A', text: '正确' },
        { id: 'B', text: '错误' }
      ],
      'A',
      '表达是检验理解的一种方式。讲不清楚的地方，往往就是知识漏洞。',
      excerpt
    ),
    createQuestion(
      3,
      'single_choice',
      '完成这段内容的学习后，最推荐的复习动作是什么？',
      [
        { id: 'A', text: '立刻关闭页面，等待下次再看' },
        { id: 'B', text: '把核心观点改写成自己的例子' },
        { id: 'C', text: '只重复阅读第一句话' },
        { id: 'D', text: '只收藏，不进行任何输出' }
      ],
      'B',
      '将知识迁移到自己的例子里，可以从“看懂”推进到“会用”。',
      excerpt
    ),
    createQuestion(
      4,
      'true_false',
      '判断：AI 生成的题目只需要看分数，不需要阅读解析。',
      [
        { id: 'A', text: '正确' },
        { id: 'B', text: '错误' }
      ],
      'B',
      '解析用于补齐理解链路。答对也值得看解析，因为它能帮助你确认思路是否稳定。',
      excerpt
    ),
    createQuestion(
      5,
      'single_choice',
      '如果你想进一步掌握「' + concept + '」，下一步最有效的是？',
      [
        { id: 'A', text: '找一个真实场景尝试解释或应用' },
        { id: 'B', text: '只看标题，不看内容' },
        { id: 'C', text: '把错误选项全部背下来' },
        { id: 'D', text: '完全依赖系统自动判断' }
      ],
      'A',
      '真实场景会逼迫你重新组织知识，能更快发现概念边界和误区。',
      excerpt
    )
  ];

  return {
    quizId: 'quiz_' + Date.now(),
    title,
    summary: 'AI 已从输入内容中提炼出核心观点，并生成 ' + questionCount + ' 道闯关题。',
    sourceType: 'text',
    questionCount,
    questions: baseQuestions.slice(0, questionCount),
    createdAt: new Date().toISOString()
  };
}

function generateReport(quiz, answers) {
  const questions = quiz.questions || [];
  const list = answers || [];
  const correctCount = list.filter(item => item.isCorrect).length;
  const total = questions.length || 1;
  const accuracy = Math.round((correctCount / total) * 100);
  const duration = list.reduce((sum, item) => sum + (item.duration || 0), 0);
  const wrong = questions.filter(q => {
    const answer = list.find(item => item.questionId === q.id);
    return answer && !answer.isCorrect;
  });

  let grade = 'A';
  if (accuracy < 60) grade = 'C';
  else if (accuracy < 80) grade = 'B';

  return {
    reportId: 'report_' + Date.now(),
    quizId: quiz.quizId,
    grade,
    score: accuracy,
    accuracy,
    correctCount,
    total,
    wrongCount: total - correctCount,
    duration,
    weakPoints: wrong.length
      ? wrong.map(item => item.stem.slice(0, 16))
      : ['继续练习迁移应用'],
    knowledgeMap: [
      { topic: '核心观点识别', mastery: accuracy >= 80 ? 'good' : 'normal', value: Math.max(accuracy, 66) },
      { topic: '概念复述', mastery: accuracy >= 70 ? 'good' : 'weak', value: Math.max(accuracy - 6, 42) },
      { topic: '举例迁移', mastery: accuracy >= 90 ? 'good' : 'normal', value: Math.max(accuracy - 18, 38) }
    ],
    reviewAdvice:
      accuracy >= 80
        ? ['你已经掌握主要内容。下一步请尝试用一个自己的例子解释它，完成从理解到应用的跃迁。']
        : ['建议回看错题解析，把每道错题对应的原文片段重新读一遍，再用自己的话复述一次。'],
    shareText: '我刚完成一次 AI 知识闯关，正确率 ' + accuracy + '%。',
    createdAt: new Date().toISOString()
  };
}

module.exports = {
  QUIZ_KEY,
  SOURCE_KEY,
  ANSWERS_KEY,
  REPORT_KEY,
  generateQuiz,
  generateReport,
  normalizeSource
};
