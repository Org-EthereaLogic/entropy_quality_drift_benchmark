---
description: Thoroughly verify a claim, file, or behavior with direct evidence. Never edits files.
---

# Verify

Independently verify the requested subject from source, tests, configs, and runtime output.

## Variables

subject: $ARGUMENTS

## Workflow

1. Read the primary source files and configs.
2. Trace dependent code paths.
3. Run the smallest convincing commands.
4. Check for contradictions between:
   - docs and code
   - config and evaluation logic
   - tests and observed runtime
5. Report:
   - Verified
   - Issues Found
   - Inconclusive

## Default Commands

```bash
ruff check src tests docs
pytest tests/ -v --tb=short
python -m entropy_quality_drift.runners.benchmark --seed 42 --rows 1000
```
