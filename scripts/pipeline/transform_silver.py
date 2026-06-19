from pathlib import Path
import sys

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PROJECT_ROOT))

from src.config import RAW_DATA_FILE, SILVER_DATA_DIR, CHUNK_SIZE, ensure_directories
from src.schema import (
    EXPECTED_COLUMNS,
    COLUMN_RENAME_MAP,
    AMOUNT_COLUMNS,
    DIMENSION_COLUMNS,
    BUSINESS_COMPOSITE_KEY_COLUMNS,
)
from src.cleaning import (
    clean_numeric,
    parse_timestamp,
    parse_date,
    clean_text,
    normalize_text,
    clean_contract_number,
)
from src.keys import add_source_row_hash, add_business_composite_key


SILVER_OUTPUT_FILE = SILVER_DATA_DIR / "vendor_payments_silver.csv"


LOW_RISK_FILL_UNKNOWN_COLUMNS = [
    "Department",
    "Department Code",
    "Program",
    "Program Code",
    "Fund Category",
    "Purchasing Authority Description",
]


def add_quality_flags(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add data quality and business rule flags.
    """
    df = df.copy()

    df["is_missing_department"] = df["department"].isna()
    df["is_missing_purchase_order_date"] = df["purchase_order_date"].isna()

    df["is_negative_paid"] = df["vouchers_paid"] < 0
    df["is_large_paid_1m"] = df["vouchers_paid"].abs() > 1_000_000
    df["is_large_paid_10m"] = df["vouchers_paid"].abs() > 10_000_000
    df["is_large_paid_100m"] = df["vouchers_paid"].abs() > 100_000_000
    df["is_large_paid_1b"] = df["vouchers_paid"].abs() > 1_000_000_000

    df["po_year"] = pd.to_datetime(df["purchase_order_date"], errors="coerce").dt.year
    df["po_month"] = pd.to_datetime(df["purchase_order_date"], errors="coerce").dt.to_period("M").astype("string")

    df["is_fiscal_year_mismatch"] = (
        df["purchase_order_date"].notna()
        & df["po_year"].notna()
        & (df["fiscal_year"] != df["po_year"])
    )

    df["is_non_profit"] = df["non_profit_indicator"].fillna("").str.upper().eq("X")

    return df


def transform_chunk(chunk: pd.DataFrame) -> pd.DataFrame:
    """
    Transform one raw chunk into silver format.
    """
    source_columns = list(chunk.columns)

    if source_columns != EXPECTED_COLUMNS:
        raise ValueError("Raw schema does not match expected schema.")

    df = chunk.copy()

    # Raw-level identity before renaming/cleaning
    df = add_source_row_hash(df, source_columns)
    df = add_business_composite_key(df, BUSINESS_COMPOSITE_KEY_COLUMNS)

    # Clean numeric fields
    for col in AMOUNT_COLUMNS:
        df[col] = clean_numeric(df[col])

    # Clean dates/timestamps
    df["data_as_of"] = parse_timestamp(df["data_as_of"])
    df["data_loaded_at"] = parse_timestamp(df["data_loaded_at"])
    df["Purchase Order Date"] = parse_date(df["Purchase Order Date"])

    # Fiscal year
    df["Fiscal Year"] = pd.to_numeric(df["Fiscal Year"], errors="coerce").astype("Int64")

    # Contract number as string/id
    df["Contract Number"] = clean_contract_number(df["Contract Number"])

    # Clean selected dimensions
    for col in DIMENSION_COLUMNS:
        if col in df.columns:
            fill_value = "Unknown" if col in LOW_RISK_FILL_UNKNOWN_COLUMNS else None
            df[col] = clean_text(df[col], fill_value=fill_value)

    # Also clean code columns that may be used in keys/filtering
    for col in [
        "Department Code",
        "Program Code",
        "Character Code",
        "Object Code",
        "Fund Code",
    ]:
        df[col] = clean_text(df[col], fill_value="Unknown")

    # Normalized searchable/grouping fields
    df["department_norm"] = normalize_text(df["Department"], fill_value="Unknown")
    df["supplier_name_norm"] = normalize_text(df["Supplier & Other Non-Supplier Payees"])
    df["fund_category_norm"] = normalize_text(df["Fund Category"], fill_value="Unknown")

    # Rename columns to snake_case
    df = df.rename(columns=COLUMN_RENAME_MAP)

    # Quality flags after renaming
    df = add_quality_flags(df)

    return df


def transform_to_silver(
    input_file: Path | None = None,
    output_file: Path | None = None,
) -> dict:
    ensure_directories()

    input_file = input_file or RAW_DATA_FILE
    output_file = output_file or SILVER_OUTPUT_FILE

    if not input_file.exists():
        raise FileNotFoundError(f"Raw data file not found: {input_file}")

    if output_file.exists():
        output_file.unlink()

    total_rows = 0
    total_chunks = 0

    for chunk in pd.read_csv(
        input_file,
        chunksize=CHUNK_SIZE,
        encoding="utf-8-sig",
        low_memory=False,
    ):
        total_chunks += 1
        silver_chunk = transform_chunk(chunk)
        total_rows += len(silver_chunk)

        silver_chunk.to_csv(
            output_file,
            mode="a",
            index=False,
            header=not output_file.exists(),
            encoding="utf-8",
        )

        print(f"Processed chunk {total_chunks}: {total_rows:,} rows total")

    print("Silver transformation completed.")
    print(f"Total rows processed: {total_rows:,}")
    print(f"Output file: {output_file}")

    return {
        "source_rows": total_rows,
        "silver_rows": total_rows,
        "chunk_count": total_chunks,
        "output_file": str(output_file),
        "available": output_file.exists(),
    }


if __name__ == "__main__":
    transform_to_silver()