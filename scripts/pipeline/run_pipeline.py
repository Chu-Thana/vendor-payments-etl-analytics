from pathlib import Path
import argparse
import json
import sys
import time
from datetime import datetime, timezone

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PROJECT_ROOT))

from scripts.pipeline.transform_silver import transform_to_silver
from scripts.pipeline.build_gold_marts import build_gold_marts
from scripts.checks.check_silver_output import check_silver_output
from scripts.checks.check_gold_outputs import check_gold_outputs
from src.config import (
    RAW_DATA_FILE,
    SAMPLE_DATA_FILE,
    SILVER_DATA_DIR,
    GOLD_DATA_DIR,
    GOLD_SAMPLE_DATA_DIR,
    CHUNK_SIZE,
    PIPELINE_SUMMARY_FILE,
    SAMPLE_PIPELINE_SUMMARY_FILE,
    SILVER_VALIDATION_REPORT_FILE,
    SAMPLE_SILVER_VALIDATION_REPORT_FILE,
    GOLD_VALIDATION_REPORT_FILE,
    SAMPLE_GOLD_VALIDATION_REPORT_FILE,
)


def write_pipeline_summary(
    summary: dict,
    output_file: Path,
) -> None:
    output_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_file.write_text(
        json.dumps(
            summary,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print(f"Pipeline summary saved to: {output_file}")


def run_pipeline(sample: bool = False) -> None:
    """
    Run the full batch ETL pipeline:
    raw/sample CSV -> silver dataset -> gold analytics marts.
    """
    start_time = time.time()

    if sample:
        input_file = SAMPLE_DATA_FILE
        silver_output_file = (
            SILVER_DATA_DIR
            / "vendor_payments_silver_sample.csv"
        )
        gold_output_dir = GOLD_SAMPLE_DATA_DIR
        pipeline_summary_file = (
            SAMPLE_PIPELINE_SUMMARY_FILE
        )
        silver_validation_report_file = (
            SAMPLE_SILVER_VALIDATION_REPORT_FILE
        )
        gold_validation_report_file = (
            SAMPLE_GOLD_VALIDATION_REPORT_FILE
        )
        mode = "SAMPLE"
    else:
        input_file = RAW_DATA_FILE
        silver_output_file = (
                SILVER_DATA_DIR
                / "vendor_payments_silver.csv"
        )
        gold_output_dir = GOLD_DATA_DIR
        pipeline_summary_file = PIPELINE_SUMMARY_FILE
        silver_validation_report_file = (
            SILVER_VALIDATION_REPORT_FILE
        )
        gold_validation_report_file = (
            GOLD_VALIDATION_REPORT_FILE
        )
        mode = "FULL"

    print("=" * 80)
    print(f"STARTING VENDOR PAYMENTS ETL PIPELINE - {mode} MODE")
    print("=" * 80)
    print(f"Input file: {input_file}")
    print(f"Silver output: {silver_output_file}")
    print(f"Gold output dir: {gold_output_dir}")

    print("\n[1/4] Transforming data to silver...")
    silver_result = transform_to_silver(
        input_file=input_file,
        output_file=silver_output_file,
    )

    print("\n[2/4] Building gold marts...")
    gold_result = build_gold_marts(
        silver_file=silver_output_file,
        gold_dir=gold_output_dir,
    )

    print("\n[3/4] Validating silver output...")
    silver_validation_result = check_silver_output(
        silver_file=silver_output_file,
        report_path=silver_validation_report_file,
    )

    print("\n[4/4] Validating gold outputs...")
    gold_validation_result = check_gold_outputs(
        gold_dir=gold_output_dir,
        report_path=gold_validation_report_file,
    )

    elapsed_seconds = time.time() - start_time
    elapsed_minutes = elapsed_seconds / 60

    pipeline_status = (
        "success"
        if silver_validation_result["status"] == "PASS"
           and gold_validation_result["status"] == "PASS"
        else "success_with_warnings"
    )

    summary = {
        "project": "Vendor Payments Batch ETL",
        "pipeline_version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "status": pipeline_status,
        "runtime_seconds": round(elapsed_seconds, 2),
        "configuration": {
            "chunk_size": CHUNK_SIZE,
        },
        "source": {
            "file": str(input_file),
            "row_count": silver_result["source_rows"],
            "available": input_file.exists(),
        },
        "silver": {
            "file": silver_result["output_file"],
            "row_count": silver_result["silver_rows"],
            "chunk_count": silver_result["chunk_count"],
            "available": silver_result["available"],
        },
        "gold": gold_result,
        "validation": {
            "silver": silver_validation_result,
            "gold": gold_validation_result,
        },
    }

    write_pipeline_summary(
        summary=summary,
        output_file=pipeline_summary_file,
    )

    print("\n" + "=" * 80)
    print("PIPELINE COMPLETED SUCCESSFULLY")
    print(f"Mode: {mode}")
    print(f"Status: {pipeline_status}")
    print(
        f"Elapsed time: {elapsed_seconds:.2f} seconds "
        f"({elapsed_minutes:.2f} minutes)"
    )


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