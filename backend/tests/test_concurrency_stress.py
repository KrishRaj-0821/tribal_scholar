"""
Convenience entrypoint for executing concurrency stress tests directly via:
    python -m pytest -v tests/test_concurrency_stress.py

All implementation is canonically housed in tests.integration.test_concurrency_stress.
"""
from tests.integration.test_concurrency_stress import (
    stress_env,
    ensure_postgresql_backend,
    test_concurrency_stress_20_different_keys_single_winner,
    test_same_idempotency_key_race_20_threads_zero_duplicates,
    test_concurrent_field_patch_10_requests_stale_revisions_produce_409,
    test_submission_and_eligibility_snapshot_immutability,
    test_submission_transaction_failure_causes_full_rollback,
    test_idempotency_record_expiration_and_renewal,
    test_application_revision_monotonicity_and_freeze,
)

__all__ = [
    "stress_env",
    "ensure_postgresql_backend",
    "test_concurrency_stress_20_different_keys_single_winner",
    "test_same_idempotency_key_race_20_threads_zero_duplicates",
    "test_concurrent_field_patch_10_requests_stale_revisions_produce_409",
    "test_submission_and_eligibility_snapshot_immutability",
    "test_submission_transaction_failure_causes_full_rollback",
    "test_idempotency_record_expiration_and_renewal",
    "test_application_revision_monotonicity_and_freeze",
]
