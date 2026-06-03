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
    errorMessage: '',
    modeText: '流式生成'
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
    this.stopTimers();
    this.runId = '';
  },

  run(source) {
    this.stopTimers();
    this.runId = 'run_' + Date.now();
    this.polling = false;
    this.completed = false;
    this.currentSource = source;
    this.setData({
      progress: 8,
      steps: createSteps(),
      failed: false,
      errorMessage: '',
      modeText: '流式生成'
    });

    const runId = this.runId;
    this.noChunkTimer = setTimeout(() => {
      this.switchToPolling(runId, '流式响应暂未返回，已切换为稳定轮询');
    }, 3000);

    api.generateQuizStream(source, {
      onProgress: event => {
        if (!this.isActive(runId)) return;
        if (this.noChunkTimer) {
          clearTimeout(this.noChunkTimer);
          this.noChunkTimer = null;
        }
        this.applyProgress(event.progress || 18, event.message || '正在生成题目');
      }
    })
      .then(quiz => {
        if (!this.isActive(runId) || this.polling) return;
        this.completeQuiz(runId, quiz);
      })
      .catch(error => {
        if (!this.isActive(runId)) return;
        this.switchToPolling(runId, error.message || '流式生成失败，已切换为轮询');
      });
  },

  switchToPolling(runId, message) {
    if (!this.isActive(runId) || this.polling || this.completed) return;
    this.polling = true;
    if (this.noChunkTimer) {
      clearTimeout(this.noChunkTimer);
      this.noChunkTimer = null;
    }
    this.setData({ modeText: '轮询生成' });
    this.applyProgress(Math.max(this.data.progress, 18), message || '已切换为稳定轮询');

    api.createQuizJob(this.currentSource)
      .then(job => {
        if (!this.isActive(runId)) return;
        this.pollJob(runId, job.jobId, 0);
      })
      .catch(() => {
        if (!this.isActive(runId)) return;
        this.applyProgress(Math.max(this.data.progress, 24), '轮询创建失败，尝试普通生成');
        api.generateQuiz(this.currentSource)
          .then(quiz => this.completeQuiz(runId, quiz))
          .catch(error => this.failGenerate(runId, error.message || '生成失败，请稍后重试'));
      });
  },

  pollJob(runId, jobId, count) {
    if (!this.isActive(runId) || this.completed) return;
    if (count > 75) {
      this.failGenerate(runId, '生成超时，请稍后重试');
      return;
    }

    api.getJobStatus(jobId)
      .then(job => {
        if (!this.isActive(runId)) return;
        this.applyProgress(job.progress || this.data.progress, job.message || '正在生成中');
        if (job.status === 'succeeded') {
          this.completeQuiz(runId, quizFromJob(job));
          return;
        }
        if (job.status === 'failed') {
          const message = job.error && job.error.message ? job.error.message : '生成失败，请稍后重试';
          this.failGenerate(runId, message);
          return;
        }
        this.pollTimer = setTimeout(() => this.pollJob(runId, jobId, count + 1), 1200);
      })
      .catch(error => {
        if (!this.isActive(runId)) return;
        this.failGenerate(runId, error.message || '查询生成任务失败');
      });
  },

  applyProgress(progress, message) {
    const safeProgress = Math.max(8, Math.min(Number(progress) || 8, 99));
    const doneCount = safeProgress >= 90 ? 3 : safeProgress >= 68 ? 2 : safeProgress >= 30 ? 1 : 0;
    const steps = this.data.steps.map(item => {
      if (item.index <= doneCount) {
        return Object.assign({}, item, { done: true, failed: false, desc: item.index === doneCount ? message : item.desc });
      }
      if (item.index === doneCount + 1) {
        return Object.assign({}, item, { desc: message });
      }
      return item;
    });
    this.setData({ progress: safeProgress, steps });
  },

  completeQuiz(runId, quiz) {
    if (!this.isActive(runId) || this.completed) return;
    this.completed = true;
    this.stopTimers();
    const steps = this.data.steps.map(item => (
      item.index === 4
        ? Object.assign({}, item, { done: true, failed: false, desc: '结构校验完成' })
        : Object.assign({}, item, { done: true, failed: false })
    ));
    this.setData({ progress: 100, steps, failed: false, errorMessage: '' });
    wx.setStorageSync(api.QUIZ_KEY, quiz);
    wx.setStorageSync(api.ANSWERS_KEY, []);
    wx.removeStorageSync(api.REPORT_KEY);
    this.redirectTimer = setTimeout(() => {
      if (this.isActive(runId)) wx.redirectTo({ url: '/pages/quiz/quiz' });
    }, 420);
  },

  failGenerate(runId, message) {
    if (!this.isActive(runId)) return;
    this.stopTimers();
    const steps = this.data.steps.map(item => (
      item.index === 4
        ? Object.assign({}, item, { done: false, failed: true, desc: message })
        : item
    ));
    this.setData({ progress: Math.max(this.data.progress, 76), steps, failed: true, errorMessage: message });
    wx.showToast({ title: '生成失败，请查看提示', icon: 'none' });
  },

  stopTimers() {
    if (this.noChunkTimer) clearTimeout(this.noChunkTimer);
    if (this.pollTimer) clearTimeout(this.pollTimer);
    if (this.redirectTimer) clearTimeout(this.redirectTimer);
    this.noChunkTimer = null;
    this.pollTimer = null;
    this.redirectTimer = null;
  },

  isActive(runId) {
    return this.runId === runId;
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

function quizFromJob(job) {
  const result = job.result || {};
  const quiz = result.quiz || {};
  quiz.modelProvider = result.provider || 'unknown';
  quiz.fallbackReason = result.fallbackReason || '';
  return quiz;
}
