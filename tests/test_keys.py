import pandas as pd

from src.keys import (
    normalize_key_value,
    make_composite_key,
    make_row_hash,
)


def test_normalize_key_value_handles_null():
    assert normalize_key_value(None) == "<NULL>"


def test_normalize_key_value_strips_text():
    assert normalize_key_value(" ABC ") == "ABC"


def test_make_composite_key():
    row = pd.Series({
        "Fiscal Year": 2025,
        "Purchase Order": "PO001",
        "Supplier": "ABC INC",
    })

    result = make_composite_key(
        row,
        ["Fiscal Year", "Purchase Order", "Supplier"],
    )

    assert result == "2025||PO001||ABC INC"


def test_make_row_hash_is_deterministic():
    row = pd.Series({
        "a": "hello",
        "b": 123,
    })

    first = make_row_hash(row, ["a", "b"])
    second = make_row_hash(row, ["a", "b"])

    assert first == second
    assert len(first) == 32