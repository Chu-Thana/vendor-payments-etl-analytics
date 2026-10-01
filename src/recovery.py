from __future__ import annotations
from datetime import datetime, timedelta, timezone

import os
import psycopg2


def recover_stale_running_chunk(
    dataset_chunk_id: int,
    stale_after_seconds: int = 900,
) -> int | None:
    stale_before = (
        datetime.now(timezone.utc)
        - timedelta(seconds=stale_after_seconds)
    )

    with get_recovery_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT recovery.recover_stale_chunk_attempt(
                    %s,
                    %s
                );
                """,
                (
                    dataset_chunk_id,
                    stale_before,
                ),
            )

            row = cursor.fetchone()

    if row is None or row[0] is None:
        return None

    return int(row[0])


def get_recovery_connection():
    return psycopg2.connect(
        host=os.environ["RECOVERY_DB_HOST"],
        port=int(
            os.getenv(
                "RECOVERY_DB_PORT",
                "5432",
            )
        ),
        dbname=os.environ["RECOVERY_DB_NAME"],
        user=os.environ["RECOVERY_DB_USER"],
        password=os.environ["RECOVERY_DB_PASSWORD"],
    )


def get_or_create_dataset_chunk(
    dataset_version_id: int,
    chunk_id: str,
    chunk_index: int,
    source_start_row: int,
    source_end_row: int,
) -> int:
    with get_recovery_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT recovery.get_or_create_dataset_chunk(
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                );
                """,
                (
                    dataset_version_id,
                    chunk_id,
                    chunk_index,
                    source_start_row,
                    source_end_row,
                ),
            )

            row = cursor.fetchone()

    if row is None:
        raise RuntimeError(
            "Dataset chunk could not be created."
        )

    return int(row[0])


def get_dataset_chunk_status(
    dataset_chunk_id: int,
) -> str:
    with get_recovery_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT status
                FROM recovery.dataset_chunks
                WHERE dataset_chunk_id = %s;
                """,
                (dataset_chunk_id,),
            )

            row = cursor.fetchone()

    if row is None:
        raise RuntimeError(
            f"Dataset chunk {dataset_chunk_id} does not exist."
        )

    return str(row[0])


def start_chunk_attempt(
    dataset_chunk_id: int,
) -> int:
    with get_recovery_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT recovery.start_chunk_attempt(%s);
                """,
                (dataset_chunk_id,),
            )

            row = cursor.fetchone()

    if row is None:
        raise RuntimeError(
            "Chunk attempt could not be started."
        )

    return int(row[0])


def finish_chunk_attempt(
    *,
    chunk_execution_id: int,
    success: bool,
    row_count: int | None = None,
    checksum: str | None = None,
    error_message: str | None = None,
) -> None:
    with get_recovery_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT recovery.finish_chunk_attempt(
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                );
                """,
                (
                    chunk_execution_id,
                    success,
                    row_count,
                    checksum,
                    error_message,
                ),
            )