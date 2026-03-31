# Constitution

This constitution defines the governing principles for development.

## Scope

It applies to:
- runner architecture and workflow orchestration,
- task intake and output surfaces,
- evaluation and operations tooling,
- documentation, reporting, and governance artifacts.

## Required Decision Order

When principles conflict, resolve them in this order:

1. Safety and correctness.
2. Evidence traceability.
3. Security and secret hygiene.
4. Simplicity and proportionality.
5. Reproducibility and operational reliability.
6. Performance and speed.

## Governing Principles

### P1. Safety, Correctness, and Repository Integrity

- Never ship a change that knowingly violates acceptance criteria, policy boundaries, or operator safety.
- Prefer explicit failure over silent unsafe behavior.
- Treat protected paths, branch protections, and policy controls as hard boundaries.

### P2. Evidence Traceability

- Every quality, benchmark, and operational claim must map to concrete evidence.
- Reports must distinguish measured facts from interpretation.
- Missing evidence blocks completion claims.
- Functional PASS claims require replayable proof, not narrative assertion.

### P3. Security and Secret Hygiene

- No credentials, tokens, or secret material in repository content or committed artifacts.
- Use least-privilege credentials and rotate exposed keys immediately.
- Treat policy violations and secret exposure as hard failures.

### P4. Simplicity and Proportionality

- Match implementation complexity to the size and risk of the problem.
- Avoid speculative abstractions, framework inflation, and enterprise patterns without immediate need.
- Prefer direct implementations until there is measured evidence for a broader pattern.

### P5. Reproducibility and Operational Reliability

- Capture phase inputs, outputs, timestamps, and model metadata where the runtime supports it.
- Keep artifacts append-only and audit-friendly.
- Build workflows so that another operator can replay the result or explain why it cannot be replayed.

### P6. Human Control and Transparency

- Provide explicit operator controls such as cancel, retry, resume, and resolve.
- Record overrides with actor, reason, and resulting effect.
- Do not hide recovery behavior behind opaque automation.

### P7. Validation Before Commercialization

- Internal validation gates must be met before commercialization claims.
- MVP readiness depends on benchmark and operations evidence, not anecdotal success.

## Evidence Integrity Rules

- PASS claims require machine-verifiable evidence and human-readable evidence.
- UI-only claims require full-context captures; cropped screenshots are supplemental only.
- Browser-console claims require console evidence from the same run.
- Sprint and milestone verdicts require independent confirmation before signoff.

## Prohibited Anti-Patterns

- Placeholder-driven delivery in production files.
- Fabricated metrics or unverifiable KPI claims.
- Pattern inflation from speculative future requirements.
- Cross-system dependency lock-in without direct MVP need.
- Destructive artifact mutation used to hide failures.
- Declaring PASS from low-integrity evidence such as missing logs, missing timestamps, or context-free screenshots.

## Relationship to Other Governance Docs

- `AGENTS.md` defines operational behavior for coding agents.
- `DIRECTIVES.md` defines enforceable repository rules.
- `specs/*.md` and `specs/deep_specs/*.md` define the MVP contract and runtime behavior.

## Repository-Specific Notes

- `configs/kpi_thresholds.json` is the source of truth for gate semantics.
- `runs/` remains append-only; do not rewrite or delete benchmark evidence bundles.
- `.claude/commands/` stores reusable Claude command surfaces.
- `.claude/agents/` stores reusable agent briefs, including cleanup and examination specialists.
- Repo-level completion requires `ruff check src tests` and `pytest tests/ -v --tb=short` to pass.
