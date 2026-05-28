from pathlib import Path
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_PATH = PROJECT_ROOT / "data" / "raw" / "Vendor_Payments.csv"
REPORT_PATH = PROJECT_ROOT / "reports" / "missing_values_report.txt"

CHUNK_SIZE = 100_000


CRITICAL_COLUMNS = [
    "Fiscal Year",
    "Purchase Order",
    "Supplier & Other Non-Supplier Payees",
    "Vouchers Paid",
    "data_as_of",
    "data_loaded_at",
]

WARNING_COLUMNS = [
    "Department",
    "Purchase Order Date",
    "Encumbrance Balance",
]

OPTIONAL_COLUMNS = [
    "Contract Number",
    "Contract Title",
    "Purchasing Authority Description",
]


def check_missing_values():
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"File not found: {DATA_PATH}")

    total_rows = 0

    all_columns = None
    missing_counts = {}

    critical_failed_rows = 0
    warning_rows = 0

    critical_failure_examples = []
    warning_examples = []

    for chunk in pd.read_csv(
        DATA_PATH,
        chunksize=CHUNK_SIZE,
        encoding="utf-8-sig",
        low_memory=False,
    ):
        if all_columns is None:
            all_columns = list(chunk.columns)
            missing_counts = {col: 0 for col in all_columns}

        total_rows += len(chunk)

        # Count missing values for all columns
        for col in all_columns:
            missing_counts[col] += chunk[col].isna().sum()

        # Critical rule: any critical column missing = failed row
        critical_mask = chunk[CRITICAL_COLUMNS].isna().any(axis=1)
        critical_failed_rows += critical_mask.sum()

        # Warning rule: any warning column missing = warning row
        warning_mask = chunk[WARNING_COLUMNS].isna().any(axis=1)
        warning_rows += warning_mask.sum()

        # Store examples
        if len(critical_failure_examples) < 10:
            examples = chunk.loc[critical_mask, CRITICAL_COLUMNS].head(10 - len(critical_failure_examples))
            critical_failure_examples.extend(examples.to_dict(orient="records"))

        if len(warning_examples) < 10:
            example_cols = [
                "Fiscal Year",
                "Purchase Order",
                "Department",
                "Purchase Order Date",
                "Encumbrance Balance",
            ]
            examples = chunk.loc[warning_mask, example_cols].head(10 - len(warning_examples))
            warning_examples.extend(examples.to_dict(orient="records"))

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(REPORT_PATH, "w", encoding="utf-8") as report:
        report.write("MISSING VALUES & FIELD RULES REPORT\n")
        report.write("=" * 80 + "\n\n")

        report.write(f"Data path: {DATA_PATH}\n")
        report.write(f"Total rows checked: {total_rows:,}\n")
        report.write(f"Chunk size: {CHUNK_SIZE:,}\n\n")

        report.write("FIELD RULE CONFIGURATION\n")
        report.write("-" * 80 + "\n")
        report.write("Critical columns: rows should fail validation if these are missing.\n")
        for col in CRITICAL_COLUMNS:
            report.write(f"  - {col}\n")

        report.write("\nWarning columns: rows can continue, but should be flagged or cleaned.\n")
        for col in WARNING_COLUMNS:
            report.write(f"  - {col}\n")

        report.write("\nOptional columns: missing values are allowed.\n")
        for col in OPTIONAL_COLUMNS:
            report.write(f"  - {col}\n")

        report.write("\n\nMISSING VALUE SUMMARY\n")
        report.write("-" * 80 + "\n")
        for col, count in missing_counts.items():
            pct = (count / total_rows) * 100 if total_rows else 0
            report.write(f"{col}: {count:,} nulls ({pct:.4f}%)\n")

        report.write("\n\nVALIDATION IMPACT SUMMARY\n")
        report.write("-" * 80 + "\n")
        critical_pct = (critical_failed_rows / total_rows) * 100 if total_rows else 0
        warning_pct = (warning_rows / total_rows) * 100 if total_rows else 0

        report.write(f"Rows failing critical missing-value rules: {critical_failed_rows:,} ({critical_pct:.4f}%)\n")
        report.write(f"Rows with warning-level missing values: {warning_rows:,} ({warning_pct:.4f}%)\n")

        report.write("\n\nCRITICAL FAILURE EXAMPLES\n")
        report.write("-" * 80 + "\n")
        if critical_failure_examples:
            for i, row in enumerate(critical_failure_examples, start=1):
                report.write(f"{i}. {row}\n")
        else:
            report.write("No rows failed critical missing-value rules.\n")

        report.write("\n\nWARNING EXAMPLES\n")
        report.write("-" * 80 + "\n")
        if warning_examples:
            for i, row in enumerate(warning_examples, start=1):
                report.write(f"{i}. {row}\n")
        else:
            report.write("No warning-level missing values found.\n")

        report.write("\n\nRECOMMENDED SILVER LAYER HANDLING\n")
        report.write("-" * 80 + "\n")
        report.write("Department: fill missing values with 'Unknown'.\n")
        report.write("Purchase Order Date: keep null; use Fiscal Year and data_as_of as fallback time references.\n")
        report.write("Contract Number: keep null; cast non-null values to string and remove trailing '.0'.\n")
        report.write("Encumbrance Balance: keep null during validation; optionally fill with 0 in analytics marts if business logic requires it.\n")

    print(f"Done. Report saved to: {REPORT_PATH}")


if __name__ == "__main__":
    check_missing_values()