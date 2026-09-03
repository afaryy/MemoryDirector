from fastapi.testclient import TestClient

from app.main import app


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
