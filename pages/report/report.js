const ai = require('../../services/mock-ai');

function formatDuration(seconds) {
  const safeSeconds = Math.max(0, Number(seconds) || 0);
  const minutes = Math.floor(safeSeconds / 60);
  const rest = safeSeconds % 60;
  return `${minutes}:${rest < 10 ? '0' : ''}${rest}`;
}

Page({
  data: {
    quiz: null,
    report: null,
    durationText: '0:00',
    knowledgeMap: [],
    weakPoints: []
  },

  onLoad() {
    const quiz = wx.getStorageSync(ai.QUIZ_KEY);
    const answers = wx.getStorageSync(ai.ANSWERS_KEY) || [];

    if (!quiz || !quiz.questions) {
      wx.redirectTo({ url: '/pages/index/index' });
      return;
    }

    const report = ai.generateReport(quiz, answers);
    wx.setStorageSync(ai.REPORT_KEY, report);

    const knowledgeMap = report.knowledgeMap.map((item) => ({
      ...item,
      name: item.topic,
      className: item.mastery === 'weak' ? 'weak' : item.mastery === 'good' ? 'good' : 'normal'
    }));

    this.setData({
      quiz,
      report,
      durationText: formatDuration(report.duration),
      knowledgeMap,
      weakPoints: report.weakPoints
    });
  },

  restart() {
    wx.removeStorageSync(ai.QUIZ_KEY);
    wx.removeStorageSync(ai.ANSWERS_KEY);
    wx.removeStorageSync(ai.REPORT_KEY);
    wx.redirectTo({ url: '/pages/index/index' });
  },

  onShareAppMessage() {
    const report = this.data.report;
    return {
      title: report ? report.shareText : '我完成了一次 AI 知识闯关',
      path: '/pages/index/index'
    };
  }
});
