---
description: Execute the entropy benchmark end to end, evaluate gates, and emit append-only evidence.
---

# Benchmark

Run the benchmark harness for this repository.

## Variables

arguments: $ARGUMENTS

## Instructions

1. Validate the working tree and configs.
2. Run:

```bash
python -m entropy_quality_drift.runners.benchmark $ARGUMENTS
```

3. Capture:
   - benchmark verdict
   - gate statuses
   - evidence bundle path
4. If the run fails, report the failing gate and supporting metrics.
