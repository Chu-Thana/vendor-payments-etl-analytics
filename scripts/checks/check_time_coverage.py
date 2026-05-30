from pathlib import Path
from collections import Counter
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_PATH = PROJECT_ROOT / "data" / "raw" / "Vendor_Payments.csv"
REPORT_PATH = PROJECT_ROOT / "reports" / "time_coverage_report.txt"

CHUNK_SIZE = 100_000


def parse_data_as_of(series: pd.Series) -> pd.Series:
    return pd.to_datetime(
        series,
        format="%Y/%m/%d %I:%M:%S %p",
        errors="coerce",
    )


def parse_data_loaded_at(series: pd.Series) -> pd.Series:
    return pd.to_datetime(
        series,
        format="%Y/%m/%d %I:%M:%S %p",
        errors="coerce",
    )


def parse_purchase_order_date(series: pd.Series) -> pd.Series:
    return pd.to_datetime(
        series,
        format="%Y/%m/%d",
        errors="coerce",
    )


def update_min(current, candidate):
    if pd.isna(candidate):
        return current
    if current is None:
        return candidate
    return min(current, candidate)


def update_max(current, candidate):
    if pd.isna(candidate):
        return current
    if current is None:
        return candidate
    return max(current, candidate)


def check_time_coverage():
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"File not found: {DATA_PATH}")

    total_rows = 0

    fiscal_year_counter = Counter()
    purchase_order_year_counter = Counter()
    purchase_order_month_counter = Counter()
    data_as_of_year_counter = Counter()
    data_as_of_month_counter = Counter()
    data_loaded_at_counter = Counter()

    fiscal_year_min = None
    fiscal_year_max = None

    po_date_min = None
    po_date_max = None
    data_as_of_min = None
    data_as_of_max = None
    data_loaded_at_min = None
    data_loaded_at_max = None

    po_date_null_count = 0
    po_date_valid_count = 0

    data_as_of_invalid_count = 0
    data_loaded_at_invalid_count = 0
    po_date_invalid_count = 0

    fiscal_year_vs_data_as_of_year_mismatch = 0

    for chunk in pd.read_csv(
        DATA_PATH,
        chunksize=CHUNK_SIZE,
        encoding="utf-8-sig",
        low_memory=False,
    ):
        total_rows += len(chunk)

        fiscal_year = pd.to_numeric(chunk["Fiscal Year"], errors="coerce")
        po_date = parse_purchase_order_date(chunk["Purchase Order Date"])
        data_as_of = parse_data_as_of(chunk["data_as_of"])
        data_loaded_at = parse_data_loaded_at(chunk["data_loaded_at"])

        # Invalid date counts
        data_as_of_invalid_count += chunk["data_as_of"].notna().sum() - data_as_of.notna().sum()
        data_loaded_at_invalid_count += chunk["data_loaded_at"].notna().sum() - data_loaded_at.notna().sum()
        po_date_invalid_count += chunk["Purchase Order Date"].notna().sum() - po_date.notna().sum()

        # Null / valid PO date
        po_date_null_count += chunk["Purchase Order Date"].isna().sum()
        po_date_valid_count += po_date.notna().sum()

        # Fiscal year distribution
        for year, count in fiscal_year.value_counts(dropna=False).items():
            fiscal_year_counter[str(year)] += int(count)

        valid_fiscal_year = fiscal_year.dropna()
        if not valid_fiscal_year.empty:
            current_min = int(valid_fiscal_year.min())
            current_max = int(valid_fiscal_year.max())
            fiscal_year_min = current_min if fiscal_year_min is None else min(fiscal_year_min, current_min)
            fiscal_year_max = current_max if fiscal_year_max is None else max(fiscal_year_max, current_max)

        # Purchase order date min/max and distribution
        valid_po_date = po_date.dropna()
        if not valid_po_date.empty:
            po_date_min = update_min(po_date_min, valid_po_date.min())
            po_date_max = update_max(po_date_max, valid_po_date.max())

            po_years = valid_po_date.dt.year
            po_months = valid_po_date.dt.to_period("M").astype(str)

            purchase_order_year_counter.update(po_years.astype(str).tolist())
            purchase_order_month_counter.update(po_months.tolist())

        # data_as_of min/max and distribution
        valid_data_as_of = data_as_of.dropna()
        if not valid_data_as_of.empty:
            data_as_of_min = update_min(data_as_of_min, valid_data_as_of.min())
            data_as_of_max = update_max(data_as_of_max, valid_data_as_of.max())

            as_of_years = valid_data_as_of.dt.year
            as_of_months = valid_data_as_of.dt.to_period("M").astype(str)

            data_as_of_year_counter.update(as_of_years.astype(str).tolist())
            data_as_of_month_counter.update(as_of_months.tolist())

        # data_loaded_at min/max and exact timestamps
        valid_loaded_at = data_loaded_at.dropna()
        if not valid_loaded_at.empty:
            data_loaded_at_min = update_min(data_loaded_at_min, valid_loaded_at.min())
            data_loaded_at_max = update_max(data_loaded_at_max, valid_loaded_at.max())

            loaded_at_text = valid_loaded_at.astype(str)
            data_loaded_at_counter.update(loaded_at_text.tolist())

        # Fiscal year vs data_as_of year
        data_as_of_year = data_as_of.dt.year
        mismatch_mask = fiscal_year.notna() & data_as_of_year.notna() & (fiscal_year != data_as_of_year)
        fiscal_year_vs_data_as_of_year_mismatch += mismatch_mask.sum()

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(REPORT_PATH, "w", encoding="utf-8") as report:
        report.write("TIME COVERAGE & FRESHNESS REPORT\n")
        report.write("=" * 80 + "\n\n")

        report.write(f"Data path: {DATA_PATH}\n")
        report.write(f"Total rows checked: {total_rows:,}\n")
        report.write(f"Chunk size: {CHUNK_SIZE:,}\n\n")

        report.write("DATE PARSING QUALITY\n")
        report.write("-" * 80 + "\n")
        report.write(f"data_as_of invalid count: {data_as_of_invalid_count:,}\n")
        report.write(f"data_loaded_at invalid count: {data_loaded_at_invalid_count:,}\n")
        report.write(f"Purchase Order Date invalid count: {po_date_invalid_count:,}\n")
        report.write(f"Purchase Order Date null count: {po_date_null_count:,}\n")
        report.write(f"Purchase Order Date valid count: {po_date_valid_count:,}\n")
        report.write(f"Purchase Order Date valid pct: {(po_date_valid_count / total_rows) * 100:.4f}%\n\n")

        report.write("DATE RANGE SUMMARY\n")
        report.write("-" * 80 + "\n")
        report.write(f"Fiscal Year min: {fiscal_year_min}\n")
        report.write(f"Fiscal Year max: {fiscal_year_max}\n")
        report.write(f"Purchase Order Date min: {po_date_min}\n")
        report.write(f"Purchase Order Date max: {po_date_max}\n")
        report.write(f"data_as_of min: {data_as_of_min}\n")
        report.write(f"data_as_of max: {data_as_of_max}\n")
        report.write(f"data_loaded_at min: {data_loaded_at_min}\n")
        report.write(f"data_loaded_at max: {data_loaded_at_max}\n\n")

        report.write("FRESHNESS CHECK\n")
        report.write("-" * 80 + "\n")
        report.write(f"Unique data_loaded_at timestamps: {len(data_loaded_at_counter):,}\n")
        report.write("Top data_loaded_at values:\n")
        for value, count in data_loaded_at_counter.most_common(10):
            pct = (count / total_rows) * 100 if total_rows else 0
            report.write(f"  - {value}: {count:,} ({pct:.4f}%)\n")

        report.write("\nFISCAL YEAR DISTRIBUTION\n")
        report.write("-" * 80 + "\n")
        for year, count in sorted(fiscal_year_counter.items(), key=lambda x: str(x[0])):
            pct = (count / total_rows) * 100 if total_rows else 0
            report.write(f"{year}: {count:,} ({pct:.4f}%)\n")

        report.write("\nPURCHASE ORDER YEAR DISTRIBUTION\n")
        report.write("-" * 80 + "\n")
        for year, count in sorted(purchase_order_year_counter.items(), key=lambda x: str(x[0])):
            pct = (count / po_date_valid_count) * 100 if po_date_valid_count else 0
            report.write(f"{year}: {count:,} ({pct:.4f}% of valid PO dates)\n")

        report.write("\nDATA_AS_OF YEAR DISTRIBUTION\n")
        report.write("-" * 80 + "\n")
        for year, count in sorted(data_as_of_year_counter.items(), key=lambda x: str(x[0])):
            pct = (count / total_rows) * 100 if total_rows else 0
            report.write(f"{year}: {count:,} ({pct:.4f}%)\n")

        report.write("\nTOP PURCHASE ORDER MONTHS\n")
        report.write("-" * 80 + "\n")
        for month, count in purchase_order_month_counter.most_common(20):
            pct = (count / po_date_valid_count) * 100 if po_date_valid_count else 0
            report.write(f"{month}: {count:,} ({pct:.4f}% of valid PO dates)\n")

        report.write("\nTOP DATA_AS_OF MONTHS\n")
        report.write("-" * 80 + "\n")
        for month, count in data_as_of_month_counter.most_common(20):
            pct = (count / total_rows) * 100 if total_rows else 0
            report.write(f"{month}: {count:,} ({pct:.4f}%)\n")

        report.write("\nFISCAL YEAR VS DATA_AS_OF YEAR CHECK\n")
        report.write("-" * 80 + "\n")
        report.write(
            f"Fiscal Year mismatch with data_as_of year: "
            f"{fiscal_year_vs_data_as_of_year_mismatch:,} "
            f"({(fiscal_year_vs_data_as_of_year_mismatch / total_rows) * 100:.4f}%)\n"
        )

        report.write("\nRECOMMENDED HANDLING\n")
        report.write("-" * 80 + "\n")
        report.write("Use Fiscal Year as the primary reporting period for dashboards and gold marts.\n")
        report.write("Use Purchase Order Date as a secondary date when available; do not require it for all records.\n")
        report.write("Use data_as_of as the source snapshot/freshness timestamp.\n")
        report.write("Use data_loaded_at as the ingestion/load timestamp.\n")
        report.write("Partition raw/silver data by Fiscal Year first; optionally add data_loaded_at date for ingestion tracking.\n")
        report.write("For incremental design, data_as_of and data_loaded_at should be preserved as metadata fields.\n")

    print(f"Done. Report saved to: {REPORT_PATH}")


if __name__ == "__main__":
    check_time_coverage()