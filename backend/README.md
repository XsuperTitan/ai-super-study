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
