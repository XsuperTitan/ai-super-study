const ai = require('../../services/mock-ai');

const examples = [
  '费曼学习法强调用自己的话解释一个概念，通过简单表达暴露理解漏洞，再回到资料中修正，最后用例子迁移应用。',
  '碎片化学习适合把零散时间用于短内容吸收，但需要及时复盘和自测，否则知识容易停留在看过但不会用的状态。',
  '复利思维说明微小改进在长期会形成巨大差异。关键不是一次性爆发，而是持续积累、减少损耗并保持方向正确。'
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
      canStart: content.trim().length >= 10
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
    const content = ai.normalizeSource(this.data.content);
    if (content.length < 10) {
      wx.showToast({ title: '至少输入 10 个字', icon: 'none' });
      return;
    }

    wx.setStorageSync(ai.SOURCE_KEY, {
      content,
      questionCount: this.data.questionCount,
      createdAt: Date.now()
    });
    wx.navigateTo({ url: '/pages/generating/generating' });
  }
});
