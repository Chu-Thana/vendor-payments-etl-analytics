from pathlib import Path
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_PATH = PROJECT_ROOT / "data" / "raw" / "Vendor_Payments.csv"
REPORT_PATH = PROJECT_ROOT / "reports" / "business_rules_report.txt"

CHUNK_SIZE = 100_000

AMOUNT_COLUMNS = [
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


def clean_numeric(series: pd.Series) -> pd.Series:
    s = series.astype("string").str.strip()
    s = s.str.replace(",", "", regex=False)
    s = s.str.replace("$", "", regex=False)
    s = s.str.replace(r"^\((.*)\)$", r"-\1", regex=True)
    return pd.to_numeric(s, errors="coerce")


def parse_dates(chunk: pd.DataFrame) -> pd.DataFrame:
    parsed = pd.DataFrame(index=chunk.index)

    parsed["data_as_of"] = pd.to_datetime(
        chunk["data_as_of"],
        format="%Y/%m/%d %I:%M:%S %p",
        errors="coerce",
    )

    parsed["data_loaded_at"] = pd.to_datetime(
        chunk["data_loaded_at"],
        format="%Y/%m/%d %I:%M:%S %p",
        errors="coerce",
    )

    parsed["Purchase Order Date"] = pd.to_datetime(
        chunk["Purchase Order Date"],
        format="%Y/%m/%d",
        errors="coerce",
    )

    return parsed


def update_extreme(current_record, candidate_record, compare_value, mode):
    if candidate_record is None:
        return current_record

    if current_record is None:
        return candidate_record

    if mode == "min":
        return candidate_record if compare_value < current_record["value"] else current_record

    if mode == "max":
        return candidate_record if compare_value > current_record["value"] else current_record

    return current_record


def check_business_rules():
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"File not found: {DATA_PATH}")

    total_rows = 0

    amount_stats = {
        col: {
            "negative_count": 0,
            "zero_count": 0,
            "positive_count": 0,
            "null_count": 0,
            "min_record": None,
            "max_record": None,
            "over_1m_count": 0,
            "over_10m_count": 0,
            "over_100m_count": 0,
            "over_1b_count": 0,
        }
        for col in AMOUNT_COLUMNS
    }

    po_date_after_data_as_of_count = 0
    po_date_after_loaded_at_count = 0
    fiscal_year_mismatch_count = 0
    fiscal_year_mismatch_examples = []
    date_rule_examples = []

    fiscal_year_counts = {}

    for chunk in pd.read_csv(
        DATA_PATH,
        chunksize=CHUNK_SIZE,
        encoding="utf-8-sig",
        low_memory=False,
    ):
        total_rows += len(chunk)

        parsed_dates = parse_dates(chunk)
        fiscal_year = pd.to_numeric(chunk["Fiscal Year"], errors="coerce")

        # Fiscal year distribution
        for year, count in fiscal_year.value_counts(dropna=False).items():
            fiscal_year_counts[year] = fiscal_year_counts.get(year, 0) + int(count)

        # Amount rules
        for col in AMOUNT_COLUMNS:
            values = clean_numeric(chunk[col])

            amount_stats[col]["null_count"] += values.isna().sum()
            amount_stats[col]["negative_count"] += (values < 0).sum()
            amount_stats[col]["zero_count"] += (values == 0).sum()
            amount_stats[col]["positive_count"] += (values > 0).sum()

            amount_stats[col]["over_1m_count"] += (values.abs() > 1_000_000).sum()
            amount_stats[col]["over_10m_count"] += (values.abs() > 10_000_000).sum()
            amount_stats[col]["over_100m_count"] += (values.abs() > 100_000_000).sum()
            amount_stats[col]["over_1b_count"] += (values.abs() > 1_000_000_000).sum()

            valid_values = values.dropna()

            if not valid_values.empty:
                min_idx = valid_values.idxmin()
                max_idx = valid_values.idxmax()

                min_value = float(values.loc[min_idx])
                max_value = float(values.loc[max_idx])

                min_record = {
                    "value": min_value,
                    "Fiscal Year": chunk.loc[min_idx, "Fiscal Year"],
                    "Department": chunk.loc[min_idx, "Department"],
                    "Purchase Order": chunk.loc[min_idx, "Purchase Order"],
                    "Supplier": chunk.loc[min_idx, "Supplier & Other Non-Supplier Payees"],
                    "Contract Number": chunk.loc[min_idx, "Contract Number"],
                }

                max_record = {
                    "value": max_value,
                    "Fiscal Year": chunk.loc[max_idx, "Fiscal Year"],
                    "Department": chunk.loc[max_idx, "Department"],
                    "Purchase Order": chunk.loc[max_idx, "Purchase Order"],
                    "Supplier": chunk.loc[max_idx, "Supplier & Other Non-Supplier Payees"],
                    "Contract Number": chunk.loc[max_idx, "Contract Number"],
                }

                amount_stats[col]["min_record"] = update_extreme(
                    amount_stats[col]["min_record"],
                    min_record,
                    min_value,
                    "min",
                )

                amount_stats[col]["max_record"] = update_extreme(
                    amount_stats[col]["max_record"],
                    max_record,
                    max_value,
                    "max",
                )

        # Date rules
        po_date = parsed_dates["Purchase Order Date"]
        data_as_of = parsed_dates["data_as_of"]
        data_loaded_at = parsed_dates["data_loaded_at"]

        po_after_asof_mask = po_date.notna() & data_as_of.notna() & (po_date > data_as_of)
        po_after_loaded_mask = po_date.notna() & data_loaded_at.notna() & (po_date > data_loaded_at)

        po_date_after_data_as_of_count += po_after_asof_mask.sum()
        po_date_after_loaded_at_count += po_after_loaded_mask.sum()

        if len(date_rule_examples) < 10:
            example_cols = [
                "Fiscal Year",
                "Purchase Order",
                "Department",
                "Purchase Order Date",
                "data_as_of",
                "data_loaded_at",
            ]
            examples = chunk.loc[po_after_asof_mask | po_after_loaded_mask, example_cols].head(
                10 - len(date_rule_examples)
            )
            date_rule_examples.extend(examples.to_dict(orient="records"))

        # Fiscal Year vs Purchase Order Date year
        po_year = po_date.dt.year
        fiscal_year_mismatch_mask = po_date.notna() & fiscal_year.notna() & (po_year != fiscal_year)

        fiscal_year_mismatch_count += fiscal_year_mismatch_mask.sum()

        if len(fiscal_year_mismatch_examples) < 10:
            example_cols = [
                "Fiscal Year",
                "Purchase Order",
                "Department",
                "Purchase Order Date",
                "data_as_of",
            ]
            examples = chunk.loc[fiscal_year_mismatch_mask, example_cols].head(
                10 - len(fiscal_year_mismatch_examples)
            )
            fiscal_year_mismatch_examples.extend(examples.to_dict(orient="records"))

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(REPORT_PATH, "w", encoding="utf-8") as report:
        report.write("BUSINESS RULE & RANGE VALIDATION REPORT\n")
        report.write("=" * 80 + "\n\n")

        report.write(f"Data path: {DATA_PATH}\n")
        report.write(f"Total rows checked: {total_rows:,}\n")
        report.write(f"Chunk size: {CHUNK_SIZE:,}\n\n")

        report.write("AMOUNT RANGE CHECK\n")
        report.write("-" * 80 + "\n")
        for col, stats in amount_stats.items():
            report.write(f"{col}\n")
            report.write(f"  null_count: {stats['null_count']:,}\n")
            report.write(f"  negative_count: {stats['negative_count']:,}\n")
            report.write(f"  zero_count: {stats['zero_count']:,}\n")
            report.write(f"  positive_count: {stats['positive_count']:,}\n")
            report.write(f"  abs(value) > 1M count: {stats['over_1m_count']:,}\n")
            report.write(f"  abs(value) > 10M count: {stats['over_10m_count']:,}\n")
            report.write(f"  abs(value) > 100M count: {stats['over_100m_count']:,}\n")
            report.write(f"  abs(value) > 1B count: {stats['over_1b_count']:,}\n")
            report.write(f"  min_record: {stats['min_record']}\n")
            report.write(f"  max_record: {stats['max_record']}\n\n")

        report.write("DATE BUSINESS RULE CHECK\n")
        report.write("-" * 80 + "\n")
        report.write(
            f"Purchase Order Date after data_as_of: "
            f"{po_date_after_data_as_of_count:,} rows "
            f"({(po_date_after_data_as_of_count / total_rows) * 100:.4f}%)\n"
        )
        report.write(
            f"Purchase Order Date after data_loaded_at: "
            f"{po_date_after_loaded_at_count:,} rows "
            f"({(po_date_after_loaded_at_count / total_rows) * 100:.4f}%)\n"
        )

        report.write("\nDATE RULE EXAMPLES\n")
        report.write("-" * 80 + "\n")
        if date_rule_examples:
            for i, row in enumerate(date_rule_examples, start=1):
                report.write(f"{i}. {row}\n")
        else:
            report.write("No date rule violations found.\n")

        report.write("\nFISCAL YEAR VS PURCHASE ORDER DATE CHECK\n")
        report.write("-" * 80 + "\n")
        report.write(
            f"Fiscal Year mismatch with Purchase Order Date year: "
            f"{fiscal_year_mismatch_count:,} rows "
            f"({(fiscal_year_mismatch_count / total_rows) * 100:.4f}%)\n"
        )

        report.write("\nFISCAL YEAR MISMATCH EXAMPLES\n")
        report.write("-" * 80 + "\n")
        if fiscal_year_mismatch_examples:
            for i, row in enumerate(fiscal_year_mismatch_examples, start=1):
                report.write(f"{i}. {row}\n")
        else:
            report.write("No fiscal year mismatch examples found.\n")

        report.write("\nFISCAL YEAR DISTRIBUTION\n")
        report.write("-" * 80 + "\n")
        for year in sorted(fiscal_year_counts, key=lambda x: str(x)):
            report.write(f"{year}: {fiscal_year_counts[year]:,}\n")

        report.write("\nRECOMMENDED HANDLING\n")
        report.write("-" * 80 + "\n")
        report.write("Negative amounts should not be automatically rejected; they may represent adjustments, reversals, refunds, or corrections.\n")
        report.write("Very large amount values should be flagged as outliers for review, not removed automatically.\n")
        report.write("Purchase Order Date can be null and should not be required for all records.\n")
        report.write("Fiscal Year should be used as the primary reporting period; Purchase Order Date can be used when available.\n")
        report.write("If Purchase Order Date year differs from Fiscal Year, keep both fields and document the distinction.\n")

    print(f"Done. Report saved to: {REPORT_PATH}")


if __name__ == "__main__":
    check_business_rules()