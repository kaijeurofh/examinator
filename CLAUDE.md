# CLAUDE.md

Claude Code does not yet read `AGENTS.md` natively, so this file imports the
canonical rules.

@AGENTS.md

---

## Claude-specific notes

- Use the `Read`, `Edit`, and `Write` tools for file operations — they
  integrate with the editor's undo stack. Do not invoke `cat`, `sed`, or
  `awk` via `Bash` for editing.
- `.claude/settings.json` defines an allow-list of safe commands and a
  deny-list around secrets. Respect it; ask before requesting a permission
  expansion.
- Prefer `Grep` (ripgrep-based) over shelling out to `grep`/`find`.
- When you complete a task, run the full check chain documented in
  `AGENTS.md` section 2 before reporting done.
