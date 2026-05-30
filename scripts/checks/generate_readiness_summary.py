from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

REPORT_PATH = PROJECT_ROOT / "reports" / "data_readiness_summary.md"


def generate_summary():
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    content = """# Data Readiness Summary Report

## Dataset

**Dataset:** Vendor Payments  
**Raw file:** `data/raw/Vendor_Payments.csv`  
**Readiness status:** READY WITH DESIGN WARNINGS

---

## 1. File Structure Check

**Status:** PASS

The raw CSV file was successfully read and profiled.

| Check | Result |
|---|---:|
| Total rows | 3,354,965 |
| File size | 1,273.84 MB |
| Column count | 33 |
| Delimiter | Comma |
| Header | Present |
| Malformed rows | 0 |

**Decision:** File structure is stable and suitable for chunk-based processing.

---

## 2. Schema Check

**Status:** PASS

The dataset contains all 33 expected columns.

| Check | Result |
|---|---:|
| Expected columns | 33 |
| Actual columns | 33 |
| Missing columns | 0 |
| Extra columns | 0 |
| Column order | Matches expected schema |

**Decision:** Schema is stable enough to start designing raw-to-silver transformations.

---

## 3. Data Type & Parsing Check

**Status:** PASS WITH WARNINGS

Numeric and date fields can be parsed successfully.

| Field Group | Result |
|---|---|
| Amount columns | Valid numeric parsing |
| Date columns | Valid date parsing |
| Fiscal Year | Valid numeric year |
| Contract Number | Should be treated as string/id |

**Warnings:**

- `Purchase Order Date` has many null values.
- `Contract Number` has many null values and float-like values ending with `.0`.
- Amount fields contain negative values and very large values.

**Decision:** Do not reject these records automatically. Convert and flag values during silver transformation.

---

## 4. Missing Value & Critical Field Rules

**Status:** PASS WITH WARNINGS

Critical fields have no missing-value failures.

| Rule Group | Result |
|---|---:|
| Rows failing critical missing-value rules | 0 |
| Rows with warning-level missing values | 1,319,023 |

**Critical fields that passed:**

- Fiscal Year
- Purchase Order
- Supplier & Other Non-Supplier Payees
- Vouchers Paid
- data_as_of
- data_loaded_at

**Warnings:**

- `Purchase Order Date` is nullable and should not be required.
- `Encumbrance Balance` is nullable.
- `Contract Number`, `Contract Title`, and `Purchasing Authority Description` are optional.

**Decision:** Keep nullable fields. Use fallback reporting logic instead of rejecting records.

---

## 5. Duplicate & Key Strategy Check

**Status:** PASS WITH KEY STRATEGY WARNING

There are no full-row duplicates, but `Purchase Order` is not unique.

| Check | Result |
|---|---:|
| Full-row duplicate rows | 0 |
| Purchase Order = Direct Payments | 1,122,941 |
| Purchase Order uniqueness | 46.7474% |
| Business composite key uniqueness | 94.1107% |

**Decision:**

Do not use `Purchase Order` alone as a primary key.

Recommended key strategy:

- Use `source_row_hash` as raw-level row identity.
- Use `business_composite_key` for business-level duplicate analysis.
- Keep `Purchase Order` as a reference field.

---

## 6. Business Rule & Range Validation

**Status:** PASS WITH BUSINESS WARNINGS

Amount fields are valid numerically but contain negative values and large outliers.

**Warnings:**

- Negative amounts exist and may represent adjustments, reversals, refunds, or corrections.
- Very large values exist and should be flagged for review.
- Fiscal Year may differ from Purchase Order Date year.

**Decision:**

Do not reject negative or large values automatically. Create quality flags such as:

- `is_negative_paid`
- `is_large_paid_1m`
- `is_large_paid_10m`
- `is_large_paid_100m`
- `is_large_paid_1b`
- `is_fiscal_year_mismatch`

---

## 7. Dimension Cardinality & Value Consistency

**Status:** PASS WITH DIMENSION NORMALIZATION WARNINGS

Dimension columns are mostly clean and suitable for analytics.

**Good dashboard dimensions:**

- Fiscal Year
- Organization Group
- Department
- Program
- Character
- Object
- Fund Type
- Fund Category

**High-cardinality dimension:**

- Supplier & Other Non-Supplier Payees

**Decision:**

Use supplier as top-N/searchable dimension, not as a full dashboard dropdown.

Recommended silver-layer handling:

- Trim all dimension values.
- Fill small missing dimension values with `Unknown`.
- Keep original text and create normalized fields for grouping/search.
- Treat `Non-Profit Indicator` as optional flag.

---

## 8. Time Coverage & Freshness Check

**Status:** PASS WITH TIME DESIGN WARNINGS

The dataset has strong fiscal year coverage and clear metadata timestamps.

| Field | Result |
|---|---|
| Fiscal Year range | 2007–2026 |
| Purchase Order Date valid pct | 60.6853% |
| data_loaded_at unique timestamp | 1 |
| data_loaded_at coverage | 100% of rows |

**Decision:**

Use time fields as follows:

| Field | Purpose |
|---|---|
| Fiscal Year | Primary reporting period |
| Purchase Order Date | Optional PO reference date |
| data_as_of | Source snapshot/freshness timestamp |
| data_loaded_at | Ingestion/load timestamp |

Recommended partitioning:

- Primary partition: `fiscal_year`
- Optional metadata partition: `ingestion_date`

---

## Overall Readiness Decision

**Final status:** READY WITH DESIGN WARNINGS

The dataset is ready for Project 1 refactor because:

- The file structure is valid.
- Schema is stable.
- Numeric and date parsing are valid.
- Critical fields are complete.
- No full-row duplicates exist.
- Fiscal year coverage is strong.
- Dimensions are usable for analytics.

However, the refactor must handle these design warnings:

1. `Purchase Order` is not a unique key.
2. `Purchase Order Date` is nullable and cannot be required.
3. `Contract Number` is optional and should be treated as string.
4. Negative and very large amounts should be flagged, not rejected.
5. Supplier is high-cardinality and should be handled with top-N/search logic.
6. Fiscal Year should be the primary reporting period.
7. `data_loaded_at` represents a single bulk load timestamp.

---

## Recommended Refactor Direction

### Raw Layer

- Store the original data unchanged.
- Add ingestion metadata.
- Generate `source_row_hash`.
- Preserve all original columns.

### Silver Layer

- Standardize column names.
- Cast data types.
- Clean contract number as string.
- Trim dimension values.
- Fill selected low-risk missing dimensions with `Unknown`.
- Create normalized dimension fields.
- Create quality flags.
- Create `business_composite_key`.

### Gold Layer

Create analytics-ready marts such as:

- `mart_spending_by_fiscal_year`
- `mart_spending_by_department`
- `mart_spending_by_supplier_top_n`
- `mart_spending_by_fund_category`
- `mart_pending_vouchers_by_department`
- `mart_procurement_authority_summary`

### Serving / Dashboard Direction

Focus on:

- Vendor payment analytics
- Department spending analysis
- Fiscal year spending trends
- Supplier top-N analysis
- Pending voucher monitoring
- Procurement authority analysis

---

## Conclusion

The new dataset is suitable for refactoring Project 1 into a larger-scale, production-style ETL and analytics pipeline.

The project should shift from the old Superstore sales analytics story to:

**Vendor Payments ETL & Analytics Pipeline**

This direction is stronger for a data engineering portfolio because it includes:

- Larger data volume
- Realistic government/vendor payment structure
- Complex keys
- Data quality rules
- Time/freshness metadata
- Analytics-ready marts
- Clear raw/silver/gold design decisions
"""

    REPORT_PATH.write_text(content, encoding="utf-8")
    print(f"Done. Report saved to: {REPORT_PATH}")


if __name__ == "__main__":
    generate_summary()