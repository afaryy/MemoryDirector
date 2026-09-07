from __future__ import annotations

import os
from hashlib import sha256
from dataclasses import dataclass
from datetime import UTC, datetime
from threading import RLock
from typing import Callable, Protocol
from uuid import uuid4


class QuotaExceeded(RuntimeError):
    def __init__(self, scope: str, message: str = "This usage limit has been reached. Please try again tomorrow.") -> None:
        super().__init__(message)
        self.scope = scope


@dataclass(frozen=True)
class UsagePolicy:
    enabled: bool
    visitor_daily_film_limit: int
    ip_daily_film_limit: int
    ip_max_concurrent_films: int
    global_daily_film_limit: int
    global_daily_film_hard_max: int
    global_max_concurrent_films: int
    visitor_daily_original_song_limit: int
    global_daily_original_song_limit: int

    def __post_init__(self) -> None:
        numeric_values = (
            self.visitor_daily_film_limit,
            self.ip_daily_film_limit,
            self.ip_max_concurrent_films,
            self.global_daily_film_limit,
            self.global_daily_film_hard_max,
            self.global_max_concurrent_films,
            self.visitor_daily_original_song_limit,
            self.global_daily_original_song_limit,
        )
        if any(value < 1 for value in numeric_values):
            raise ValueError("Usage limits must be positive integers.")
        if self.global_daily_film_limit > self.global_daily_film_hard_max:
            raise ValueError("Global daily film limit exceeds the reviewed hard maximum.")

    @classmethod
    def from_environment(cls) -> UsagePolicy:
        def integer(name: str, default: int) -> int:
            return int(os.environ.get(name, str(default)))

        return cls(
            enabled=os.environ.get("QUOTA_ENABLED", "false").lower() == "true",
            visitor_daily_film_limit=integer("VISITOR_DAILY_FILM_LIMIT", 5),
            ip_daily_film_limit=integer("IP_DAILY_FILM_LIMIT", 10),
            ip_max_concurrent_films=integer("IP_MAX_CONCURRENT_FILMS", 2),
            global_daily_film_limit=integer("GLOBAL_DAILY_FILM_LIMIT", 30),
            global_daily_film_hard_max=integer("GLOBAL_DAILY_FILM_HARD_MAX", 100),
            global_max_concurrent_films=integer("GLOBAL_MAX_CONCURRENT_FILMS", 6),
            visitor_daily_original_song_limit=integer("VISITOR_DAILY_ORIGINAL_SONG_LIMIT", 3),
            global_daily_original_song_limit=integer("GLOBAL_DAILY_ORIGINAL_SONG_LIMIT", 20),
        )


@dataclass(frozen=True)
class QuotaRequest:
    visitor_id: str
    client_ip: str
    includes_original_song: bool = False
    admitted_at: datetime | None = None

    @property
    def utc_day(self) -> str:
        current = self.admitted_at or datetime.now(UTC)
        if current.tzinfo is None:
            current = current.replace(tzinfo=UTC)
        return current.astimezone(UTC).date().isoformat()


class QuotaLease:
    def __init__(self, release_callback: Callable[[], None]) -> None:
        self._release_callback = release_callback
        self._released = False

    def release(self) -> None:
        if self._released:
            return
        self._released = True
        self._release_callback()

    def __enter__(self) -> QuotaLease:
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.release()


class QuotaStore(Protocol):
    def acquire(self, request: QuotaRequest) -> QuotaLease: ...


class InMemoryQuotaStore:
    """Thread-safe behavioral reference used when exercising quota policy locally."""

    def __init__(self, policy: UsagePolicy) -> None:
        self.policy = policy
        self._lock = RLock()
        self._daily: dict[str, dict[str, int]] = {}

    def _key(self, day: str, scope: str, identifier: str = "all") -> str:
        return f"{day}:{scope}:{identifier}"

    def _counter(self, key: str) -> dict[str, int]:
        return self._daily.setdefault(key, {"film": 0, "song": 0, "in_flight": 0})

    def acquire(self, request: QuotaRequest) -> QuotaLease:
        if not self.policy.enabled:
            return QuotaLease(lambda: None)

        day = request.utc_day
        with self._lock:
            visitor = self._counter(self._key(day, "visitor", request.visitor_id))
            ip = self._counter(self._key(day, "ip", request.client_ip))
            global_counter = self._counter(self._key(day, "global"))
            checks = [
                (visitor["film"] >= self.policy.visitor_daily_film_limit, "visitor"),
                (ip["film"] >= self.policy.ip_daily_film_limit, "ip"),
                (ip["in_flight"] >= self.policy.ip_max_concurrent_films, "ip_concurrency"),
                (global_counter["film"] >= self.policy.global_daily_film_limit, "global"),
                (global_counter["in_flight"] >= self.policy.global_max_concurrent_films, "global_concurrency"),
            ]
            if request.includes_original_song:
                checks.extend([
                    (visitor["song"] >= self.policy.visitor_daily_original_song_limit, "visitor_song"),
                    (global_counter["song"] >= self.policy.global_daily_original_song_limit, "global_song"),
                ])
            for exceeded, scope in checks:
                if exceeded:
                    raise QuotaExceeded(scope, "Your daily film limit has been reached. Please try again tomorrow.")

            visitor["film"] += 1
            ip["film"] += 1
            ip["in_flight"] += 1
            global_counter["film"] += 1
            global_counter["in_flight"] += 1
            if request.includes_original_song:
                visitor["song"] += 1
                global_counter["song"] += 1

        def release() -> None:
            with self._lock:
                ip["in_flight"] = max(0, ip["in_flight"] - 1)
                global_counter["in_flight"] = max(0, global_counter["in_flight"] - 1)

        return QuotaLease(release)

    def snapshot(self, request: QuotaRequest) -> dict[str, int]:
        day = request.utc_day
        with self._lock:
            visitor = self._counter(self._key(day, "visitor", request.visitor_id))
            ip = self._counter(self._key(day, "ip", request.client_ip))
            global_counter = self._counter(self._key(day, "global"))
            return {
                "visitor_film_admitted": visitor["film"],
                "visitor_song_admitted": visitor["song"],
                "ip_film_admitted": ip["film"],
                "ip_in_flight": ip["in_flight"],
                "global_film_admitted": global_counter["film"],
                "global_song_admitted": global_counter["song"],
                "global_in_flight": global_counter["in_flight"],
            }


def quota_document_id(day: str, scope: str, identifier: str) -> str:
    digest = sha256(identifier.encode("utf-8")).hexdigest()
    return f"{day}-{scope}-{digest}"


class FirestoreQuotaStore:
    """Atomic quota admission shared by every API instance."""

    def __init__(self, policy: UsagePolicy, client) -> None:
        self.policy = policy
        self.client = client

    @staticmethod
    def _values(snapshot) -> dict[str, int]:
        raw = snapshot.to_dict() if snapshot.exists else {}
        return {
            "film": int(raw.get("film", 0)),
            "song": int(raw.get("song", 0)),
            "in_flight": int(raw.get("in_flight", 0)),
        }

    def acquire(self, request: QuotaRequest) -> QuotaLease:
        if not self.policy.enabled:
            return QuotaLease(lambda: None)

        from google.cloud import firestore

        day = request.utc_day
        visitor_ref = self.client.collection("quota_counters").document(
            quota_document_id(day, "visitor", request.visitor_id)
        )
        ip_ref = self.client.collection("quota_counters").document(
            quota_document_id(day, "ip", request.client_ip)
        )
        global_ref = self.client.collection("quota_counters").document(f"{day}-global")
        lease_ref = self.client.collection("quota_leases").document(uuid4().hex)

        @firestore.transactional
        def admit(transaction) -> None:
            visitor_snapshot, ip_snapshot, global_snapshot = list(
                transaction.get_all([visitor_ref, ip_ref, global_ref])
            )
            visitor = self._values(visitor_snapshot)
            ip = self._values(ip_snapshot)
            global_counter = self._values(global_snapshot)
            checks = [
                (visitor["film"] >= self.policy.visitor_daily_film_limit, "visitor"),
                (ip["film"] >= self.policy.ip_daily_film_limit, "ip"),
                (ip["in_flight"] >= self.policy.ip_max_concurrent_films, "ip_concurrency"),
                (global_counter["film"] >= self.policy.global_daily_film_limit, "global"),
                (global_counter["in_flight"] >= self.policy.global_max_concurrent_films, "global_concurrency"),
            ]
            if request.includes_original_song:
                checks.extend([
                    (visitor["song"] >= self.policy.visitor_daily_original_song_limit, "visitor_song"),
                    (global_counter["song"] >= self.policy.global_daily_original_song_limit, "global_song"),
                ])
            for exceeded, scope in checks:
                if exceeded:
                    raise QuotaExceeded(scope, "Your daily film limit has been reached. Please try again tomorrow.")

            visitor["film"] += 1
            ip["film"] += 1
            ip["in_flight"] += 1
            global_counter["film"] += 1
            global_counter["in_flight"] += 1
            if request.includes_original_song:
                visitor["song"] += 1
                global_counter["song"] += 1
            transaction.set(visitor_ref, {**visitor, "day": day, "scope": "visitor"})
            transaction.set(ip_ref, {**ip, "day": day, "scope": "ip"})
            transaction.set(global_ref, {**global_counter, "day": day, "scope": "global"})
            transaction.set(
                lease_ref,
                {
                    "released": False,
                    "ip_counter": ip_ref.path,
                    "global_counter": global_ref.path,
                    "day": day,
                },
            )

        admit(self.client.transaction())

        def release() -> None:
            @firestore.transactional
            def release_transaction(transaction) -> None:
                lease_snapshot = lease_ref.get(transaction=transaction)
                if not lease_snapshot.exists or lease_snapshot.to_dict().get("released") is True:
                    return
                ip_snapshot, global_snapshot = list(transaction.get_all([ip_ref, global_ref]))
                ip = self._values(ip_snapshot)
                global_counter = self._values(global_snapshot)
                ip["in_flight"] = max(0, ip["in_flight"] - 1)
                global_counter["in_flight"] = max(0, global_counter["in_flight"] - 1)
                transaction.update(ip_ref, {"in_flight": ip["in_flight"]})
                transaction.update(global_ref, {"in_flight": global_counter["in_flight"]})
                transaction.update(lease_ref, {"released": True})

            release_transaction(self.client.transaction())

        return QuotaLease(release)


def quota_store_from_environment(*, client_factory=None) -> QuotaStore:
    policy = UsagePolicy.from_environment()
    if not policy.enabled:
        return InMemoryQuotaStore(policy)
    if client_factory is None:
        from google.cloud import firestore

        client_factory = firestore.Client
    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    database = os.environ.get("QUOTA_FIRESTORE_DATABASE", "(default)")
    return FirestoreQuotaStore(policy, client_factory(project=project, database=database))
