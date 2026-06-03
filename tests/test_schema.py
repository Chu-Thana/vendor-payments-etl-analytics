from src.schema import EXPECTED_COLUMNS, COLUMN_RENAME_MAP


def test_expected_columns_count():
    assert len(EXPECTED_COLUMNS) == 33


def test_column_rename_map_has_all_expected_columns():
    assert set(EXPECTED_COLUMNS) == set(COLUMN_RENAME_MAP.keys())


def test_column_rename_map_outputs_are_unique():
    renamed_columns = list(COLUMN_RENAME_MAP.values())
    assert len(renamed_columns) == len(set(renamed_columns))


def test_required_columns_exist():
    required = {
        "Fiscal Year",
        "Purchase Order",
        "Supplier & Other Non-Supplier Payees",
        "Vouchers Paid",
        "data_as_of",
        "data_loaded_at",
    }

    assert required.issubset(set(EXPECTED_COLUMNS))