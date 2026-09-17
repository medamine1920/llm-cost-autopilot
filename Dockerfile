# syntax=docker/dockerfile:1

# ---------- Stage 1: builder ----------
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Deps installed from pinned file, BEFORE any app code (layer caching)
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# ---------- Stage 2: runtime ----------
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Bring in only the installed packages, not build tooling
COPY --from=builder /opt/venv /opt/venv

# App code last — changes here don't invalidate the deps layer
COPY app ./app

# Fix for blocker 2: don't run as root
RUN useradd --create-home --shell /bin/bash appuser
USER appuser

EXPOSE 8000

# Exec form, final stage, last line — the line that was lost
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]