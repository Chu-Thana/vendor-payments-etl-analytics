from pathlib import Path
import sys

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PROJECT_ROOT))

from src.config import GOLD_DATA_DIR


REPORT_PATH = PROJECT_ROOT / "reports" / "gold_output_validation_report.txt"


GOLD_FILES = {
    "mart_spending_by_fiscal_year": {
        "path": GOLD_DATA_DIR / "mart_spending_by_fiscal_year.csv",
        "required_columns": [
            "fiscal_year",
            "total_vouchers_paid",
            "total_vouchers_pending",
            "record_count",
        ],
    },
    "mart_spending_by_department": {
        "path": GOLD_DATA_DIR / "mart_spending_by_department.csv",
        "required_columns": [
            "fiscal_year",
            "organization_group",
            "department",
            "total_vouchers_paid",
            "record_count",
        ],
    },
    "mart_spending_by_supplier_top_n": {
        "path": GOLD_DATA_DIR / "mart_spending_by_supplier_top_n.csv",
        "required_columns": [
            "supplier_name",
            "total_vouchers_paid",
            "record_count",
        ],
    },
    "mart_pending_by_department": {
        "path": GOLD_DATA_DIR / "mart_pending_by_department.csv",
        "required_columns": [
            "fiscal_year",
            "department",
            "total_vouchers_pending",
            "record_count",
        ],
    },
    "mart_fund_category_summary": {
        "path": GOLD_DATA_DIR / "mart_fund_category_summary.csv",
        "required_columns": [
            "fiscal_year",
            "fund_type",
            "fund_category",
            "total_vouchers_paid",
            "record_count",
        ],
    },
}


METRIC_COLUMNS = [
    "total_vouchers_paid",
    "total_vouchers_pending",
    "total_encumbrance_balance",
    "total_pending_retainage",
    "record_count",
]


def validate_gold_file(name: str, config: dict) -> dict:
    file_path = config["path"]
    required_columns = config["required_columns"]

    result = {
        "name": name,
        "path": file_path,
        "exists": file_path.exists(),
        "row_count": 0,
        "column_count": 0,
        "missing_columns": [],
        "metric_null_counts": {},
        "metric_sums": {},
        "status": "FAIL",
    }

    if not file_path.exists():
        result["status"] = "FAIL: file does not exist"
        return result

    df = pd.read_csv(file_path, encoding="utf-8")

    result["row_count"] = len(df)
    result["column_count"] = len(df.columns)
    result["missing_columns"] = [
        col for col in required_columns if col not in df.columns
    ]

    for col in METRIC_COLUMNS:
        if col in df.columns:
            numeric = pd.to_numeric(df[col], errors="coerce")
            result["metric_null_counts"][col] = int(numeric.isna().sum())
            result["metric_sums"][col] = float(numeric.sum(skipna=True))

    if result["row_count"] == 0:
        result["status"] = "FAIL: no rows"
    elif result["missing_columns"]:
        result["status"] = "FAIL: missing required columns"
    else:
        result["status"] = "PASS"

    return result


def check_gold_outputs() -> None:
    results = [
        validate_gold_file(name, config)
        for name, config in GOLD_FILES.items()
    ]

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(REPORT_PATH, "w", encoding="utf-8") as report:
        report.write("GOLD OUTPUT VALIDATION REPORT\n")
        report.write("=" * 80 + "\n\n")

        overall_pass = all(result["status"] == "PASS" for result in results)

        report.write(f"Overall status: {'PASS' if overall_pass else 'FAIL'}\n\n")

        for result in results:
            report.write(result["name"] + "\n")
            report.write("-" * 80 + "\n")
            report.write(f"Path: {result['path']}\n")
            report.write(f"Exists: {result['exists']}\n")
            report.write(f"Status: {result['status']}\n")
            report.write(f"Row count: {result['row_count']:,}\n")
            report.write(f"Column count: {result['column_count']:,}\n")
            report.write(f"Missing required columns: {result['missing_columns'] if result['missing_columns'] else 'None'}\n")

            report.write("Metric null counts:\n")
            if result["metric_null_counts"]:
                for col, count in result["metric_null_counts"].items():
                    report.write(f"  - {col}: {count:,}\n")
            else:
                report.write("  - None\n")

            report.write("Metric sums:\n")
            if result["metric_sums"]:
                for col, value in result["metric_sums"].items():
                    report.write(f"  - {col}: {value:,.2f}\n")
            else:
                report.write("  - None\n")

            report.write("\n")

        report.write("VALIDATION DECISION\n")
        report.write("-" * 80 + "\n")
        if overall_pass:
            report.write("PASS: All gold mart files exist, contain rows, and include required columns.\n")
        else:
            report.write("FAIL: Review missing files, empty marts, or missing required columns.\n")

    print(f"Done. Report saved to: {REPORT_PATH}")


if __name__ == "__main__":
    check_gold_outputs()