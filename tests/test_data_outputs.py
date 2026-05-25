from pathlib import Path

import pandas as pd


ROOT_DIR = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT_DIR / "output"


def test_required_output_files_exist():
    required_files = [
        OUTPUT_DIR / "cleaning_report.json",
        OUTPUT_DIR / "cleaning_summary.csv",
        OUTPUT_DIR / "superstore_cleaned.csv",
        OUTPUT_DIR / "superstore_rejected.csv",
        OUTPUT_DIR / "superstore.db",
    ]

    for file_path in required_files:
        assert file_path.exists(), f"Missing required output file: {file_path}"


def test_cleaned_dataset_is_not_empty():
    cleaned_file = OUTPUT_DIR / "superstore_cleaned.csv"

    df = pd.read_csv(cleaned_file)

    assert len(df) > 0