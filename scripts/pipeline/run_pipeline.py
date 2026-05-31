from pathlib import Path
import sys
import time


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PROJECT_ROOT))

from scripts.pipeline.transform_silver import transform_to_silver
from scripts.pipeline.build_gold_marts import build_gold_marts


def run_pipeline() -> None:
    """
    Run the full batch ETL pipeline:
    raw CSV -> silver dataset -> gold analytics marts.
    """
    start_time = time.time()

    print("=" * 80)
    print("STARTING VENDOR PAYMENTS ETL PIPELINE")
    print("=" * 80)

    print("\n[1/2] Transforming raw data to silver...")
    transform_to_silver()

    print("\n[2/2] Building gold marts...")
    build_gold_marts()

    elapsed_seconds = time.time() - start_time
    elapsed_minutes = elapsed_seconds / 60

    print("\n" + "=" * 80)
    print("PIPELINE COMPLETED SUCCESSFULLY")
    print(f"Elapsed time: {elapsed_seconds:.2f} seconds ({elapsed_minutes:.2f} minutes)")
    print("=" * 80)


if __name__ == "__main__":
    run_pipeline()