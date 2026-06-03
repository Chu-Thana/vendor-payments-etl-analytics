# 📊 Vendor Payments ETL & Analytics Pipeline — Validated Batch Processing

> Production-style batch ETL pipeline for large-scale vendor payment analytics
>
> Raw data readiness → Silver transformation → Gold marts → Automated validation → CI

![Python](https://img.shields.io/badge/Python-3.12-blue)
![Pipeline](https://img.shields.io/badge/Pipeline-Batch%20ETL-orange)
![Processing](https://img.shields.io/badge/Processing-Pandas-lightblue)
![Data Quality](https://img.shields.io/badge/Data%20Quality-Validated-success)
![Testing](https://img.shields.io/badge/Testing-pytest-0A9EDC?logo=pytest\&logoColor=white)
![Code Quality](https://img.shields.io/badge/Code%20Quality-Ruff-8A2BE2)
![CI](https://github.com/Chu-Thana/superstore-etl-analytics/actions/workflows/ci.yml/badge.svg)

---

## 📌 Summary

This project refactors a small Superstore ETL project into a larger-scale **Vendor Payments ETL & Analytics Pipeline**.

The pipeline processes over **3.35 million vendor payment records**, performs data readiness checks, transforms raw data into a validated silver layer, builds analytics-ready gold marts, and validates outputs through automated tests and GitHub Actions CI.

The project demonstrates a production-style batch data engineering workflow:

```text
Raw Data
  → Data Readiness Checks
  → Silver Transformation
  → Silver Output Validation
  → Gold Mart Build
  → Gold Output Validation
  → Automated Tests & CI
```

---

## 🧭 ETL Workflow

![Validated Batch ETL Workflow](assets/validated-batch-etl-workflow.png)

**Design principle:** Validate each data layer before promoting outputs downstream.

---

## 🔥 What This Project Demonstrates

* Large-scale batch processing with **3.35M+ records**
* Data readiness profiling before transformation
* Raw → Silver → Gold layered pipeline design
* Chunk-based processing for large CSV files
* Data quality checks and validation reports
* Deterministic row identity using `source_row_hash`
* Business-level duplicate analysis using `business_composite_key`
* Analytics-ready gold marts for reporting
* Sample mode for fast local testing and CI
* Unit tests, integration tests, Ruff linting, and GitHub Actions CI

---

## 📂 Dataset

The source dataset is a vendor payments dataset containing government payment and purchase order records.

The data includes:

* Fiscal year
* Department and organization group
* Program and fund information
* Supplier / payee name
* Purchase order reference
* Voucher paid amount
* Voucher pending amount
* Encumbrance balance
* Contract information
* Data freshness timestamps

The full raw dataset is stored locally and is not committed to GitHub due to file size.

A representative sample dataset is included for testing and CI:

```text
data/sample/vendor_payments_sample.csv
```

---

## 🧪 Data Readiness Checks

Before building the ETL pipeline, the raw dataset was profiled across multiple readiness dimensions.

| Check                            | Purpose                                                              |
| -------------------------------- | -------------------------------------------------------------------- |
| File Structure Check             | Validate file size, delimiter, header, row count, and malformed rows |
| Schema Check                     | Confirm expected columns and column order                            |
| Data Type & Parsing Check        | Validate numeric and date parsing                                    |
| Missing Value Rules              | Define critical, warning, and optional fields                        |
| Duplicate & Key Strategy         | Evaluate primary key candidates and duplicate behavior               |
| Business Rule & Range Validation | Detect negative values, outliers, and date logic issues              |
| Dimension Cardinality            | Profile departments, suppliers, funds, and other dimensions          |
| Time Coverage & Freshness        | Analyze fiscal year coverage and timestamp freshness                 |

### Readiness Result

```text
Final status: READY WITH DESIGN WARNINGS
```

The dataset is suitable for refactoring into a production-style ETL pipeline, with important design decisions around nullable purchase order dates, non-unique purchase order values, large payment outliers, and fiscal year reporting logic.

---

## 🏗️ Pipeline Architecture

### 1. Raw Layer

The raw layer stores the original vendor payments CSV file locally.

```text
data/raw/Vendor_Payments.csv
```

The raw file is excluded from GitHub because it is large.

### 2. Silver Layer

The silver transformation performs:

* Schema validation
* Column renaming to snake_case
* Numeric cleaning
* Date and timestamp parsing
* Contract number cleaning
* Text trimming and normalization
* `source_row_hash` generation
* `business_composite_key` generation
* Data quality flag creation

Silver output:

```text
data/processed/silver/vendor_payments_silver.csv
```

### 3. Gold Layer

The gold layer creates analytics-ready marts:

```text
data/processed/gold/
  mart_spending_by_fiscal_year.csv
  mart_spending_by_department.csv
  mart_spending_by_supplier_top_n.csv
  mart_pending_by_department.csv
  mart_fund_category_summary.csv
```

These marts support analysis such as:

* Spending trend by fiscal year
* Department spending
* Top supplier payments
* Pending voucher monitoring
* Fund category summary

---

## ✅ Validation Strategy

This project validates each layer before downstream use.

### Silver Output Validation

Checks include:

* Required columns
* Null counts
* Hash uniqueness
* Fiscal year range
* Data quality flag counts

### Gold Output Validation

Checks include:

* Gold mart file existence
* Row counts
* Required columns
* Metric null counts
* Metric summaries

---

## 🧪 Automated Testing

The project includes both unit tests and integration tests.

### Unit Tests

Unit tests validate:

* Schema definitions
* Column rename mapping
* Numeric cleaning
* Contract number cleaning
* Text normalization
* Date parsing
* Row hash and composite key generation

### Integration Test

The integration test runs the sample ETL pipeline:

```text
sample data → silver output → gold marts
```

Current test status:

```text
15 passed
```

---

## ⚙️ CI/CD

GitHub Actions runs automatically on push and pull requests.

The CI workflow performs:

1. Checkout repository
2. Set up Python
3. Install dependencies
4. Run Ruff lint
5. Run sample ETL pipeline
6. Run pytest

CI uses the committed sample dataset, not the full raw dataset.

```bash
python scripts/pipeline/run_pipeline.py --sample
python -m pytest -v
```

---

## 🚀 How to Run

### Run Full Pipeline

Use this when the full raw dataset exists locally:

```bash
python scripts/pipeline/run_pipeline.py
```

This processes the full vendor payments dataset.

### Run Sample Pipeline

Use this for fast local testing or CI:

```bash
python scripts/pipeline/run_pipeline.py --sample
```

This uses:

```text
data/sample/vendor_payments_sample.csv
```

and writes sample outputs to:

```text
data/processed/silver/vendor_payments_silver_sample.csv
data/processed/gold_sample/
```

---

## 🧪 Run Tests

```bash
python -m pytest -v
```

Run Ruff lint:

```bash
python -m ruff check .
```

---

## 📁 Project Structure

```text
project1_etl/
  data/
    raw/                         # Local raw data, not committed
    sample/                      # Committed representative sample data
    processed/
      silver/                    # Generated silver outputs
      gold/                      # Generated gold marts
      gold_sample/               # Generated sample-mode gold marts

  scripts/
    checks/                      # Data readiness and output validation scripts
    pipeline/                    # ETL pipeline scripts

  src/
    config.py                    # Paths and pipeline configuration
    schema.py                    # Expected schema and column groups
    cleaning.py                  # Cleaning utilities
    keys.py                      # Hash and composite key utilities

  tests/
    test_schema.py
    test_cleaning.py
    test_keys.py
    test_sample_pipeline.py

  reports/                       # Profiling and validation reports
  .github/workflows/ci.yml       # GitHub Actions CI workflow
```

---

## 🧠 Key Engineering Decisions

### Why use sample mode?

The full dataset contains more than 3.35 million records, so CI should not depend on the full raw file.

Sample mode enables fast and reliable validation in GitHub Actions.

### Why use `source_row_hash`?

The dataset does not have a simple unique primary key.

`source_row_hash` provides deterministic row-level identity for raw and silver layers.

### Why not use `Purchase Order` as a primary key?

`Purchase Order` is not unique and includes many `Direct Payments` records.

It is kept as a reference field, not used as the primary key.

### Why use `Fiscal Year` as the main reporting period?

`Purchase Order Date` is nullable for many records.

`Fiscal Year` is more reliable as the primary reporting period for analytics and gold marts.

### Why flag negative and large amounts instead of rejecting them?

Negative and large payment values may represent adjustments, reversals, refunds, corrections, or legitimate large government payments.

The pipeline flags these records instead of automatically removing them.

---

## 📊 Gold Marts

| Mart                              | Purpose                               |
| --------------------------------- | ------------------------------------- |
| `mart_spending_by_fiscal_year`    | Fiscal year spending trend            |
| `mart_spending_by_department`     | Department-level spending analytics   |
| `mart_spending_by_supplier_top_n` | Top supplier payment analysis         |
| `mart_pending_by_department`      | Pending voucher monitoring            |
| `mart_fund_category_summary`      | Fund type and fund category analytics |

---

## 🔗 Role in the Data Platform

This project represents the **batch ETL foundation layer** of a broader data engineering platform.

```text
Project 1: Batch ETL Foundation
Project 2: API Serving Layer
Project 3: Streaming Pipeline
Project 4: Airflow Orchestration
Project 5: Cloud Data Platform
```

Project 4 can orchestrate this Project 1 pipeline by triggering:

```bash
python scripts/pipeline/run_pipeline.py
```

---

## 💡 Key Takeaway

Raw data is not ready for analytics by default.

This project demonstrates how a data engineer validates, transforms, tests, and prepares large-scale raw data into reliable analytics-ready outputs.

```text
Raw → Validated Silver → Analytics-ready Gold → Tested & CI-validated Pipeline
```
