import pytest

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
        '{"CLICKHOUSE_HOST":"clickhouse.example","CLICKHOUSE_PORT":"8443","CLICKHOUSE_USER":"writer","CLICKHOUSE_PASSWORD":"secret","CLICKHOUSE_DATABASE":"memory_director","CLICKHOUSE_SECURE":"true","CLICKHOUSE_VERIFY":"true"}',
        client_factory=lambda **kwargs: received.update(kwargs) or client,
    )

    repository.record(ConsentEvent("session-1", "media-1", "media_selected"))

    assert received == {
        "host": "clickhouse.example",
        "port": 8443,
        "username": "writer",
        "password": "secret",
        "database": "memory_director",
        "secure": True,
        "verify": True,
    }
    assert client.calls


def test_repository_rejects_the_obsolete_lowercase_secret_contract() -> None:
    try:
        repository_from_credentials(
            '{"host":"clickhouse.example","username":"writer","password":"secret"}',
            client_factory=lambda **kwargs: RecordingClient(),
        )
    except ValueError as error:
        assert str(error) == "ClickHouse event writer credentials are invalid"
    else:
        raise AssertionError("obsolete lowercase credentials must not be accepted")


@pytest.mark.parametrize(
    ("secure", "verify", "expected_secure", "expected_verify"),
    [
        ("false", "false", False, False),
        (True, False, True, False),
    ],
)
def test_repository_parses_string_and_native_tls_booleans(
    secure, verify, expected_secure, expected_verify
) -> None:
    received = {}
    credentials = {
        "CLICKHOUSE_HOST": "clickhouse.example",
        "CLICKHOUSE_PORT": "8443",
        "CLICKHOUSE_USER": "writer",
        "CLICKHOUSE_PASSWORD": "secret",
        "CLICKHOUSE_DATABASE": "memory_director",
        "CLICKHOUSE_SECURE": secure,
        "CLICKHOUSE_VERIFY": verify,
    }

    import json

    repository_from_credentials(
        json.dumps(credentials),
        client_factory=lambda **kwargs: received.update(kwargs) or RecordingClient(),
    )

    assert received["secure"] is expected_secure
    assert received["verify"] is expected_verify


def test_repository_rejects_invalid_tls_boolean_text() -> None:
    with pytest.raises(ValueError, match="credentials are invalid"):
        repository_from_credentials(
            '{"CLICKHOUSE_HOST":"clickhouse.example","CLICKHOUSE_USER":"writer","CLICKHOUSE_PASSWORD":"secret","CLICKHOUSE_SECURE":"sometimes"}',
            client_factory=lambda **kwargs: RecordingClient(),
        )
