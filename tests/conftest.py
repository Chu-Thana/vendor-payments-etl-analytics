import pytest


@pytest.fixture
def mock_batch_recovery(monkeypatch):
    monkeypatch.setenv(
        "RECOVERY_DATASET_VERSION_ID",
        "999999",
    )

    recovery_modules = [
        "scripts.pipeline.transform_silver",
        "scripts.pipeline.build_gold_marts",
    ]

    for module in recovery_modules:
        monkeypatch.setattr(
            f"{module}.get_or_create_dataset_chunk",
            lambda **kwargs: 1,
        )

        monkeypatch.setattr(
            f"{module}.get_dataset_chunk_metadata",
            lambda dataset_chunk_id: {
                "status": "CREATED",
                "row_count": None,
                "checksum": None,
            },
        )

        monkeypatch.setattr(
            f"{module}.recover_stale_running_chunk",
            lambda *args, **kwargs: None,
        )

        monkeypatch.setattr(
            f"{module}.start_chunk_attempt",
            lambda dataset_chunk_id: 1,
        )

        monkeypatch.setattr(
            f"{module}.finish_chunk_attempt",
            lambda **kwargs: None,
        )

        monkeypatch.setattr(
            f"{module}.invalidate_dataset_chunk",
            lambda dataset_chunk_id: None,
        )

        monkeypatch.setattr(
            f"{module}.get_chunk_completion_summary",
            lambda dataset_version_id: {
                "total_chunks": 1,
                "validated_chunks": 1,
                "failed_chunks": 0,
                "processing_chunks": 0,
                "created_chunks": 0,
                "min_chunk_index": 1,
                "max_chunk_index": 1,
            },
        )