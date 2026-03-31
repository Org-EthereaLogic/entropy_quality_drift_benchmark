---
description: Sync code, docs, commands, and workflow-facing artifacts after a change set.
---

# Sync

Audit the repository for documentation and command drift after implementation work.

## Surfaces to Audit

- `README.md`
- `CLAUDE.md`
- `AGENTS.md`
- `.claude/commands/`
- `.claude/agents/`
- `.github/workflows/`
- `configs/kpi_thresholds.json`

## Validation

```bash
git diff --check
ruff check src tests
pytest tests/ -v --tb=short
```

Do not rewrite existing evidence in `runs/`.
