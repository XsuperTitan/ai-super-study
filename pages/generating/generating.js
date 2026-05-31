const api = require('../../services/api');

function createSteps() {
  return [
    { index: 1, title: '识别主题', desc: '等待输入内容', done: false, failed: false },
    { index: 2, title: '提炼考点', desc: '准备生成关键概念', done: false, failed: false },
    { index: 3, title: '生成题目', desc: '构造选项与答案', done: false, failed: false },
    { index: 4, title: '校验结构', desc: '检查题干、答案和解析', done: false, failed: false }
  ];
}

Page({
  data: {
    progress: 8,
    steps: createSteps(),
    failed: false,
    errorMessage: ''
  },

  onLoad() {
    const source = wx.getStorageSync(api.SOURCE_KEY);
    if (!source || !source.content) {
      wx.redirectTo({ url: '/pages/index/index' });
      return;
    }
    this.currentSource = source;
    this.run(source);
  },

  onUnload() {
    if (this.timer) clearTimeout(this.timer);
  },

  run(source) {
    if (this.timer) clearTimeout(this.timer);
    this.setData({
      progress: 8,
      steps: createSteps(),
      failed: false,
      errorMessage: ''
    });

    const marks = [
      { progress: 22, done: 1, desc: '主题已识别' },
      { progress: 48, done: 2, desc: '关键概念已收束' },
      { progress: 76, done: 3, desc: '题目草稿已生成' }
    ];
    let index = 0;

    const tick = () => {
      const mark = marks[index];
      const steps = this.data.steps.map(item => {
        if (item.index <= mark.done) {
          return Object.assign({}, item, { done: true, desc: item.index === mark.done ? mark.desc : item.desc });
        }
        return item;
      });
      this.setData({ progress: mark.progress, steps });
      index += 1;

      if (index < marks.length) {
        this.timer = setTimeout(tick, 520);
        return;
      }

      api.generateQuiz(source)
        .then(quiz => {
          const steps = this.data.steps.map(item => (
            item.index === 4
              ? Object.assign({}, item, { done: true, failed: false, desc: '结构校验完成' })
              : item
          ));
          this.setData({ progress: 100, steps, failed: false, errorMessage: '' });
          wx.setStorageSync(api.QUIZ_KEY, quiz);
          wx.setStorageSync(api.ANSWERS_KEY, []);
          this.timer = setTimeout(() => {
            wx.redirectTo({ url: '/pages/quiz/quiz' });
          }, 420);
        })
        .catch(error => {
          const message = error.message || '生成失败，请稍后重试';
          const steps = this.data.steps.map(item => (
            item.index === 4
              ? Object.assign({}, item, { done: false, failed: true, desc: message })
              : item
          ));
          this.setData({ progress: 76, steps, failed: true, errorMessage: message });
          wx.showToast({ title: '生成失败，请查看提示', icon: 'none' });
        });
    };

    this.timer = setTimeout(tick, 420);
  },

  retryGenerate() {
    if (!this.currentSource) {
      wx.redirectTo({ url: '/pages/index/index' });
      return;
    }
    this.run(this.currentSource);
  },

  backHome() {
    wx.redirectTo({ url: '/pages/index/index' });
  }
});
