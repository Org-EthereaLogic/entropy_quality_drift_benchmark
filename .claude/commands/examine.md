---
description: Independently examine a target from primary sources without trusting summaries.
argument-hint: <file | module | claim | current diff>
---

# Examine

Perform a rigorous read-and-run examination of the requested target.

## Agent Delegation

This command maps to `.claude/agents/examine.md`.

## Workflow

1. Read the primary source files.
2. Trace imports and config dependencies.
3. Run the smallest convincing commands.
4. Report:
   - Verified
   - Issues Found
   - Inconclusive

## Baseline Validation Commands

```bash
ruff check src tests docs
pytest tests/ -v --tb=short
python -m entropy_quality_drift.runners.benchmark --seed 42 --rows 1000
```
