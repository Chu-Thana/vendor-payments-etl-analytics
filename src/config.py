import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
SILVER_DATA_DIR = PROCESSED_DATA_DIR / "silver"
GOLD_DATA_DIR = PROCESSED_DATA_DIR / "gold"

SAMPLE_DATA_DIR = DATA_DIR / "sample"
SAMPLE_DATA_FILE = SAMPLE_DATA_DIR / "vendor_payments_sample.csv"
STREAM_SAMPLE_DATA_FILE = SAMPLE_DATA_DIR / "vendor_payments_stream_sample_100k.csv"
STREAM_SAMPLE_ROWS = 100_000

GOLD_SAMPLE_DATA_DIR = PROCESSED_DATA_DIR / "gold_sample"

SILVER_STREAM_SAMPLE_DATA_FILE = (
    SILVER_DATA_DIR / "vendor_payments_silver_stream_sample_100k.csv"
)

REPORTS_DIR = PROJECT_ROOT / "reports"

PIPELINE_SUMMARY_FILE = (
    REPORTS_DIR / "pipeline_summary.json"
)

SAMPLE_PIPELINE_SUMMARY_FILE = (
    REPORTS_DIR / "pipeline_summary_sample.json"
)

SILVER_VALIDATION_REPORT_FILE = (
    REPORTS_DIR / "silver_output_validation_report.txt"
)

SAMPLE_SILVER_VALIDATION_REPORT_FILE = (
    REPORTS_DIR / "silver_output_validation_report_sample.txt"
)

GOLD_VALIDATION_REPORT_FILE = (
    REPORTS_DIR / "gold_output_validation_report.txt"
)

SAMPLE_GOLD_VALIDATION_REPORT_FILE = (
    REPORTS_DIR / "gold_output_validation_report_sample.txt"
)

RAW_DATA_FILE = RAW_DATA_DIR / "Vendor_Payments.csv"

CHUNK_SIZE = 100_000

# ==================================
# Business rule thresholds
# ==================================
LARGE_PAYMENT_THRESHOLD = float(
    os.getenv("LARGE_PAYMENT_THRESHOLD", "1000000")
)

TELEGRAM_LARGE_PAYMENT_ALERT_LIMIT = int(
    os.getenv("TELEGRAM_LARGE_PAYMENT_ALERT_LIMIT", "5")
)


def ensure_directories() -> None:
    """
    Create required local output directories for processed data and reports.
    Raw data directory is expected to already contain the source CSV file.
    """
    for path in [
        PROCESSED_DATA_DIR,
        SILVER_DATA_DIR,
        GOLD_DATA_DIR,
        GOLD_SAMPLE_DATA_DIR,
        SAMPLE_DATA_DIR,
        REPORTS_DIR,
    ]:
        path.mkdir(parents=True, exist_ok=True)