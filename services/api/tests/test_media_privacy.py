import pytest
from httpx import ASGITransport, AsyncClient

import app.main as main_module
from app.media_analysis import MediaAnalysis, StoredMedia


class PrivacyStorage:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.metadata: dict[str, StoredMedia] = {}
        self.decisions: dict[str, tuple[str, str]] = {}

    def put(self, media_id: str, content_type: str, body: bytes) -> StoredMedia:
        self.objects[media_id] = body
        stored = StoredMedia(
            media_id=media_id,
            content_type=content_type,
            size_bytes=len(body),
            sha256="digest",
            gs_uri=f"gs://private-bucket/media/{media_id}/original",
        )
        self.metadata[media_id] = stored
        return stored

    def read(self, media_id: str):
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


class LeakyAnalyzer:
    def analyze(self, stored_media: StoredMedia) -> MediaAnalysis:
        return MediaAnalysis(
            media_id=stored_media.media_id,
            description="provider echoed gs://private-bucket/media/secret",
            quality_score=0.8,
            privacy_flags=[],
            orientation="portrait",
            duration_seconds=None,
        )


class SafeAnalyzer:
    def analyze(self, stored_media: StoredMedia) -> MediaAnalysis:
        return MediaAnalysis(
            media_id=stored_media.media_id,
            description="a quiet family moment",
            quality_score=0.8,
            privacy_flags=[],
            orientation="portrait",
            duration_seconds=None,
        )


class FlaggedAnalyzer:
    def analyze(self, stored_media: StoredMedia) -> MediaAnalysis:
        return MediaAnalysis(
            media_id=stored_media.media_id,
            description="a family moment with visible faces",
            quality_score=0.8,
            privacy_flags=["contains_face", "contains_text"],
            orientation="portrait",
            duration_seconds=None,
        )


@pytest.mark.anyio
async def test_model_echo_of_private_gcs_uri_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    storage = PrivacyStorage()
    monkeypatch.setattr(main_module, "get_media_storage", lambda: storage, raising=False)
    monkeypatch.setattr(main_module, "get_media_analyzer", lambda: LeakyAnalyzer(), raising=False)

    async with AsyncClient(transport=ASGITransport(app=main_module.app), base_url="http://test") as client:
        response = await client.post(
            "/media/analyze",
            files={"media": ("memory.jpg", b"privacy-bytes", "image/jpeg")},
            data={"consent": "true"},
        )

    assert response.status_code == 502
    assert "gs://" not in response.text
    assert storage.objects


@pytest.mark.anyio
async def test_held_back_decision_keeps_original_object(monkeypatch: pytest.MonkeyPatch) -> None:
    storage = PrivacyStorage()
    monkeypatch.setattr(main_module, "get_media_storage", lambda: storage, raising=False)
    monkeypatch.setattr(main_module, "get_media_analyzer", lambda: SafeAnalyzer(), raising=False)

    async with AsyncClient(transport=ASGITransport(app=main_module.app), base_url="http://test") as client:
        analyzed = await client.post(
            "/media/analyze",
            files={"media": ("memory.jpg", b"held-back-bytes", "image/jpeg")},
            data={"consent": "true"},
        )
        media_id = analyzed.json()["media_id"]
        decision = await client.post(
            f"/media/{media_id}/decision",
            json={"status": "held_back", "reason": "duplicate"},
        )

    assert decision.status_code == 200
    assert decision.json()["status"] == "held_back"
    assert storage.objects[media_id] == b"held-back-bytes"


@pytest.mark.anyio
async def test_allowlisted_privacy_flags_are_returned_for_user_review(monkeypatch: pytest.MonkeyPatch) -> None:
    storage = PrivacyStorage()
    monkeypatch.setattr(main_module, "get_media_storage", lambda: storage, raising=False)
    monkeypatch.setattr(main_module, "get_media_analyzer", lambda: FlaggedAnalyzer(), raising=False)

    async with AsyncClient(transport=ASGITransport(app=main_module.app), base_url="http://test") as client:
        response = await client.post(
            "/media/analyze",
            files={"media": ("memory.jpg", b"flagged-bytes", "image/jpeg")},
            data={"consent": "true"},
        )

    assert response.status_code == 201
    assert response.json()["privacy_flags"] == ["contains_face", "contains_text"]
