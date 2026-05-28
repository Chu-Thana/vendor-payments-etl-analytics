from pathlib import Path
from collections import Counter, defaultdict
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_PATH = PROJECT_ROOT / "data" / "raw" / "Vendor_Payments.csv"
REPORT_PATH = PROJECT_ROOT / "reports" / "dimension_profile_report.txt"

CHUNK_SIZE = 100_000

DIMENSION_COLUMNS = [
    "Organization Group",
    "Department",
    "Program",
    "Character",
    "Object",
    "Sub-object",
    "Fund Type",
    "Fund",
    "Fund Category",
    "Supplier & Other Non-Supplier Payees",
    "Non-Profit Indicator",
    "Purchasing Authority Description",
]

SPECIAL_VALUES = [
    "Unknown",
    "UNKNOWN",
    "Other",
    "OTHER",
    "Direct Payments",
    "N/A",
    "NA",
    "None",
    "NULL",
    "",
]


def normalize_text(value) -> str:
    if pd.isna(value):
        return "<NULL>"
    return str(value)


def stripped_text(value) -> str:
    if pd.isna(value):
        return "<NULL>"
    return str(value).strip()


def check_dimensions():
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"File not found: {DATA_PATH}")

    total_rows = 0

    value_counters = {col: Counter() for col in DIMENSION_COLUMNS}
    stripped_counters = {col: Counter() for col in DIMENSION_COLUMNS}
    lower_counters = {col: Counter() for col in DIMENSION_COLUMNS}

    null_counts = {col: 0 for col in DIMENSION_COLUMNS}
    whitespace_issue_counts = {col: 0 for col in DIMENSION_COLUMNS}
    special_value_counts = {col: Counter() for col in DIMENSION_COLUMNS}

    for chunk in pd.read_csv(
        DATA_PATH,
        chunksize=CHUNK_SIZE,
        encoding="utf-8-sig",
        low_memory=False,
    ):
        total_rows += len(chunk)

        for col in DIMENSION_COLUMNS:
            series = chunk[col]

            null_counts[col] += series.isna().sum()

            raw_text = series.map(normalize_text)
            stripped = series.map(stripped_text)
            lowered = stripped.str.lower()

            value_counters[col].update(raw_text)
            stripped_counters[col].update(stripped)
            lower_counters[col].update(lowered)

            whitespace_issue_counts[col] += (raw_text != stripped).sum()

            for special in SPECIAL_VALUES:
                special_mask = stripped == special
                count = special_mask.sum()
                if count:
                    special_value_counts[col][special] += int(count)

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(REPORT_PATH, "w", encoding="utf-8") as report:
        report.write("DIMENSION CARDINALITY & VALUE CONSISTENCY REPORT\n")
        report.write("=" * 80 + "\n\n")

        report.write(f"Data path: {DATA_PATH}\n")
        report.write(f"Total rows checked: {total_rows:,}\n")
        report.write(f"Chunk size: {CHUNK_SIZE:,}\n\n")

        report.write("DIMENSION SUMMARY\n")
        report.write("-" * 80 + "\n")

        for col in DIMENSION_COLUMNS:
            raw_unique = len(value_counters[col])
            stripped_unique = len(stripped_counters[col])
            lower_unique = len(lower_counters[col])

            null_count = null_counts[col]
            null_pct = (null_count / total_rows) * 100 if total_rows else 0

            whitespace_count = whitespace_issue_counts[col]
            whitespace_pct = (whitespace_count / total_rows) * 100 if total_rows else 0

            report.write(f"{col}\n")
            report.write(f"  raw_unique_count: {raw_unique:,}\n")
            report.write(f"  stripped_unique_count: {stripped_unique:,}\n")
            report.write(f"  lower_unique_count: {lower_unique:,}\n")
            report.write(f"  null_count: {null_count:,} ({null_pct:.4f}%)\n")
            report.write(f"  whitespace_issue_count: {whitespace_count:,} ({whitespace_pct:.4f}%)\n")

            if raw_unique != stripped_unique:
                report.write("  note: stripping whitespace reduces unique values.\n")

            if stripped_unique != lower_unique:
                report.write("  note: case normalization reduces unique values.\n")

            report.write("  special_values:\n")
            if special_value_counts[col]:
                for value, count in special_value_counts[col].most_common():
                    pct = (count / total_rows) * 100 if total_rows else 0
                    report.write(f"    - {value!r}: {count:,} ({pct:.4f}%)\n")
            else:
                report.write("    - None\n")

            report.write("  top_values:\n")
            for value, count in stripped_counters[col].most_common(15):
                pct = (count / total_rows) * 100 if total_rows else 0
                report.write(f"    - {value!r}: {count:,} ({pct:.4f}%)\n")

            report.write("\n")

        report.write("RECOMMENDED HANDLING\n")
        report.write("-" * 80 + "\n")
        report.write("Trim leading/trailing whitespace for all dimension columns.\n")
        report.write("Keep original text fields where needed, but create normalized versions for grouping.\n")
        report.write("Use Department, Fund Category, Fund Type, Character, Object, and Fiscal Year as dashboard filters.\n")
        report.write("Supplier is high-cardinality and should be searchable or top-N filtered rather than shown as a full dropdown.\n")
        report.write("Non-Profit Indicator has high missingness and should be optional, not a primary filter.\n")
        report.write("Purchasing Authority Description is useful for compliance-style analysis but may require grouping or top-N views.\n")

    print(f"Done. Report saved to: {REPORT_PATH}")


if __name__ == "__main__":
    check_dimensions()