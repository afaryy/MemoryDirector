import pytest
from httpx import ASGITransport, AsyncClient

import app.main as main_module
from app.media_analysis import MediaAnalysis, StoredMedia


class FakeStorage:
    def __init__(self) -> None:
        self.put_calls: list[tuple[str, str, bytes]] = []
        self.objects: dict[str, bytes] = {}
        self.metadata: dict[str, StoredMedia] = {}
        self.decisions: dict[str, tuple[str, str]] = {}

    def put(self, media_id: str, content_type: str, body: bytes) -> StoredMedia:
        self.put_calls.append((media_id, content_type, body))
        self.objects[media_id] = body
        stored = StoredMedia(
            media_id=media_id,
            content_type=content_type,
            size_bytes=len(body),
            sha256="stored-digest",
            gs_uri=f"gs://private/media/{media_id}/original",
        )
        self.metadata[media_id] = stored
        return stored

    def read(self, media_id: str) -> tuple[StoredMedia, bytes] | None:
        if media_id not in self.objects:
            return None
        return self.metadata[media_id], self.objects[media_id]

    def save_decision(self, state):
        self.decisions[state.media_id] = (state.status, state.reason)
        return state

    def load_decision(self, media_id: str):
        decision = self.decisions.get(media_id)
        if decision is None:
            return None
        from app.media_analysis import MediaDecisionState

        return MediaDecisionState(media_id=media_id, status=decision[0], reason=decision[1])


class FakeAnalyzer:
    def analyze(self, stored_media: StoredMedia) -> MediaAnalysis:
        return MediaAnalysis(
            media_id=stored_media.media_id,
            description="a family garden",
            quality_score=0.9,
            privacy_flags=[],
            orientation="landscape",
            duration_seconds=None,
        )


class FailingAnalyzer:
    def analyze(self, stored_media: StoredMedia) -> MediaAnalysis:
        raise RuntimeError("provider details must not reach the API")


class WrongIdAnalyzer:
    def analyze(self, stored_media: StoredMedia) -> MediaAnalysis:
        return MediaAnalysis(
            media_id="sha256:wrong",
            description="a family garden",
            quality_score=0.9,
            privacy_flags=[],
            orientation="landscape",
            duration_seconds=None,
        )


def patch_dependencies(monkeypatch: pytest.MonkeyPatch, storage: FakeStorage, analyzer: object) -> None:
    monkeypatch.setattr(main_module, "get_media_storage", lambda: storage, raising=False)
    monkeypatch.setattr(main_module, "get_media_analyzer", lambda: analyzer, raising=False)


@pytest.mark.anyio
async def test_analysis_requires_consent_before_reading_or_storing(monkeypatch: pytest.MonkeyPatch) -> None:
    storage = FakeStorage()
    patch_dependencies(monkeypatch, storage, FakeAnalyzer())

    async with AsyncClient(transport=ASGITransport(app=main_module.app), base_url="http://test") as client:
        response = await client.post(
            "/media/analyze",
            files={"media": ("memory.jpg", b"bytes", "image/jpeg")},
            data={"consent": "false"},
        )

    assert response.status_code == 409
    assert storage.put_calls == []


@pytest.mark.anyio
async def test_analysis_returns_safe_schema_without_private_uri(monkeypatch: pytest.MonkeyPatch) -> None:
    storage = FakeStorage()
    patch_dependencies(monkeypatch, storage, FakeAnalyzer())

    async with AsyncClient(transport=ASGITransport(app=main_module.app), base_url="http://test") as client:
        response = await client.post(
            "/media/analyze",
            files={"media": ("memory.jpg", b"bytes", "image/jpeg")},
            data={"consent": "true"},
        )

    assert response.status_code == 201
    assert response.json()["description"] == "a family garden"
    assert response.json()["decision_status"] == "unselected"
    assert "gs://" not in response.text


@pytest.mark.anyio
async def test_analysis_rejects_unsupported_mime(monkeypatch: pytest.MonkeyPatch) -> None:
    storage = FakeStorage()
    patch_dependencies(monkeypatch, storage, FakeAnalyzer())

    async with AsyncClient(transport=ASGITransport(app=main_module.app), base_url="http://test") as client:
        response = await client.post(
            "/media/analyze",
            files={"media": ("memory.txt", b"bytes", "text/plain")},
            data={"consent": "true"},
        )

    assert response.status_code == 415
    assert storage.put_calls == []


@pytest.mark.anyio
async def test_analysis_rejects_upload_over_50_mib(monkeypatch: pytest.MonkeyPatch) -> None:
    storage = FakeStorage()
    patch_dependencies(monkeypatch, storage, FakeAnalyzer())

    async with AsyncClient(transport=ASGITransport(app=main_module.app), base_url="http://test") as client:
        response = await client.post(
            "/media/analyze",
            files={"media": ("large.mp4", b"x" * (50 * 1024 * 1024 + 1), "video/mp4")},
            data={"consent": "true"},
        )

    assert response.status_code == 413
    assert storage.put_calls == []


@pytest.mark.anyio
async def test_analysis_requires_literal_true_consent(monkeypatch: pytest.MonkeyPatch) -> None:
    storage = FakeStorage()
    patch_dependencies(monkeypatch, storage, FakeAnalyzer())

    async with AsyncClient(transport=ASGITransport(app=main_module.app), base_url="http://test") as client:
        response = await client.post(
            "/media/analyze",
            files={"media": ("memory.jpg", b"bytes", "image/jpeg")},
            data={"consent": "yes"},
        )

    assert response.status_code == 409
    assert storage.put_calls == []


@pytest.mark.anyio
async def test_analysis_maps_provider_failure_to_generic_502(monkeypatch: pytest.MonkeyPatch) -> None:
    storage = FakeStorage()
    patch_dependencies(monkeypatch, storage, FailingAnalyzer())

    async with AsyncClient(transport=ASGITransport(app=main_module.app), base_url="http://test") as client:
        response = await client.post(
            "/media/analyze",
            files={"media": ("memory.jpg", b"bytes", "image/jpeg")},
            data={"consent": "true"},
        )

    assert response.status_code == 502
    assert "provider details" not in response.text


@pytest.mark.anyio
async def test_analysis_rejects_provider_media_id_that_differs_from_content_id(monkeypatch: pytest.MonkeyPatch) -> None:
    storage = FakeStorage()
    patch_dependencies(monkeypatch, storage, WrongIdAnalyzer())

    async with AsyncClient(transport=ASGITransport(app=main_module.app), base_url="http://test") as client:
        response = await client.post(
            "/media/analyze",
            files={"media": ("memory.jpg", b"bytes", "image/jpeg")},
            data={"consent": "true"},
        )

    assert response.status_code == 502
    assert "wrong" not in response.text


@pytest.mark.anyio
async def test_decision_is_idempotent_and_never_deletes_source(monkeypatch: pytest.MonkeyPatch) -> None:
    storage = FakeStorage()
    patch_dependencies(monkeypatch, storage, FakeAnalyzer())

    async with AsyncClient(transport=ASGITransport(app=main_module.app), base_url="http://test") as client:
        analyzed = await client.post(
            "/media/analyze",
            files={"media": ("memory.jpg", b"bytes", "image/jpeg")},
            data={"consent": "true"},
        )
        media_id = analyzed.json()["media_id"]
        first = await client.post(
            f"/media/{media_id}/decision",
            json={"status": "selected", "reason": "clear family moment"},
        )
        second = await client.post(
            f"/media/{media_id}/decision",
            json={"status": "selected", "reason": "clear family moment"},
        )

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json() == first.json()
    assert storage.objects[media_id] == b"bytes"
    assert not hasattr(storage, "delete")
