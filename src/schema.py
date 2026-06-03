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


CRITICAL_COLUMNS = [
    "Fiscal Year",
    "Purchase Order",
    "Supplier & Other Non-Supplier Payees",
    "Vouchers Paid",
    "data_as_of",
    "data_loaded_at",
]


WARNING_COLUMNS = [
    "Department",
    "Purchase Order Date",
    "Encumbrance Balance",
]


OPTIONAL_COLUMNS = [
    "Contract Number",
    "Contract Title",
    "Purchasing Authority Description",
]


DIMENSION_COLUMNS = [
    "Organization Group",
    "Department",
    "Program",
    "Character",
    "Object",
    "Sub-object",
    "Fund Type",
    "Fund",
    "Fund Category",
    "Supplier & Other Non-Supplier Payees",
    "Non-Profit Indicator",
    "Purchasing Authority Description",
]


BUSINESS_COMPOSITE_KEY_COLUMNS = [
    "Fiscal Year",
    "Department Code",
    "Program Code",
    "Character Code",
    "Object Code",
    "Sub-object Code",
    "Fund Code",
    "Purchase Order",
    "Supplier & Other Non-Supplier Payees",
    "Contract Number",
]


COLUMN_RENAME_MAP = {
    "Fiscal Year": "fiscal_year",
    "Related Govt Units": "related_govt_units",
    "Organization Group Code": "organization_group_code",
    "Organization Group": "organization_group",
    "Department Code": "department_code",
    "Department": "department",
    "Program Code": "program_code",
    "Program": "program",
    "Character Code": "character_code",
    "Character": "character",
    "Object Code": "object_code",
    "Object": "object",
    "Sub-object Code": "sub_object_code",
    "Sub-object": "sub_object",
    "Fund Type Code": "fund_type_code",
    "Fund Type": "fund_type",
    "Fund Code": "fund_code",
    "Fund": "fund",
    "Fund Category Code": "fund_category_code",
    "Fund Category": "fund_category",
    "Purchase Order": "purchase_order",
    "Supplier & Other Non-Supplier Payees": "supplier_name",
    "Vouchers Paid": "vouchers_paid",
    "Vouchers Pending": "vouchers_pending",
    "Encumbrance Balance": "encumbrance_balance",
    "Vouchers Pending Retainage": "vouchers_pending_retainage",
    "data_as_of": "data_as_of",
    "data_loaded_at": "data_loaded_at",
    "Non-Profit Indicator": "non_profit_indicator",
    "Contract Number": "contract_number",
    "Contract Title": "contract_title",
    "Purchase Order Date": "purchase_order_date",
    "Purchasing Authority Description": "purchasing_authority_description",
}