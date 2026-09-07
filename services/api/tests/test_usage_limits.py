from datetime import UTC, datetime, timedelta

import pytest

from app.usage_limits import (
    FirestoreQuotaStore,
    InMemoryQuotaStore,
    QuotaExceeded,
    QuotaRequest,
    UsagePolicy,
)


def policy(**overrides: int | bool) -> UsagePolicy:
    values: dict[str, int | bool] = {
        "enabled": True,
        "visitor_daily_film_limit": 5,
        "ip_daily_film_limit": 10,
        "ip_max_concurrent_films": 2,
        "global_daily_film_limit": 30,
        "global_daily_film_hard_max": 100,
        "global_max_concurrent_films": 6,
        "visitor_daily_original_song_limit": 3,
        "global_daily_original_song_limit": 20,
    }
    values.update(overrides)
    return UsagePolicy(**values)


def request(*, visitor: str = "visitor-a", ip: str = "203.0.113.8", song: bool = False, now: datetime | None = None) -> QuotaRequest:
    return QuotaRequest(
        visitor_id=visitor,
        client_ip=ip,
        includes_original_song=song,
        admitted_at=now or datetime(2026, 9, 7, 8, tzinfo=UTC),
    )


def test_rejects_the_sixth_film_for_one_visitor_without_consuming_an_ip_slot() -> None:
    store = InMemoryQuotaStore(policy())
    for _ in range(5):
        store.acquire(request()).release()

    with pytest.raises(QuotaExceeded, match="daily film limit") as error:
        store.acquire(request())

    assert error.value.scope == "visitor"
    assert store.snapshot(request())["ip_film_admitted"] == 5


def test_rejects_the_eleventh_film_for_one_ip_across_visitors() -> None:
    store = InMemoryQuotaStore(policy(visitor_daily_film_limit=20))
    for index in range(10):
        store.acquire(request(visitor=f"visitor-{index}")).release()

    with pytest.raises(QuotaExceeded) as error:
        store.acquire(request(visitor="visitor-eleven"))

    assert error.value.scope == "ip"


def test_rejects_more_than_two_concurrent_films_for_one_ip_and_release_restores_capacity() -> None:
    store = InMemoryQuotaStore(policy())
    first = store.acquire(request(visitor="one"))
    second = store.acquire(request(visitor="two"))

    with pytest.raises(QuotaExceeded) as error:
        store.acquire(request(visitor="three"))
    assert error.value.scope == "ip_concurrency"

    first.release()
    replacement = store.acquire(request(visitor="three"))
    replacement.release()
    second.release()
    assert store.snapshot(request())["ip_in_flight"] == 0


def test_context_manager_releases_concurrency_after_failure_but_keeps_the_admission() -> None:
    store = InMemoryQuotaStore(policy())

    with pytest.raises(RuntimeError):
        with store.acquire(request()):
            raise RuntimeError("render failed")

    snapshot = store.snapshot(request())
    assert snapshot["ip_in_flight"] == 0
    assert snapshot["visitor_film_admitted"] == 1


def test_global_daily_limit_is_shared_across_visitors_and_ips() -> None:
    store = InMemoryQuotaStore(policy(global_daily_film_limit=2))
    store.acquire(request(visitor="one", ip="203.0.113.1")).release()
    store.acquire(request(visitor="two", ip="203.0.113.2")).release()

    with pytest.raises(QuotaExceeded) as error:
        store.acquire(request(visitor="three", ip="203.0.113.3"))

    assert error.value.scope == "global"


def test_original_song_limits_are_checked_atomically_with_film_limits() -> None:
    store = InMemoryQuotaStore(policy(visitor_daily_original_song_limit=1))
    store.acquire(request(song=True)).release()

    with pytest.raises(QuotaExceeded) as error:
        store.acquire(request(song=True))

    assert error.value.scope == "visitor_song"
    assert store.snapshot(request())["visitor_film_admitted"] == 1


def test_no_sound_admission_cannot_be_upgraded_to_original_song() -> None:
    store = InMemoryQuotaStore(policy())
    lease = store.acquire(request(song=False))

    with pytest.raises(QuotaExceeded) as error:
        store.consume(lease.admission_id, request(song=True), "export")

    assert error.value.scope == "admission_soundtrack"


def test_admission_has_bounded_stage_uses() -> None:
    store = InMemoryQuotaStore(policy())
    lease = store.acquire(request(song=True))

    for index in range(15):
        store.consume(
            lease.admission_id,
            request(song=True),
            "media_analysis",
            operation_key=f"media-{index}",
            max_uses=15,
            max_attempts=2,
        )
    with pytest.raises(QuotaExceeded, match="already been used"):
        store.consume(
            lease.admission_id,
            request(song=True),
            "media_analysis",
            operation_key="media-16",
            max_uses=15,
            max_attempts=2,
        )

    store.consume(lease.admission_id, request(song=True), "planning")
    with pytest.raises(QuotaExceeded, match="already been used"):
        store.consume(lease.admission_id, request(song=True), "planning")

    store.consume(lease.admission_id, request(song=True), "export")
    with pytest.raises(QuotaExceeded, match="already been used"):
        store.consume(lease.admission_id, request(song=True), "export")


def test_media_retry_is_idempotent_at_the_configured_maximum() -> None:
    store = InMemoryQuotaStore(policy())
    lease = store.acquire(request())

    for index in range(15):
        store.consume(
            lease.admission_id,
            request(),
            "media_analysis",
            operation_key=f"media-{index}",
            max_uses=15,
            max_attempts=2,
        )

    store.consume(
        lease.admission_id,
        request(),
        "media_analysis",
        operation_key="media-0",
        max_uses=15,
        max_attempts=2,
    )

    with pytest.raises(QuotaExceeded, match="already been used"):
        store.consume(
            lease.admission_id,
            request(),
            "media_analysis",
            operation_key="media-0",
            max_uses=15,
            max_attempts=2,
        )

    with pytest.raises(QuotaExceeded, match="already been used"):
        store.consume(
            lease.admission_id,
            request(),
            "media_analysis",
            operation_key="different-media",
            max_uses=15,
            max_attempts=2,
        )


def test_original_song_can_only_be_consumed_once_across_song_and_export() -> None:
    store = InMemoryQuotaStore(policy())
    lease = store.acquire(request(song=True))
    store.consume(lease.admission_id, request(song=True), "song")

    with pytest.raises(QuotaExceeded, match="already been used"):
        store.consume(lease.admission_id, request(song=True), "export")


def test_utc_day_boundary_starts_new_counters() -> None:
    store = InMemoryQuotaStore(policy(visitor_daily_film_limit=1))
    before_midnight = datetime(2026, 9, 7, 23, 59, tzinfo=UTC)
    store.acquire(request(now=before_midnight)).release()

    next_day = before_midnight + timedelta(minutes=2)
    store.acquire(request(now=next_day)).release()

    assert store.snapshot(request(now=next_day))["visitor_film_admitted"] == 1


def test_policy_rejects_a_runtime_daily_limit_above_the_reviewed_hard_maximum() -> None:
    with pytest.raises(ValueError, match="hard maximum"):
        policy(global_daily_film_limit=101)


def test_disabled_policy_returns_a_noop_lease() -> None:
    store = InMemoryQuotaStore(policy(enabled=False, visitor_daily_film_limit=1))
    for _ in range(3):
        store.acquire(request()).release()

    assert store.snapshot(request())["visitor_film_admitted"] == 0


def test_expired_concurrency_lease_is_reclaimed_after_a_worker_disappears() -> None:
    current = datetime(2026, 9, 7, 8, tzinfo=UTC)
    store = InMemoryQuotaStore(policy(ip_max_concurrent_films=1), clock=lambda: current)
    store.acquire(request(now=current))

    current += timedelta(minutes=17)
    replacement = store.acquire(request(visitor="visitor-b", now=current))

    assert replacement.admission_id is not None


def test_firestore_snapshots_are_resolved_by_reference_path_not_result_order() -> None:
    class Reference:
        def __init__(self, path: str) -> None:
            self.path = path

    class Snapshot:
        def __init__(self, path: str) -> None:
            self.reference = Reference(path)

    visitor = Snapshot("quota/visitor")
    ip = Snapshot("quota/ip")
    global_counter = Snapshot("quota/global")

    resolved = FirestoreQuotaStore._by_path([global_counter, visitor, ip])

    assert resolved["quota/visitor"] is visitor
    assert resolved["quota/ip"] is ip
    assert resolved["quota/global"] is global_counter
