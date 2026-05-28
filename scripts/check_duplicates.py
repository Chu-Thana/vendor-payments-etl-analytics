from pathlib import Path
from collections import Counter
import hashlib
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_PATH = PROJECT_ROOT / "data" / "raw" / "Vendor_Payments.csv"
REPORT_PATH = PROJECT_ROOT / "reports" / "duplicate_key_report.txt"

CHUNK_SIZE = 100_000


KEY_CANDIDATES = {
    "purchase_order": [
        "Purchase Order",
    ],
    "purchase_order_supplier": [
        "Purchase Order",
        "Supplier & Other Non-Supplier Payees",
    ],
    "fiscal_year_purchase_order_supplier": [
        "Fiscal Year",
        "Purchase Order",
        "Supplier & Other Non-Supplier Payees",
    ],
    "fiscal_year_department_purchase_order_supplier": [
        "Fiscal Year",
        "Department",
        "Purchase Order",
        "Supplier & Other Non-Supplier Payees",
    ],
    "business_composite_key": [
        "Fiscal Year",
        "Department Code",
        "Program Code",
        "Character Code",
        "Object Code",
        "Sub-object Code",
        "Fund Code",
        "Purchase Order",
        "Supplier & Other Non-Supplier Payees",
        "Contract Number",
    ],
}


def normalize_value(value) -> str:
    if pd.isna(value):
        return "<NULL>"
    return str(value).strip()


def make_key(row: pd.Series, columns: list[str]) -> str:
    values = [normalize_value(row[col]) for col in columns]
    return "||".join(values)


def make_row_hash(row: pd.Series, columns: list[str]) -> str:
    values = [normalize_value(row[col]) for col in columns]
    raw = "||".join(values)
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def check_duplicates():
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"File not found: {DATA_PATH}")

    total_rows = 0
    all_columns = None

    key_counters = {
        key_name: Counter()
        for key_name in KEY_CANDIDATES
    }

    full_row_hash_counter = Counter()

    direct_payments_count = 0
    purchase_order_null_count = 0

    sample_duplicate_keys = {
        key_name: []
        for key_name in KEY_CANDIDATES
    }

    for chunk in pd.read_csv(
        DATA_PATH,
        chunksize=CHUNK_SIZE,
        encoding="utf-8-sig",
        low_memory=False,
    ):
        if all_columns is None:
            all_columns = list(chunk.columns)

        total_rows += len(chunk)

        # Purchase Order profile
        po_series = chunk["Purchase Order"].astype("string")
        direct_payments_count += (po_series.str.strip() == "Direct Payments").sum()
        purchase_order_null_count += chunk["Purchase Order"].isna().sum()

        # Candidate keys
        for key_name, columns in KEY_CANDIDATES.items():
            keys = chunk.apply(lambda row: make_key(row, columns), axis=1)
            key_counters[key_name].update(keys)

        # Full row duplicate check
        row_hashes = chunk.apply(lambda row: make_row_hash(row, all_columns), axis=1)
        full_row_hash_counter.update(row_hashes)

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(REPORT_PATH, "w", encoding="utf-8") as report:
        report.write("DUPLICATE & KEY STRATEGY REPORT\n")
        report.write("=" * 80 + "\n\n")

        report.write(f"Data path: {DATA_PATH}\n")
        report.write(f"Total rows checked: {total_rows:,}\n")
        report.write(f"Chunk size: {CHUNK_SIZE:,}\n\n")

        report.write("PURCHASE ORDER PROFILE\n")
        report.write("-" * 80 + "\n")
        report.write(f"Purchase Order null count: {purchase_order_null_count:,}\n")
        report.write(f"Purchase Order = Direct Payments count: {direct_payments_count:,}\n")
        report.write(
            f"Purchase Order = Direct Payments pct: "
            f"{(direct_payments_count / total_rows) * 100:.4f}%\n\n"
        )

        report.write("CANDIDATE KEY DUPLICATE CHECK\n")
        report.write("-" * 80 + "\n")

        for key_name, counter in key_counters.items():
            unique_count = len(counter)
            duplicate_key_count = sum(1 for _, count in counter.items() if count > 1)
            duplicate_rows = sum(count - 1 for _, count in counter.items() if count > 1)
            max_duplicate_count = max(counter.values()) if counter else 0

            uniqueness_pct = (unique_count / total_rows) * 100 if total_rows else 0
            duplicate_row_pct = (duplicate_rows / total_rows) * 100 if total_rows else 0

            report.write(f"{key_name}\n")
            report.write(f"  columns: {KEY_CANDIDATES[key_name]}\n")
            report.write(f"  unique_key_count: {unique_count:,}\n")
            report.write(f"  uniqueness_pct: {uniqueness_pct:.4f}%\n")
            report.write(f"  duplicate_key_count: {duplicate_key_count:,}\n")
            report.write(f"  duplicate_rows_beyond_first: {duplicate_rows:,}\n")
            report.write(f"  duplicate_rows_pct: {duplicate_row_pct:.4f}%\n")
            report.write(f"  max_records_per_key: {max_duplicate_count:,}\n")

            top_duplicates = [
                (key, count)
                for key, count in counter.most_common(10)
                if count > 1
            ]

            report.write("  top_duplicate_keys:\n")
            if top_duplicates:
                for key, count in top_duplicates:
                    report.write(f"    - count={count:,} | key={key[:300]}\n")
            else:
                report.write("    - None\n")

            report.write("\n")

        report.write("FULL ROW DUPLICATE CHECK\n")
        report.write("-" * 80 + "\n")
        full_row_unique_count = len(full_row_hash_counter)
        full_row_duplicate_hash_count = sum(1 for _, count in full_row_hash_counter.items() if count > 1)
        full_row_duplicate_rows = sum(count - 1 for _, count in full_row_hash_counter.items() if count > 1)

        report.write(f"unique_full_row_hash_count: {full_row_unique_count:,}\n")
        report.write(f"duplicate_full_row_hash_count: {full_row_duplicate_hash_count:,}\n")
        report.write(f"duplicate_full_rows_beyond_first: {full_row_duplicate_rows:,}\n")
        report.write(
            f"duplicate_full_rows_pct: "
            f"{(full_row_duplicate_rows / total_rows) * 100 if total_rows else 0:.4f}%\n\n"
        )

        report.write("RECOMMENDED KEY STRATEGY\n")
        report.write("-" * 80 + "\n")
        report.write("Do not use Purchase Order alone as a primary key.\n")
        report.write("Evaluate business_composite_key as the natural deduplication key.\n")
        report.write("If business_composite_key still has duplicates, use a deterministic row_hash for raw-level identity.\n")
        report.write("For silver layer, keep both source fields and generated keys:\n")
        report.write("  - source_row_hash\n")
        report.write("  - business_composite_key\n")
        report.write("  - ingestion metadata such as data_loaded_at\n")

    print(f"Done. Report saved to: {REPORT_PATH}")


if __name__ == "__main__":
    check_duplicates()