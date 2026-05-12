# Devcontainer image for llm-uv-template.
#
# Goals:
#   * Python 3.12 baseline matching .python-version.
#   * `uv` preinstalled at a pinned version, on PATH for the non-root user.
#   * No build tooling or shells beyond what the dev loop needs.
#   * No `curl | sh` install of any binary — we copy `uv` from the
#     official, immutable OCI image instead, which satisfies the rule in
#     .cursor/rules/30-security.mdc (#7).
#
# The base image is maintained by Microsoft and ships with a non-root
# `vscode` user, git, sudo, and common tooling already configured.

# Pin the uv version in one place. Bump this and the `tool.uv.required-version`
# constraint in pyproject.toml together so every contributor sees the same uv.
# The trailing `@sha256:...` digest makes the image bit-for-bit immutable;
# Dependabot (see .github/dependabot.yml docker ecosystem) will open PRs that
# bump both the tag comment and the digest in lockstep.
#
# Resolved 2026-05-11 against ghcr.io/astral-sh/uv:0.11.13.
FROM ghcr.io/astral-sh/uv:0.11.13@sha256:841c8e6fe30a8b07b4478d12d0c608cba6de66102d29d65d1cc423af86051563 AS uv

# Microsoft-maintained devcontainer base; tag pins the Python minor version
# and Debian release, digest pins the exact build.
# Resolved 2026-05-11 against mcr.microsoft.com/devcontainers/python:1-3.12-bookworm.
FROM mcr.microsoft.com/devcontainers/python:1-3.12-bookworm@sha256:7876580dc67fd460fd962f004cbeb480027e9bbc0657096f1087db11f9eaff39

ENV UV_LINK_MODE=copy \
    UV_NO_PROGRESS=1 \
    UV_PYTHON_DOWNLOADS=never \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY --from=uv /uv /uvx /usr/local/bin/
RUN uv --version

USER vscode
WORKDIR /workspaces/llm-uv-template
