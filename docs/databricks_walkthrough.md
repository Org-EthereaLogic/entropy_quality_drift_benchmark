# How This Pattern Maps to Databricks Data-Quality and Drift Monitoring

This walkthrough explains how each benchmark concept translates to a
Databricks Lakehouse environment. The benchmark itself runs as pure Python
with no Databricks dependency, but the patterns it demonstrates are designed
to slot into a governed Delta Lake pipeline.

---

## Overview

In a Databricks medallion architecture, data quality and drift checks
typically sit at **two boundaries**:

1. **Bronze-to-Silver promotion** — validate that ingested data meets schema,
   null-rate, range, and distribution expectations before it enters curated
   tables.
2. **Silver-to-Gold promotion** — detect drift between training-era
   distributions and current production distributions before data reaches
   feature stores, ML models, or BI dashboards.

This benchmark exercises both boundaries using synthetic data and deterministic
fault/drift injection so the evaluation is replayable.

---

## Concept Mapping

### Data Sourcing

| Benchmark | Databricks |
| --- | --- |
| `generate_clean_batch()` | Read the latest Delta table version via `spark.read.format("delta")` |
| `inject_quality_faults()` | Not needed in production — faults arrive naturally. In testing, corrupt a staging table version to exercise the quality adapters. |
| `inject_drift()` | Not needed in production — drift arrives naturally. In testing, write a shifted partition to exercise drift adapters. |
| Change Data Feed (CDF) stubs | Use `readStream.option("readChangeFeed", "true")` on Delta tables to get incremental batches |

The benchmark includes abstract CDF and ingestion-logger seams in
[`src/entropy_quality_drift/databricks_seams/`](../src/entropy_quality_drift/databricks_seams/__init__.py).
A production implementation would replace `LocalCDFReader` with a real
`CDFReaderBase` subclass that reads from Unity Catalog tables.

### Quality Adapters

| Benchmark Adapter | Databricks Equivalent |
| --- | --- |
| `DeequAdapter` (null rate, range, schema, volume rules) | [Databricks Data Quality Expectations](https://docs.databricks.com/en/delta-live-tables/expectations.html) or `dbt-expectations` macros |
| `EntropyForge` (per-column Shannon Entropy, collapse detection) | Custom PySpark UDF or notebook step computing `entropy = -sum(p * log(p))` per column per batch |

In a Databricks Workflow, the quality gate would be a **task** between the
ingestion task and the Silver-write task:

```
[Ingest to Bronze] --> [Quality Gate Task] --> [Write to Silver]
                            |
                     reads kpi_thresholds
                     from Unity Catalog tag
                     or _quality_gates table
```

If the quality gate returns `FAIL`, the workflow halts and routes the batch to
a quarantine table. If it returns `WARN`, the batch promotes with an advisory
flag logged to the evidence table.

### Drift Adapters

| Benchmark Adapter | Databricks Equivalent |
| --- | --- |
| `EvidentlyAdapter` (KS-test per column) | [Lakehouse Monitoring](https://docs.databricks.com/en/lakehouse-monitoring/index.html) statistical drift profiles |
| `EntropySentinel` (entropy gradient + KL divergence) | Custom monitor comparing per-column entropy between the reference window and the current batch |

In production, the drift check runs on a **schedule** (e.g., daily or on each
new partition) and writes its result to an evidence table. The gate evaluator
then decides whether to alert, quarantine, or pass.

### Gate Configuration

| Benchmark | Databricks |
| --- | --- |
| `configs/kpi_thresholds.json` | A governed `_quality_gates` Delta table in Unity Catalog, or Unity Catalog table/column tags encoding pass/warn/fail thresholds |
| `GateEvaluator.evaluate_benchmark()` | A Databricks Workflow task that reads the gate table, evaluates the latest adapter output, and sets the workflow outcome |

The key design point is that **gate thresholds live in configuration, not in
code**. This lets data stewards adjust thresholds without redeploying the
pipeline.

### Evidence Storage

| Benchmark | Databricks |
| --- | --- |
| `runs/` directory with append-only JSON | A `_benchmark_evidence` Delta table with append-only writes and `RETAIN` history |
| `write_evidence_bundle()` | `INSERT INTO _benchmark_evidence VALUES (...)` via the `IngestionLoggerBase` seam |
| Evidence includes full threshold context | Each row includes the gate contract snapshot so verdicts are self-contained |

Evidence immutability is enforced by Delta Lake's append-only table property:
```sql
ALTER TABLE _benchmark_evidence SET TBLPROPERTIES ('delta.appendOnly' = 'true');
```

---

## Example: Wiring Into a Databricks Workflow

```text
Job: daily_quality_drift_check
  Task 1: ingest_to_bronze
    - Read from source, write to bronze Delta table
    - Enable CDF: ALTER TABLE bronze_taxi SET TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true')

  Task 2: quality_gate  (depends on Task 1)
    - Read latest CDF changes from bronze_taxi
    - Run DeequAdapter + EntropyForge on the batch
    - Evaluate gates from _quality_gates table
    - If FAIL: write to quarantine, skip downstream tasks
    - If WARN: write advisory flag, continue
    - If PASS: continue

  Task 3: write_to_silver  (depends on Task 2, skipped on FAIL)
    - Merge validated rows into silver_taxi

  Task 4: drift_check  (depends on Task 3)
    - Read silver_taxi reference window (last 30 days)
    - Read silver_taxi current batch
    - Run EvidentlyAdapter + EntropySentinel
    - Evaluate drift gates
    - Write evidence to _benchmark_evidence

  Task 5: promote_to_gold  (depends on Task 4, skipped on FAIL)
    - Aggregate and write to gold reporting tables
```

---

## What the Benchmark Proves for This Pattern

1. **Entropy catches what rules miss.** The quality track shows `EntropyForge`
   detecting constant-column collapse (`recall: 1.00`) that the Deequ-style
   baseline misses (`recall: 0.75`). In a Databricks pipeline, this means the
   entropy check would catch a silent data issue that Expectations alone would
   pass through.

2. **Gate logic is portable.** The `GateEvaluator` reads a JSON contract with
   symbolic conditions (`>=baseline`, numeric thresholds, warn bands). This
   same logic works whether the contract lives in a local file or a Unity
   Catalog table.

3. **Evidence is self-contained.** Each evidence bundle includes the full
   threshold context, so an auditor can reconstruct the verdict without
   cross-referencing the gate configuration. This maps directly to a governed
   Delta evidence table.

4. **WARN is a feature, not a failure.** The benchmark's four-state per-run
   verdict (`PASS` / `WARN` / `FAIL` / `INCOMPLETE`) gives pipeline operators a
   way to promote data with advisory flags, hard-block on critical failures,
   and halt safely when required evidence is missing. This is critical in
   production where both over-blocking and silent partial execution create
   operational risk.

---

## Further Reading

- [Databricks Lakehouse Monitoring](https://docs.databricks.com/en/lakehouse-monitoring/index.html)
- [Delta Live Tables Expectations](https://docs.databricks.com/en/delta-live-tables/expectations.html)
- [Unity Catalog](https://docs.databricks.com/en/data-governance/unity-catalog/index.html)
- [Change Data Feed](https://docs.databricks.com/en/delta/delta-change-data-feed.html)
