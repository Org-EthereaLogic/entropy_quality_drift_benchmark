---
description: Preview or perform safe workspace cleanup for caches, temp artifacts, and local analysis output.
argument-hint: [--execute]
---

# cleanup_workspace

Clean local workspace artifacts without touching tracked source files.

## Agent Delegation

This command maps to `.claude/agents/cleanup_workspace.md`.

## Default Mode

Dry-run. Do not delete anything unless `--execute` is provided.

## Cleanup Targets

- `__pycache__/`
- `*.pyc`
- `.pytest_cache/`
- `.ruff_cache/`
- `.codacy/`
- local temporary evidence generated during ad hoc runs

## Protected Paths

- `.git/`
- `.github/`
- `.claude/`
- `src/`
- `tests/`
- `configs/`
- committed files in `runs/`

## Execute

Only remove `runs/` content when the user explicitly asks for it.
