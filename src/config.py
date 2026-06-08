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

REPORTS_DIR = PROJECT_ROOT / "reports"

RAW_DATA_FILE = RAW_DATA_DIR / "Vendor_Payments.csv"

CHUNK_SIZE = 100_000


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