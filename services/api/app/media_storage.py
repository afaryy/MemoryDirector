import os
from hashlib import sha256
from typing import Protocol

from app.media_analysis import MediaDecisionState, StoredMedia


class MediaStorageError(RuntimeError):
    """Raised when private media cannot be safely stored or read."""


class MediaStorage(Protocol):
    def put(self, media_id: str, content_type: str, body: bytes) -> StoredMedia: ...

    def read(self, media_id: str) -> tuple[StoredMedia, bytes] | None: ...

    def save_decision(self, state: MediaDecisionState) -> MediaDecisionState: ...

    def load_decision(self, media_id: str) -> MediaDecisionState | None: ...


class InMemoryMediaStorage:
    def __init__(self, bucket_name: str = "test-media") -> None:
        self.bucket_name = bucket_name
        self.objects: dict[str, bytes] = {}
        self.metadata: dict[str, StoredMedia] = {}
        self.decisions: dict[str, MediaDecisionState] = {}

    def put(self, media_id: str, content_type: str, body: bytes) -> StoredMedia:
        existing = self.objects.get(media_id)
        if existing is not None and existing != body:
            raise MediaStorageError("content-addressed object hash mismatch")
        self.objects.setdefault(media_id, body)
        digest = sha256(body).hexdigest()
        stored = StoredMedia(
            media_id=media_id,
            content_type=content_type,
            size_bytes=len(body),
            sha256=digest,
            gs_uri=f"gs://{self.bucket_name}/media/{media_id}/original",
        )
        self.metadata[media_id] = stored
        return stored

    def read(self, media_id: str) -> tuple[StoredMedia, bytes] | None:
        if media_id not in self.objects:
            return None
        return self.metadata[media_id], self.objects[media_id]

    def save_decision(self, state: MediaDecisionState) -> MediaDecisionState:
        if state.media_id not in self.objects:
            raise MediaStorageError("media object not found")
        self.decisions[state.media_id] = state
        return state

    def load_decision(self, media_id: str) -> MediaDecisionState | None:
        return self.decisions.get(media_id)


class GcsMediaStorage:
    def __init__(self, bucket_name: str, client: object | None = None) -> None:
        if client is None:
            from google.cloud import storage

            client = storage.Client(project=os.environ.get("GOOGLE_CLOUD_PROJECT"))
        self._bucket = client.bucket(bucket_name)
        self._bucket_name = bucket_name

    @classmethod
    def from_environment(cls) -> "GcsMediaStorage":
        bucket_name = os.environ.get("MEDIA_BUCKET")
        if not bucket_name:
            raise KeyError("MEDIA_BUCKET")
        return cls(bucket_name)

    def put(self, media_id: str, content_type: str, body: bytes) -> StoredMedia:
        digest = sha256(body).hexdigest()
        object_name = f"media/{media_id}/original"
        blob = self._bucket.blob(object_name)
        if blob.exists():
            existing = blob.download_as_bytes()
            if sha256(existing).hexdigest() != digest:
                raise MediaStorageError("content-addressed object hash mismatch")
        else:
            blob.upload_from_string(body, content_type=content_type)
        return StoredMedia(
            media_id=media_id,
            content_type=content_type,
            size_bytes=len(body),
            sha256=digest,
            gs_uri=f"gs://{self._bucket_name}/{object_name}",
        )

    def read(self, media_id: str) -> tuple[StoredMedia, bytes] | None:
        object_name = f"media/{media_id}/original"
        blob = self._bucket.blob(object_name)
        if not blob.exists():
            return None
        body = blob.download_as_bytes()
        content_type = blob.content_type or "application/octet-stream"
        digest = sha256(body).hexdigest()
        return (
            StoredMedia(
                media_id=media_id,
                content_type=content_type,
                size_bytes=len(body),
                sha256=digest,
                gs_uri=f"gs://{self._bucket_name}/{object_name}",
            ),
            body,
        )

    def save_decision(self, state: MediaDecisionState) -> MediaDecisionState:
        object_name = f"media/{state.media_id}/original"
        blob = self._bucket.blob(object_name)
        if not blob.exists():
            raise MediaStorageError("media object not found")
        blob.reload()
        metadata = blob.metadata or {}
        metadata["memory-director-decision-status"] = state.status
        metadata["memory-director-decision-reason"] = state.reason
        blob.metadata = metadata
        blob.patch()
        return state

    def load_decision(self, media_id: str) -> MediaDecisionState | None:
        object_name = f"media/{media_id}/original"
        blob = self._bucket.blob(object_name)
        if not blob.exists():
            return None
        blob.reload()
        metadata = blob.metadata or {}
        decision_status = metadata.get("memory-director-decision-status")
        if decision_status not in {"unselected", "selected", "held_back"}:
            return None
        return MediaDecisionState(
            media_id=media_id,
            status=decision_status,
            reason=metadata.get("memory-director-decision-reason", ""),
        )
