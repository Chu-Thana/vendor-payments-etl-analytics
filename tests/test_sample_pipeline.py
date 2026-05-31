import pandas as pd

from scripts.pipeline.transform_silver import transform_to_silver
from scripts.pipeline.build_gold_marts import build_gold_marts
from src.config import SAMPLE_DATA_FILE, SILVER_DATA_DIR, PROCESSED_DATA_DIR


TEST_SILVER_FILE = SILVER_DATA_DIR / "vendor_payments_silver_test.csv"
TEST_GOLD_DIR = PROCESSED_DATA_DIR / "gold_test"


def test_sample_pipeline_builds_silver_and_gold_outputs():
    """
    Run the ETL pipeline on the committed sample dataset.

    This test verifies that:
    - sample input exists
    - silver output is created
    - gold mart files are created
    - required output columns exist
    """

    assert SAMPLE_DATA_FILE.exists(), f"Sample file not found: {SAMPLE_DATA_FILE}"

    transform_to_silver(
        input_file=SAMPLE_DATA_FILE,
        output_file=TEST_SILVER_FILE,
    )

    assert TEST_SILVER_FILE.exists()

    silver_df = pd.read_csv(TEST_SILVER_FILE, nrows=100)

    required_silver_columns = {
        "source_row_hash",
        "business_composite_key",
        "fiscal_year",
        "purchase_order",
        "supplier_name",
        "vouchers_paid",
        "data_as_of",
        "data_loaded_at",
        "is_negative_paid",
        "is_large_paid_1m",
    }

    assert required_silver_columns.issubset(set(silver_df.columns))

    build_gold_marts(
        silver_file=TEST_SILVER_FILE,
        gold_dir=TEST_GOLD_DIR,
    )

    expected_gold_files = [
        "mart_spending_by_fiscal_year.csv",
        "mart_spending_by_department.csv",
        "mart_spending_by_supplier_top_n.csv",
        "mart_pending_by_department.csv",
        "mart_fund_category_summary.csv",
    ]

    for file_name in expected_gold_files:
        file_path = TEST_GOLD_DIR / file_name
        assert file_path.exists(), f"Missing gold mart: {file_path}"

        df = pd.read_csv(file_path)
        assert len(df) > 0