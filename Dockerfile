# Multi-stage, multi-target build. Two images share one dependency layer:
#   docker build --target api    -t vfe-api    .
#   docker build --target worker -t vfe-worker .
#
# Stages: builder (deps only, cached) -> runtime (slim, non-root) -> {api, worker}.

# ---- builder: resolve + install locked deps into /app/.venv ----------------
FROM python:3.12-slim-bookworm AS builder

# uv binary from the pinned official image (no curl|sh).
COPY --from=ghcr.io/astral-sh/uv:0.10.2 /uv /bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /app

# Install ONLY dependencies (package=false → no project build), cached on the
# uv cache mount and invalidated only when pyproject.toml / uv.lock change.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    uv sync --frozen --no-dev --no-install-project

# ---- runtime: slim base shared by every service image ----------------------
FROM python:3.12-slim-bookworm AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app/src"

# Non-root runtime user.
RUN groupadd --system app && useradd --system --gid app --home-dir /app app

WORKDIR /app
COPY --from=builder --chown=app:app /app/.venv /app/.venv
COPY --chown=app:app src ./src

USER app

# ---- api image -------------------------------------------------------------
FROM runtime AS api
EXPOSE 8000
# Liveness only — does not depend on the DB, so it never flaps on a DB outage.
HEALTHCHECK --interval=30s --timeout=3s --start-period=20s --retries=3 \
    CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health/live').status==200 else 1)"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

# ---- worker image ----------------------------------------------------------
FROM runtime AS worker
# Lightweight liveness: the entrypoint and its deps import cleanly.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import workers.runner"]
CMD ["python", "-m", "workers.runner"]
