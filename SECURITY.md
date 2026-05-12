# Security policy

## Supported versions

This is a project template. There are no "supported versions" in the
traditional release sense — security fixes land on `main` and propagate to
downstream forks when they pull.

## Reporting a vulnerability

If you believe you have found a security issue in this template, please
**do not open a public GitHub issue**.

Instead, use GitHub's
[private vulnerability reporting](https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing-information-about-vulnerabilities/privately-reporting-a-security-vulnerability)
for this repository (Security tab → "Report a vulnerability"), or email the
maintainer listed in `pyproject.toml`. Include:

- a short description of the issue,
- the file(s) and line(s) involved,
- a minimal reproduction (commands, prompts, or a PoC repo),
- the impact you believe it has (secret leakage, sandbox escape, RCE,
 supply-chain risk, etc.).

We aim to acknowledge reports within **5 working days** and to publish a
fix or mitigation within **30 days** of confirming the issue. Coordinated
disclosure is appreciated.

## Scope

In scope:

- Default configuration of any file in this repository.
- Documented agent guardrails (`AGENTS.md`, `.cursor/rules/`,
 `.codex/config.toml`, `.claude/settings.json`).
- CI workflow (`.github/workflows/ci.yml`) and the secret-scanning /
 dependency-audit pipeline.
- Devcontainer image build.

Out of scope:

- Vulnerabilities in third-party LLM providers, GitHub Actions, or
 dependencies of this template. Please report those to the upstream
 maintainers; we will track via Dependabot.
- Issues that require a non-default configuration explicitly contrary to
 the security model documented in `README.md` (e.g. running Codex with
 `--sandbox danger-full-access`).

## Hardening checklist for downstream forks

When you clone this template into a real project, you SHOULD additionally:

1. Enable **branch protection** on `main`: require pull request review,
 require status checks (`checks`, `actionlint`), disallow force-pushes
 and direct pushes.
2. Enable **GitHub secret scanning** and **push protection** at the
 repository or org level.
3. Configure a real `CODEOWNERS` (the included template has placeholder
 owners).
4. Tighten `egress-policy: audit` in `.github/workflows/ci.yml` to
 `egress-policy: block` with an explicit `allowed-endpoints` list once
 you have observed real traffic.
5. Replace the placeholder email in `pyproject.toml` with a real
 reporting address, and decide whether to publish a security contact in
 your organization's `SECURITY.md`.
