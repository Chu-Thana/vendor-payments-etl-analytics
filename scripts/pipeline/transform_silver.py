from pathlib import Path
import sys

import pandas as pd
import hashlib
import os

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
from src.recovery import (
    get_or_create_dataset_chunk,
    get_dataset_chunk_status,
    recover_stale_running_chunk,
    start_chunk_attempt,
    finish_chunk_attempt,
)


SILVER_OUTPUT_FILE = SILVER_DATA_DIR / "vendor_payments_silver.csv"
SILVER_CANDIDATE_FILE = (SILVER_DATA_DIR / "vendor_payments_silver.candidate.csv")
SILVER_CHUNK_DIR = SILVER_DATA_DIR / "chunks"

LOW_RISK_FILL_UNKNOWN_COLUMNS = [
    "Department",
    "Department Code",
    "Program",
    "Program Code",
    "Fund Category",
    "Purchasing Authority Description",
]


def validate_silver_chunk(
    silver_chunk: pd.DataFrame,
    expected_input_rows: int,
) -> dict:
    errors: list[str] = []

    actual_rows = len(silver_chunk)

    if actual_rows != expected_input_rows:
        errors.append(
            "Silver chunk row count does not match input chunk row count."
        )

    required_columns = [
        "source_row_hash",
        "business_composite_key",
        "fiscal_year",
        "department",
        "supplier_name",
        "vouchers_paid",
        "purchase_order_date",
        "po_year",
        "po_month",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in silver_chunk.columns
    ]

    if missing_columns:
        errors.append(
            "Missing required Silver columns: "
            + ", ".join(missing_columns)
        )

    null_source_hashes = 0

    if "source_row_hash" in silver_chunk.columns:
        null_source_hashes = int(
            silver_chunk["source_row_hash"]
            .isna()
            .sum()
        )

        if null_source_hashes > 0:
            errors.append(
                f"source_row_hash contains "
                f"{null_source_hashes:,} null values."
            )

    duplicate_source_hashes = 0

    if "source_row_hash" in silver_chunk.columns:
        duplicate_source_hashes = int(
            silver_chunk["source_row_hash"]
            .duplicated()
            .sum()
        )

    status = (
        "FAIL"
        if errors
        else "PASS"
    )

    return {
        "status": status,
        "row_count": actual_rows,
        "expected_input_rows": expected_input_rows,
        "null_source_hashes": null_source_hashes,
        "duplicate_source_hashes": duplicate_source_hashes,
        "errors": errors,
    }


def calculate_file_checksum(
    file_path: Path,
) -> str:
    checksum = hashlib.sha256()

    with file_path.open("rb") as file:
        for chunk in iter(
            lambda: file.read(1024 * 1024),
            b"",
        ):
            checksum.update(chunk)

    return checksum.hexdigest()


def get_silver_chunk_file(chunk_index: int) -> Path:
    return SILVER_CHUNK_DIR / f"chunk_{chunk_index:03d}.csv"


def write_silver_chunk(
    silver_chunk: pd.DataFrame,
    chunk_index: int,
) -> Path:
    SILVER_CHUNK_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    chunk_file = get_silver_chunk_file(
        chunk_index
    )

    temp_file = chunk_file.with_suffix(
        ".candidate.csv"
    )

    temp_file.unlink(
        missing_ok=True
    )

    silver_chunk.to_csv(
        temp_file,
        index=False,
        encoding="utf-8",
    )

    temp_file.replace(
        chunk_file
    )

    return chunk_file


def assemble_silver_chunks(
    chunk_files: list[Path],
    output_file: Path,
) -> int:
    output_file.unlink(
        missing_ok=True
    )

    total_rows = 0

    for chunk_number, chunk_file in enumerate(
        chunk_files,
        start=1,
    ):
        chunk_df = pd.read_csv(
            chunk_file,
            encoding="utf-8",
            low_memory=False,
        )

        total_rows += len(
            chunk_df
        )

        chunk_df.to_csv(
            output_file,
            mode="a",
            index=False,
            header=chunk_number == 1,
            encoding="utf-8",
        )

    return total_rows


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

    dataset_version_id_raw = os.getenv(
        "RECOVERY_DATASET_VERSION_ID"
    )

    if not dataset_version_id_raw:
        raise RuntimeError(
            "RECOVERY_DATASET_VERSION_ID is required "
            "for chunk recovery."
        )

    dataset_version_id = int(
        dataset_version_id_raw
    )

    input_file = input_file or RAW_DATA_FILE
    output_file = output_file or SILVER_CANDIDATE_FILE

    if not input_file.exists():
        raise FileNotFoundError(
            f"Raw data file not found: {input_file}"
        )

    SILVER_CHUNK_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    FAIL_BEFORE_CHUNK = os.getenv(
        "FAIL_BEFORE_CHUNK"
    )

    fail_before_chunk = (
        int(FAIL_BEFORE_CHUNK)
        if FAIL_BEFORE_CHUNK
        else None
    )

    total_rows = 0
    total_chunks = 0
    chunk_files: list[Path] = []

    for chunk_index, chunk in enumerate(
            pd.read_csv(
                input_file,
                chunksize=CHUNK_SIZE,
                encoding="utf-8-sig",
                low_memory=False,
            ),
            start=1,
    ):
        chunk_id = f"chunk_{chunk_index:03d}"

        source_start_row = (
                                   (chunk_index - 1) * CHUNK_SIZE
                           ) + 1

        source_end_row = (
                source_start_row
                + len(chunk)
                - 1
        )

        dataset_chunk_id = (
            get_or_create_dataset_chunk(
                dataset_version_id=dataset_version_id,
                chunk_id=chunk_id,
                chunk_index=chunk_index,
                source_start_row=source_start_row,
                source_end_row=source_end_row,
            )
        )

        chunk_file = get_silver_chunk_file(
            chunk_index
        )

        chunk_status = get_dataset_chunk_status(
            dataset_chunk_id
        )

        if (
                chunk_status == "VALIDATED"
                and chunk_file.exists()
        ):
            chunk_rows = len(chunk)

            total_rows += chunk_rows
            total_chunks += 1

            chunk_files.append(
                chunk_file
            )

            print(
                f"Skipped {chunk_id}: "
                "already VALIDATED"
            )

            continue

        if (
                fail_before_chunk is not None
                and chunk_index == fail_before_chunk
        ):
            raise RuntimeError(
                f"Controlled failure before chunk_{chunk_index:03d}"
            )

        stale_after_seconds = int(
            os.getenv(
                "CHUNK_STALE_AFTER_SECONDS",
                "900",
            )
        )

        recovered_execution_id = (
            recover_stale_running_chunk(
                dataset_chunk_id,
                stale_after_seconds=stale_after_seconds,
            )
        )

        if recovered_execution_id is not None:
            print(
                f"Recovered stale RUNNING attempt "
                f"for {chunk_id}: "
                f"execution_id={recovered_execution_id}"
            )

        chunk_execution_id = (
            start_chunk_attempt(
                dataset_chunk_id
            )
        )

        try:
            silver_chunk = transform_chunk(
                chunk
            )

            validation_result = (
                validate_silver_chunk(
                    silver_chunk,
                    expected_input_rows=len(chunk),
                )
            )

            if (
                    validation_result["status"]
                    == "FAIL"
            ):
                raise RuntimeError(
                    "Chunk validation failed for "
                    f"{chunk_id}: "
                    + "; ".join(
                        validation_result["errors"]
                    )
                )

            chunk_file = write_silver_chunk(
                silver_chunk,
                chunk_index,
            )

            chunk_row_count = len(
                silver_chunk
            )

            checksum = calculate_file_checksum(
                chunk_file
            )

            finish_chunk_attempt(
                chunk_execution_id=chunk_execution_id,
                success=True,
                row_count=chunk_row_count,
                checksum=checksum,
                error_message=None,
            )

            total_rows += chunk_row_count
            total_chunks += 1

            chunk_files.append(
                chunk_file
            )

            print(
                f"Processed {chunk_id}: "
                f"{chunk_row_count:,} rows "
                f"[validation={validation_result['status']}]"
            )

        except Exception as exc:
            finish_chunk_attempt(
                chunk_execution_id=chunk_execution_id,
                success=False,
                error_message=str(exc),
            )

            raise

    if total_rows == 0:
        raise ValueError(
            "Silver transformation produced zero rows."
        )

    missing_chunk_files = [
        chunk_file
        for chunk_file in chunk_files
        if not chunk_file.exists()
    ]

    if missing_chunk_files:
        raise RuntimeError(
            "Missing Silver chunk files: "
            + ", ".join(
                str(file)
                for file in missing_chunk_files
            )
        )

    assembled_rows = assemble_silver_chunks(
        chunk_files,
        output_file,
    )

    if assembled_rows != total_rows:
        raise RuntimeError(
            "Assembled Silver row count "
            "does not match processed row count."
        )

    print(
        "Silver transformation completed."
    )

    print(
        f"Total rows processed: {total_rows:,}"
    )

    print(
        f"Chunk count: {total_chunks}"
    )

    print(
        f"Candidate file: {output_file}"
    )

    return {
        "source_rows": total_rows,
        "silver_rows": total_rows,
        "chunk_count": total_chunks,
        "output_file": str(output_file),
        "available": output_file.exists(),
    }


if __name__ == "__main__":
    transform_to_silver()