"""Pure helpers for Worker database retry and lease-authority decisions."""

from __future__ import annotations


def database_retry_delay(
    failure_count: int,
    *,
    initial_seconds: float,
    maximum_seconds: float,
    jitter_sample: float,
) -> float:
    """Return bounded exponential backoff with a 0.8-1.2 jitter multiplier."""
    count = max(1, failure_count)
    base = min(maximum_seconds, initial_seconds * (2 ** (count - 1)))
    bounded_sample = min(1.0, max(0.0, jitter_sample))
    return base * (0.8 + (0.4 * bounded_sample))


def lease_authority_expired(*, last_confirmed_at: float, now: float, lease_seconds: float) -> bool:
    """Fail closed once a Worker cannot confirm database authority for one lease window."""
    return now - last_confirmed_at >= lease_seconds
