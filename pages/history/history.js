const api = require('../../services/api');
const history = require('../../services/history');

function excerpt(text, size) {
  const value = String(text || '').replace(/\s+/g, ' ').trim();
  return value.length > size ? `${value.slice(0, size)}...` : value;
}

function formatTime(value) {
  const date = new Date(value || Date.now());
  const month = date.getMonth() + 1;
  const day = date.getDate();
  const hour = String(date.getHours()).padStart(2, '0');
  const minute = String(date.getMinutes()).padStart(2, '0');
  return `${month}/${day} ${hour}:${minute}`;
}

function formatProvider(provider) {
  if (provider === 'deepseek') return 'DeepSeek';
  if (provider === 'mock') return 'Mock';
  return provider || 'AI';
}

Page({
  data: {
    records: [],
    hasHistory: false,
    loading: false
  },

  onShow() {
    this.loadHistory();
  },

  loadHistory() {
    this.setData({ loading: true });
    history.getHistory()
      .then(list => {
        const records = list.map(item => ({
          ...item,
          title: item.quiz && item.quiz.title ? item.quiz.title : '未命名闯关',
          sourcePreview: item.sourcePreview || excerpt(item.sourceContent, 42),
          timeText: formatTime(item.updatedAt || item.createdAt),
          providerText: formatProvider(item.provider),
          questionText: `${item.questionCount || 0} 题`
        }));
        this.setData({
          records,
          hasHistory: records.length > 0,
          loading: false
        });
      })
      .catch(() => {
        this.setData({ records: [], hasHistory: false, loading: false });
      });
  },

  openRecord(event) {
    const historyId = event.currentTarget.dataset.id;
    history.getHistoryRecord(historyId)
      .then(record => {
        if (!record) {
          wx.showToast({ title: '记录不存在', icon: 'none' });
          this.loadHistory();
          return;
        }

        wx.setStorageSync(api.SOURCE_KEY, {
          content: record.sourceContent,
          questionCount: record.questionCount || 3,
          restoredFromHistory: true,
          createdAt: record.createdAt
        });
        wx.setStorageSync(api.QUIZ_KEY, record.quiz);
        wx.setStorageSync(api.ANSWERS_KEY, record.answers || []);
        wx.setStorageSync(api.REPORT_KEY, record.report);
        wx.redirectTo({ url: '/pages/report/report' });
      });
  },

  deleteRecord(event) {
    const historyId = event.currentTarget.dataset.id;
    wx.showModal({
      title: '删除记录',
      content: '这条学习记录会从本机移除。',
      confirmText: '删除',
      confirmColor: '#d85c74',
      success: (res) => {
        if (!res.confirm) return;
        history.deleteHistoryRecord(historyId).then(() => this.loadHistory());
      }
    });
  },

  clearAll() {
    wx.showModal({
      title: '清空历史',
      content: '最近 10 条本地学习记录都会被清空。',
      confirmText: '清空',
      confirmColor: '#d85c74',
      success: (res) => {
        if (!res.confirm) return;
        history.clearHistory().then(() => this.loadHistory());
      }
    });
  },

  backHome() {
    wx.redirectTo({ url: '/pages/index/index' });
  }
});
