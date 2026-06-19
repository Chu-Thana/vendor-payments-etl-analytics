from pathlib import Path
import sys

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PROJECT_ROOT))

from src.config import (
    CHUNK_SIZE,
    GOLD_DATA_DIR,
    SILVER_DATA_DIR,
    ensure_directories,
)


SILVER_FILE = SILVER_DATA_DIR / "vendor_payments_silver.csv"

MART_FISCAL_YEAR = (
    GOLD_DATA_DIR / "mart_spending_by_fiscal_year.csv"
)
MART_DEPARTMENT = (
    GOLD_DATA_DIR / "mart_spending_by_department.csv"
)
MART_SUPPLIER_TOP_N = (
    GOLD_DATA_DIR / "mart_spending_by_supplier_top_n.csv"
)
MART_PENDING_DEPARTMENT = (
    GOLD_DATA_DIR / "mart_pending_by_department.csv"
)
MART_FUND_CATEGORY = (
    GOLD_DATA_DIR / "mart_fund_category_summary.csv"
)


def aggregate_by_group(
    group_cols: list[str],
    silver_file: Path = SILVER_FILE,
) -> pd.DataFrame:
    """
    Aggregate silver data by selected group columns
    using chunk processing.
    """
    result_parts = []

    for chunk in pd.read_csv(
        silver_file,
        chunksize=CHUNK_SIZE,
        encoding="utf-8",
        low_memory=False,
    ):
        grouped = (
            chunk.groupby(group_cols, dropna=False)
            .agg(
                total_vouchers_paid=(
                    "vouchers_paid",
                    "sum",
                ),
                total_vouchers_pending=(
                    "vouchers_pending",
                    "sum",
                ),
                total_encumbrance_balance=(
                    "encumbrance_balance",
                    "sum",
                ),
                total_pending_retainage=(
                    "vouchers_pending_retainage",
                    "sum",
                ),
                record_count=(
                    "source_row_hash",
                    "count",
                ),
                unique_suppliers=(
                    "supplier_name",
                    "nunique",
                ),
                negative_paid_records=(
                    "is_negative_paid",
                    "sum",
                ),
                large_paid_1m_records=(
                    "is_large_paid_1m",
                    "sum",
                ),
                missing_po_date_records=(
                    "is_missing_purchase_order_date",
                    "sum",
                ),
            )
            .reset_index()
        )

        result_parts.append(grouped)

    combined = pd.concat(
        result_parts,
        ignore_index=True,
    )

    return (
        combined.groupby(
            group_cols,
            dropna=False,
        )
        .agg(
            total_vouchers_paid=(
                "total_vouchers_paid",
                "sum",
            ),
            total_vouchers_pending=(
                "total_vouchers_pending",
                "sum",
            ),
            total_encumbrance_balance=(
                "total_encumbrance_balance",
                "sum",
            ),
            total_pending_retainage=(
                "total_pending_retainage",
                "sum",
            ),
            record_count=(
                "record_count",
                "sum",
            ),
            unique_suppliers=(
                "unique_suppliers",
                "sum",
            ),
            negative_paid_records=(
                "negative_paid_records",
                "sum",
            ),
            large_paid_1m_records=(
                "large_paid_1m_records",
                "sum",
            ),
            missing_po_date_records=(
                "missing_po_date_records",
                "sum",
            ),
        )
        .reset_index()
    )


def build_mart(
    *,
    name: str,
    group_cols: list[str],
    output_file: Path,
    silver_file: Path = SILVER_FILE,
    sort_columns: list[str] | None = None,
    ascending: list[bool] | bool = True,
    top_n: int | None = None,
    nonzero_filter_column: str | None = None,
) -> dict:
    """
    Build one Gold mart, write it to CSV,
    and return structured execution metadata.
    """
    mart = aggregate_by_group(
        group_cols=group_cols,
        silver_file=silver_file,
    )

    if nonzero_filter_column is not None:
        mart = mart[
            mart[nonzero_filter_column] != 0
        ]

    if sort_columns:
        mart = mart.sort_values(
            sort_columns,
            ascending=ascending,
        )

    if top_n is not None:
        mart = mart.head(top_n)

    output_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    mart.to_csv(
        output_file,
        index=False,
        encoding="utf-8",
    )

    print(f"Created: {output_file}")

    return {
        "name": name,
        "row_count": len(mart),
        "output_file": str(output_file),
        "available": output_file.exists(),
    }


def build_fiscal_year_mart(
    silver_file: Path = SILVER_FILE,
    output_file: Path = MART_FISCAL_YEAR,
) -> dict:
    return build_mart(
        name="mart_spending_by_fiscal_year",
        group_cols=["fiscal_year"],
        output_file=output_file,
        silver_file=silver_file,
        sort_columns=["fiscal_year"],
    )


def build_department_mart(
    silver_file: Path = SILVER_FILE,
    output_file: Path = MART_DEPARTMENT,
) -> dict:
    return build_mart(
        name="mart_spending_by_department",
        group_cols=[
            "fiscal_year",
            "organization_group",
            "department",
        ],
        output_file=output_file,
        silver_file=silver_file,
        sort_columns=[
            "fiscal_year",
            "total_vouchers_paid",
        ],
        ascending=[True, False],
    )


def build_supplier_top_n_mart(
    silver_file: Path = SILVER_FILE,
    output_file: Path = MART_SUPPLIER_TOP_N,
    top_n: int = 100,
) -> dict:
    return build_mart(
        name="mart_spending_by_supplier_top_n",
        group_cols=["supplier_name"],
        output_file=output_file,
        silver_file=silver_file,
        sort_columns=["total_vouchers_paid"],
        ascending=False,
        top_n=top_n,
    )


def build_pending_department_mart(
    silver_file: Path = SILVER_FILE,
    output_file: Path = MART_PENDING_DEPARTMENT,
) -> dict:
    return build_mart(
        name="mart_pending_by_department",
        group_cols=[
            "fiscal_year",
            "department",
        ],
        output_file=output_file,
        silver_file=silver_file,
        sort_columns=[
            "fiscal_year",
            "total_vouchers_pending",
        ],
        ascending=[True, False],
        nonzero_filter_column=(
            "total_vouchers_pending"
        ),
    )


def build_fund_category_mart(
    silver_file: Path = SILVER_FILE,
    output_file: Path = MART_FUND_CATEGORY,
) -> dict:
    return build_mart(
        name="mart_fund_category_summary",
        group_cols=[
            "fiscal_year",
            "fund_type",
            "fund_category",
        ],
        output_file=output_file,
        silver_file=silver_file,
        sort_columns=[
            "fiscal_year",
            "total_vouchers_paid",
        ],
        ascending=[True, False],
    )


def build_gold_marts(
    silver_file: Path = SILVER_FILE,
    gold_dir: Path = GOLD_DATA_DIR,
) -> dict:
    ensure_directories()

    if not silver_file.exists():
        raise FileNotFoundError(
            f"Silver file not found: {silver_file}"
        )

    gold_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    mart_results = [
        build_fiscal_year_mart(
            silver_file=silver_file,
            output_file=(
                gold_dir
                / "mart_spending_by_fiscal_year.csv"
            ),
        ),
        build_department_mart(
            silver_file=silver_file,
            output_file=(
                gold_dir
                / "mart_spending_by_department.csv"
            ),
        ),
        build_supplier_top_n_mart(
            silver_file=silver_file,
            output_file=(
                gold_dir
                / "mart_spending_by_supplier_top_n.csv"
            ),
        ),
        build_pending_department_mart(
            silver_file=silver_file,
            output_file=(
                gold_dir
                / "mart_pending_by_department.csv"
            ),
        ),
        build_fund_category_mart(
            silver_file=silver_file,
            output_file=(
                gold_dir
                / "mart_fund_category_summary.csv"
            ),
        ),
    ]

    print("Gold mart build completed.")

    return {
        "mart_count": len(mart_results),
        "marts": mart_results,
    }


if __name__ == "__main__":
    build_gold_marts()

