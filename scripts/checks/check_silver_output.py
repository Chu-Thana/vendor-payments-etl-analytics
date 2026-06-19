from pathlib import Path
import sys

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PROJECT_ROOT))

from src.config import SILVER_DATA_DIR, CHUNK_SIZE


SILVER_FILE = SILVER_DATA_DIR / "vendor_payments_silver.csv"
REPORT_PATH = PROJECT_ROOT / "reports" / "silver_output_validation_report.txt"


REQUIRED_COLUMNS = [
    "source_row_hash",
    "business_composite_key",
    "fiscal_year",
    "department",
    "department_norm",
    "purchase_order",
    "supplier_name",
    "supplier_name_norm",
    "vouchers_paid",
    "vouchers_pending",
    "encumbrance_balance",
    "vouchers_pending_retainage",
    "data_as_of",
    "data_loaded_at",
    "purchase_order_date",
    "po_year",
    "po_month",
    "is_missing_department",
    "is_missing_purchase_order_date",
    "is_negative_paid",
    "is_large_paid_1m",
    "is_large_paid_10m",
    "is_large_paid_100m",
    "is_large_paid_1b",
    "is_fiscal_year_mismatch",
    "is_non_profit",
]


def check_silver_output(
    silver_file: Path = SILVER_FILE,
    report_path: Path = REPORT_PATH,
) -> dict:
    if not silver_file.exists():
        raise FileNotFoundError(f"Silver file not found: {silver_file}")

    total_rows = 0
    columns = None

    missing_required_columns = []
    null_counts = {col: 0 for col in REQUIRED_COLUMNS}
    unique_source_hashes = set()

    flag_true_counts = {
        "is_missing_department": 0,
        "is_missing_purchase_order_date": 0,
        "is_negative_paid": 0,
        "is_large_paid_1m": 0,
        "is_large_paid_10m": 0,
        "is_large_paid_100m": 0,
        "is_large_paid_1b": 0,
        "is_fiscal_year_mismatch": 0,
        "is_non_profit": 0,
    }

    fiscal_year_min = None
    fiscal_year_max = None

    for chunk in pd.read_csv(
        silver_file,
        chunksize=CHUNK_SIZE,
        encoding="utf-8",
        low_memory=False,
    ):
        total_rows += len(chunk)

        if columns is None:
            columns = list(chunk.columns)
            missing_required_columns = [
                col for col in REQUIRED_COLUMNS
                if col not in columns
            ]

        for col in REQUIRED_COLUMNS:
            if col in chunk.columns:
                null_counts[col] += int(chunk[col].isna().sum())

        if "source_row_hash" in chunk.columns:
            unique_source_hashes.update(
                chunk["source_row_hash"]
                .dropna()
                .astype(str)
                .tolist()
            )

        for flag_col in flag_true_counts:
            if flag_col in chunk.columns:
                flag_true_counts[flag_col] += int(
                    chunk[flag_col]
                    .astype(str)
                    .str.lower()
                    .eq("true")
                    .sum()
                )

        if "fiscal_year" in chunk.columns:
            fiscal_year = pd.to_numeric(
                chunk["fiscal_year"],
                errors="coerce",
            ).dropna()

            if not fiscal_year.empty:
                current_min = int(fiscal_year.min())
                current_max = int(fiscal_year.max())

                fiscal_year_min = (
                    current_min
                    if fiscal_year_min is None
                    else min(fiscal_year_min, current_min)
                )

                fiscal_year_max = (
                    current_max
                    if fiscal_year_max is None
                    else max(fiscal_year_max, current_max)
                )

    status = (
        "PASS"
        if not missing_required_columns
        and total_rows == len(unique_source_hashes)
        else "PASS_WITH_WARNINGS"
    )

    uniqueness_pct = (
        (len(unique_source_hashes) / total_rows) * 100
        if total_rows
        else 0
    )

    report_path.parent.mkdir(parents=True, exist_ok=True)

    with open(report_path, "w", encoding="utf-8") as report:
        report.write("SILVER OUTPUT VALIDATION REPORT\n")
        report.write("=" * 80 + "\n\n")

        report.write(f"Silver file: {silver_file}\n")
        report.write(f"Total rows checked: {total_rows:,}\n")
        report.write(
            f"Column count: {len(columns) if columns else 0}\n\n"
        )

        report.write("REQUIRED COLUMN CHECK\n")
        report.write("-" * 80 + "\n")

        if missing_required_columns:
            report.write(
                f"Missing required columns: "
                f"{missing_required_columns}\n"
            )
        else:
            report.write(
                "All required silver columns are present.\n"
            )

        report.write("\nSOURCE ROW HASH CHECK\n")
        report.write("-" * 80 + "\n")
        report.write(
            f"Unique source_row_hash count: "
            f"{len(unique_source_hashes):,}\n"
        )
        report.write(f"Total rows: {total_rows:,}\n")
        report.write(
            f"source_row_hash uniqueness pct: "
            f"{uniqueness_pct:.4f}%\n"
        )

        report.write("\nFISCAL YEAR RANGE\n")
        report.write("-" * 80 + "\n")
        report.write(f"Fiscal year min: {fiscal_year_min}\n")
        report.write(f"Fiscal year max: {fiscal_year_max}\n")

        report.write("\nNULL COUNTS FOR REQUIRED COLUMNS\n")
        report.write("-" * 80 + "\n")

        for col, count in null_counts.items():
            pct = (
                (count / total_rows) * 100
                if total_rows
                else 0
            )
            report.write(
                f"{col}: {count:,} nulls ({pct:.4f}%)\n"
            )

        report.write("\nQUALITY FLAG TRUE COUNTS\n")
        report.write("-" * 80 + "\n")

        for col, count in flag_true_counts.items():
            pct = (
                (count / total_rows) * 100
                if total_rows
                else 0
            )
            report.write(
                f"{col}: {count:,} true ({pct:.4f}%)\n"
            )

        report.write("\nVALIDATION DECISION\n")
        report.write("-" * 80 + "\n")

        if status == "PASS":
            report.write(
                "PASS: Silver output structure and "
                "row identity checks passed.\n"
            )
        else:
            report.write(
                "PASS WITH WARNINGS: Review missing columns "
                "or hash uniqueness.\n"
            )

    print(f"Done. Report saved to: {report_path}")

    return {
        "status": status,
        "row_count": total_rows,
        "column_count": len(columns) if columns else 0,
        "missing_required_columns": missing_required_columns,
        "unique_source_hash_count": len(unique_source_hashes),
        "source_row_hash_uniqueness_pct": round(
            uniqueness_pct,
            4,
        ),
        "fiscal_year_min": fiscal_year_min,
        "fiscal_year_max": fiscal_year_max,
        "null_counts": {
            column: int(count)
            for column, count in null_counts.items()
        },
        "quality_flag_true_counts": {
            column: int(count)
            for column, count in flag_true_counts.items()
        },
        "report_file": str(report_path),
    }

if __name__ == "__main__":
    check_silver_output()