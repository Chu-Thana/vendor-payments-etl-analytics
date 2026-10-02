from pathlib import Path
import sys

import pandas as pd
import hashlib
import json
import os

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PROJECT_ROOT))

from src.config import (
    CHUNK_SIZE,
    GOLD_DATA_DIR,
    SILVER_DATA_DIR,
    ensure_directories,
)

from src.recovery import (
    finish_chunk_attempt,
    get_or_create_dataset_chunk,
    start_chunk_attempt,
)

SILVER_FILE = SILVER_DATA_DIR / "vendor_payments_silver.csv"

GOLD_CANDIDATE_DIR = (
    GOLD_DATA_DIR.parent / "gold_candidate"
)

GOLD_PARTIAL_DIR = (
    GOLD_DATA_DIR.parent / "gold_partial"
)

GOLD_PARTIAL_STATE_TYPES = [
    "metrics",
    "suppliers",
]

MART_SPECS = {
    "mart_spending_by_fiscal_year": {
        "group_cols": [
            "fiscal_year",
        ],
        "sort_columns": [
            "fiscal_year",
        ],
        "ascending": True,
        "top_n": None,
        "nonzero_filter_column": None,
    },

    "mart_spending_by_department": {
        "group_cols": [
            "fiscal_year",
            "organization_group",
            "department",
        ],
        "sort_columns": [
            "fiscal_year",
            "total_vouchers_paid",
        ],
        "ascending": [True, False],
        "top_n": None,
        "nonzero_filter_column": None,
    },

    "mart_spending_by_supplier_top_n": {
        "group_cols": [
            "supplier_name",
        ],
        "sort_columns": [
            "total_vouchers_paid",
        ],
        "ascending": False,
        "top_n": 100,
        "nonzero_filter_column": None,
    },

    "mart_pending_by_department": {
        "group_cols": [
            "fiscal_year",
            "department",
        ],
        "sort_columns": [
            "fiscal_year",
            "total_vouchers_pending",
        ],
        "ascending": [True, False],
        "top_n": None,
        "nonzero_filter_column": (
            "total_vouchers_pending"
        ),
    },

    "mart_fund_category_summary": {
        "group_cols": [
            "fiscal_year",
            "fund_type",
            "fund_category",
        ],
        "sort_columns": [
            "fiscal_year",
            "total_vouchers_paid",
        ],
        "ascending": [True, False],
        "top_n": None,
        "nonzero_filter_column": None,
    },
}

MART_FISCAL_YEAR = (
    GOLD_CANDIDATE_DIR
    / "mart_spending_by_fiscal_year.csv"
)

MART_DEPARTMENT = (
    GOLD_CANDIDATE_DIR
    / "mart_spending_by_department.csv"
)

MART_SUPPLIER_TOP_N = (
    GOLD_CANDIDATE_DIR
    / "mart_spending_by_supplier_top_n.csv"
)

MART_PENDING_DEPARTMENT = (
    GOLD_CANDIDATE_DIR
    / "mart_pending_by_department.csv"
)

MART_FUND_CATEGORY = (
    GOLD_CANDIDATE_DIR
    / "mart_fund_category_summary.csv"
)


def calculate_file_checksum(
    file_path: Path,
) -> str:
    sha256 = hashlib.sha256()

    with file_path.open("rb") as file:
        for block in iter(
            lambda: file.read(1024 * 1024),
            b"",
        ):
            sha256.update(block)

    return sha256.hexdigest()


def build_gold_partial_manifest(
    chunk_dir: Path,
    chunk_id: str,
    source_rows: int,
) -> dict:
    files = {}

    for mart_name in MART_SPECS:
        for state_type in GOLD_PARTIAL_STATE_TYPES:
            file_name = (
                f"{mart_name}."
                f"{state_type}.csv"
            )

            file_path = (
                chunk_dir
                / file_name
            )

            if not file_path.exists():
                raise FileNotFoundError(
                    f"Gold partial file missing: "
                    f"{file_path}"
                )

            row_count = sum(
                len(chunk)
                for chunk in pd.read_csv(
                    file_path,
                    chunksize=100_000,
                    low_memory=False,
                )
            )

            files[file_name] = {
                "row_count": row_count,
                "checksum": (
                    calculate_file_checksum(
                        file_path
                    )
                ),
            }

    return {
        "chunk_id": chunk_id,
        "source_rows": source_rows,
        "files": files,
    }


def calculate_gold_bundle_checksum(
    manifest: dict,
) -> str:
    payload = {
        "chunk_id": manifest["chunk_id"],
        "source_rows": manifest["source_rows"],
        "files": manifest["files"],
    }

    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    )

    return hashlib.sha256(
        canonical.encode("utf-8")
    ).hexdigest()


def aggregate_chunk_metrics(
    chunk: pd.DataFrame,
    group_cols: list[str],
) -> pd.DataFrame:
    return (
        chunk.groupby(
            group_cols,
            dropna=False,
        )
        .agg(
            total_vouchers_paid=(
                "vouchers_paid",
                "sum",
            ),
            total_vouchers_pending=(
                "vouchers_pending",
                "sum",
            ),
            total_encumbrance_balance=(
                "encumbrance_balance",
                "sum",
            ),
            total_pending_retainage=(
                "vouchers_pending_retainage",
                "sum",
            ),
            record_count=(
                "source_row_hash",
                "count",
            ),
            negative_paid_records=(
                "is_negative_paid",
                "sum",
            ),
            large_paid_1m_records=(
                "is_large_paid_1m",
                "sum",
            ),
            missing_po_date_records=(
                "is_missing_purchase_order_date",
                "sum",
            ),
        )
        .reset_index()
    )


def build_chunk_supplier_state(
    chunk: pd.DataFrame,
    group_cols: list[str],
) -> pd.DataFrame:
    supplier_columns = list(
        dict.fromkeys(
            group_cols
            + ["supplier_name"]
        )
    )

    return (
        chunk[
            supplier_columns
        ]
        .drop_duplicates()
    )

def write_gold_partial_bundle(
    silver_chunk: pd.DataFrame,
    chunk_index: int,
) -> Path:
    chunk_id = f"chunk_{chunk_index:03d}"

    chunk_dir = (
        GOLD_PARTIAL_DIR
        / chunk_id
    )

    chunk_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    for mart_name, spec in MART_SPECS.items():
        group_cols = spec[
            "group_cols"
        ]

        metrics = aggregate_chunk_metrics(
            silver_chunk,
            group_cols,
        )

        suppliers = build_chunk_supplier_state(
            silver_chunk,
            group_cols,
        )

        metrics.to_csv(
            chunk_dir
            / f"{mart_name}.metrics.csv",
            index=False,
            encoding="utf-8",
        )

        suppliers.to_csv(
            chunk_dir
            / f"{mart_name}.suppliers.csv",
            index=False,
            encoding="utf-8",
        )

    manifest = build_gold_partial_manifest(
        chunk_dir=chunk_dir,
        chunk_id=chunk_id,
        source_rows=len(silver_chunk),
    )

    manifest["bundle_checksum"] = (
        calculate_gold_bundle_checksum(
            manifest
        )
    )

    manifest_file = (
            chunk_dir
            / "manifest.json"
    )

    with manifest_file.open(
            "w",
            encoding="utf-8",
    ) as file:
        json.dump(
            manifest,
            file,
            indent=2,
            sort_keys=True,
        )

    return chunk_dir


def validate_gold_partial_bundle(
    chunk_dir: Path,
    expected_chunk_id: str,
    expected_source_rows: int,
) -> dict:
    manifest_file = (
        chunk_dir
        / "manifest.json"
    )

    if not manifest_file.exists():
        raise FileNotFoundError(
            f"Gold manifest missing: "
            f"{manifest_file}"
        )

    with manifest_file.open(
        "r",
        encoding="utf-8",
    ) as file:
        manifest = json.load(file)

    if manifest.get("chunk_id") != expected_chunk_id:
        raise ValueError(
            "Gold partial chunk_id mismatch: "
            f"expected={expected_chunk_id}, "
            f"actual={manifest.get('chunk_id')}"
        )

    if (
        manifest.get("source_rows")
        != expected_source_rows
    ):
        raise ValueError(
            "Gold partial source row mismatch: "
            f"expected={expected_source_rows:,}, "
            f"actual={manifest.get('source_rows')}"
        )

    expected_files = {
        (
            f"{mart_name}."
            f"{state_type}.csv"
        )
        for mart_name in MART_SPECS
        for state_type
        in GOLD_PARTIAL_STATE_TYPES
    }

    manifest_files = set(
        manifest.get(
            "files",
            {},
        ).keys()
    )

    if manifest_files != expected_files:
        missing = (
            expected_files
            - manifest_files
        )

        unexpected = (
            manifest_files
            - expected_files
        )

        raise ValueError(
            "Gold partial manifest files "
            "do not match expected bundle. "
            f"missing={sorted(missing)}, "
            f"unexpected={sorted(unexpected)}"
        )

    for file_name in sorted(
        expected_files
    ):
        file_path = (
            chunk_dir
            / file_name
        )

        if not file_path.exists():
            raise FileNotFoundError(
                f"Gold partial file missing: "
                f"{file_path}"
            )

        expected_metadata = (
            manifest["files"][
                file_name
            ]
        )

        actual_row_count = sum(
            len(chunk)
            for chunk in pd.read_csv(
                file_path,
                chunksize=100_000,
                low_memory=False,
            )
        )

        if (
            actual_row_count
            != expected_metadata["row_count"]
        ):
            raise ValueError(
                "Gold partial row count "
                "mismatch: "
                f"{file_name}, "
                f"expected="
                f"{expected_metadata['row_count']}, "
                f"actual={actual_row_count}"
            )

        actual_checksum = (
            calculate_file_checksum(
                file_path
            )
        )

        if (
            actual_checksum
            != expected_metadata["checksum"]
        ):
            raise ValueError(
                "Gold partial checksum "
                "mismatch: "
                f"{file_name}"
            )

    expected_bundle_checksum = (
        manifest.get(
            "bundle_checksum"
        )
    )

    actual_bundle_checksum = (
        calculate_gold_bundle_checksum(
            manifest
        )
    )

    if (
        expected_bundle_checksum
        != actual_bundle_checksum
    ):
        raise ValueError(
            "Gold partial bundle checksum "
            "mismatch."
        )

    return {
        "chunk_id": expected_chunk_id,
        "source_rows": expected_source_rows,
        "file_count": len(
            expected_files
        ),
        "bundle_checksum": (
            actual_bundle_checksum
        ),
    }


def build_gold_partials(
    silver_file: Path = SILVER_FILE,
) -> dict:
    if not silver_file.exists():
        raise FileNotFoundError(
            f"Silver file not found: {silver_file}"
        )

    dataset_version_id_raw = os.getenv(
        "RECOVERY_DATASET_VERSION_ID"
    )

    if not dataset_version_id_raw:
        raise RuntimeError(
            "RECOVERY_DATASET_VERSION_ID "
            "is required for Gold chunk recovery."
        )

    dataset_version_id = int(
        dataset_version_id_raw
    )

    total_rows = 0
    total_chunks = 0

    for chunk_index, chunk in enumerate(
            pd.read_csv(
                silver_file,
                chunksize=CHUNK_SIZE,
                encoding="utf-8",
                low_memory=False,
            ),
            start=1,
    ):
        chunk_id = (
            f"chunk_{chunk_index:03d}"
        )

        source_start_row = (
                (chunk_index - 1)
                * CHUNK_SIZE
                + 1
        )

        source_end_row = (
                source_start_row
                + len(chunk)
                - 1
        )

        dataset_chunk_id = (
            get_or_create_dataset_chunk(
                dataset_version_id=(
                    dataset_version_id
                ),
                chunk_id=chunk_id,
                chunk_index=chunk_index,
                source_start_row=(
                    source_start_row
                ),
                source_end_row=(
                    source_end_row
                ),
            )
        )

        chunk_execution_id = (
            start_chunk_attempt(
                dataset_chunk_id
            )
        )

        try:
            chunk_dir = (
                write_gold_partial_bundle(
                    chunk,
                    chunk_index,
                )
            )

            validation = (
                validate_gold_partial_bundle(
                    chunk_dir=chunk_dir,
                    expected_chunk_id=(
                        chunk_id
                    ),
                    expected_source_rows=(
                        len(chunk)
                    ),
                )
            )

            bundle_checksum = (
                validation[
                    "bundle_checksum"
                ]
            )

            finish_chunk_attempt(
                chunk_execution_id=(
                    chunk_execution_id
                ),
                success=True,
                row_count=len(chunk),
                checksum=bundle_checksum,
                error_message=None,
            )

        except Exception as exc:
            finish_chunk_attempt(
                chunk_execution_id=(
                    chunk_execution_id
                ),
                success=False,
                row_count=None,
                checksum=None,
                error_message=str(exc),
            )

            raise

        total_rows += len(chunk)
        total_chunks += 1

        print(
            f"Created Gold partial "
            f"{chunk_id}: "
            f"{len(chunk):,} source rows "
            f"[validation=PASS, "
            f"files={validation['file_count']}]"
        )

    if total_rows == 0:
        raise ValueError(
            "Silver input contains no rows."
        )

    return {
        "source_rows": total_rows,
        "chunk_count": total_chunks,
    }


def merge_gold_partial_state(
    mart_name: str,
    group_cols: list[str],
) -> pd.DataFrame:
    metric_files = sorted(
        GOLD_PARTIAL_DIR.glob(
            f"chunk_*/"
            f"{mart_name}.metrics.csv"
        )
    )

    supplier_files = sorted(
        GOLD_PARTIAL_DIR.glob(
            f"chunk_*/"
            f"{mart_name}.suppliers.csv"
        )
    )

    if not metric_files:
        raise RuntimeError(
            f"No Gold metric partial files "
            f"found for {mart_name}."
        )

    if not supplier_files:
        raise RuntimeError(
            f"No Gold supplier partial files "
            f"found for {mart_name}."
        )

    metric_parts = [
        pd.read_csv(
            file,
            encoding="utf-8",
            low_memory=False,
        )
        for file in metric_files
    ]

    supplier_parts = [
        pd.read_csv(
            file,
            encoding="utf-8",
            low_memory=False,
        )
        for file in supplier_files
    ]

    combined_metrics = pd.concat(
        metric_parts,
        ignore_index=True,
    )

    final_metrics = (
        combined_metrics.groupby(
            group_cols,
            dropna=False,
        )
        .agg(
            total_vouchers_paid=(
                "total_vouchers_paid",
                "sum",
            ),
            total_vouchers_pending=(
                "total_vouchers_pending",
                "sum",
            ),
            total_encumbrance_balance=(
                "total_encumbrance_balance",
                "sum",
            ),
            total_pending_retainage=(
                "total_pending_retainage",
                "sum",
            ),
            record_count=(
                "record_count",
                "sum",
            ),
            negative_paid_records=(
                "negative_paid_records",
                "sum",
            ),
            large_paid_1m_records=(
                "large_paid_1m_records",
                "sum",
            ),
            missing_po_date_records=(
                "missing_po_date_records",
                "sum",
            ),
        )
        .reset_index()
    )

    supplier_columns = list(
        dict.fromkeys(
            group_cols
            + ["supplier_name"]
        )
    )

    distinct_suppliers = (
        pd.concat(
            supplier_parts,
            ignore_index=True,
        )
        .drop_duplicates(
            subset=supplier_columns
        )
    )

    unique_suppliers = (
        distinct_suppliers.groupby(
            group_cols,
            dropna=False,
        )
        .size()
        .reset_index(
            name="unique_suppliers"
        )
    )

    return final_metrics.merge(
        unique_suppliers,
        on=group_cols,
        how="left",
    )


def finalize_gold_mart(
    *,
    mart_name: str,
    output_file: Path,
) -> dict:
    spec = MART_SPECS[
        mart_name
    ]

    mart = merge_gold_partial_state(
        mart_name=mart_name,
        group_cols=spec["group_cols"],
    )

    nonzero_filter_column = spec[
        "nonzero_filter_column"
    ]

    if nonzero_filter_column is not None:
        mart = mart[
            mart[nonzero_filter_column] != 0
            ]

    sort_columns = spec[
        "sort_columns"
    ]

    if sort_columns:
        mart = mart.sort_values(
            sort_columns,
            ascending=spec["ascending"],
        )

    top_n = spec["top_n"]

    if top_n is not None:
        mart = mart.head(
            top_n
        )

    output_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    mart.to_csv(
        output_file,
        index=False,
        encoding="utf-8",
    )

    print(
        f"Created: {output_file}"
    )

    return {
        "name": mart_name,
        "row_count": len(mart),
        "output_file": str(output_file),
        "available": output_file.exists(),
    }

def aggregate_by_group(
    group_cols: list[str],
    silver_file: Path = SILVER_FILE,
) -> pd.DataFrame:
    """
    Aggregate Silver data using chunk processing.

    Additive metrics are partially aggregated per chunk.
    unique_suppliers is calculated separately using an exact
    distinct group + supplier combination across all chunks.
    """
    metric_parts = []
    supplier_parts = []

    supplier_columns = list(
        dict.fromkeys(
            group_cols + ["supplier_name"]
        )
    )

    for chunk in pd.read_csv(
        silver_file,
        chunksize=CHUNK_SIZE,
        encoding="utf-8",
        low_memory=False,
    ):
        grouped = (
            chunk.groupby(
                group_cols,
                dropna=False,
            )
            .agg(
                total_vouchers_paid=(
                    "vouchers_paid",
                    "sum",
                ),
                total_vouchers_pending=(
                    "vouchers_pending",
                    "sum",
                ),
                total_encumbrance_balance=(
                    "encumbrance_balance",
                    "sum",
                ),
                total_pending_retainage=(
                    "vouchers_pending_retainage",
                    "sum",
                ),
                record_count=(
                    "source_row_hash",
                    "count",
                ),
                negative_paid_records=(
                    "is_negative_paid",
                    "sum",
                ),
                large_paid_1m_records=(
                    "is_large_paid_1m",
                    "sum",
                ),
                missing_po_date_records=(
                    "is_missing_purchase_order_date",
                    "sum",
                ),
            )
            .reset_index()
        )

        metric_parts.append(grouped)

        supplier_distinct = (
            chunk[supplier_columns]
            .drop_duplicates()
        )

        supplier_parts.append(
            supplier_distinct
        )

    if not metric_parts:
        raise ValueError(
            "Silver input contains no rows."
        )

    combined_metrics = pd.concat(
        metric_parts,
        ignore_index=True,
    )

    final_metrics = (
        combined_metrics.groupby(
            group_cols,
            dropna=False,
        )
        .agg(
            total_vouchers_paid=(
                "total_vouchers_paid",
                "sum",
            ),
            total_vouchers_pending=(
                "total_vouchers_pending",
                "sum",
            ),
            total_encumbrance_balance=(
                "total_encumbrance_balance",
                "sum",
            ),
            total_pending_retainage=(
                "total_pending_retainage",
                "sum",
            ),
            record_count=(
                "record_count",
                "sum",
            ),
            negative_paid_records=(
                "negative_paid_records",
                "sum",
            ),
            large_paid_1m_records=(
                "large_paid_1m_records",
                "sum",
            ),
            missing_po_date_records=(
                "missing_po_date_records",
                "sum",
            ),
        )
        .reset_index()
    )

    distinct_suppliers = (
        pd.concat(
            supplier_parts,
            ignore_index=True,
        )
        .drop_duplicates(
            subset=supplier_columns
        )
    )

    unique_suppliers = (
        distinct_suppliers.groupby(
            group_cols,
            dropna=False,
        )
        .size()
        .reset_index(
            name="unique_suppliers"
        )
    )

    return final_metrics.merge(
        unique_suppliers,
        on=group_cols,
        how="left",
    )


def build_mart(
    *,
    name: str,
    group_cols: list[str],
    output_file: Path,
    silver_file: Path = SILVER_FILE,
    sort_columns: list[str] | None = None,
    ascending: list[bool] | bool = True,
    top_n: int | None = None,
    nonzero_filter_column: str | None = None,
) -> dict:
    """
    Build one Gold mart, write it to CSV,
    and return structured execution metadata.
    """
    mart = aggregate_by_group(
        group_cols=group_cols,
        silver_file=silver_file,
    )

    if nonzero_filter_column is not None:
        mart = mart[
            mart[nonzero_filter_column] != 0
        ]

    if sort_columns:
        mart = mart.sort_values(
            sort_columns,
            ascending=ascending,
        )

    if top_n is not None:
        mart = mart.head(top_n)

    output_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    mart.to_csv(
        output_file,
        index=False,
        encoding="utf-8",
    )

    print(f"Created: {output_file}")

    return {
        "name": name,
        "row_count": len(mart),
        "output_file": str(output_file),
        "available": output_file.exists(),
    }


def build_fiscal_year_mart(
    silver_file: Path = SILVER_FILE,
    output_file: Path = MART_FISCAL_YEAR,
) -> dict:
    return build_mart(
        name="mart_spending_by_fiscal_year",
        group_cols=["fiscal_year"],
        output_file=output_file,
        silver_file=silver_file,
        sort_columns=["fiscal_year"],
    )


def build_department_mart(
    silver_file: Path = SILVER_FILE,
    output_file: Path = MART_DEPARTMENT,
) -> dict:
    return build_mart(
        name="mart_spending_by_department",
        group_cols=[
            "fiscal_year",
            "organization_group",
            "department",
        ],
        output_file=output_file,
        silver_file=silver_file,
        sort_columns=[
            "fiscal_year",
            "total_vouchers_paid",
        ],
        ascending=[True, False],
    )


def build_supplier_top_n_mart(
    silver_file: Path = SILVER_FILE,
    output_file: Path = MART_SUPPLIER_TOP_N,
    top_n: int = 100,
) -> dict:
    return build_mart(
        name="mart_spending_by_supplier_top_n",
        group_cols=["supplier_name"],
        output_file=output_file,
        silver_file=silver_file,
        sort_columns=["total_vouchers_paid"],
        ascending=False,
        top_n=top_n,
    )


def build_pending_department_mart(
    silver_file: Path = SILVER_FILE,
    output_file: Path = MART_PENDING_DEPARTMENT,
) -> dict:
    return build_mart(
        name="mart_pending_by_department",
        group_cols=[
            "fiscal_year",
            "department",
        ],
        output_file=output_file,
        silver_file=silver_file,
        sort_columns=[
            "fiscal_year",
            "total_vouchers_pending",
        ],
        ascending=[True, False],
        nonzero_filter_column=(
            "total_vouchers_pending"
        ),
    )


def build_fund_category_mart(
    silver_file: Path = SILVER_FILE,
    output_file: Path = MART_FUND_CATEGORY,
) -> dict:
    return build_mart(
        name="mart_fund_category_summary",
        group_cols=[
            "fiscal_year",
            "fund_type",
            "fund_category",
        ],
        output_file=output_file,
        silver_file=silver_file,
        sort_columns=[
            "fiscal_year",
            "total_vouchers_paid",
        ],
        ascending=[True, False],
    )


def clear_gold_partial_dir() -> None:
    if not GOLD_PARTIAL_DIR.exists():
        return

    for chunk_dir in GOLD_PARTIAL_DIR.glob(
        "chunk_*"
    ):
        if not chunk_dir.is_dir():
            continue

        for file in chunk_dir.iterdir():
            if file.is_file():
                file.unlink()

        chunk_dir.rmdir()


def build_gold_marts(
    silver_file: Path = SILVER_FILE,
    gold_dir: Path = GOLD_CANDIDATE_DIR,
) -> dict:
    ensure_directories()

    if not silver_file.exists():
        raise FileNotFoundError(
            f"Silver file not found: {silver_file}"
        )

    gold_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    expected_files = [
        "mart_spending_by_fiscal_year.csv",
        "mart_spending_by_department.csv",
        "mart_spending_by_supplier_top_n.csv",
        "mart_pending_by_department.csv",
        "mart_fund_category_summary.csv",
    ]

    for file_name in expected_files:
        (
            gold_dir / file_name
        ).unlink(
            missing_ok=True
        )

    # Phase 1:
    # Rebuild Gold partial checkpoints from scratch.
    # Recovery-aware resume will be added later.

    partial_result = build_gold_partials(
        silver_file=silver_file
    )

    mart_results = [
        finalize_gold_mart(
            mart_name="mart_spending_by_fiscal_year",
            output_file=(
                gold_dir
                / "mart_spending_by_fiscal_year.csv"
            ),
        ),

        finalize_gold_mart(
            mart_name="mart_spending_by_department",
            output_file=(
                gold_dir
                / "mart_spending_by_department.csv"
            ),
        ),

        finalize_gold_mart(
            mart_name="mart_spending_by_supplier_top_n",
            output_file=(
                gold_dir
                / "mart_spending_by_supplier_top_n.csv"
            ),
        ),

        finalize_gold_mart(
            mart_name="mart_pending_by_department",
            output_file=(
                gold_dir
                / "mart_pending_by_department.csv"
            ),
        ),

        finalize_gold_mart(
            mart_name="mart_fund_category_summary",
            output_file=(
                gold_dir
                / "mart_fund_category_summary.csv"
            ),
        ),
    ]

    print(
        "Gold partial build completed: "
        f"{partial_result['chunk_count']} chunks, "
        f"{partial_result['source_rows']:,} source rows"
    )

    print(
        "Gold candidate build completed."
    )

    return {
        "source_rows": partial_result[
            "source_rows"
        ],
        "chunk_count": partial_result[
            "chunk_count"
        ],
        "mart_count": len(
            mart_results
        ),
        "marts": mart_results,
        "candidate_dir": str(
            gold_dir
        ),
        "available": all(
            (
                gold_dir
                / file_name
            ).exists()
            for file_name in expected_files
        ),
    }


if __name__ == "__main__":
    build_gold_marts()

