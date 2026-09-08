from __future__ import annotations

import os
from hashlib import sha256
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from threading import RLock
from typing import Callable, Literal, Protocol
from uuid import uuid4


GATE_MESSAGES = {
    "visitor": "You have reached today's film limit on this device. Please try again tomorrow.",
    "ip": "This network has reached today's film limit. Please try again tomorrow.",
    "ip_concurrency": (
        "This network is already making the maximum number of films. "
        "Please wait a few minutes, then try again."
    ),
    "global": "Memory Director has reached today's shared film limit. Please try again tomorrow.",
    "global_concurrency": "Memory Director is busy making other films. Please wait a few minutes, then try again.",
    "visitor_song": (
        "You have reached today's original-song limit. Choose Gentle instrumental or No music, "
        "or try again tomorrow."
    ),
    "global_song": (
        "Original-song creation has reached today's shared limit. Choose Gentle instrumental or No music, "
        "or try again tomorrow."
    ),
}


class QuotaExceeded(RuntimeError):
    def __init__(self, scope: str, message: str | None = None) -> None:
        fallback = "This usage limit has been reached. Please try again tomorrow."
        super().__init__(message or GATE_MESSAGES.get(scope, fallback))
        self.scope = scope
        self.retry_after_seconds = 60 if scope in {"ip_concurrency", "global_concurrency"} else 86_400


AdmissionStage = Literal["media_analysis", "planning", "song", "export"]
STAGE_LIMITS: dict[AdmissionStage, int] = {
    "planning": 1,
    "song": 1,
    "export": 1,
}


def stage_limit(stage: AdmissionStage, max_uses: int | None) -> int:
    if stage == "media_analysis":
        if max_uses is None or max_uses < 1:
            raise ValueError("media analysis requires its configured positive media limit")
        return max_uses
    return STAGE_LIMITS[stage]


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
    def __init__(self, release_callback: Callable[[], None], admission_id: str | None = None) -> None:
        self._release_callback = release_callback
        self._released = False
        self.admission_id = admission_id

    def release(self) -> None:
        if self._released:
            return
        self._release_callback()
        self._released = True

    def __enter__(self) -> QuotaLease:
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.release()


class QuotaStore(Protocol):
    def acquire(self, request: QuotaRequest) -> QuotaLease: ...
    def consume_thumbnail(self, request: QuotaRequest, *, visitor_limit: int, ip_limit: int) -> None: ...
    def validate(self, admission_id: str, request: QuotaRequest) -> None: ...
    def consume(
        self,
        admission_id: str,
        request: QuotaRequest,
        stage: AdmissionStage,
        *,
        operation_key: str | None = None,
        max_uses: int | None = None,
        max_attempts: int | None = None,
    ) -> None: ...
    def release(self, admission_id: str) -> None: ...


class InMemoryQuotaStore:
    """Thread-safe behavioral reference used when exercising quota policy locally."""

    def __init__(self, policy: UsagePolicy, *, clock: Callable[[], datetime] | None = None) -> None:
        self.policy = policy
        self._clock = clock or (lambda: datetime.now(UTC))
        self._lock = RLock()
        self._daily: dict[str, dict[str, int]] = {}
        self._leases: dict[str, tuple[QuotaRequest, datetime, bool, dict[str, dict[str, int]]]] = {}

    def _key(self, day: str, scope: str, identifier: str = "all") -> str:
        return f"{day}:{scope}:{identifier}"

    def _counter(self, key: str) -> dict[str, int]:
        return self._daily.setdefault(key, {"film": 0, "song": 0, "thumbnail": 0, "in_flight": 0})

    def consume_thumbnail(self, request: QuotaRequest, *, visitor_limit: int, ip_limit: int) -> None:
        if not self.policy.enabled:
            return
        with self._lock:
            visitor = self._counter(self._key(request.utc_day, "visitor", request.visitor_id))
            ip = self._counter(self._key(request.utc_day, "ip", request.client_ip))
            if visitor["thumbnail"] >= visitor_limit:
                raise QuotaExceeded("visitor_thumbnail", "Daily video preview limit reached.")
            if ip["thumbnail"] >= ip_limit:
                raise QuotaExceeded("ip_thumbnail", "Daily video preview limit reached.")
            visitor["thumbnail"] += 1
            ip["thumbnail"] += 1

    def _reap_expired_leases(self) -> None:
        now = self._clock()
        for admission_id, (request, expires_at, released, stage_uses) in list(self._leases.items()):
            if released or expires_at > now:
                continue
            ip = self._counter(self._key(request.utc_day, "ip", request.client_ip))
            global_counter = self._counter(self._key(request.utc_day, "global"))
            ip["in_flight"] = max(0, ip["in_flight"] - 1)
            global_counter["in_flight"] = max(0, global_counter["in_flight"] - 1)
            self._leases[admission_id] = (request, expires_at, True, stage_uses)

    def acquire(self, request: QuotaRequest) -> QuotaLease:
        if not self.policy.enabled:
            return QuotaLease(lambda: None)

        day = request.utc_day
        with self._lock:
            self._reap_expired_leases()
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
                    raise QuotaExceeded(scope)

            admission_id = uuid4().hex
            visitor["film"] += 1
            ip["film"] += 1
            ip["in_flight"] += 1
            global_counter["film"] += 1
            global_counter["in_flight"] += 1
            if request.includes_original_song:
                visitor["song"] += 1
                global_counter["song"] += 1
            self._leases[admission_id] = (request, self._clock() + timedelta(minutes=16), False, {})

        def release() -> None:
            self.release(admission_id)

        return QuotaLease(release, admission_id)

    def validate(self, admission_id: str, request: QuotaRequest) -> None:
        if not self.policy.enabled:
            return
        with self._lock:
            lease = self._leases.get(admission_id)
            if lease is None or lease[2] or lease[1] <= self._clock():
                raise QuotaExceeded("admission", "Start a new film request and try again.")
            original = lease[0]
            if original.visitor_id != request.visitor_id or original.client_ip != request.client_ip:
                raise QuotaExceeded("admission", "This film request is not valid for this device.")

    def consume(
        self,
        admission_id: str,
        request: QuotaRequest,
        stage: AdmissionStage,
        *,
        operation_key: str | None = None,
        max_uses: int | None = None,
        max_attempts: int | None = None,
    ) -> None:
        if not self.policy.enabled:
            return
        with self._lock:
            self.validate(admission_id, request)
            lease = self._leases[admission_id]
            original, expires_at, released, stage_uses = lease
            if request.includes_original_song and not original.includes_original_song:
                raise QuotaExceeded("admission_soundtrack", "Start a new film request with an original song.")
            if stage_uses.get("export"):
                raise QuotaExceeded("admission_stage", "This film request has already been used.")
            if stage == "media_analysis" and not operation_key:
                raise ValueError("media analysis requires an operation key")
            if stage == "media_analysis" and (max_attempts is None or max_attempts < 1):
                raise ValueError("media analysis requires its configured positive attempt limit")
            required_stages = [stage]
            if stage == "export" and request.includes_original_song:
                required_stages.append("song")
            for required_stage in required_stages:
                key = operation_key if required_stage == "media_analysis" else "once"
                used_keys = stage_uses.get(required_stage, {})
                attempts = used_keys.get(key, 0)
                if attempts:
                    if required_stage == "media_analysis" and attempts < max_attempts:
                        continue
                    raise QuotaExceeded("admission_stage", "This film request has already been used.")
                if len(used_keys) >= stage_limit(required_stage, max_uses):
                    raise QuotaExceeded("admission_stage", "This film request has already been used.")
            updated = {name: dict(keys) for name, keys in stage_uses.items()}
            for required_stage in required_stages:
                key = operation_key if required_stage == "media_analysis" else "once"
                uses = updated.setdefault(required_stage, {})
                uses[key] = uses.get(key, 0) + 1
            self._leases[admission_id] = (original, expires_at, released, updated)

    def release(self, admission_id: str) -> None:
        if not self.policy.enabled:
            return
        with self._lock:
            lease = self._leases.get(admission_id)
            if lease is None or lease[2]:
                return
            request = lease[0]
            ip = self._counter(self._key(request.utc_day, "ip", request.client_ip))
            global_counter = self._counter(self._key(request.utc_day, "global"))
            ip["in_flight"] = max(0, ip["in_flight"] - 1)
            global_counter["in_flight"] = max(0, global_counter["in_flight"] - 1)
            self._leases[admission_id] = (lease[0], lease[1], True, lease[3])

    def snapshot(self, request: QuotaRequest) -> dict[str, int]:
        day = request.utc_day
        with self._lock:
            visitor = self._counter(self._key(day, "visitor", request.visitor_id))
            ip = self._counter(self._key(day, "ip", request.client_ip))
            global_counter = self._counter(self._key(day, "global"))
            return {
                "visitor_film_admitted": visitor["film"],
                "visitor_song_admitted": visitor["song"],
                "visitor_thumbnails": visitor["thumbnail"],
                "ip_film_admitted": ip["film"],
                "ip_in_flight": ip["in_flight"],
                "ip_thumbnails": ip["thumbnail"],
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
    def _by_path(snapshots) -> dict[str, object]:
        return {snapshot.reference.path: snapshot for snapshot in snapshots}

    @staticmethod
    def _values(snapshot) -> dict[str, object]:
        raw = snapshot.to_dict() if snapshot.exists else {}
        now = datetime.now(UTC)
        active_leases = {
            lease_id: expires_at
            for lease_id, expires_at in raw.get("active_leases", {}).items()
            if isinstance(expires_at, datetime) and expires_at > now
        }
        return {
            "film": int(raw.get("film", 0)),
            "song": int(raw.get("song", 0)),
            "thumbnail": int(raw.get("thumbnail", 0)),
            "in_flight": len(active_leases),
            "active_leases": active_leases,
        }

    def consume_thumbnail(self, request: QuotaRequest, *, visitor_limit: int, ip_limit: int) -> None:
        if not self.policy.enabled:
            return
        from google.cloud import firestore

        day = request.utc_day
        visitor_ref = self.client.collection("quota_counters").document(
            quota_document_id(day, "visitor", request.visitor_id)
        )
        ip_ref = self.client.collection("quota_counters").document(
            quota_document_id(day, "ip", request.client_ip)
        )

        @firestore.transactional
        def consume_transaction(transaction) -> None:
            snapshots = self._by_path(transaction.get_all([visitor_ref, ip_ref]))
            visitor = self._values(snapshots[visitor_ref.path])
            ip = self._values(snapshots[ip_ref.path])
            if visitor["thumbnail"] >= visitor_limit:
                raise QuotaExceeded("visitor_thumbnail", "Daily video preview limit reached.")
            if ip["thumbnail"] >= ip_limit:
                raise QuotaExceeded("ip_thumbnail", "Daily video preview limit reached.")
            transaction.set(
                visitor_ref,
                {"thumbnail": visitor["thumbnail"] + 1, "day": day, "scope": "visitor"},
                merge=True,
            )
            transaction.set(
                ip_ref,
                {"thumbnail": ip["thumbnail"] + 1, "day": day, "scope": "ip"},
                merge=True,
            )

        consume_transaction(self.client.transaction())

    def acquire(self, request: QuotaRequest) -> QuotaLease:
        if not self.policy.enabled:
            return QuotaLease(lambda: None)

        from google.cloud import firestore

        day = request.utc_day
        admission_id = uuid4().hex
        expires_at = datetime.now(UTC) + timedelta(minutes=16)
        visitor_ref = self.client.collection("quota_counters").document(
            quota_document_id(day, "visitor", request.visitor_id)
        )
        ip_ref = self.client.collection("quota_counters").document(
            quota_document_id(day, "ip", request.client_ip)
        )
        global_ref = self.client.collection("quota_counters").document(f"{day}-global")
        lease_ref = self.client.collection("quota_leases").document(admission_id)

        @firestore.transactional
        def admit(transaction) -> None:
            snapshots = self._by_path(transaction.get_all([visitor_ref, ip_ref, global_ref]))
            visitor_snapshot = snapshots[visitor_ref.path]
            ip_snapshot = snapshots[ip_ref.path]
            global_snapshot = snapshots[global_ref.path]
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
                    raise QuotaExceeded(scope)

            visitor["film"] += 1
            ip["film"] += 1
            global_counter["film"] += 1
            ip["active_leases"][admission_id] = expires_at
            global_counter["active_leases"][admission_id] = expires_at
            ip["in_flight"] = len(ip["active_leases"])
            global_counter["in_flight"] = len(global_counter["active_leases"])
            if request.includes_original_song:
                visitor["song"] += 1
                global_counter["song"] += 1
            visitor.pop("active_leases", None)
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
                    "visitor_hash": sha256(request.visitor_id.encode()).hexdigest(),
                    "ip_hash": sha256(request.client_ip.encode()).hexdigest(),
                    "includes_original_song": request.includes_original_song,
                    "stage_uses": {},
                    "expires_at": expires_at,
                },
            )

        admit(self.client.transaction())

        return QuotaLease(lambda: self.release(lease_ref.id), lease_ref.id)

    def validate(self, admission_id: str, request: QuotaRequest) -> None:
        if not self.policy.enabled:
            return
        snapshot = self.client.collection("quota_leases").document(admission_id).get()
        values = snapshot.to_dict() if snapshot.exists else {}
        expires_at = values.get("expires_at")
        if (
            not snapshot.exists
            or values.get("released") is True
            or not isinstance(expires_at, datetime)
            or expires_at <= datetime.now(UTC)
            or values.get("visitor_hash") != sha256(request.visitor_id.encode()).hexdigest()
            or values.get("ip_hash") != sha256(request.client_ip.encode()).hexdigest()
        ):
            raise QuotaExceeded("admission", "Start a new film request and try again.")

    def consume(
        self,
        admission_id: str,
        request: QuotaRequest,
        stage: AdmissionStage,
        *,
        operation_key: str | None = None,
        max_uses: int | None = None,
        max_attempts: int | None = None,
    ) -> None:
        if not self.policy.enabled:
            return
        from google.cloud import firestore

        lease_ref = self.client.collection("quota_leases").document(admission_id)

        @firestore.transactional
        def consume_transaction(transaction) -> None:
            snapshot = lease_ref.get(transaction=transaction)
            values = snapshot.to_dict() if snapshot.exists else {}
            expires_at = values.get("expires_at")
            if (
                not snapshot.exists
                or values.get("released") is True
                or not isinstance(expires_at, datetime)
                or expires_at <= datetime.now(UTC)
                or values.get("visitor_hash") != sha256(request.visitor_id.encode()).hexdigest()
                or values.get("ip_hash") != sha256(request.client_ip.encode()).hexdigest()
            ):
                raise QuotaExceeded("admission", "Start a new film request and try again.")
            if request.includes_original_song and values.get("includes_original_song") is not True:
                raise QuotaExceeded("admission_soundtrack", "Start a new film request with an original song.")
            raw_stage_uses = values.get("stage_uses", {})
            stage_uses: dict[str, dict[str, int]] = {}
            for key, value in raw_stage_uses.items():
                if isinstance(value, dict):
                    stage_uses[key] = {str(operation): int(attempts) for operation, attempts in value.items()}
                elif isinstance(value, list):
                    stage_uses[key] = {str(operation): 1 for operation in value}
                else:
                    stage_uses[key] = {f"__legacy_{index}": 1 for index in range(int(value))}
            if stage_uses.get("export"):
                raise QuotaExceeded("admission_stage", "This film request has already been used.")
            if stage == "media_analysis" and not operation_key:
                raise ValueError("media analysis requires an operation key")
            if stage == "media_analysis" and (max_attempts is None or max_attempts < 1):
                raise ValueError("media analysis requires its configured positive attempt limit")
            required_stages = [stage]
            if stage == "export" and request.includes_original_song:
                required_stages.append("song")
            for required_stage in required_stages:
                key = operation_key if required_stage == "media_analysis" else "once"
                used_keys = stage_uses.get(required_stage, {})
                attempts = used_keys.get(key, 0)
                if attempts:
                    if required_stage == "media_analysis" and attempts < max_attempts:
                        continue
                    raise QuotaExceeded("admission_stage", "This film request has already been used.")
                if len(used_keys) >= stage_limit(required_stage, max_uses):
                    raise QuotaExceeded("admission_stage", "This film request has already been used.")
            for required_stage in required_stages:
                key = operation_key if required_stage == "media_analysis" else "once"
                uses = stage_uses.setdefault(required_stage, {})
                uses[key] = uses.get(key, 0) + 1
            transaction.update(lease_ref, {"stage_uses": stage_uses})

        consume_transaction(self.client.transaction())

    def release(self, admission_id: str) -> None:
        if not self.policy.enabled:
            return
        from google.cloud import firestore

        lease_ref = self.client.collection("quota_leases").document(admission_id)

        @firestore.transactional
        def release_transaction(transaction) -> None:
            lease_snapshot = lease_ref.get(transaction=transaction)
            if not lease_snapshot.exists or lease_snapshot.to_dict().get("released") is True:
                return
            lease = lease_snapshot.to_dict()
            ip_ref = self.client.document(lease["ip_counter"])
            global_ref = self.client.document(lease["global_counter"])
            snapshots = self._by_path(transaction.get_all([ip_ref, global_ref]))
            ip = self._values(snapshots[ip_ref.path])
            global_counter = self._values(snapshots[global_ref.path])
            ip["active_leases"].pop(admission_id, None)
            global_counter["active_leases"].pop(admission_id, None)
            transaction.update(ip_ref, {"active_leases": ip["active_leases"], "in_flight": len(ip["active_leases"])})
            transaction.update(global_ref, {"active_leases": global_counter["active_leases"], "in_flight": len(global_counter["active_leases"])})
            transaction.update(lease_ref, {"released": True})

        release_transaction(self.client.transaction())


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
