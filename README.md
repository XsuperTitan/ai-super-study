# AI Super Questions

微信小程序 + Python FastAPI 的 AI 微学习闯关原型。用户输入短主题、长文本、普通网页 URL 或公开可访问的微信公众号文章链接后，后端调用 DeepSeek 或 Mock Adapter 生成结构化题目；用户答题后生成学习报告，并可将学习历史保存到 MySQL 或回退到本地缓存。

## 当前状态

已完成的主线能力：

- M0 核心闭环：输入内容 -> 生成题目 -> 答题 -> 生成报告。
- DeepSeek / Mock 模型适配，后端统一结构化校验。
- MySQL 服务端学习历史，支持本地缓存兜底。
- M1 生成体验：流式进度、任务轮询降级、普通接口兜底。
- 首页推荐知识 4 行 2 列、继续答题进度、历史入口。
- M2.1 普通网页 URL 解析：支持重定向安全校验、HTML 白名单、正文抽取、截断和清晰错误码。
- M2.2 公众号文章解析：支持公开可访问的 `mp.weixin.qq.com` 文章正文抽取并生成题目。

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

运行 M0 历史闭环自测：

```powershell
cd C:\projects\ai-super-questions\backend
python scripts\history_e2e_check.py --keep-record
```

该脚本会请求正在运行的后端，按 `生成题目 -> 生成报告 -> 保存历史 -> 历史列表 -> 历史详情` 跑一遍。默认要求 `/health` 中 `historyDatabase` 为 `true`，用于验证真实服务端历史链路；不加 `--keep-record` 时会在校验后删除本次生成的记录。

## 小程序本地联调

1. 用微信开发者工具打开项目根目录。
2. 确认小程序端 API Base URL 为 `http://127.0.0.1:8000`。
3. 在开发者工具本地设置里开启“不校验合法域名、web-view、TLS 版本以及 HTTPS 证书”。
4. 从首页输入短主题、长文本、普通网页 URL 或公开可访问的公众号文章链接。
5. 完成生成、答题、报告、历史回看流程。

推荐自测输入：

```text
RAG
```

```text
https://www.python.org/about/gettingstarted/
```

```text
公开可访问的微信公众号文章链接，例如 https://mp.weixin.qq.com/s/...
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

- M0：核心闭环和 MySQL 历史自测已完成，持续回归。
- M1：流式生成、轮询降级、普通接口兜底、分享入口和历史体验基础已完成。
- M2.1：普通网页 URL 解析已完成。
- M2.2：公众号文章解析可行性闭环已完成，只支持公开可访问文章，不做反爬绕过。
- M2 后续：B 站字幕、PDF/Doc、OCR 继续按单一目标小步验证。
- M3：登录、支付、商业化、RAG、多人 PK 暂缓到产品价值验证后。
