const QUIZ_KEY = 'm0_current_quiz';
const SOURCE_KEY = 'm0_source';
const ANSWERS_KEY = 'm0_answers';
const REPORT_KEY = 'm0_report';
const API_BASE_URL_KEY = 'm0_api_base_url';
const DEFAULT_API_BASE_URL = 'http://127.0.0.1:8000';

const FALLBACK_SOURCE =
  '费曼学习法强调用自己的话解释一个概念，通过简单表达暴露理解漏洞，再回到资料中修正，最后用例子迁移应用。';
const MIN_SOURCE_LENGTH = 2;

function normalizeSource(content) {
  const text = String(content || '').trim();
  return text || FALLBACK_SOURCE;
}

function getApiBaseUrl() {
  return wx.getStorageSync(API_BASE_URL_KEY) || DEFAULT_API_BASE_URL;
}

function formatRequestError(error) {
  const message = String((error && (error.errMsg || error.message)) || '网络请求失败');
  if (message.includes('url not in domain list')) {
    return '本地后端请求被微信合法域名校验拦截。请在微信开发者工具详情/本地设置中开启“不校验合法域名、web-view、TLS 版本以及 HTTPS 证书”。';
  }
  if (message.includes('timeout')) {
    return '本地后端响应超时，请确认 Python 服务已启动后重试。';
  }
  if (message.includes('fail')) {
    return '无法连接本地 Python 后端，请确认 http://127.0.0.1:8000/health 可以访问。';
  }
  return message;
}

function request(path, method, data) {
  return new Promise((resolve, reject) => {
    wx.request({
      url: getApiBaseUrl() + path,
      method,
      data,
      timeout: 60000,
      header: {
        'content-type': 'application/json'
      },
      success(res) {
        const body = res.data || {};
        if (res.statusCode >= 200 && res.statusCode < 300 && body.success !== false) {
          resolve(body.data || body);
          return;
        }
        const message = body.error && body.error.message ? body.error.message : '服务暂时不可用';
        reject(new Error(message));
      },
      fail(error) {
        reject(new Error(formatRequestError(error)));
      }
    });
  });
}

function generateQuiz(source) {
  return request('/api/v1/quiz/generate', 'POST', {
    sourceType: 'text',
    content: normalizeSource(source && source.content),
    questionCount: source && source.questionCount === 5 ? 5 : 3,
    questionTypes: ['single_choice', 'true_false'],
    difficulty: 'normal'
  }).then(data => data.quiz);
}

function generateReport(quiz, answers) {
  const list = answers || [];
  const duration = list.reduce((sum, item) => sum + (Number(item.duration) || 0), 0);
  return request('/api/v1/reports/generate', 'POST', {
    quizId: quiz.quizId,
    questions: quiz.questions || [],
    answers: list,
    duration
  }).then(data => data.report);
}

module.exports = {
  QUIZ_KEY,
  SOURCE_KEY,
  ANSWERS_KEY,
  REPORT_KEY,
  API_BASE_URL_KEY,
  DEFAULT_API_BASE_URL,
  MIN_SOURCE_LENGTH,
  normalizeSource,
  getApiBaseUrl,
  formatRequestError,
  generateQuiz,
  generateReport
};
