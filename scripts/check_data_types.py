from pathlib import Path
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_PATH = PROJECT_ROOT / "data" / "raw" / "Vendor_Payments.csv"
REPORT_PATH = PROJECT_ROOT / "reports" / "data_type_parsing_report.txt"

CHUNK_SIZE = 100_000

NUMERIC_COLUMNS = [
    "Vouchers Paid",
    "Vouchers Pending",
    "Encumbrance Balance",
    "Vouchers Pending Retainage",
]

DATE_COLUMNS = [
    "data_as_of",
    "data_loaded_at",
    "Purchase Order Date",
]

CRITICAL_COLUMNS = [
    "Fiscal Year",
    "Department",
    "Purchase Order",
    "Supplier & Other Non-Supplier Payees",
    "Vouchers Paid",
    "data_as_of",
    "data_loaded_at",
    "Purchase Order Date",
]


def clean_numeric(series: pd.Series) -> pd.Series:
    """
    Convert numeric-like text into numbers.
    Handles commas, dollar signs, blanks, and parentheses negatives.
    Example:
      "$1,234.50" -> 1234.50
      "(123.45)" -> -123.45
    """
    s = series.astype("string").str.strip()

    s = s.str.replace(",", "", regex=False)
    s = s.str.replace("$", "", regex=False)

    # Convert accounting-style negative numbers: (123.45) -> -123.45
    s = s.str.replace(r"^\((.*)\)$", r"-\1", regex=True)

    return pd.to_numeric(s, errors="coerce")


def check_data_types():
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"File not found: {DATA_PATH}")

    total_rows = 0

    numeric_invalid_counts = {col: 0 for col in NUMERIC_COLUMNS}
    numeric_null_counts = {col: 0 for col in NUMERIC_COLUMNS}
    numeric_min = {col: None for col in NUMERIC_COLUMNS}
    numeric_max = {col: None for col in NUMERIC_COLUMNS}

    date_invalid_counts = {col: 0 for col in DATE_COLUMNS}
    date_null_counts = {col: 0 for col in DATE_COLUMNS}
    date_min = {col: None for col in DATE_COLUMNS}
    date_max = {col: None for col in DATE_COLUMNS}

    critical_null_counts = {col: 0 for col in CRITICAL_COLUMNS}

    fiscal_year_invalid_count = 0
    fiscal_year_min = None
    fiscal_year_max = None

    contract_number_null_count = 0
    contract_number_float_like_count = 0

    for chunk in pd.read_csv(
        DATA_PATH,
        chunksize=CHUNK_SIZE,
        encoding="utf-8-sig",
        low_memory=False,
    ):
        total_rows += len(chunk)

        # Critical null check
        for col in CRITICAL_COLUMNS:
            critical_null_counts[col] += chunk[col].isna().sum()

        # Numeric parsing check
        for col in NUMERIC_COLUMNS:
            original = chunk[col]
            parsed = clean_numeric(original)

            original_non_null = original.notna()
            invalid_mask = original_non_null & parsed.isna()

            numeric_invalid_counts[col] += invalid_mask.sum()
            numeric_null_counts[col] += original.isna().sum()

            valid_values = parsed.dropna()
            if not valid_values.empty:
                current_min = valid_values.min()
                current_max = valid_values.max()

                numeric_min[col] = current_min if numeric_min[col] is None else min(numeric_min[col], current_min)
                numeric_max[col] = current_max if numeric_max[col] is None else max(numeric_max[col], current_max)

        # Date parsing check
        for col in DATE_COLUMNS:
            original = chunk[col]
            parsed = pd.to_datetime(original, errors="coerce")

            original_non_null = original.notna()
            invalid_mask = original_non_null & parsed.isna()

            date_invalid_counts[col] += invalid_mask.sum()
            date_null_counts[col] += original.isna().sum()

            valid_dates = parsed.dropna()
            if not valid_dates.empty:
                current_min = valid_dates.min()
                current_max = valid_dates.max()

                date_min[col] = current_min if date_min[col] is None else min(date_min[col], current_min)
                date_max[col] = current_max if date_max[col] is None else max(date_max[col], current_max)

        # Fiscal year check
        fiscal_year = pd.to_numeric(chunk["Fiscal Year"], errors="coerce")
        fiscal_year_invalid_count += chunk["Fiscal Year"].notna().sum() - fiscal_year.notna().sum()

        valid_years = fiscal_year.dropna()
        if not valid_years.empty:
            current_min = int(valid_years.min())
            current_max = int(valid_years.max())

            fiscal_year_min = current_min if fiscal_year_min is None else min(fiscal_year_min, current_min)
            fiscal_year_max = current_max if fiscal_year_max is None else max(fiscal_year_max, current_max)

        # Contract Number check
        contract_raw = chunk["Contract Number"]
        contract_number_null_count += contract_raw.isna().sum()

        contract_as_text = contract_raw.dropna().astype("string")
        contract_number_float_like_count += contract_as_text.str.endswith(".0").sum()

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(REPORT_PATH, "w", encoding="utf-8") as report:
        report.write("DATA TYPE & PARSING REPORT\n")
        report.write("=" * 80 + "\n\n")

        report.write(f"Data path: {DATA_PATH}\n")
        report.write(f"Total rows checked: {total_rows:,}\n")
        report.write(f"Chunk size: {CHUNK_SIZE:,}\n\n")

        report.write("NUMERIC PARSING CHECK\n")
        report.write("-" * 80 + "\n")
        for col in NUMERIC_COLUMNS:
            report.write(f"{col}\n")
            report.write(f"  null_count: {numeric_null_counts[col]:,}\n")
            report.write(f"  invalid_numeric_count: {numeric_invalid_counts[col]:,}\n")
            report.write(f"  min: {numeric_min[col]}\n")
            report.write(f"  max: {numeric_max[col]}\n\n")

        report.write("DATE PARSING CHECK\n")
        report.write("-" * 80 + "\n")
        for col in DATE_COLUMNS:
            report.write(f"{col}\n")
            report.write(f"  null_count: {date_null_counts[col]:,}\n")
            report.write(f"  invalid_date_count: {date_invalid_counts[col]:,}\n")
            report.write(f"  min: {date_min[col]}\n")
            report.write(f"  max: {date_max[col]}\n\n")

        report.write("FISCAL YEAR CHECK\n")
        report.write("-" * 80 + "\n")
        report.write(f"invalid_fiscal_year_count: {fiscal_year_invalid_count:,}\n")
        report.write(f"min_fiscal_year: {fiscal_year_min}\n")
        report.write(f"max_fiscal_year: {fiscal_year_max}\n\n")

        report.write("CONTRACT NUMBER CHECK\n")
        report.write("-" * 80 + "\n")
        report.write(f"null_count: {contract_number_null_count:,}\n")
        report.write(f"float_like_values_ending_with_dot_zero: {contract_number_float_like_count:,}\n")
        report.write("note: Contract Number should be treated as string/id in the silver layer.\n\n")

        report.write("CRITICAL COLUMN NULL CHECK\n")
        report.write("-" * 80 + "\n")
        for col in CRITICAL_COLUMNS:
            null_count = critical_null_counts[col]
            null_pct = (null_count / total_rows) * 100 if total_rows else 0
            report.write(f"{col}: {null_count:,} nulls ({null_pct:.4f}%)\n")

    print(f"Done. Report saved to: {REPORT_PATH}")


if __name__ == "__main__":
    check_data_types()