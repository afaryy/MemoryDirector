from app.events import ConsentEvent
from app.repository import ClickHouseEventRepository, repository_from_credentials


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


def test_repository_connects_using_the_writer_credentials_only() -> None:
    received = {}
    client = RecordingClient()

    repository = repository_from_credentials(
        '{"host":"clickhouse.example","port":8443,"username":"writer","password":"secret","database":"default"}',
        client_factory=lambda **kwargs: received.update(kwargs) or client,
    )

    repository.record(ConsentEvent("session-1", "media-1", "media_selected"))

    assert received == {
        "host": "clickhouse.example",
        "port": 8443,
        "username": "writer",
        "password": "secret",
        "database": "default",
        "secure": True,
    }
    assert client.calls
