from fastapi.testclient import TestClient

from app.main import app
import app.main as main_module


def test_memory_song_brief_endpoint_returns_safe_generation_request() -> None:
    client = TestClient(app)

    response = client.post(
        "/memory-songs/brief",
        json={
            "memory_details": ["Mum's garden visit", "two grandchildren laughing"],
            "requested_style": "warm acoustic pop",
        },
    )

    assert response.status_code == 201
    assert response.json()["fallback"] == "instrumental"
    assert "Mum's garden visit" in response.json()["prompt"]


def test_memory_song_brief_endpoint_rejects_voice_cloning() -> None:
    client = TestClient(app)

    response = client.post(
        "/memory-songs/brief",
        json={"memory_details": ["A garden visit"], "requested_style": "Clone my mother's voice"},
    )

    assert response.status_code == 422
    assert "original style" in response.json()["detail"]


def test_memory_song_generation_endpoint_returns_audio_metadata(monkeypatch) -> None:
    class FakeLyria:
        def generate(self, prompt: str):
            from app.lyria_client import GeneratedSong
            return GeneratedSong(audio=b"song", lyrics="garden song", model="lyria-test")

    monkeypatch.setattr(main_module, "get_lyria_client", lambda: FakeLyria())
    response = TestClient(app).post("/memory-songs", json={"memory_details": ["Garden"], "requested_style": "warm"})
    assert response.status_code == 201
    assert response.json()["model"] == "lyria-test"
