---
description: Generate and execute a scoped Conventional Commit for the current diff.
---

# Commit

Create a Conventional Commit for the current change set.

## Variables

message_hint: $ARGUMENTS

## Instructions

1. Review `git diff HEAD`.
2. Stage only relevant files.
3. Use the format:

```text
<type>(<scope>): <subject>
```

4. Prefer scopes such as:
   - `challengers`
   - `metrics`
   - `runners`
   - `evidence`
   - `docs`
   - `ci`
   - `governance`

5. Never use `--no-verify`.
