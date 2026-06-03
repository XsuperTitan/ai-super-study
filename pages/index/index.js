const api = require('../../services/api');

const examples = [
  'RAG',
  '向量数据库',
  '费曼学习法',
  'RAG定义',
  '提示词工程',
  '大模型幻觉',
  '知识图谱',
  'Transformer'
];

Page({
  data: {
    content: examples[0],
    contentLength: examples[0].length,
    recommendedTopics: examples,
    sourceModeLabel: 'TEXT MODE',
    questionCount: 3,
    canStart: true
  },

  onInput(event) {
    const content = event.detail.value || '';
    this.setData({
      content,
      contentLength: content.length,
      sourceModeLabel: api.isHttpUrl(content) ? 'URL MODE' : 'TEXT MODE',
      canStart: content.trim().length >= api.MIN_SOURCE_LENGTH
    });
  },

  useExample(event) {
    const index = Number(event.currentTarget.dataset.index || 0);
    const content = examples[index] || examples[0];
    this.setData({
      content,
      contentLength: content.length,
      sourceModeLabel: 'TEXT MODE',
      canStart: true
    });
  },

  setQuestionCount(event) {
    this.setData({
      questionCount: Number(event.currentTarget.dataset.count || 3)
    });
  },

  startGenerate() {
    const content = api.normalizeSource(this.data.content);
    if (content.length < api.MIN_SOURCE_LENGTH) {
      wx.showToast({ title: '至少输入 2 个有效字符', icon: 'none' });
      return;
    }

    wx.setStorageSync(api.SOURCE_KEY, {
      content,
      sourceType: api.detectSourceType(content),
      questionCount: this.data.questionCount,
      createdAt: Date.now()
    });
    wx.navigateTo({ url: '/pages/generating/generating' });
  },

  openHistory() {
    wx.navigateTo({ url: '/pages/history/history' });
  },

  continueProgress() {
    const quiz = wx.getStorageSync(api.QUIZ_KEY);
    if (!quiz || !quiz.questions || !quiz.questions.length) {
      wx.showToast({ title: '暂无可继续的答题', icon: 'none' });
      return;
    }

    const answers = wx.getStorageSync(api.ANSWERS_KEY) || [];
    if (answers.length >= quiz.questions.length) {
      wx.navigateTo({ url: '/pages/report/report' });
      return;
    }

    wx.navigateTo({ url: '/pages/quiz/quiz' });
  }
});
