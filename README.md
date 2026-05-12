# llm-uv-template

[![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/your-org/llm-uv-template/badge)](https://scorecard.dev/viewer/?uri=github.com/your-org/llm-uv-template)

A secure, agent-ready Python template for building LLM workflows with
[`uv`](https://docs.astral.sh/uv/) and
[`pydantic-ai`](https://ai.pydantic.dev/). It ships with cross-tool agent
rules (`AGENTS.md`), passive security guardrails for Cursor / Codex /
Claude Code, hardened CI, and an optional devcontainer — so an LLM coding
agent can be productive in this repo from the first prompt.

The goal of this template is **rules over code**: keep the Python skeleton
intentionally small, push the conventions into config files an agent will
actually read.

> New to AI coding agents and the security questions they raise? See
> [`docs/walkthrough.md`](docs/walkthrough.md) for a layer-by-layer
> explanation of every file in this template and the threat model it
> defends against. The walkthrough is purely educational — delete it
> (and this line) if you do not need it.

---

## Quickstart

```bash
# 1. Install uv (once per machine). Prefer a trusted package manager:
#      macOS:    brew install uv
#      Windows:  winget install --id=astral-sh.uv -e
#      Linux:    pipx install uv   (or your distro's package, e.g. pacman -S uv)
#
#    If none of those is available, Astral also publishes a verified install
#    script. Inspect it before executing — `curl | sh` is otherwise explicitly
#    forbidden by .cursor/rules/30-security.mdc for code inside this repo:
#      curl -LsSf https://astral.sh/uv/install.sh -o /tmp/uv-install.sh
#      less /tmp/uv-install.sh && sh /tmp/uv-install.sh

# 2. Sync the locked environment.
uv sync

# 3. Configure provider keys.
cp .env.example .env
# then edit .env

# 4. Run the example agent.
uv run llm-uv-template "The windy city in the US of A."
```

The example agent returns a typed `CityInfo` JSON object. Swap the model in
`.env` (`PYDANTIC_AI_MODEL=anthropic:claude-4.6-sonnet`, etc.) — the code is
provider-agnostic.

### Day-to-day commands

| Task              | Command                                |
| ----------------- | -------------------------------------- |
| Add a dependency  | `uv add <pkg>`                         |
| Add a dev dep     | `uv add --group dev <pkg>`             |
| Run the CLI       | `uv run llm-uv-template "your prompt"` |
| Lint (autofix)    | `uv run ruff check --fix .`            |
| Format            | `uv run ruff format .`                 |
| Type-check        | `uv run mypy src tests`                |
| Tests             | `uv run pytest`                        |

---

## Using this with coding agents

This template targets the [`AGENTS.md`](AGENTS.md) standard — a single
canonical file that any modern agent reads. Tool-specific files are thin
shims, not duplicate sources of truth.

| Tool             | Reads                                                       |
| ---------------- | ----------------------------------------------------------- |
| OpenAI Codex CLI | `AGENTS.md` + `.codex/config.toml`                          |
| GitHub Copilot   | `AGENTS.md`                                                 |
| Cursor           | `AGENTS.md` + `.cursor/rules/*.mdc` + `.cursor/hooks.json`  |
| Windsurf         | `AGENTS.md`                                                 |
| Claude Code      | `CLAUDE.md` (imports `AGENTS.md`) + `.claude/settings.json` |
| Aider            | `.aiderignore` + project conventions                        |

To change project rules, **edit `AGENTS.md` first** and only add a
tool-specific override when the behaviour is truly tool-specific (e.g.
Cursor file-glob auto-attachment rules).

### What gets hidden from your agent's context

`.cursorignore`, `.codexignore`, and `.aiderignore` all share the same
content. They block:

- secrets (`.env`, `*.pem`, `credentials.json`, `.aws/`, `.ssh/`),
- lockfiles (`uv.lock`, `package-lock.json`, etc. — large, low signal),
- caches and build output,
- large data / binary files (`*.csv`, `*.parquet`, images, archives, …),
- the `.git/` directory.

If your agent suddenly needs visibility into one of these, edit all three
files in sync.

---

## Security model

The template is defensive by default; relax it intentionally, not
accidentally.

### What is enforced

- **`.gitignore`** keeps `.env`, `.env.*` (except `.env.example`),
  `__pycache__/`, `.venv/`, caches, and IDE state out of git.
- **`.cursorignore` / `.codexignore` / `.aiderignore`** hide the same files
  from the agent's context window so secrets can't be exfiltrated via a
  "summarize this file" prompt.
- **`.codex/config.toml`** sets Codex CLI to `approval_policy = "on-request"`,
  `sandbox_mode = "workspace-write"`, with `network_access = false`. Codex
  must ask before running shell commands, cannot write outside the
  workspace, and cannot reach the network.
- **`.claude/settings.json`** allow-lists exactly the commands the dev
  loop needs (`uv`, `pytest`, `ruff`, `mypy`, `git status/diff/log/add/commit`)
  and explicitly denies reads/writes to `.env*`, plus `curl`, `wget`,
  `sudo`, `rm -rf`, `git push`, and rival package managers.
- **`.cursor/rules/30-security.mdc`** is an always-applied prompt rule
  forbidding secrets in code, network calls to unknown hosts, and unsafe
  use of `subprocess` / `eval` on LLM-generated strings.
- **`.cursor/hooks/`** intercepts agent actions in Cursor: `guard-env.py`
  (a `beforeShellExecution` hook) blocks any shell command that targets
  a real `.env` file — closing the `echo … > .env` redirect gap that
  Cursor / Codex / Claude allow-lists cannot easily express. A
  `beforeSubmitPrompt` hook (`scan-prompt.py`) also flags prompts that
  appear to contain a live API key before they reach the model.
- **`tests/conftest.py`** overwrites real provider env vars with fake keys
  before each test, so a misconfigured test can never reach a live API.
- **CI** runs with `permissions: contents: read` at workflow *and* job
  level, pinned action SHAs, `step-security/harden-runner` egress audit,
  `uv lock --check`, `uv sync --frozen`, a `gitleaks` step, and a
  `pip-audit` step (pinned version) that audits the locked runtime
  dependencies against the OSV / PyPI advisory database. A second job
  runs `actionlint` (Docker image pinned by digest) against the workflow
  YAML.
- **OpenSSF Scorecard** runs on every push to `main` and weekly (see
  `.github/workflows/scorecard.yml`). Findings appear in *Security →
  Code Scanning* and as annotations on PRs that introduce them, but the
  job is intentionally *not* a required status check so a low score
  never blocks a merge.
- **`.gitleaks.toml`** + the `pre-commit` hook catch accidentally
  committed secrets locally; the same hook is re-run in CI so the
  guarantee holds even when a developer skipped `pre-commit install`.

### How to relax

- Need Codex to install a system package? `codex --sandbox danger-full-access`
  for that session, do not edit `.codex/config.toml`.
- Need Claude to run a new command type? Add it to the `allow` list in
  `.claude/settings.json` with a comment explaining why.
- Need to commit a file currently blocked by `.gitleaks.toml`? Add a tight
  path regex to `[allowlist].paths`.
- Need to disable a Cursor hook for one session? Open Cursor's *Hooks*
  settings tab and toggle it off; do not silently edit `.cursor/hooks.json`
  in a PR.

### Recommended branch protection (GitHub UI, one-time)

The CI workflow and `CODEOWNERS` are designed to be enforced by branch
protection. After pushing this template to GitHub, configure on `main`:

1. **Require a pull request before merging** — no direct pushes.
2. **Require review from Code Owners** (so changes under
   `.cursor/`, `.codex/`, `.claude/`, `.github/workflows/`, etc. trigger
   a security-team review).
3. **Require status checks to pass**: the `checks` matrix jobs and
   `actionlint`. The `Scorecard analysis` job is *intentionally not
   required* — it surfaces findings without gating merges (see below).
4. **Require signed commits** if your org uses commit signing.
5. **Block force pushes** and **block deletion**.
6. Enable **secret scanning** and **push protection** for the
   repository (Settings → Code security).

### Post-setup security: OpenSSF Scorecard

This template ships [`.github/workflows/scorecard.yml`](.github/workflows/scorecard.yml),
which runs the [OpenSSF Scorecard](https://scorecard.dev/) checks on a
weekly schedule and on every push to `main`. Scorecard scores ~18
best-practice signals (pinned dependencies, branch protection, code
review coverage, signed releases, …) on a 0–10 scale and uploads the
results to GitHub's *Security → Code Scanning* tab.

The workflow is **non-blocking by design**: it does not run on
`pull_request`, so a low score never refuses a merge. Findings still
appear as Code Scanning annotations on PRs — which is exactly what you
want when an agent proposes a workflow change that drops a pinned SHA
or asks for a wider `GITHUB_TOKEN`.

A GitHub template repository copies **files but not settings**. Your
freshly instantiated repo therefore starts with a partial Scorecard score
until you also configure the repository-level controls. To approach
10/10, do the following in the new repo's Settings:

1. **Branch protection on `main`** — required PR review, no force-push,
   no deletion. (Lifts the `Branch-Protection` and `Code-Review` checks.)
2. **Default `GITHUB_TOKEN` permissions** → *Read repository contents
   and packages permissions* (Settings → Actions → General → Workflow
   permissions). Lifts the `Token-Permissions` check beyond what the
   workflow-level `permissions:` block already gives you.
3. **Enable Dependabot security updates** (Settings → Code security).
   Lifts the `Vulnerabilities` check.
4. **Sign your releases** (Sigstore / GPG) once you start publishing
   anything. Lifts the `Signed-Releases` check; not relevant for a
   template.
5. Replace the `your-org/llm-uv-template` placeholder in the Scorecard
   badge URL at the top of this README with your real
   `<org>/<repo>` slug.

### Optional but recommended: pre-commit

```bash
uv run pre-commit install         # one-time
uv run pre-commit run --all-files # first pass, then auto on every commit
```

The hook runs `ruff` (lint + format), `gitleaks` (secret scanning), and
the standard whitespace / large-file / merge-conflict checks.

### Optional: devcontainer

Open this folder in VS Code or Cursor with the Dev Containers extension
and it will build the image in `.devcontainer/Dockerfile` (Python 3.12 +
`uv` copied from Astral's official OCI image, both base images pinned by
tag *and* digest, non-root `vscode` user, `uv sync` on first start).
Useful as a sandbox for letting an agent execute generated code.

---

## Customizing for your project

1. **Rename the package.** Change `llm_uv_template` → `your_pkg` in:
   - `pyproject.toml` (`[project.scripts]`, `[tool.hatch.build.targets.wheel]`,
     `[tool.ruff.lint.isort] known-first-party`),
   - the `src/llm_uv_template/` directory name,
   - imports inside `src/` and `tests/`,
   - the `name` in `.devcontainer/devcontainer.json`.
2. **Swap the agent framework** if `pydantic-ai` doesn't fit:
   `uv remove pydantic-ai && uv add <your-framework>`, then rewrite
   `src/<pkg>/agent.py` and the test pattern. The rest of the template
   (rules, ignores, sandbox, CI) is framework-agnostic.
3. **Adjust the strictness** in `pyproject.toml`:
   - Loosen `[tool.mypy] strict = true` if migrating an existing codebase.
   - Drop ruff rule families you find noisy from `[tool.ruff.lint] select`.
4. **Pick a license.** This template ships an MIT `LICENSE` and matching
   `pyproject.toml` metadata as a *default*. Replace both (and the
   copyright line in `LICENSE`) before publishing if MIT is not what you
   want.
5. **Fill in `CODEOWNERS` and `SECURITY.md`.** The shipped versions are
   templates with `@your-org/...` placeholders and a generic reporting
   address — they do nothing until you point them at real handles.

---

## Explicitly out of scope

These were considered and intentionally **not** included:

- **LLM-powered PR review GitHub Action** (`ai-review.yml`). Generic LLM
  reviewers are noisy and require leaking API keys into GitHub Secrets.
  Use a dedicated GitHub App (CodeRabbit, Sweep, Codium) if you want this.
- **Editor-save / format-on-save hooks.** The `.cursor/hooks/` directory
  here intercepts *agent actions* (shell commands, prompt submissions) —
  those are Cursor-specific by design and degrade gracefully in other
  editors (they simply don't fire). What is still out of scope is hooks
  that fight your editor's own save / format / lint pipeline; that work
  belongs in `.pre-commit-config.yaml` so it is tool-agnostic.
- **Spec-driven YAML state machines** (à la `temple8`). Over-engineered
  for most projects; if you need this layer, add it on top — the template
  stays neutral.
- **Legacy `.cursorrules`** single-file format. Deprecated by Cursor in
  favour of the `.cursor/rules/*.mdc` directory format used here.

---

## How this template was built

See `AGENTS.md` for the canonical rules an agent should follow when
extending the template itself. Pull requests welcome — keep them small,
keep them tested, and keep them aligned with the existing rule files.
