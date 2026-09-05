from fastapi.testclient import TestClient

import app.main as main_module
from app.main import app


class RecordingRepository:
    def __init__(self) -> None:
        self.events = []

    def record(self, event) -> None:
        self.events.append(event)


def test_writer_accepts_an_allowed_anonymous_event(monkeypatch) -> None:
    repository = RecordingRepository()
    monkeypatch.setattr(main_module, "get_repository", lambda: repository)
    client = TestClient(app)

    response = client.post(
        "/events",
        json={"session_id": "session-1", "media_id": "media-1", "event_type": "media_selected"},
    )

    assert response.status_code == 201
    assert response.json() == {"status": "recorded"}
    assert repository.events[0].media_id == "media-1"
