from app.media_storage import GcsMediaStorage, InMemoryMediaStorage


def test_in_memory_storage_records_content_addressed_private_object() -> None:
    storage = InMemoryMediaStorage(bucket_name="memory-director-media")

    stored = storage.put("sha256:abc", "image/jpeg", b"abc")

    assert stored.media_id == "sha256:abc"
    assert stored.content_type == "image/jpeg"
    assert stored.size_bytes == 3
    assert stored.sha256 == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    assert stored.gs_uri == "gs://memory-director-media/media/sha256:abc/original"
    assert storage.objects[stored.media_id] == b"abc"
    assert not hasattr(storage, "delete")


def test_gcs_read_refreshes_content_type_before_reusing_a_thumbnail_upload() -> None:
    class Blob:
        content_type = None

        def exists(self) -> bool:
            return True

        def reload(self) -> None:
            self.content_type = "video/quicktime"

        def download_as_bytes(self) -> bytes:
            return b"video"

    blob = Blob()

    class Bucket:
        def blob(self, _object_name: str) -> Blob:
            return blob

    class Client:
        def bucket(self, _bucket_name: str) -> Bucket:
            return Bucket()

    storage = GcsMediaStorage("private-media", client=Client())

    stored, body = storage.read("sha256:video") or (None, None)

    assert stored is not None
    assert stored.content_type == "video/quicktime"
    assert body == b"video"
