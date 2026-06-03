from pathlib import Path
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_PATH = PROJECT_ROOT / "data" / "raw" / "Vendor_Payments.csv"
REPORT_PATH = PROJECT_ROOT / "reports" / "schema_report.txt"

SAMPLE_ROWS = 100_000


EXPECTED_COLUMNS = [
    "Fiscal Year",
    "Related Govt Units",
    "Organization Group Code",
    "Organization Group",
    "Department Code",
    "Department",
    "Program Code",
    "Program",
    "Character Code",
    "Character",
    "Object Code",
    "Object",
    "Sub-object Code",
    "Sub-object",
    "Fund Type Code",
    "Fund Type",
    "Fund Code",
    "Fund",
    "Fund Category Code",
    "Fund Category",
    "Purchase Order",
    "Supplier & Other Non-Supplier Payees",
    "Vouchers Paid",
    "Vouchers Pending",
    "Encumbrance Balance",
    "Vouchers Pending Retainage",
    "data_as_of",
    "data_loaded_at",
    "Non-Profit Indicator",
    "Contract Number",
    "Contract Title",
    "Purchase Order Date",
    "Purchasing Authority Description",
]


def check_schema():
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"File not found: {DATA_PATH}")

    df = pd.read_csv(
        DATA_PATH,
        nrows=SAMPLE_ROWS,
        encoding="utf-8-sig",
        low_memory=False,
    )

    actual_columns = list(df.columns)

    missing_columns = [col for col in EXPECTED_COLUMNS if col not in actual_columns]
    extra_columns = [col for col in actual_columns if col not in EXPECTED_COLUMNS]

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(REPORT_PATH, "w", encoding="utf-8") as report:
        report.write("SCHEMA REPORT\n")
        report.write("=" * 80 + "\n\n")

        report.write(f"Data path: {DATA_PATH}\n")
        report.write(f"Sample rows checked: {len(df):,}\n")
        report.write(f"Expected column count: {len(EXPECTED_COLUMNS)}\n")
        report.write(f"Actual column count: {len(actual_columns)}\n\n")

        report.write("COLUMN CHECK\n")
        report.write("-" * 80 + "\n")
        report.write(f"Missing columns: {missing_columns if missing_columns else 'None'}\n")
        report.write(f"Extra columns: {extra_columns if extra_columns else 'None'}\n\n")

        report.write("COLUMN ORDER CHECK\n")
        report.write("-" * 80 + "\n")
        if actual_columns == EXPECTED_COLUMNS:
            report.write("Column order matches expected schema.\n")
        else:
            report.write("Column order does NOT match expected schema.\n\n")
            for i, (expected, actual) in enumerate(zip(EXPECTED_COLUMNS, actual_columns), start=1):
                status = "OK" if expected == actual else "DIFF"
                report.write(f"{i}. {status} | expected={expected} | actual={actual}\n")

        report.write("\nPANDAS DTYPES FROM SAMPLE\n")
        report.write("-" * 80 + "\n")
        report.write(df.dtypes.to_string())
        report.write("\n\n")

        report.write("SAMPLE VALUES\n")
        report.write("-" * 80 + "\n")
        for col in actual_columns:
            values = df[col].dropna().astype(str).head(5).tolist()
            report.write(f"{col}: {values}\n")

    print(f"Done. Report saved to: {REPORT_PATH}")


if __name__ == "__main__":
    check_schema()