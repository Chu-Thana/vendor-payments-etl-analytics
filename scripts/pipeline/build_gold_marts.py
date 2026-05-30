from pathlib import Path
import sys

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PROJECT_ROOT))

from src.config import SILVER_DATA_DIR, GOLD_DATA_DIR, CHUNK_SIZE, ensure_directories


SILVER_FILE = SILVER_DATA_DIR / "vendor_payments_silver.csv"

MART_FISCAL_YEAR = GOLD_DATA_DIR / "mart_spending_by_fiscal_year.csv"
MART_DEPARTMENT = GOLD_DATA_DIR / "mart_spending_by_department.csv"
MART_SUPPLIER_TOP_N = GOLD_DATA_DIR / "mart_spending_by_supplier_top_n.csv"
MART_PENDING_DEPARTMENT = GOLD_DATA_DIR / "mart_pending_by_department.csv"
MART_FUND_CATEGORY = GOLD_DATA_DIR / "mart_fund_category_summary.csv"


METRIC_COLUMNS = [
    "vouchers_paid",
    "vouchers_pending",
    "encumbrance_balance",
    "vouchers_pending_retainage",
]


def aggregate_by_group(group_cols: list[str]) -> pd.DataFrame:
    """
    Aggregate silver data by selected group columns using chunk processing.
    """
    result_parts = []

    for chunk in pd.read_csv(
        SILVER_FILE,
        chunksize=CHUNK_SIZE,
        encoding="utf-8",
        low_memory=False,
    ):
        grouped = (
            chunk.groupby(group_cols, dropna=False)
            .agg(
                total_vouchers_paid=("vouchers_paid", "sum"),
                total_vouchers_pending=("vouchers_pending", "sum"),
                total_encumbrance_balance=("encumbrance_balance", "sum"),
                total_pending_retainage=("vouchers_pending_retainage", "sum"),
                record_count=("source_row_hash", "count"),
                unique_suppliers=("supplier_name", "nunique"),
                negative_paid_records=("is_negative_paid", "sum"),
                large_paid_1m_records=("is_large_paid_1m", "sum"),
                missing_po_date_records=("is_missing_purchase_order_date", "sum"),
            )
            .reset_index()
        )

        result_parts.append(grouped)

    combined = pd.concat(result_parts, ignore_index=True)

    final = (
        combined.groupby(group_cols, dropna=False)
        .agg(
            total_vouchers_paid=("total_vouchers_paid", "sum"),
            total_vouchers_pending=("total_vouchers_pending", "sum"),
            total_encumbrance_balance=("total_encumbrance_balance", "sum"),
            total_pending_retainage=("total_pending_retainage", "sum"),
            record_count=("record_count", "sum"),
            unique_suppliers=("unique_suppliers", "sum"),
            negative_paid_records=("negative_paid_records", "sum"),
            large_paid_1m_records=("large_paid_1m_records", "sum"),
            missing_po_date_records=("missing_po_date_records", "sum"),
        )
        .reset_index()
    )

    return final


def build_fiscal_year_mart() -> None:
    mart = aggregate_by_group(["fiscal_year"])
    mart = mart.sort_values("fiscal_year")
    mart.to_csv(MART_FISCAL_YEAR, index=False, encoding="utf-8")
    print(f"Created: {MART_FISCAL_YEAR}")


def build_department_mart() -> None:
    mart = aggregate_by_group(["fiscal_year", "organization_group", "department"])
    mart = mart.sort_values(
        ["fiscal_year", "total_vouchers_paid"],
        ascending=[True, False],
    )
    mart.to_csv(MART_DEPARTMENT, index=False, encoding="utf-8")
    print(f"Created: {MART_DEPARTMENT}")


def build_supplier_top_n_mart(top_n: int = 100) -> None:
    mart = aggregate_by_group(["supplier_name"])
    mart = mart.sort_values("total_vouchers_paid", ascending=False).head(top_n)
    mart.to_csv(MART_SUPPLIER_TOP_N, index=False, encoding="utf-8")
    print(f"Created: {MART_SUPPLIER_TOP_N}")


def build_pending_department_mart() -> None:
    mart = aggregate_by_group(["fiscal_year", "department"])
    mart = mart[mart["total_vouchers_pending"] != 0]
    mart = mart.sort_values(
        ["fiscal_year", "total_vouchers_pending"],
        ascending=[True, False],
    )
    mart.to_csv(MART_PENDING_DEPARTMENT, index=False, encoding="utf-8")
    print(f"Created: {MART_PENDING_DEPARTMENT}")


def build_fund_category_mart() -> None:
    mart = aggregate_by_group(["fiscal_year", "fund_type", "fund_category"])
    mart = mart.sort_values(
        ["fiscal_year", "total_vouchers_paid"],
        ascending=[True, False],
    )
    mart.to_csv(MART_FUND_CATEGORY, index=False, encoding="utf-8")
    print(f"Created: {MART_FUND_CATEGORY}")


def build_gold_marts() -> None:
    ensure_directories()

    if not SILVER_FILE.exists():
        raise FileNotFoundError(f"Silver file not found: {SILVER_FILE}")

    build_fiscal_year_mart()
    build_department_mart()
    build_supplier_top_n_mart(top_n=100)
    build_pending_department_mart()
    build_fund_category_mart()

    print("Gold mart build completed.")


if __name__ == "__main__":
    build_gold_marts()