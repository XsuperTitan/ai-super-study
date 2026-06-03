const api = require('./api');

const HISTORY_KEY = 'm0_study_history';
const ANONYMOUS_ID_KEY = 'm0_anonymous_id';
const MAX_HISTORY_COUNT = 10;

function getAnonymousId() {
  let value = wx.getStorageSync(ANONYMOUS_ID_KEY);
  if (!value) {
    value = 'anon_' + Date.now() + '_' + Math.random().toString(36).slice(2, 10);
    wx.setStorageSync(ANONYMOUS_ID_KEY, value);
  }
  return value;
}

function getLocalHistory() {
  const value = wx.getStorageSync(HISTORY_KEY);
  return Array.isArray(value) ? value : [];
}

function setLocalHistory(list) {
  wx.setStorageSync(HISTORY_KEY, list.slice(0, MAX_HISTORY_COUNT));
}

function upsertLocalHistory(record) {
  if (!record || !record.historyId) return null;
  const list = getLocalHistory();
  const existedIndex = list.findIndex(item => item.historyId === record.historyId);
  if (existedIndex >= 0) {
    list.splice(existedIndex, 1);
  }
  list.unshift(record);
  setLocalHistory(list);
  return record;
}

function buildRecord(payload) {
  const source = payload.source || {};
  const quiz = payload.quiz || {};
  const answers = payload.answers || [];
  const report = payload.report || {};
  if (!quiz.quizId || !report.reportId) return null;

  const existed = getLocalHistory().find(item => item.historyId === quiz.quizId);
  const now = Date.now();
  return {
    historyId: quiz.quizId,
    sourceContent: source.content || '',
    sourcePreview: excerpt(source.content || '', 80),
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
}

function getHistory() {
  return requestRemoteHistory()
    .then(records => {
      setLocalHistory(records);
      return records;
    })
    .catch(() => getLocalHistory());
}

function saveStudyHistory(payload) {
  const record = buildRecord(payload);
  if (!record) return Promise.resolve(null);

  return saveRemoteHistory(record)
    .then(remoteRecord => upsertLocalHistory(remoteRecord))
    .catch(() => upsertLocalHistory(record));
}

function getHistoryRecord(historyId) {
  return requestRemoteHistoryRecord(historyId)
    .then(record => {
      upsertLocalHistory(record);
      return record;
    })
    .catch(() => getLocalHistory().find(item => item.historyId === historyId));
}

function deleteHistoryRecord(historyId) {
  return deleteRemoteHistoryRecord(historyId)
    .catch(() => null)
    .then(() => {
      const list = getLocalHistory().filter(item => item.historyId !== historyId);
      setLocalHistory(list);
      return list;
    });
}

function clearHistory() {
  return clearRemoteHistory()
    .catch(() => null)
    .then(() => {
      wx.removeStorageSync(HISTORY_KEY);
      return [];
    });
}

function requestRemoteHistory() {
  return api.request('/api/v1/history?anonymousId=' + encodeURIComponent(getAnonymousId()), 'GET')
    .then(data => data.records || []);
}

function requestRemoteHistoryRecord(historyId) {
  return api.request(
    '/api/v1/history/' + encodeURIComponent(historyId) + '?anonymousId=' + encodeURIComponent(getAnonymousId()),
    'GET'
  ).then(data => data.record);
}

function saveRemoteHistory(record) {
  return api.request('/api/v1/history', 'POST', {
    anonymousId: getAnonymousId(),
    historyId: record.historyId,
    sourceContent: record.sourceContent,
    quiz: record.quiz,
    answers: record.answers,
    report: record.report,
    provider: record.provider,
    questionCount: record.questionCount,
    accuracy: record.accuracy,
    score: record.score
  }).then(data => data.record);
}

function deleteRemoteHistoryRecord(historyId) {
  return api.request(
    '/api/v1/history/' + encodeURIComponent(historyId) + '?anonymousId=' + encodeURIComponent(getAnonymousId()),
    'DELETE'
  );
}

function clearRemoteHistory() {
  return api.request('/api/v1/history?anonymousId=' + encodeURIComponent(getAnonymousId()), 'DELETE');
}

function excerpt(text, size) {
  const value = String(text || '').replace(/\s+/g, ' ').trim();
  return value.length > size ? value.slice(0, size) + '...' : value;
}

module.exports = {
  HISTORY_KEY,
  ANONYMOUS_ID_KEY,
  MAX_HISTORY_COUNT,
  getAnonymousId,
  getHistory,
  saveStudyHistory,
  getHistoryRecord,
  deleteHistoryRecord,
  clearHistory
};
