const ai = require('../../services/mock-ai');

Page({
  data: {
    progress: 8,
    steps: [
      { index: 1, title: '识别主题', desc: '等待输入内容', done: false },
      { index: 2, title: '提炼考点', desc: '准备生成关键概念', done: false },
      { index: 3, title: '生成题目', desc: '构造选项与答案', done: false },
      { index: 4, title: '校验结构', desc: '检查题干、答案和解析', done: false }
    ]
  },

  onLoad() {
    const source = wx.getStorageSync(ai.SOURCE_KEY);
    if (!source || !source.content) {
      wx.redirectTo({ url: '/pages/index/index' });
      return;
    }
    this.run(source);
  },

  onUnload() {
    if (this.timer) clearTimeout(this.timer);
  },

  run(source) {
    const marks = [
      { progress: 22, done: 1, desc: '主题已识别' },
      { progress: 48, done: 2, desc: '关键概念已收束' },
      { progress: 76, done: 3, desc: '题目草稿已生成' },
      { progress: 100, done: 4, desc: '结构校验完成' }
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

      const quiz = ai.generateQuiz(source);
      wx.setStorageSync(ai.QUIZ_KEY, quiz);
      wx.setStorageSync(ai.ANSWERS_KEY, []);
      this.timer = setTimeout(() => {
        wx.redirectTo({ url: '/pages/quiz/quiz' });
      }, 420);
    };

    this.timer = setTimeout(tick, 420);
  },

  backHome() {
    wx.redirectTo({ url: '/pages/index/index' });
  }
});
