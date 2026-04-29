# Temple Identity Service

FastAPI service for sign-in, session lifecycle, and role-aware user lookup.

## Responsibilities

- contact number and password sign-in
- refresh and sign-out endpoints
- current user profile lookup
- future session persistence and token rotation

## Local run

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e .
uvicorn app.main:app --reload --port 8001
```

## Render start command

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

