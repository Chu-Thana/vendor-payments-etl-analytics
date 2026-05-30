from pathlib import Path
import csv
import os
from collections import Counter


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_PATH = PROJECT_ROOT / "data" / "raw" / "Vendor_Payments.csv"
REPORT_PATH = PROJECT_ROOT / "reports" / "file_structure_report.txt"


def sniff_dialect(file_path: Path, encoding: str = "utf-8-sig", sample_size: int = 1024 * 1024):
    """
    Detect delimiter, quotechar, and CSV dialect from a sample.
    """
    with open(file_path, "r", encoding=encoding, errors="replace", newline="") as f:
        sample = f.read(sample_size)

    sniffer = csv.Sniffer()

    try:
        dialect = sniffer.sniff(sample)
        has_header = sniffer.has_header(sample)
    except csv.Error:
        dialect = csv.excel
        has_header = True

    return dialect, has_header


def check_file_structure(file_path: Path, max_bad_rows_to_show: int = 20):
    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)

    # Use utf-8-sig to handle BOM if exists
    encoding = "utf-8-sig"

    dialect, has_header = sniff_dialect(file_path, encoding=encoding)

    delimiter = dialect.delimiter
    quotechar = dialect.quotechar

    total_rows = 0
    bad_rows = []
    column_count_counter = Counter()

    with open(file_path, "r", encoding=encoding, errors="replace", newline="") as f:
        reader = csv.reader(f, dialect)

        try:
            header = next(reader)
        except StopIteration:
            raise ValueError("File is empty")

        expected_col_count = len(header)
        column_names = header

        for row_number, row in enumerate(reader, start=2):
            total_rows += 1
            col_count = len(row)
            column_count_counter[col_count] += 1

            if col_count != expected_col_count:
                if len(bad_rows) < max_bad_rows_to_show:
                    bad_rows.append({
                        "row_number": row_number,
                        "expected_columns": expected_col_count,
                        "actual_columns": col_count,
                        "row_preview": row[:10],
                    })

    total_data_rows = total_rows

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(REPORT_PATH, "w", encoding="utf-8") as report:
        report.write("FILE STRUCTURE REPORT\n")
        report.write("=" * 80 + "\n\n")

        report.write(f"File path: {file_path}\n")
        report.write(f"File size: {file_size_mb:.2f} MB\n")
        report.write(f"Detected encoding used: {encoding}\n")
        report.write(f"Detected delimiter: {repr(delimiter)}\n")
        report.write(f"Detected quotechar: {repr(quotechar)}\n")
        report.write(f"Has header: {has_header}\n\n")

        report.write("HEADER\n")
        report.write("-" * 80 + "\n")
        report.write(f"Column count: {expected_col_count}\n")
        report.write("Columns:\n")
        for i, col in enumerate(column_names, start=1):
            report.write(f"{i}. {col}\n")

        report.write("\nROW COUNT\n")
        report.write("-" * 80 + "\n")
        report.write(f"Total data rows: {total_data_rows:,}\n\n")

        report.write("COLUMN COUNT CONSISTENCY\n")
        report.write("-" * 80 + "\n")
        for col_count, count in column_count_counter.most_common():
            report.write(f"{col_count} columns: {count:,} rows\n")

        report.write("\nBAD ROWS SAMPLE\n")
        report.write("-" * 80 + "\n")
        if bad_rows:
            report.write(f"Found malformed rows. Showing first {len(bad_rows)} rows:\n\n")
            for item in bad_rows:
                report.write(
                    f"Row {item['row_number']}: "
                    f"expected={item['expected_columns']}, "
                    f"actual={item['actual_columns']}, "
                    f"preview={item['row_preview']}\n"
                )
        else:
            report.write("No malformed rows found based on column count.\n")

    print(f"Done. Report saved to: {REPORT_PATH}")


if __name__ == "__main__":
    check_file_structure(DATA_PATH)