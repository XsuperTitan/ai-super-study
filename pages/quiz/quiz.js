const api = require('../../services/api');

Page({
  data: {
    quiz: null,
    currentIndex: 0,
    currentNumber: 1,
    total: 0,
    progress: 0,
    currentQuestion: {},
    displayOptions: [],
    selectedOption: '',
    submitted: false,
    isCorrect: false,
    isLast: false,
    modelProviderLabel: ''
  },

  onLoad() {
    const quiz = wx.getStorageSync(api.QUIZ_KEY);
    if (!quiz || !quiz.questions || !quiz.questions.length) {
      wx.redirectTo({ url: '/pages/index/index' });
      return;
    }
    const answers = wx.getStorageSync(api.ANSWERS_KEY) || [];
    const currentIndex = Math.min(answers.length, quiz.questions.length - 1);
    this.startedAt = Date.now();
    this.setData({
      quiz,
      currentIndex,
      total: quiz.questions.length,
      modelProviderLabel: formatProviderLabel(quiz)
    }, () => this.syncQuestion());
  },

  syncQuestion() {
    const question = this.data.quiz.questions[this.data.currentIndex];
    const typeLabel = question.type === 'true_false' ? '判断题' : '单选题';
    const currentQuestion = Object.assign({}, question, { typeLabel });
    const displayOptions = question.options.map(option => ({
      id: option.id,
      text: option.text,
      className: ''
    }));
    const currentNumber = this.data.currentIndex + 1;
    this.setData({
      currentQuestion,
      displayOptions,
      currentNumber,
      progress: Math.round((this.data.currentIndex / this.data.total) * 100),
      selectedOption: '',
      submitted: false,
      isCorrect: false,
      isLast: currentNumber === this.data.total
    });
    this.startedAt = Date.now();
  },

  chooseOption(event) {
    const id = event.currentTarget.dataset.id;
    const displayOptions = this.data.currentQuestion.options.map(option => ({
      id: option.id,
      text: option.text,
      className: option.id === id ? 'selected' : ''
    }));
    this.setData({ selectedOption: id, displayOptions });
  },

  submitAnswer() {
    if (!this.data.selectedOption) return;

    const question = this.data.currentQuestion;
    const isCorrect = this.data.selectedOption === question.answer;
    const displayOptions = question.options.map(option => {
      let className = '';
      if (option.id === question.answer) className = 'correct';
      if (option.id === this.data.selectedOption && !isCorrect) className = 'wrong';
      return { id: option.id, text: option.text, className };
    });

    const answers = wx.getStorageSync(api.ANSWERS_KEY) || [];
    answers.push({
      questionId: question.id,
      selectedOption: this.data.selectedOption,
      isCorrect,
      duration: Math.max(1, Math.round((Date.now() - this.startedAt) / 1000))
    });
    wx.setStorageSync(api.ANSWERS_KEY, answers);

    this.setData({
      submitted: true,
      isCorrect,
      displayOptions,
      progress: Math.round(((this.data.currentIndex + 1) / this.data.total) * 100)
    });
  },

  nextQuestion() {
    if (this.data.isLast) {
      wx.redirectTo({ url: '/pages/report/report' });
      return;
    }
    this.setData({ currentIndex: this.data.currentIndex + 1 }, () => this.syncQuestion());
  },

  restart() {
    wx.redirectTo({ url: '/pages/index/index' });
  }
});

function formatProviderLabel(quiz) {
  if (!quiz || !quiz.modelProvider) return 'AI 引擎';
  if (quiz.modelProvider === 'deepseek') return 'DeepSeek';
  if (quiz.modelProvider === 'mock') return quiz.fallbackReason ? 'Mock 兜底' : 'Mock';
  return quiz.modelProvider;
}
