const HISTORY_KEY = 'm0_study_history';
const MAX_HISTORY_COUNT = 10;

function getHistory() {
  const value = wx.getStorageSync(HISTORY_KEY);
  return Array.isArray(value) ? value : [];
}

function setHistory(list) {
  wx.setStorageSync(HISTORY_KEY, list.slice(0, MAX_HISTORY_COUNT));
}

function saveStudyHistory(payload) {
  const source = payload.source || {};
  const quiz = payload.quiz || {};
  const answers = payload.answers || [];
  const report = payload.report || {};
  if (!quiz.quizId || !report.reportId) return null;

  const list = getHistory();
  const existedIndex = list.findIndex(item => item.quiz && item.quiz.quizId === quiz.quizId);
  const existed = existedIndex >= 0 ? list[existedIndex] : null;
  const now = Date.now();
  const record = {
    historyId: existed ? existed.historyId : quiz.quizId,
    sourceContent: source.content || '',
    quiz,
    answers,
    report,
    createdAt: existed ? existed.createdAt : now,
    updatedAt: now,
    provider: quiz.modelProvider || 'unknown',
    questionCount: quiz.questionCount || (quiz.questions ? quiz.questions.length : 0),
    accuracy: report.accuracy || 0,
    score: report.score || 0
  };

  if (existedIndex >= 0) {
    list.splice(existedIndex, 1);
  }
  list.unshift(record);
  setHistory(list);
  return record;
}

function getHistoryRecord(historyId) {
  return getHistory().find(item => item.historyId === historyId);
}

function deleteHistoryRecord(historyId) {
  const list = getHistory().filter(item => item.historyId !== historyId);
  setHistory(list);
  return list;
}

function clearHistory() {
  wx.removeStorageSync(HISTORY_KEY);
}

module.exports = {
  HISTORY_KEY,
  MAX_HISTORY_COUNT,
  getHistory,
  saveStudyHistory,
  getHistoryRecord,
  deleteHistoryRecord,
  clearHistory
};
