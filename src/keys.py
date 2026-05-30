import hashlib
import pandas as pd


def normalize_key_value(value) -> str:
    """
    Normalize a value before building deterministic keys.
    """
    if pd.isna(value):
        return "<NULL>"

    return str(value).strip()


def make_composite_key(row: pd.Series, columns: list[str]) -> str:
    """
    Build a business composite key from selected columns.
    """
    values = [normalize_key_value(row[col]) for col in columns]
    return "||".join(values)


def make_row_hash(row: pd.Series, columns: list[str]) -> str:
    """
    Build deterministic row hash from all source columns.
    """
    values = [normalize_key_value(row[col]) for col in columns]
    raw = "||".join(values)

    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def add_source_row_hash(df: pd.DataFrame, source_columns: list[str]) -> pd.DataFrame:
    """
    Add source_row_hash for raw-level row identity.
    """
    df = df.copy()
    df["source_row_hash"] = df.apply(
        lambda row: make_row_hash(row, source_columns),
        axis=1,
    )
    return df


def add_business_composite_key(df: pd.DataFrame, key_columns: list[str]) -> pd.DataFrame:
    """
    Add business_composite_key for business-level duplicate checks.
    """
    df = df.copy()
    df["business_composite_key"] = df.apply(
        lambda row: make_composite_key(row, key_columns),
        axis=1,
    )
    return df