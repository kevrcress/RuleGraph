# Backend image — serves the FastAPI app and also runs the arq ingest worker
# (same image, different command; see docker-compose.yml).
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# git    — GitPython clones source repos during ingest
# libmagic1 — python-magic sniffs uploaded file types
RUN apt-get update \
    && apt-get install -y --no-install-recommends git libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Dependency install is split because cognee 0.1.15 pins older
# anthropic/fastapi/sqlalchemy/uvicorn than the app requires, so a single
# `pip install -r requirements.txt` is unresolvable. Install cognee first, then
# the rest (minus cognee), which upgrades those shared packages to the versions
# the app actually uses. cognee's stale pins become warnings, not errors — the
# same coexistence the app runs with (cognee failures are silent by design).
COPY requirements.txt .
RUN python -m pip install --upgrade pip \
    && pip install "cognee==0.1.15" \
    && grep -v '^cognee==' requirements.txt > requirements.runtime.txt \
    && pip install -r requirements.runtime.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
