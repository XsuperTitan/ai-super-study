const api = require('../../services/api');
const history = require('../../services/history');

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
    const quiz = wx.getStorageSync(api.QUIZ_KEY);
    const answers = wx.getStorageSync(api.ANSWERS_KEY) || [];
    const source = wx.getStorageSync(api.SOURCE_KEY) || {};
    const cachedReport = wx.getStorageSync(api.REPORT_KEY);

    if (!quiz || !quiz.questions) {
      wx.redirectTo({ url: '/pages/index/index' });
      return;
    }

    if (cachedReport && cachedReport.quizId === quiz.quizId) {
      history.saveStudyHistory({ source, quiz, answers, report: cachedReport });
      this.displayReport(quiz, cachedReport);
      return;
    }

    api.generateReport(quiz, answers)
      .then(report => {
        wx.setStorageSync(api.REPORT_KEY, report);
        history.saveStudyHistory({ source, quiz, answers, report });
        this.displayReport(quiz, report);
      })
      .catch(error => {
        wx.showModal({
          title: '报告生成失败',
          content: error.message || '请检查后端服务是否已启动',
          showCancel: false,
          success: () => wx.redirectTo({ url: '/pages/index/index' })
        });
      });
  },

  displayReport(quiz, report) {
    const knowledgeMap = (report.knowledgeMap || []).map((item) => ({
      ...item,
      name: item.topic,
      className: item.mastery === 'weak' ? 'weak' : item.mastery === 'good' ? 'good' : 'normal'
    }));

    this.setData({
      quiz,
      report,
      durationText: formatDuration(report.duration),
      knowledgeMap,
      weakPoints: report.weakPoints || []
    });
  },

  restart() {
    wx.removeStorageSync(api.QUIZ_KEY);
    wx.removeStorageSync(api.ANSWERS_KEY);
    wx.removeStorageSync(api.REPORT_KEY);
    wx.redirectTo({ url: '/pages/index/index' });
  },

  openHistory() {
    wx.navigateTo({ url: '/pages/history/history' });
  },

  onShareAppMessage() {
    const report = this.data.report;
    return {
      title: report ? report.shareText : '我完成了一次 AI 知识闯关',
      path: '/pages/index/index'
    };
  }
});
