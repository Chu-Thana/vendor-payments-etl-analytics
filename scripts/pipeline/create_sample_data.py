from pathlib import Path
import sys

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PROJECT_ROOT))

from src.config import (
    RAW_DATA_FILE,
    SAMPLE_DATA_DIR,
    SILVER_STREAM_SAMPLE_DATA_FILE,
    STREAM_SAMPLE_DATA_FILE,
    STREAM_SAMPLE_ROWS,
)
from src.schema import EXPECTED_COLUMNS
from scripts.pipeline.transform_silver import transform_to_silver


SAMPLE_OUTPUT_FILE = SAMPLE_DATA_DIR / "vendor_payments_sample.csv"
SAMPLE_ROWS_PER_YEAR = 500


def create_sample_data() -> None:
    """
    Create a small representative sample dataset from the full raw dataset.

    The sample is stratified by Fiscal Year so tests and demos can cover
    multiple reporting years without using the full 3.3M-row source file.
    """
    if not RAW_DATA_FILE.exists():
        raise FileNotFoundError(f"Raw data file not found: {RAW_DATA_FILE}")

    SAMPLE_DATA_DIR.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(
        RAW_DATA_FILE,
        encoding="utf-8-sig",
        low_memory=False,
    )

    if list(df.columns) != EXPECTED_COLUMNS:
        raise ValueError("Raw schema does not match expected schema.")

    sample_df = (
        df.groupby("Fiscal Year", group_keys=False)
        .sample(n=SAMPLE_ROWS_PER_YEAR, random_state=42)
        .reset_index(drop=True)
    )

    if list(sample_df.columns) != EXPECTED_COLUMNS:
        raise ValueError("Sample schema does not match expected schema.")

    sample_df.to_csv(
        SAMPLE_OUTPUT_FILE,
        index=False,
        encoding="utf-8",
    )

    print(f"Sample data created: {SAMPLE_OUTPUT_FILE}")
    print(f"Sample rows: {len(sample_df):,}")
    print(
        f"Fiscal years: "
        f"{sample_df['Fiscal Year'].min()} - {sample_df['Fiscal Year'].max()}"
    )

def create_stream_sample_data() -> None:
    """
    Create a larger sample dataset for Kafka streaming simulation.

    This file is intended for Project 3 streaming demos. It uses the same
    raw schema as the original dataset and samples 100,000 rows from the
    full Vendor Payments raw dataset.
    """
    if not RAW_DATA_FILE.exists():
        raise FileNotFoundError(f"Raw data file not found: {RAW_DATA_FILE}")

    SAMPLE_DATA_DIR.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(
        RAW_DATA_FILE,
        encoding="utf-8-sig",
        low_memory=False,
    )

    if list(df.columns) != EXPECTED_COLUMNS:
        raise ValueError("Raw schema does not match expected schema.")

    stream_sample_size = min(STREAM_SAMPLE_ROWS, len(df))

    stream_sample_df = (
        df.sample(
            n=stream_sample_size,
            random_state=42,
            replace=False,
        )
        .reset_index(drop=True)
    )

    if list(stream_sample_df.columns) != EXPECTED_COLUMNS:
        raise ValueError("Stream sample schema does not match expected schema.")

    stream_sample_df.to_csv(
        STREAM_SAMPLE_DATA_FILE,
        index=False,
        encoding="utf-8",
    )

    print(f"Stream sample data created: {STREAM_SAMPLE_DATA_FILE}")
    print(f"Stream sample rows: {len(stream_sample_df):,}")

def create_silver_stream_sample_data() -> None:
    """
    Transform the 100,000-row raw stream sample into silver format.

    This output is intended for Project 3 Kafka streaming demos so the
    streaming pipeline consumes cleaned silver-level Vendor Payments records
    instead of raw data.
    """
    if not STREAM_SAMPLE_DATA_FILE.exists():
        raise FileNotFoundError(
            f"Stream sample data file not found: {STREAM_SAMPLE_DATA_FILE}"
        )

    transform_to_silver(
        input_file=STREAM_SAMPLE_DATA_FILE,
        output_file=SILVER_STREAM_SAMPLE_DATA_FILE,
    )

    print(f"Silver stream sample created: {SILVER_STREAM_SAMPLE_DATA_FILE}")


if __name__ == "__main__":
    create_sample_data()
    create_stream_sample_data()
    create_silver_stream_sample_data()