# AI Super Questions

微信小程序 + Python FastAPI 的 AI 微学习闯关原型。用户输入短主题、长文本或普通网页 URL 后，后端调用 DeepSeek 或 Mock Adapter 生成结构化题目；用户答题后生成学习报告，并可将学习历史保存到 MySQL 或回退到本地缓存。

## 当前状态

已完成的主线能力：

- M0 核心闭环：输入内容 -> 生成题目 -> 答题 -> 生成报告。
- DeepSeek / Mock 模型适配，后端统一结构化校验。
- MySQL 服务端学习历史，支持本地缓存兜底。
- M1 生成体验：流式进度、任务轮询降级、普通接口兜底。
- 首页推荐知识 4 行 2 列、继续答题进度、历史入口。
- M2.1 普通网页 URL 解析，可粘贴网页链接生成题目。

近期开发纪律：

```text
1. 只选一个目标
2. 写清楚验收场景
3. 后端先测接口
4. 小程序再联调
5. 最后真机验证
```

当前最重要的验收场景：

```text
生成题目 -> 答题 -> 报告页 -> MySQL 入库 -> 历史页回看
```

## 项目结构

```text
.
├── backend/                 Python FastAPI 后端
│   ├── app/
│   ├── migrations/           Alembic 迁移
│   └── tests/
├── docs/                     方案与规划文档
├── pages/                    微信小程序页面
├── services/                 小程序端 API 与历史服务
├── app.js
├── app.json
└── app.wxss
```

## 后端本地运行

```powershell
cd C:\projects\ai-super-questions\backend
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

编辑 `backend/.env`：

```env
AI_PROVIDER=deepseek
DEEPSEEK_API_KEY=replace-with-your-local-key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
DATABASE_URL=mysql+pymysql://user:password@127.0.0.1:3306/ai_super_questions?charset=utf8mb4
```

不要提交 `.env`，仓库已忽略本地密钥文件。

初始化数据库：

```powershell
cd C:\projects\ai-super-questions\backend
python -m alembic upgrade head
```

启动后端：

```powershell
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

健康检查：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

当 MySQL 历史可用时，期望 `historyDatabase` 为 `true`。

## 小程序本地联调

1. 用微信开发者工具打开项目根目录。
2. 确认小程序端 API Base URL 为 `http://127.0.0.1:8000`。
3. 在开发者工具本地设置里开启“不校验合法域名、web-view、TLS 版本以及 HTTPS 证书”。
4. 从首页输入短主题、长文本或普通网页 URL。
5. 完成生成、答题、报告、历史回看流程。

推荐自测输入：

```text
RAG
```

```text
https://www.python.org/about/gettingstarted/
```

## 测试

后端测试：

```powershell
cd C:\projects\ai-super-questions\backend
python -m pytest
```

小程序 JS 语法检查：

```powershell
node --check pages\index\index.js
node --check pages\generating\generating.js
node --check pages\quiz\quiz.js
node --check pages\report\report.js
node --check pages\history\history.js
node --check services\api.js
node --check services\history.js
```

## 接口概览

- `GET /health`
- `POST /api/v1/quiz/generate`
- `POST /api/v1/quiz/generate/stream`
- `POST /api/v1/quiz/jobs`
- `GET /api/v1/jobs/{jobId}`
- `POST /api/v1/reports/generate`
- `POST /api/v1/history`
- `GET /api/v1/history`
- `GET /api/v1/history/{recordId}`
- `DELETE /api/v1/history/{recordId}`
- `DELETE /api/v1/history`

## 阶段路线

- M0：稳定核心闭环和 MySQL 历史自测。
- M1：继续打磨轮询降级、流式生成、分享和历史体验。
- M2.1：普通网页 URL 解析已先行实现，后续多源解析暂缓。
- M3：登录、支付、商业化、RAG、多人 PK 暂缓到产品价值验证后。

