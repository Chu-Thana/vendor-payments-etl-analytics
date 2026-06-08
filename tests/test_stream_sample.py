from scripts.pipeline.create_sample_data import (
    create_silver_stream_sample_data,
    create_stream_sample_data,
)
from src.config import (
    SAMPLE_DATA_DIR,
    SILVER_DATA_DIR,
    SILVER_STREAM_SAMPLE_DATA_FILE,
    STREAM_SAMPLE_DATA_FILE,
    STREAM_SAMPLE_ROWS,
)


def test_stream_sample_config_points_to_expected_file():
    assert STREAM_SAMPLE_ROWS == 100_000
    assert STREAM_SAMPLE_DATA_FILE.parent == SAMPLE_DATA_DIR
    assert STREAM_SAMPLE_DATA_FILE.name == "vendor_payments_stream_sample_100k.csv"


def test_create_stream_sample_data_function_exists():
    assert callable(create_stream_sample_data)

def test_silver_stream_sample_config_points_to_expected_file():
    assert SILVER_STREAM_SAMPLE_DATA_FILE.parent == SILVER_DATA_DIR
    assert (
        SILVER_STREAM_SAMPLE_DATA_FILE.name
        == "vendor_payments_silver_stream_sample_100k.csv"
    )


def test_create_silver_stream_sample_data_function_exists():
    assert callable(create_silver_stream_sample_data)