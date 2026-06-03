# AI Super Study Backend

Python FastAPI backend for the MVP text loop:

```text
content -> quiz -> answers -> report
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
