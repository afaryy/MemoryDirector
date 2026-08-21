import io
import zipfile

import pytest
from httpx import ASGITransport, AsyncClient

import app.main as main_module
from app.media_analysis import MediaAnalysis, StoredMedia
from app.render import DeterministicVerticalRenderer


class RenderStorage:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.decisions: dict[str, tuple[str, str]] = {}

    def put(self, media_id: str, content_type: str, body: bytes) -> StoredMedia:
        self.objects[media_id] = body
        return StoredMedia(
            media_id=media_id,
            content_type=content_type,
            size_bytes=len(body),
            sha256="digest",
            gs_uri=f"gs://private/media/{media_id}/original",
        )

    def read(self, media_id: str):
        if media_id not in self.objects:
            return None
        return StoredMedia(
            media_id=media_id,
            content_type="image/jpeg",
            size_bytes=len(self.objects[media_id]),
            sha256="digest",
            gs_uri=f"gs://private/media/{media_id}/original",
        ), self.objects[media_id]

    def save_decision(self, state):
        self.decisions[state.media_id] = (state.status, state.reason)
        return state

    def load_decision(self, media_id: str):
        decision = self.decisions.get(media_id)
        if decision is None:
            return None
        from app.media_analysis import MediaDecisionState

        return MediaDecisionState(media_id=media_id, status=decision[0], reason=decision[1])


class RenderAnalyzer:
    def analyze(self, stored_media: StoredMedia) -> MediaAnalysis:
        return MediaAnalysis(
            media_id=stored_media.media_id,
            description="a family moment",
            quality_score=0.9,
            privacy_flags=[],
            orientation="landscape",
            duration_seconds=None,
        )


class RecordingExecutor:
    def __init__(self) -> None:
        self.commands: list[list[str]] = []

    def run(self, command: list[str]) -> None:
        self.commands.append(command)
        output = command[-1]
        if output.endswith(".mp4"):
            with open(output, "wb") as video:
                video.write(b"fake-video")
        elif output.endswith(".jpg"):
            with open(output, "wb") as cover:
                cover.write(b"fake-cover")


@pytest.mark.anyio
async def test_selected_analyzed_media_reaches_renderer_without_new_upload(monkeypatch: pytest.MonkeyPatch) -> None:
    storage = RenderStorage()
    monkeypatch.setattr(main_module, "get_media_storage", lambda: storage, raising=False)
    monkeypatch.setattr(main_module, "get_media_analyzer", lambda: RenderAnalyzer(), raising=False)
    monkeypatch.setattr(main_module, "get_renderer", lambda: DeterministicVerticalRenderer(RecordingExecutor()))

    async with AsyncClient(transport=ASGITransport(app=main_module.app), base_url="http://test") as client:
        analyzed = await client.post(
            "/media/analyze",
            files={"media": ("memory.jpg", b"render-me", "image/jpeg")},
            data={"consent": "true"},
        )
        media_id = analyzed.json()["media_id"]
        selected = await client.post(
            f"/media/{media_id}/decision",
            json={"status": "selected", "reason": "best frame"},
        )
        exported = await client.post(
            "/renders/export",
            data={"title": "A memory", "caption": "Together.", "approved": "true", "media_id": media_id},
        )

    assert selected.status_code == 200
    assert exported.status_code == 200
    with zipfile.ZipFile(io.BytesIO(exported.content)) as bundle:
        assert any(name.endswith(".mp4") for name in bundle.namelist())
        assert any(name.endswith(".jpg") for name in bundle.namelist())


@pytest.mark.anyio
async def test_held_back_analyzed_media_cannot_reach_renderer(monkeypatch: pytest.MonkeyPatch) -> None:
    storage = RenderStorage()
    monkeypatch.setattr(main_module, "get_media_storage", lambda: storage, raising=False)
    monkeypatch.setattr(main_module, "get_media_analyzer", lambda: RenderAnalyzer(), raising=False)

    async with AsyncClient(transport=ASGITransport(app=main_module.app), base_url="http://test") as client:
        analyzed = await client.post(
            "/media/analyze",
            files={"media": ("held.jpg", b"hold-me", "image/jpeg")},
            data={"consent": "true"},
        )
        media_id = analyzed.json()["media_id"]
        await client.post(
            f"/media/{media_id}/decision",
            json={"status": "held_back", "reason": "duplicate"},
        )
        exported = await client.post(
            "/renders/export",
            data={"title": "A memory", "caption": "Together.", "approved": "true", "media_id": media_id},
        )

    assert exported.status_code == 409


@pytest.mark.anyio
async def test_two_selected_analyzed_media_are_combined_in_one_export(monkeypatch: pytest.MonkeyPatch) -> None:
    storage = RenderStorage()
    monkeypatch.setattr(main_module, "get_media_storage", lambda: storage, raising=False)
    monkeypatch.setattr(main_module, "get_media_analyzer", lambda: RenderAnalyzer(), raising=False)
    executor = RecordingExecutor()
    renderer = DeterministicVerticalRenderer(executor)
    monkeypatch.setattr(main_module, "get_renderer", lambda: renderer)

    async with AsyncClient(transport=ASGITransport(app=main_module.app), base_url="http://test") as client:
        first = await client.post("/media/analyze", files={"media": ("first.jpg", b"first", "image/jpeg")}, data={"consent": "true"})
        second = await client.post("/media/analyze", files={"media": ("second.jpg", b"second", "image/jpeg")}, data={"consent": "true"})
        first_id = first.json()["media_id"]
        second_id = second.json()["media_id"]
        await client.post(f"/media/{first_id}/decision", json={"status": "selected", "reason": "best moment"})
        await client.post(f"/media/{second_id}/decision", json={"status": "selected", "reason": "best moment"})
        exported = await client.post(
            "/renders/export",
            data={"title": "A memory", "caption": "Together.", "approved": "true"},
            files=[("media_ids", (None, first_id)), ("media_ids", (None, second_id))],
        )

    assert exported.status_code == 200
    assert any("concat=n=2:v=1:a=0" in " ".join(command) for command in executor.commands)
