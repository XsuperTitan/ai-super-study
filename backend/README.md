# AI Super Study Backend

Python FastAPI backend for the AI micro-learning loop:

```text
content/url/wechat article -> quiz -> answers -> report -> history
```

## Local setup

```powershell
cd C:\projects\ai-super-questions\backend
python -m pip install -r requirements.txt
Copy-Item .env.example .env
# Edit .env and set DEEPSEEK_API_KEY locally. Do not commit .env.
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

For local WeChat Developer Tools testing, keep the mini program API base URL at `http://127.0.0.1:8000` and disable legal domain validation in the devtools details panel.

## Tests

```powershell
cd C:\projects\ai-super-questions\backend
python -m pytest
```

The backend test suite covers:

- Quiz and report generation APIs.
- Job polling and NDJSON stream output.
- MySQL-backed history APIs.
- Plain webpage URL parsing and quiz generation.
- Public WeChat article parsing through `mp.weixin.qq.com` URLs.
- Bilibili public video subtitle parsing through `bilibili.com` or `b23.tv` URLs.
- URL safety checks, redirect limits, non-HTML rejection, short-content errors, and long-content truncation.

## Optional MySQL history storage

The mini program still falls back to local storage when server history is disabled. To enable server-side history records:

```powershell
cd C:\projects\ai-super-questions\backend
Copy-Item .env.example .env
# Set DATABASE_URL in .env:
# DATABASE_URL=mysql+pymysql://user:password@host:3306/ai_super_questions?charset=utf8mb4
python -m alembic upgrade head
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

`DATABASE_URL` can be left empty for normal local MVP development. In that mode, `/api/v1/history` returns a disabled response and the mini program keeps using local cached history.

## M0 history acceptance check

After starting the backend with `DATABASE_URL` enabled, run:

```powershell
cd C:\projects\ai-super-questions\backend
python scripts\history_e2e_check.py --keep-record
```

The script checks `health -> quiz generation -> report generation -> save history -> list history -> history detail` against the running API. It requires `/health` to return `historyDatabase: true`; omit `--keep-record` to delete the generated check record after verification.

## URL and WeChat article parsing

`POST /api/v1/quiz/generate` accepts `sourceType=url`. The parser supports ordinary public HTML webpages, publicly accessible WeChat article pages under `mp.weixin.qq.com`, and Bilibili public videos when subtitle JSON is discoverable from the page. If a Bilibili video has no accessible subtitle URL, the parser falls back to public title/description/tag text when that text is long enough.

Current limits:

- No login simulation or anti-scraping bypass.
- No JavaScript-rendered page execution.
- No Bilibili audio download, speech transcription, PDF/Doc, or OCR yet.
- If parsing fails or the body/subtitle is too short, ask the user to copy the article body, video subtitle, or video notes and retry as plain text.
