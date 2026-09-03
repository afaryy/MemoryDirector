import io
import zipfile

import app.main as main_module
import pytest
from httpx import ASGITransport, AsyncClient

from app.render import DeterministicVerticalRenderer


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
async def test_export_returns_mp4_cover_and_caption_bundle(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(main_module, "get_renderer", lambda: DeterministicVerticalRenderer(RecordingExecutor()))

    async with AsyncClient(transport=ASGITransport(app=main_module.app), base_url="http://test") as client:
        response = await client.post(
            "/renders/export",
            files={"media": ("memory.mp4", b"source", "video/mp4")},
            data={"title": "A weekend", "caption": "Together by the sea.", "approved": "true"},
        )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    with zipfile.ZipFile(io.BytesIO(response.content)) as bundle:
        assert sorted(bundle.namelist()) == sorted([name for name in bundle.namelist() if name.endswith((".mp4", ".jpg", ".txt"))])
        assert any(name.endswith(".mp4") for name in bundle.namelist())
        assert any(name.endswith(".jpg") for name in bundle.namelist())
        assert bundle.read(next(name for name in bundle.namelist() if name.endswith(".txt"))) == b"A weekend\n\nTogether by the sea.\n"


@pytest.mark.anyio
async def test_export_requires_approval_before_reading_media() -> None:
    async with AsyncClient(transport=ASGITransport(app=main_module.app), base_url="http://test") as client:
        response = await client.post(
            "/renders/export",
            files={"media": ("memory.mp4", b"source", "video/mp4")},
            data={"title": "A weekend", "caption": "Together by the sea.", "approved": "false"},
        )

    assert response.status_code == 409
    assert response.json()["detail"] == "Approve the plan before creating a video."


@pytest.mark.anyio
async def test_export_generates_and_uses_an_original_memory_song(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeLyria:
        def generate(self, prompt: str):
            from app.lyria_client import GeneratedSong

            return GeneratedSong(audio=b"song-bytes", lyrics="a garden song", model="lyria-test")

    executor = RecordingExecutor()
    monkeypatch.setattr(main_module, "get_renderer", lambda: DeterministicVerticalRenderer(executor))
    monkeypatch.setattr(main_module, "get_lyria_client", lambda: FakeLyria())

    async with AsyncClient(transport=ASGITransport(app=main_module.app), base_url="http://test") as client:
        response = await client.post(
            "/renders/export",
            files={"media": ("memory.mp4", b"source", "video/mp4")},
            data={
                "title": "Garden day",
                "caption": "Together outside.",
                "approved": "true",
                "soundtrack_mode": "original_song",
                "memory_details": ["Mum in the garden", "two grandchildren laughing"],
                "requested_style": "warm acoustic pop",
            },
        )

    assert response.status_code == 200
    render_command = executor.commands[0]
    assert any(path.endswith("memory-song.mp3") for path in render_command)
    assert "1:a:0" in render_command
