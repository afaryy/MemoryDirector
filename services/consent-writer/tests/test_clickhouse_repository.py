from app.events import ConsentEvent
from app.repository import ClickHouseEventRepository


class RecordingClient:
    def __init__(self) -> None:
        self.calls = []

    def insert(self, table, data, column_names) -> None:
        self.calls.append((table, data, column_names))


def test_repository_inserts_only_allowlisted_event_columns() -> None:
    client = RecordingClient()

    ClickHouseEventRepository(client).record(ConsentEvent("session-1", "media-1", "media_selected"))

    assert client.calls == [(
        "production_events",
        [["session-1", "media-1", "media_selected", None]],
        ["session_id", "media_id", "event_type", "render_id"],
    )]

