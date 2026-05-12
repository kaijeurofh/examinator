# Production image for the FastAPI backend.
#
# Two stages:
#   builder  - resolves and installs runtime deps into /app/.venv via uv,
#              keeps build cache out of the final image.
#   runtime  - slim image with only the venv, source, and a non-root user.
#
# The `uv` binary is copied from Astral's official OCI image at a pinned tag
# (matching .devcontainer/Dockerfile). Bump both files in lockstep.

FROM ghcr.io/astral-sh/uv:0.11.13 AS uv

# ---------- builder ----------------------------------------------------------
FROM python:3.12-slim-bookworm AS builder

ENV UV_LINK_MODE=copy \
    UV_NO_PROGRESS=1 \
    UV_PYTHON_DOWNLOADS=never \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY --from=uv /uv /uvx /usr/local/bin/

WORKDIR /app

# Install runtime deps first (better layer caching). uv needs README + LICENSE
# because pyproject.toml's metadata references both files.
COPY pyproject.toml README.md LICENSE ./
COPY uv.lock* ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev --no-install-project

# Now install the project itself.
COPY src ./src
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev

# ---------- runtime ----------------------------------------------------------
FROM python:3.12-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:${PATH}"

# Drop privileges: the API has no reason to run as root.
RUN groupadd --system --gid 1001 examinator \
 && useradd  --system --uid 1001 --gid examinator --create-home examinator

WORKDIR /app

COPY --from=builder --chown=examinator:examinator /app/.venv /app/.venv
COPY --from=builder --chown=examinator:examinator /app/src   /app/src
COPY --from=builder --chown=examinator:examinator /app/pyproject.toml /app/README.md /app/LICENSE /app/

USER examinator

EXPOSE 8000

# `examinator-serve` is the console-script entry point declared in
# pyproject.toml. --host 0.0.0.0 makes the container reachable from the
# docker-compose network and from the host port mapping.
CMD ["examinator-serve", "--host", "0.0.0.0", "--port", "8000"]
