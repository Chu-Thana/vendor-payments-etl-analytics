from pathlib import Path
import argparse
import sys
import time


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PROJECT_ROOT))

from scripts.pipeline.transform_silver import transform_to_silver
from scripts.pipeline.build_gold_marts import build_gold_marts
from src.config import (
    RAW_DATA_FILE,
    SAMPLE_DATA_FILE,
    SILVER_DATA_DIR,
    GOLD_DATA_DIR,
    GOLD_SAMPLE_DATA_DIR,
)


def run_pipeline(sample: bool = False) -> None:
    """
    Run the full batch ETL pipeline:
    raw/sample CSV -> silver dataset -> gold analytics marts.
    """
    start_time = time.time()

    if sample:
        input_file = SAMPLE_DATA_FILE
        silver_output_file = SILVER_DATA_DIR / "vendor_payments_silver_sample.csv"
        gold_output_dir = GOLD_SAMPLE_DATA_DIR
        mode = "SAMPLE"
    else:
        input_file = RAW_DATA_FILE
        silver_output_file = SILVER_DATA_DIR / "vendor_payments_silver.csv"
        gold_output_dir = GOLD_DATA_DIR
        mode = "FULL"

    print("=" * 80)
    print(f"STARTING VENDOR PAYMENTS ETL PIPELINE - {mode} MODE")
    print("=" * 80)
    print(f"Input file: {input_file}")
    print(f"Silver output: {silver_output_file}")
    print(f"Gold output dir: {gold_output_dir}")

    print("\n[1/2] Transforming data to silver...")
    transform_to_silver(
        input_file=input_file,
        output_file=silver_output_file,
    )

    print("\n[2/2] Building gold marts...")
    build_gold_marts(
        silver_file=silver_output_file,
        gold_dir=gold_output_dir,
    )

    elapsed_seconds = time.time() - start_time
    elapsed_minutes = elapsed_seconds / 60

    print("\n" + "=" * 80)
    print("PIPELINE COMPLETED SUCCESSFULLY")
    print(f"Mode: {mode}")
    print(f"Elapsed time: {elapsed_seconds:.2f} seconds ({elapsed_minutes:.2f} minutes)")
    print("=" * 80)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run Vendor Payments ETL pipeline."
    )
    parser.add_argument(
        "--sample",
        action="store_true",
        help="Run pipeline using the small sample dataset.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_pipeline(sample=args.sample)