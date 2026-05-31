const api = require('../../services/api');

const examples = [
  'RAG',
  '向量数据库',
  '费曼学习法',
  'RAG是AI的检索增强引擎'
];

Page({
  data: {
    content: examples[0],
    contentLength: examples[0].length,
    questionCount: 3,
    canStart: true
  },

  onInput(event) {
    const content = event.detail.value || '';
    this.setData({
      content,
      contentLength: content.length,
      canStart: content.trim().length >= api.MIN_SOURCE_LENGTH
    });
  },

  useExample(event) {
    const index = Number(event.currentTarget.dataset.index || 0);
    const content = examples[index] || examples[0];
    this.setData({
      content,
      contentLength: content.length,
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
      questionCount: this.data.questionCount,
      createdAt: Date.now()
    });
    wx.navigateTo({ url: '/pages/generating/generating' });
  }
});
