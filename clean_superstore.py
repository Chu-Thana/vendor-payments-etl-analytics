from __future__ import annotations
from pathlib import Path
import json
import sqlite3
from datetime import datetime, timezone
import uuid
import pandas as pd


# -------------------------
# 1) PURE: cleaning only (no file I/O)
# -------------------------
def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = (
        df.columns.astype("string").str.strip()
        .str.lower()
        .str.replace(" ", "_", regex=False)
        .str.replace("-", "_", regex=False)
    )
    return df


def strip_object_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    obj_cols = df.select_dtypes(include="object").columns
    for c in obj_cols:
        # use pandas StringDtype so missing stays <NA> instead of "nan"
        df[c] = df[c].astype("string").str.strip()
    return df


def clean_superstore(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """
    PURE function:
    - input: raw df
    - output: clean_df, rejected_df, report
    - no reading/writing files, no mkdir, no sqlite
    """
    report = {
        "rows_before": int(len(df)),
        "rows_after": None,
        "dropped_rows": 0,
        "invalid_counts": {},
        "rules_applied": [],
        "notes": [],
        "dtype_after": {},
        "missing_before": {},
        "missing_after": {},
        "missing_before_pct": {},
        "missing_after_pct": {},
    }

    df = normalize_columns(df)
    df = strip_object_columns(df)

    if "postal_code" in df.columns:
        df["postal_code"] = df["postal_code"].astype("string").str.strip()
    report["rules_applied"].append("Normalize columns + strip strings")

    report["missing_before"] = df.isna().sum().astype(int).to_dict()
    report["missing_before_pct"] = (df.isna().mean() * 100).round(2).to_dict()

    for col in ["order_date", "ship_date"]:
        if col in df.columns:
            s = df[col].astype("string").str.strip()
            d1 = pd.to_datetime(s, errors="coerce")
            d2 = pd.to_datetime(s, errors="coerce", dayfirst=True)
            df[col] = d2 if d2.notna().sum() > d1.notna().sum() else d1
    report["rules_applied"].append("Parse dates (robust)")

    for col in ["sales", "profit", "discount", "quantity"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    report["rules_applied"].append("Cast numerics (errors='coerce')")

    # --- reject rules build masks ---
    masks: dict[str, pd.Series] = {}

    must_have = [
        c for c in
        ["order_id", "order_date", "ship_date", "customer_id", "product_id", "sales", "quantity"]
        if c in df.columns
    ]
    masks["missing_core_fields"] = (
        df[must_have].isna().any(axis=1)
        if must_have
        else pd.Series(False, index=df.index)
    )

    masks["ship_before_order"] = (
        (df["ship_date"] < df["order_date"])
        if {"order_date", "ship_date"}.issubset(df.columns)
        else pd.Series(False, index=df.index)
    )

    masks["quantity_non_positive"] = (
        (df["quantity"] <= 0) if "quantity" in df.columns else pd.Series(False, index=df.index)
    )

    # discount normalize + reject out of range
    if "discount" in df.columns:
        # convert 1..100 to 0..1 (treat as percent) — leaves 0..1 as-is
        pct_mask = df["discount"].between(1, 100)
        df.loc[pct_mask, "discount"] = df.loc[pct_mask, "discount"] / 100
        masks["discount_out_of_range"] = (df["discount"] < 0) | (df["discount"] > 1)
    else:
        masks["discount_out_of_range"] = pd.Series(False, index=df.index)

    masks["sales_negative"] = (
        (df["sales"] <= 0)
        if "sales" in df.columns
        else pd.Series(False, index=df.index)
    )

    # count invalids + combine reject mask
    reject_mask = pd.Series(False, index=df.index)
    for name, m in masks.items():
        reject_mask |= m
        report["invalid_counts"][name] = int(m.sum())

    # rejected_df with reason
    rejected_df = df[reject_mask].copy()
    if not rejected_df.empty:
        rejected_df["reject_reason"] = [
            "|".join([name for name, m in masks.items() if m.loc[i]])
            for i in rejected_df.index
        ]
        report["notes"].append("Rejected rows saved with reject_reason")

    # clean_df + duplicates
    clean_df = df[~reject_mask].copy()
    before_dup = len(clean_df)
    clean_df = clean_df.drop_duplicates()
    report["invalid_counts"]["exact_duplicate_rows"] = int(before_dup - len(clean_df))
    report["rules_applied"].append("Drop exact duplicate rows")

    # soft flags (keep rows, add warnings)
    clean_df["flag_negative_profit"] = False
    if "profit" in clean_df.columns:
        clean_df["flag_negative_profit"] = clean_df["profit"] < 0

    clean_df["flag_high_discount"] = False
    if "discount" in clean_df.columns:
        clean_df["flag_high_discount"] = clean_df["discount"] > 0.7

    # Missing AFTER
    report["missing_after"] = clean_df.isna().sum().astype(int).to_dict()
    report["missing_after_pct"] = (clean_df.isna().mean() * 100).round(2).to_dict()

    report["rows_after"] = int(len(clean_df))
    report["dropped_rows"] = int(report["rows_before"] - report["rows_after"])
    report["dtype_after"] = {k: str(v) for k, v in clean_df.dtypes.to_dict().items()}

    return clean_df, rejected_df, report


# -------------------------
# 2) IO: pipeline runner
# -------------------------
def run_pipeline(
    raw_path: str | Path,
    out_dir: str | Path,
    db_path: str | Path | None = None,
    encoding: str = "latin1",
) -> dict:
    """
    IO function:
    - read raw csv
    - run clean_superstore(df)
    - write outputs (csv/json)
    - optionally load into sqlite
    - return report (and maybe paths)
    """
    raw_path = Path(raw_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    clean_csv = out_dir / "superstore_cleaned.csv"
    rejected_csv = out_dir / "superstore_rejected.csv"
    report_json = out_dir / "cleaning_report.json"

    df = pd.read_csv(raw_path, encoding=encoding)
    clean_df, rejected_df, report = clean_superstore(df)

    # save outputs
    clean_df.to_csv(clean_csv, index=False)
    rejected_df.to_csv(rejected_csv, index=False)
    with open(report_json, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    # run log row (optional, for DB)
    report_row = pd.DataFrame([{
        "run_id": str(uuid.uuid4()),
        "run_at": datetime.now(timezone.utc).isoformat(),
        "source_file": raw_path.name,
        "rows_before": report["rows_before"],
        "rows_after": report["rows_after"],
        "dropped_rows": report["dropped_rows"],
    }])

    # optional: sqlite load
    if db_path is not None:
        db_path = Path(db_path)
        with sqlite3.connect(db_path) as conn:
            clean_df.to_sql("superstore_clean", conn, if_exists="replace", index=False)
            rejected_df.to_sql("superstore_rejected", conn, if_exists="replace", index=False)
            report_row.to_sql("etl_run_log", conn, if_exists="append", index=False)

    # add output paths into report for convenience
    report["outputs"] = {
        "clean_csv": str(clean_csv),
        "rejected_csv": str(rejected_csv),
        "report_json": str(report_json),
        "db_path": str(db_path) if db_path is not None else None,
    }
    return report


# -------------------------
# 3) Script entrypoint
# -------------------------
def main():
    base_dir = Path(__file__).resolve().parent
    raw_path = base_dir / "Superstore.csv"
    out_dir = base_dir / "output"
    db_path = out_dir / "superstore.db"

    report = run_pipeline(raw_path=raw_path, out_dir=out_dir, db_path=db_path)
    print("✅ Done")
    print("Rows before:", report["rows_before"])
    print("Rows after :", report["rows_after"])
    print("Dropped    :", report["dropped_rows"])
    print("Invalid counts:", report["invalid_counts"])
    print("Outputs:", report.get("outputs"))


if __name__ == "__main__":
    main()
