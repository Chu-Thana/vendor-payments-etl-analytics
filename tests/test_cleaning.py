import pandas as pd

from src.cleaning import (
    clean_numeric,
    clean_contract_number,
    clean_text,
    normalize_text,
    parse_date,
    parse_timestamp,
)


def test_clean_numeric_basic_values():
    series = pd.Series(["1,234.50", "$500.00", "(123.45)", "", None])
    result = clean_numeric(series)

    assert result.iloc[0] == 1234.50
    assert result.iloc[1] == 500.00
    assert result.iloc[2] == -123.45
    assert pd.isna(result.iloc[3])
    assert pd.isna(result.iloc[4])


def test_clean_contract_number_removes_dot_zero():
    series = pd.Series(["1000001664.0", "1000003191.0", None])
    result = clean_contract_number(series)

    assert result.iloc[0] == "1000001664"
    assert result.iloc[1] == "1000003191"
    assert pd.isna(result.iloc[2])


def test_clean_text_trims_and_fills_missing():
    series = pd.Series([" ABC ", None])
    result = clean_text(series, fill_value="Unknown")

    assert result.iloc[0] == "ABC"
    assert result.iloc[1] == "Unknown"


def test_normalize_text_lowercase():
    series = pd.Series([" DPH Public Health "])
    result = normalize_text(series)

    assert result.iloc[0] == "dph public health"


def test_parse_timestamp():
    series = pd.Series(["2019/06/26 02:32:12 PM"])
    result = parse_timestamp(series)

    assert str(result.iloc[0]) == "2019-06-26 14:32:12"


def test_parse_date():
    series = pd.Series(["2018/08/07"])
    result = parse_date(series)

    assert str(result.iloc[0]) == "2018-08-07"