---
description: Audit and update living documentation to match the current repository behavior.
---

# Doc Maintain

Audit documentation drift and update the minimum necessary files.

## Scope

- `README.md`
- `CLAUDE.md`
- `AGENTS.md`
- `.claude/commands/`
- `.claude/agents/`
- workflow-facing docs

## Validation

Run after documentation updates:

```bash
ruff check src tests docs
pytest tests/ -v --tb=short
```

Do not claim a command, path, or metric unless it matches the codebase.
