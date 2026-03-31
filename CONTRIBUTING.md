# Contributing to Entropy Quality & Drift Benchmark

Thank you for your interest in contributing. This project is a formal benchmark — contributions must preserve its scientific integrity and public-safety requirements.

## Before You Contribute

Read the decision order in [CLAUDE.md](CLAUDE.md). All contributions must comply with the non-negotiable rules there:

- **No UMIF.** Shannon Entropy, KL divergence, and standard statistical tests only.
- **No client data.** No ADB, OTSI, or any client-specific identifiers.
- **No credentials.** No API keys, tokens, passwords, or connection strings.
- **Public-safe only.** Every file must be safe for public GitHub.

## Development Setup

```bash
git clone https://github.com/org-etherealogic/entropy_quality_drift_benchmark.git
cd entropy_quality_drift_benchmark
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Running Tests and Lint

```bash
pytest tests/ -v
ruff check src/ tests/
```

All tests must pass and ruff must report zero violations before a PR can be merged.

## Commit Conventions

This project follows [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/).

| Type | When to use |
|------|-------------|
| `feat` | New feature or benchmark track component |
| `fix` | Bug fix |
| `test` | Adding or updating tests |
| `docs` | Documentation only |
| `chore` | Build, CI, tooling (no production code change) |
| `refactor` | Code restructuring without behaviour change |
| `perf` | Performance improvement |

**Format:** `<type>(<optional scope>): <short imperative description>`

Examples:
```
feat(sentinel): add gradual-drift gradient detection
fix(forge): clamp normalized entropy to [0, 1]
test: add determinism assertions for canonical seeds
docs: expand gate definitions in README
chore(ci): add Python 3.12 to test matrix
```

Breaking changes must include `BREAKING CHANGE:` in the commit body.

## Pull Request Process

1. Fork the repository and create a feature branch from `main`.
2. Ensure all tests pass and lint is clean.
3. Write a clear PR description explaining the change and why it belongs in this benchmark.
4. Reference any relevant gate IDs (e.g., `Q-GATE-2`) if your change affects scoring.
5. A maintainer will review within a reasonable timeframe.

## Reporting Issues

Open a GitHub Issue. For security concerns, see [SECURITY.md](SECURITY.md).

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
