from app.media_storage import InMemoryMediaStorage


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
