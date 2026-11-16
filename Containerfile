# Based on the Yard `yard:python-uv` template output (yard app cat containerfile).
# Yard does not write it for this app because the repo has its own compose.yml.
FROM python:3.14-slim-trixie@sha256:35caba83af2fe6da9a5d922f9b0156f21d1246a48278c58a08bd253303ba42e8 AS builder
COPY --from=ghcr.io/astral-sh/uv:0.13.5@sha256:32a7bb39b496babbd997b0a39a4d66c126bdaf5661b302bf6f06abda8deca6ff /uv /uvx /bin/
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0
WORKDIR /workspace
# COPY, not a bind mount: a Podman build on an SELinux host (Fedora, RHEL) cannot read a bind-mounted file.
COPY pyproject.toml uv.lock /workspace/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project --no-dev
COPY . /workspace
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

FROM python:3.14-slim-trixie@sha256:35caba83af2fe6da9a5d922f9b0156f21d1246a48278c58a08bd253303ba42e8
ENV PYTHONUNBUFFERED=1 \
    PORT=8000
WORKDIR /workspace
COPY --from=builder /workspace /workspace
ENV PATH="/workspace/.venv/bin:$PATH"
CMD ["python", "-m", "app.main"]
