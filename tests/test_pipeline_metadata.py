from scripts.pipeline.build_gold_marts import build_gold_marts
from scripts.pipeline.transform_silver import transform_to_silver
from src.config import (
    PROCESSED_DATA_DIR,
    SAMPLE_DATA_FILE,
    SILVER_DATA_DIR,
)


TEST_SILVER_FILE = (
    SILVER_DATA_DIR
    / "vendor_payments_silver_metadata_test.csv"
)

TEST_GOLD_DIR = (
    PROCESSED_DATA_DIR
    / "gold_metadata_test"
)


def test_sample_pipeline_returns_execution_metrics():
    silver_result = transform_to_silver(
        input_file=SAMPLE_DATA_FILE,
        output_file=TEST_SILVER_FILE,
    )

    assert silver_result["source_rows"] > 0
    assert (
        silver_result["silver_rows"]
        == silver_result["source_rows"]
    )
    assert silver_result["chunk_count"] > 0
    assert silver_result["available"] is True
    assert TEST_SILVER_FILE.exists()

    gold_result = build_gold_marts(
        silver_file=TEST_SILVER_FILE,
        gold_dir=TEST_GOLD_DIR,
    )

    assert gold_result["mart_count"] == 5
    assert len(gold_result["marts"]) == 5
    assert all(
        mart["available"]
        for mart in gold_result["marts"]
    )
    assert all(
        mart["row_count"] > 0
        for mart in gold_result["marts"]
    )