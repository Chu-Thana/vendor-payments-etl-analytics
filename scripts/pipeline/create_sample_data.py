from pathlib import Path
import sys

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PROJECT_ROOT))

from src.config import RAW_DATA_FILE, SAMPLE_DATA_DIR
from src.schema import EXPECTED_COLUMNS


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


if __name__ == "__main__":
    create_sample_data()