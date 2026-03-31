# Runs Archive

`runs/` is an append-only archive of historical benchmark evidence bundles.

- New bundles written by the current code include `"evidence_schema_version": 2`.
- Older bundles are intentionally preserved verbatim for audit history.
- Some legacy bundles predate the current schema and may omit fields such as
  `status` or `thresholds` on individual gates.
- When you need the current self-contained example used by the docs, prefer
  `docs/fixtures/sample_evidence_seed42.json` or a bundle in `runs/` that
  includes `"evidence_schema_version": 2`.

Do not rewrite or delete historical bundles in this directory.
