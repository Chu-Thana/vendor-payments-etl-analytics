import pandas as pd


def clean_numeric(series: pd.Series) -> pd.Series:
    """
    Convert numeric-like values into numeric dtype.

    Handles:
    - commas
    - dollar signs
    - blanks
    - accounting-style negatives: (123.45) -> -123.45
    """
    s = series.astype("string").str.strip()

    s = s.str.replace(",", "", regex=False)
    s = s.str.replace("$", "", regex=False)
    s = s.str.replace(r"^\((.*)\)$", r"-\1", regex=True)

    return pd.to_numeric(s, errors="coerce")


def parse_timestamp(series: pd.Series) -> pd.Series:
    """
    Parse timestamp format used by data_as_of and data_loaded_at.
    Example: 2019/06/26 02:32:12 PM
    """
    return pd.to_datetime(
        series,
        format="%Y/%m/%d %I:%M:%S %p",
        errors="coerce",
    )


def parse_date(series: pd.Series) -> pd.Series:
    """
    Parse date format used by Purchase Order Date.
    Example: 2018/08/07
    """
    return pd.to_datetime(
        series,
        format="%Y/%m/%d",
        errors="coerce",
    ).dt.date


def clean_text(series: pd.Series, fill_value: str | None = None) -> pd.Series:
    """
    Trim text values and optionally fill missing values.
    """
    s = series.astype("string").str.strip()

    if fill_value is not None:
        s = s.fillna(fill_value)

    return s


def normalize_text(series: pd.Series, fill_value: str | None = None) -> pd.Series:
    """
    Create normalized text for grouping/search.
    """
    s = clean_text(series, fill_value=fill_value)
    return s.str.lower()


def clean_contract_number(series: pd.Series) -> pd.Series:
    """
    Clean contract number as string/id.

    Example:
    1000001664.0 -> 1000001664
    null -> <NA>
    """
    s = series.astype("string").str.strip()

    s = s.replace({"nan": pd.NA, "NaN": pd.NA, "<NA>": pd.NA})
    s = s.str.replace(r"\.0$", "", regex=True)

    return s