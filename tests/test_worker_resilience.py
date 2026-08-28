import pytest

from app.worker_resilience import database_retry_delay, lease_authority_expired


def test_database_retry_delay_is_exponential_bounded_and_jittered():
    assert database_retry_delay(1, initial_seconds=1, maximum_seconds=8, jitter_sample=0.5) == 1
    assert database_retry_delay(2, initial_seconds=1, maximum_seconds=8, jitter_sample=0.5) == 2
    assert database_retry_delay(8, initial_seconds=1, maximum_seconds=8, jitter_sample=0.5) == 8
    assert database_retry_delay(1, initial_seconds=1, maximum_seconds=8, jitter_sample=0) == 0.8
    assert database_retry_delay(1, initial_seconds=1, maximum_seconds=8, jitter_sample=1) == pytest.approx(1.2)


def test_lease_authority_expires_only_after_the_full_window():
    assert lease_authority_expired(last_confirmed_at=100, now=129.999, lease_seconds=30) is False
    assert lease_authority_expired(last_confirmed_at=100, now=130, lease_seconds=30) is True
