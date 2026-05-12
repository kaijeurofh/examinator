# AGENTS.md

Canonical, cross-tool instructions for coding agents working in this repository.
This file is read by **OpenAI Codex CLI**, **Cursor**, **GitHub Copilot**,
**Windsurf**, and any other tool that follows the
[AGENTS.md standard](https://agents.md). Claude Code reads `CLAUDE.md`, which
imports this file.

If a tool-specific file contradicts this one, the tool-specific file wins
(for example, `.cursor/rules/*.mdc` overrides for Cursor only).

---

## 1. Project purpose

This repository is a template for building production-grade **LLM agent
applications** in Python with `pydantic-ai`. The runnable skeleton in
`src/llm_uv_template/` is intentionally minimal — treat it as a starting
point, not as architecture to preserve.

## 2. Environment

- **Python**: 3.12+ only. Never assume an older version is available.
- **Package manager**: [`uv`](https://docs.astral.sh/uv/). Do **not** use
  `pip`, `poetry`, `pipenv`, or `conda`. Do **not** invoke `python` directly —
  always go through `uv run` so the locked environment is used.
- **`uv` version**: pinned via `[tool.uv] required-version` in
  `pyproject.toml`. The devcontainer image, CI, and your laptop must all
  agree; bump the constraint deliberately when validating a new uv release.
- **Lockfile**: `uv.lock` is committed. If you change `pyproject.toml`, run
  `uv lock` and commit the result. `uv lock --check` should pass before you
  end a task.

### Copy-pasteable commands

| Task              | Command                                |
| ----------------- | -------------------------------------- |
| Install deps      | `uv sync`                              |
| Add a dependency  | `uv add <pkg>`                         |
| Add a dev dep     | `uv add --group dev <pkg>`             |
| Verify lockfile   | `uv lock --check`                      |
| Run the CLI       | `uv run llm-uv-template "your prompt"` |
| Run tests         | `uv run pytest`                        |
| Lint (autofix)    | `uv run ruff check --fix .`            |
| Format            | `uv run ruff format .`                 |
| Type-check        | `uv run mypy src tests`                |
| Secret scan       | `uv run pre-commit run gitleaks --all-files` |
| All checks (CI)   | `uv lock --check && uv run ruff check . && uv run ruff format --check . && uv run mypy src tests && uv run pytest && uv run pre-commit run gitleaks --all-files` |

You **must** run lint, format, type-check, tests, and secret scan before
ending a task. If you modified `pyproject.toml`, also run `uv lock --check`
(or `uv lock` to regenerate).

## 3. Code style

- **Typed everywhere.** Every function signature, parameter, and return value
  has type annotations. `mypy --strict` must pass.
- **Prefer functions over classes.** Only introduce a class when there is
  meaningful state or polymorphism. A bag of static methods is a code smell.
- **No broad `except:` or `except Exception:`** without an explicit reason and
  a `# noqa` comment. Catch the specific exception you expect.
- **Pathlib over `os.path`** for filesystem work.
- **Pydantic models** for any structured input/output that crosses an LLM,
  HTTP, or file boundary. Avoid free-form dicts.
- **No comments that just restate the code.** Comment intent, trade-offs, or
  constraints — never narrate what is already obvious from reading.
- **Line length 100.** Ruff enforces it.

## 4. Tests

- Use `pytest`. Place tests under `tests/`, mirror source layout.
- **Never make real network calls in unit tests.** Mock LLM calls with
  `pydantic_ai.models.test.TestModel` or
  `pydantic_ai.models.function.FunctionModel`. See `tests/test_agent.py` for
  the pattern.
- New behavior requires a new test in the same change.
- Tests must be deterministic — no `time.sleep`, no real clocks (use
  monkeypatching), no network, no LLM, no flaky assertions.

## 5. Security boundaries

Hard rules. Violations should fail review.

1. **Never read, write, modify, print, or log the contents of `.env`** or any
   file matching `.env.*` (except `.env.example`). If you need to know what
   variables exist, look at `.env.example`.
2. **Never embed real secrets** in source, tests, fixtures, or docs. Use
   placeholders like `sk-replace-me`.
3. **Never log API keys, tokens, or full request/response bodies** that may
   contain them. Redact before logging.
4. **Validate any value that originated from an LLM or user** before passing
   it to `subprocess`, `eval`, `exec`, `os.system`, the filesystem, or a
   network call. Prefer explicit allow-lists.
5. **Do not add new network calls** outside the agent's configured LLM
   provider without explicit instruction in the user prompt.
6. **Do not bypass the sandbox.** `.codex/config.toml`,
   `.claude/settings.json`, and `.cursor/hooks.json` codify what is allowed;
   if you need more, ask the human, do not edit those files unilaterally.
7. **Respect the Cursor hooks.** `.cursor/hooks/guard-env.py` denies any
   shell command that touches a real `.env*` file (everything except
   `.env.example`); `.cursor/hooks/scan-prompt.py` asks for confirmation
   when a prompt looks like it contains a live API key. If a hook blocks a
   legitimate action, fix the action (use `.env.example`, redact the
   secret), do not disable the hook.

## 6. Dependencies

- Prefer the standard library and existing dependencies before adding new
  ones. Justify each new dependency in the commit message.
- Pin major versions in `pyproject.toml` (`>=X,<X+1`). Let `uv.lock` pin the
  exact resolution.
- Never add a dependency that requires a paid license or a CLA without
  explicit human approval.

## 7. Commits and PRs

- One logical change per commit.
- Imperative subject, ≤72 chars: `add foo`, not `added foo` or `foos added`.
- Body explains **why**, not what — the diff already shows what.
- Reference an issue if there is one: `Fixes #123.`
- Do **not** include emojis, AI-attribution footers, or "Generated with …"
  lines.

## 8. When in doubt

Stop and ask. A short clarifying question is always cheaper than a wrong
50-line diff.
