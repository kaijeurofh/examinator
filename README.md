# examinator

A web app that generates higher-education exam tasks from study material
(PDF or pasted text) for four assignment types:

* **Hausarbeitsfragen** — academic term-paper prompts with rubric and student roadmap.
* **Projektarbeitsfragen** — practice-oriented project assignments with execution format.
* **Klausurfragen** — closed-book exam questions with model answer and rubric.
* **Einsendeaufgaben** — open-book booklet assignments with model answer and rubric.

The backend is FastAPI + `pydantic-ai`; the frontend is a small Next.js 14
app. Each job uses a *chunked-with-overlap* generation strategy: pages are
grouped into chunks, the LLM emits candidate questions per chunk, and a
final reducer call selects exactly 10 deduplicated questions. The result
can be downloaded as an `.xlsx` workbook with one column per schema field.

The repo was originally bootstrapped from a secure pydantic-ai template;
all the security guardrails (Cursor/Codex/Claude hooks, hardened CI,
devcontainer) still apply.

The goal of this template is **rules over code**: keep the Python skeleton
intentionally small, push the conventions into config files an agent will
actually read.

> New to AI coding agents and the security questions they raise? See
> [`docs/walkthrough.md`](docs/walkthrough.md) for a layer-by-layer
> explanation of every file in this template and the threat model it
> defends against. The walkthrough is purely educational — delete it
> (and this line) if you do not need it.

---

## Quickstart with Docker (recommended for first run)

If you just want to try the app locally and have [Docker
Desktop](https://docs.docker.com/desktop/) (or Docker Engine + Compose v2)
installed, this is the fastest path:

```bash
# 1. Configure provider keys (the backend reads them at startup).
cp .env.example .env
#   then edit .env and set OPENAI_API_KEY (or the key for whichever provider
#   you put in PYDANTIC_AI_MODEL).

# 2. Build and start both services.
docker compose up --build

# 3. Open the frontend in your browser.
#    http://localhost:3040
```

Compose starts two containers (defaults on this branch — see table for the
distinction from the `main` / OpenAI branch):

| Service           | Host port (default)        | Image tag                   | Container                   |
| ----------------- | -------------------------- | --------------------------- | --------------------------- |
| `backend` (API)   | `8210`  (`$BACKEND_PORT`)  | `examinator-lokal-backend`  | `examinator-lokal-backend`  |
| `frontend` (UI)   | `3040`  (`$FRONTEND_PORT`) | `examinator-lokal-frontend` | `examinator-lokal-frontend` |

`docker-compose.yml` on this branch also pins `name: examinator-lokal` so
the Compose project lives in its own network and doesn't collide with the
`examinator` project on `main`. That means you can run **both stacks side
by side**: check out `main` and `examinator-lokal` into two separate
worktrees (or just toggle Compose's `up`/`down` per directory) and you'll
have OpenAI on `3030/8200` and Ollama on `3040/8210` at the same time.

The defaults stay away from popular collision points (`3000`, `8000`,
`8080`). The browser talks to **both** containers via `localhost` — the
frontend on `:3040`, the backend on `:8210`. CORS is generated from the same
env var that picks the host port, so the two stay in sync.

### Picking different host ports

If one of the defaults is still taken on your machine, override before the
`up` call — both values are referenced through env-var substitution in
`docker-compose.yml`:

```bash
# Bash / zsh:
FRONTEND_PORT=3141 BACKEND_PORT=8211 docker compose up --build

# PowerShell:
$env:FRONTEND_PORT=3141; $env:BACKEND_PORT=8211; docker compose up --build
```

`NEXT_PUBLIC_API_URL` is baked into the JS bundle at build time, so changing
`BACKEND_PORT` requires a rebuild of the frontend image:

```bash
docker compose build frontend
docker compose up -d frontend
```

To stop and remove the containers:

```bash
docker compose down
```

> The backend keeps job state in RAM, so it is intentionally limited to a
> single replica. Restarting the container drops all jobs.

---

## Lokal mit Ollama (Branch `examinator-lokal`)

Dieser Branch tauscht den OpenAI-Pfad gegen ein lokal laufendes Ollama-Modell
aus. Ziel: kein Provider-Key, keine ausgehenden API-Calls, alles auf der
eigenen GPU. Auf einer RTX 5090 (32 GB VRAM) laeuft das mitgelieferte
`gemma4:31b` komfortabel.

### Voraussetzungen

* [Ollama](https://ollama.com/) ist auf dem Host installiert und der Daemon
  laeuft (Default-URL `http://localhost:11434`).
* Das Zielmodell ist bereits gezogen — auf dieser Maschine sollte
  `gemma4:31b` bereits vorhanden sein. Pruefen:

  ```bash
  curl http://localhost:11434/api/tags
  # oder
  ollama list
  ```

  Falls nicht vorhanden:

  ```bash
  ollama pull gemma4:31b
  ```

### Start mit Docker Compose

`docker-compose.yml` auf diesem Branch ist bereits vorkonfiguriert: das
Backend bekommt `EXAMINATOR_LLM_PROVIDER=ollama`,
`OLLAMA_BASE_URL=http://host.docker.internal:11434/v1`,
`OLLAMA_MODEL=gemma4:31b` und `EXAMINATOR_OUTPUT_MODE=tool`. Auf Linux
sorgt der `extra_hosts: host.docker.internal:host-gateway`-Eintrag dafuer,
dass der Backend-Container den Host-Daemon trotzdem erreicht.

```bash
docker compose up --build
# Frontend:  http://localhost:3040
# Backend:   http://localhost:8210
```

Da die Compose-Umgebung Vorrang vor `.env` hat, brauchst du fuer den
Ollama-Pfad keinen einzigen Eintrag in `.env`. Ein `OPENAI_API_KEY=...`
darf auch weiter dort stehen — er wird einfach ignoriert.

### Parallelbetrieb: OpenAI- und Ollama-Stack gleichzeitig

Die Default-Ports auf diesem Branch (`3040` / `8210`) und der Compose-
Projektname `examinator-lokal` sind absichtlich so gewaehlt, dass beide
Stacks parallel laufen koennen:

| Branch              | Frontend | Backend | Compose-Projekt    |
| ------------------- | -------- | ------- | ------------------ |
| `main` (OpenAI)     | `3030`   | `8200`  | `examinator`       |
| `examinator-lokal`  | `3040`   | `8210`  | `examinator-lokal` |

Empfohlener Workflow per Git-Worktree, damit die `main`-Container nicht beim
Branch-Wechsel zerstoert werden:

```bash
git worktree add ../examinator-lokal examinator-lokal
cd ../examinator-lokal
docker compose up --build       # Ollama-Stack:  http://localhost:3040
```

Im urspruenglichen Working Directory laeuft parallel:

```bash
cd /pfad/zu/examinator           # main-Branch
docker compose up --build       # OpenAI-Stack:  http://localhost:3030
```

`docker ps` zeigt dann vier Container nebeneinander
(`examinator-backend` / `examinator-frontend` und
`examinator-lokal-backend` / `examinator-lokal-frontend`).

### Start bei lokaler Entwicklung (ohne Docker)

```bash
export EXAMINATOR_LLM_PROVIDER=ollama
export OLLAMA_BASE_URL=http://localhost:11434/v1
export OLLAMA_MODEL=gemma4:31b
export EXAMINATOR_OUTPUT_MODE=tool

uv run examinator-serve --reload
```

### Output-Modus: tool vs. prompted vs. native

`EXAMINATOR_OUTPUT_MODE` steuert, wie pydantic-ai das strukturierte
JSON-Ergebnis erzwingt:

| Wert       | Verhalten                                                                                     | Wann nutzen                                                                          |
| ---------- | --------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| `tool`     | Native Function-/Tool-Calls.                                                                  | Default auf `examinator-lokal`. OpenAI/Anthropic/Gemini *und* Gemma 4 via Ollama.    |
| `prompted` | JSON-Schema wird in den System-Prompt eingebettet und die Antwort geparst.                    | Fallback fuer aeltere Modelle ohne Tool-Call-Template (Gemma 2/3, kleine Llamas).    |
| `native`   | JSON-Schema wird via `response_format` durchgereicht (OpenAI-Style Structured Outputs).       | Experimentell gegen Ollama (pydantic-ai #4917); erst per Benchmark validieren.       |

**Warum `tool` der Default ist:** Ein A/B-Lauf mit
`scripts/benchmark_local.py` gegen ein echtes Studienheft-PDF (siehe unten)
hat klar gezeigt, dass `prompted` mit `gemma4:31b` *nicht* funktioniert.
Gemma 4 emittiert ueber die Ollama-Chat-Template-Integration Reasoning-
Tokens vor dem JSON; unser verschachteltes `PageQuestions[T]`-Schema
verwirft diese Antworten dann komplett (Status: `Keine Kandidatenfragen
erzeugt.`). Im `tool`-Modus laeuft derselbe Job reproduzierbar in ca.
4-5 Minuten durch und liefert die geforderten 10 Fragen.

Wenn du ein Modell ohne Tool-Call-Template einsetzt (alte Gemmas,
Mistral 7B, kleine Llamas), brauchst du `prompted` weiterhin als
Fallback. Fuer alles, was Tool-Calls ueber Ollama liefern kann, ist
`tool` die richtige Wahl.

### Alternative lokale Modelle

`gemma4:31b` ist der Default, weil Gemma 4 31B aktuell der Open-Weights-
Spitzenreiter auf MMMLU (Multilingual MMLU) ist — also genau der Achse, die
fuer deutschsprachige Klausurfragen zaehlt. Auf einer RTX 5090 (32 GB
VRAM) belegt das Q4_K_M-Quant rund 20 GB und laesst ausreichend Spielraum
fuer Kontext.

Wenn du primaer auf Function-Calling-Robustheit optimieren willst (z. B.
weil ihr in Zukunft Multi-Tool-Workflows fahren wollt), ist **Qwen 3 32B**
laut BFCL v4 die staerkste lokale Option:

```bash
ollama pull qwen3:32b-q4_K_M
# dann in der env / docker-compose ueberschreiben:
OLLAMA_MODEL=qwen3:32b-q4_K_M
```

VRAM-Bedarf vergleichbar (~19-20 GB Q4_K_M), Tool-Calling-Treue
typischerweise hoeher. Welches Modell fuer **deine** Schemas und
PDF-Inhalte tatsaechlich die besseren Klausurfragen liefert, beantwortet
nur ein A/B-Test — dafuer gibt es `scripts/benchmark_local.py`:

```bash
uv run python scripts/benchmark_local.py \
    --pdf path/to/sample.pdf \
    --task klausur \
    --out benchmark.md
```

Das Skript fuehrt die Pipeline gegen die Kreuzmenge der konfigurierten
Modelle und Output-Modi aus und schreibt eine Markdown-Tabelle mit
Latenz, Validation-Retries und Schema-Validitaet je Kombination. Erst
danach gegebenenfalls den Default in `docker-compose.yml` umstellen.

### Zurueck auf OpenAI wechseln

Provider und Output-Modus sind reine Env-Schalter — kein Code-Aenderung
notwendig:

```bash
# .env oder Shell-Env
EXAMINATOR_LLM_PROVIDER=openai
EXAMINATOR_OUTPUT_MODE=tool
PYDANTIC_AI_MODEL=openai:gpt-5.2
OPENAI_API_KEY=sk-...
```

In Docker einfach die drei Eintraege oben in `docker-compose.yml` (oder
ueber die `environment:`-Sektion eines `docker-compose.override.yml`)
ueberschreiben und `docker compose up --build` neu starten.

### Performance & Quality Hinweise

* `gemma4:31b` liefert solide strukturierte Antworten, ist aber spuerbar
  langsamer als Cloud-Modelle. Plane fuer einen Vier-Chunk-Job grob mit
  60–120 s je nach Prompt-Laenge.
* Sehr kleine Modelle (< 7 B) scheitern oft an den verschachtelten
  Pydantic-Schemas — das ist genau der Grund, weshalb dieser Branch
  defaultmaessig auf einem 31 B-Modell mit `prompted` laeuft.
* Bei groesseren Studienmaterialien `EXAMINATOR_MAX_CHUNKS` auf 4-6
  begrenzen, sonst sammelt der Reducer mehr Kandidaten an, als die
  Kontextlaenge bequem schluckt.

---

## Quickstart (local Python + Node)

Use this when you want hot-reload during development.

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

# 4. Start the API.
uv run examinator-serve --reload

# 5. In a separate shell, start the frontend.
cd frontend
cp .env.example .env.local       # adjust NEXT_PUBLIC_API_URL if needed
npm install
npm run dev                       # http://localhost:3000
```

Swap the model in `.env` (`PYDANTIC_AI_MODEL=anthropic:claude-4.6-sonnet`,
etc.) — the backend is provider-agnostic.

### Day-to-day commands

| Task              | Command                                |
| ----------------- | -------------------------------------- |
| Add a dependency  | `uv add <pkg>`                         |
| Add a dev dep     | `uv add --group dev <pkg>`             |
| Start the API     | `uv run examinator-serve --reload`     |
| Frontend dev      | `cd frontend && npm run dev`           |
| Lint (autofix)    | `uv run ruff check --fix .`            |
| Format            | `uv run ruff format .`                 |
| Type-check        | `uv run mypy src tests`                |
| Tests             | `uv run pytest`                        |

---

## Examinator Web App

### How a job flows through the system

1. The frontend (`/new/[taskType]`) posts a multipart form to
   `POST /api/jobs`. The `config` field is a JSON blob validated against
   `examinator.core.schemas.JobConfig` (discriminated on `task_type`); the
   study material is either a `pdf` file part or a `text` string part.
2. The backend schedules a background `asyncio` task that:
   * Parses the input into pages (pypdf or pseudo-pages for plaintext).
   * Builds page-aware chunks with overlap (cap: `EXAMINATOR_MAX_CHUNKS`).
   * Runs the candidate agent per chunk to produce up to 4 candidates each.
   * Runs the reducer agent once across the pooled candidates to pick
     **exactly 10** non-overlapping final questions.
3. Progress is fan-out to subscribers via `GET /api/jobs/{id}/events`
   (Server-Sent Events). The frontend opens an `EventSource` and renders a
   live timeline.
4. When the job is `done` the result lives in-memory; the user clicks
   "Excel herunterladen" which streams `.xlsx` from
   `GET /api/jobs/{id}/excel`.

### API surface

| Method | Path                          | Purpose                                  |
| ------ | ----------------------------- | ---------------------------------------- |
| GET    | `/api/health`                 | Readiness probe                          |
| POST   | `/api/jobs`                   | Queue a new generation job (multipart)   |
| GET    | `/api/jobs/{id}/events`       | SSE progress stream                      |
| GET    | `/api/jobs/{id}`              | Final JSON result + last events          |
| GET    | `/api/jobs/{id}/excel`        | `.xlsx` download                         |

OpenAPI / Swagger UI: <http://localhost:8000/api/docs>.

### Operational notes

* **Single worker only.** The `JobStore` is in-process; run uvicorn with
  `--workers 1`. The CLI entry-point (`examinator-serve`) enforces this.
* **No persistence.** Jobs are kept in RAM and evicted by a TTL janitor
  (default 1 hour after completion). Restarting the API drops everything.
* **No auth / no DB.** The MVP is single-tenant and trusts the network it
  is deployed on. Put a reverse proxy with auth in front if you expose it
  beyond localhost.
* **OCR is out of scope.** Scanned PDFs without an embedded text layer
  will produce an explicit `error` event.
* **Model selection.** Set `PYDANTIC_AI_MODEL` in `.env` (default
  `openai:gpt-5.2`). Any provider supported by `pydantic-ai` works.

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
