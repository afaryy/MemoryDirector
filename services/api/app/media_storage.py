import os
from hashlib import sha256
from typing import Protocol

from app.media_analysis import StoredMedia


class MediaStorage(Protocol):
    def put(self, media_id: str, content_type: str, body: bytes) -> StoredMedia: ...


class InMemoryMediaStorage:
    def __init__(self, bucket_name: str = "test-media") -> None:
        self.bucket_name = bucket_name
        self.objects: dict[str, bytes] = {}

    def put(self, media_id: str, content_type: str, body: bytes) -> StoredMedia:
        self.objects.setdefault(media_id, body)
        digest = sha256(body).hexdigest()
        return StoredMedia(
            media_id=media_id,
            content_type=content_type,
            size_bytes=len(body),
            sha256=digest,
            gs_uri=f"gs://{self.bucket_name}/media/{media_id}/original",
        )


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
        blob.upload_from_string(body, content_type=content_type)
        return StoredMedia(
            media_id=media_id,
            content_type=content_type,
            size_bytes=len(body),
            sha256=digest,
            gs_uri=f"gs://{self._bucket_name}/{object_name}",
        )

