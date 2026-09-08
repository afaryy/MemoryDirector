import subprocess

import pytest
from httpx import ASGITransport, AsyncClient

import app.main as main_module
from app.media_analysis import StoredMedia
from app.usage_limits import QuotaExceeded


class ThumbnailStorage:
    def __init__(self) -> None:
        self.put_calls: list[tuple[str, str, bytes]] = []
        self.objects: dict[str, bytes] = {}
        self.metadata: dict[str, StoredMedia] = {}

    def put(self, media_id: str, content_type: str, body: bytes) -> StoredMedia:
        self.put_calls.append((media_id, content_type, body))
        stored = StoredMedia(
            media_id=media_id,
            content_type=content_type,
            size_bytes=len(body),
            sha256=media_id.removeprefix("sha256:"),
            gs_uri=f"gs://private/media/{media_id}/original",
        )
        self.objects[media_id] = body
        self.metadata[media_id] = stored
        return stored

    def read(self, media_id: str):
        if media_id not in self.objects:
            return None
        return self.metadata[media_id], self.objects[media_id]

    def save_decision(self, state):
        return state

    def load_decision(self, media_id: str):
        return None


class RecordingThumbnailer:
    def __init__(self, result: bytes = b"jpeg-preview") -> None:
        self.result = result
        self.calls: list[tuple[bytes, str]] = []

    def create(self, contents: bytes, suffix: str) -> bytes:
        self.calls.append((contents, suffix))
        return self.result


@pytest.mark.anyio
async def test_video_thumbnail_requires_explicit_consent_before_storage(monkeypatch: pytest.MonkeyPatch) -> None:
    storage = ThumbnailStorage()
    thumbnailer = RecordingThumbnailer()
    monkeypatch.setattr(main_module, "get_media_storage", lambda: storage)
    monkeypatch.setattr(main_module, "get_video_thumbnailer", lambda: thumbnailer, raising=False)

    async with AsyncClient(transport=ASGITransport(app=main_module.app), base_url="http://test") as client:
        response = await client.post(
            "/media/thumbnail",
            files={"media": ("memory.mp4", b"video", "video/mp4")},
            data={"consent": "false"},
        )

    assert response.status_code == 409
    assert storage.put_calls == []
    assert thumbnailer.calls == []


@pytest.mark.anyio
async def test_video_thumbnail_stores_private_source_and_returns_jpeg(monkeypatch: pytest.MonkeyPatch) -> None:
    storage = ThumbnailStorage()
    thumbnailer = RecordingThumbnailer()
    monkeypatch.setattr(main_module, "get_media_storage", lambda: storage)
    monkeypatch.setattr(main_module, "get_video_thumbnailer", lambda: thumbnailer, raising=False)

    async with AsyncClient(transport=ASGITransport(app=main_module.app), base_url="http://test") as client:
        response = await client.post(
            "/media/thumbnail",
            files={"media": ("IMG_3419.MOV", b"video", "video/quicktime")},
            data={"consent": "true"},
        )

    assert response.status_code == 201
    assert response.headers["content-type"] == "image/jpeg"
    assert response.headers["x-memory-director-media-id"].startswith("sha256:")
    assert response.content == b"jpeg-preview"
    assert storage.put_calls[0][1:] == ("video/quicktime", b"video")
    assert thumbnailer.calls == [(b"video", ".mov")]
    assert "gs://" not in response.text


@pytest.mark.anyio
async def test_video_thumbnail_accepts_an_extension_only_iphone_mov(monkeypatch: pytest.MonkeyPatch) -> None:
    storage = ThumbnailStorage()
    thumbnailer = RecordingThumbnailer()
    monkeypatch.setattr(main_module, "get_media_storage", lambda: storage)
    monkeypatch.setattr(main_module, "get_video_thumbnailer", lambda: thumbnailer, raising=False)

    async with AsyncClient(transport=ASGITransport(app=main_module.app), base_url="http://test") as client:
        response = await client.post(
            "/media/thumbnail",
            files={"media": ("IMG_3419.MOV", b"video", "application/octet-stream")},
            data={"consent": "true"},
        )

    assert response.status_code == 201
    assert storage.put_calls[0][1] == "video/quicktime"
    assert thumbnailer.calls == [(b"video", ".mov")]


@pytest.mark.anyio
async def test_video_thumbnail_rejects_photo_upload(monkeypatch: pytest.MonkeyPatch) -> None:
    storage = ThumbnailStorage()
    thumbnailer = RecordingThumbnailer()
    monkeypatch.setattr(main_module, "get_media_storage", lambda: storage)
    monkeypatch.setattr(main_module, "get_video_thumbnailer", lambda: thumbnailer, raising=False)

    async with AsyncClient(transport=ASGITransport(app=main_module.app), base_url="http://test") as client:
        response = await client.post(
            "/media/thumbnail",
            files={"media": ("memory.jpg", b"photo", "image/jpeg")},
            data={"consent": "true"},
        )

    assert response.status_code == 415
    assert storage.put_calls == []


@pytest.mark.anyio
async def test_video_thumbnail_uses_shared_quota_before_ffmpeg(monkeypatch: pytest.MonkeyPatch) -> None:
    class RejectingQuotaStore:
        def consume_thumbnail(self, *_args, **_kwargs) -> None:
            raise QuotaExceeded("ip_thumbnail", "Daily video preview limit reached.")

    thumbnailer = RecordingThumbnailer()
    monkeypatch.setenv("QUOTA_ENABLED", "true")
    monkeypatch.setattr(main_module, "get_quota_store", lambda: RejectingQuotaStore())
    monkeypatch.setattr(main_module, "get_video_thumbnailer", lambda: thumbnailer, raising=False)

    async with AsyncClient(transport=ASGITransport(app=main_module.app), base_url="http://test") as client:
        response = await client.post(
            "/media/thumbnail",
            files={"media": ("memory.mp4", b"video", "video/mp4")},
            data={"consent": "true"},
            headers={"X-Memory-Director-Visitor": "visitor-a"},
        )

    assert response.status_code == 429
    assert response.headers["retry-after"] == "86400"
    assert thumbnailer.calls == []


def test_subprocess_thumbnailer_extracts_a_bounded_representative_jpeg(monkeypatch, tmp_path) -> None:
    from app.media_thumbnail import SubprocessVideoThumbnailer

    recorded: list[list[str]] = []

    def fake_run(command, **kwargs):
        recorded.append(command)
        (tmp_path / "preview.jpg").write_bytes(b"jpeg")

    monkeypatch.setattr("app.media_thumbnail.tempfile.TemporaryDirectory", lambda **_kwargs: _TemporaryDirectory(tmp_path))
    monkeypatch.setattr("app.media_thumbnail.subprocess.run", fake_run)

    result = SubprocessVideoThumbnailer().create(b"video", ".mp4")

    assert result == b"jpeg"
    assert recorded[0][0:2] == ["ffmpeg", "-y"]
    filter_expression = recorded[0][recorded[0].index("-vf") + 1]
    assert "thumbnail=30" in filter_expression
    assert "scale=480:480:force_original_aspect_ratio=decrease" in filter_expression
    assert recorded[0][recorded[0].index("-protocol_whitelist") + 1] == "file,pipe"
    assert recorded[0][recorded[0].index("-f") + 1] == "mov"
    assert recorded[0][-1].endswith("preview.jpg")


class _TemporaryDirectory:
    def __init__(self, path) -> None:
        self.path = path

    def __enter__(self):
        return str(self.path)

    def __exit__(self, *_args):
        return None
