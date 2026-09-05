import json
from collections.abc import Callable
from typing import Any, Protocol

from app.events import ConsentEvent


class ClickHouseInsertClient(Protocol):
    def insert(self, table: str, data: list[list[str | None]], column_names: list[str]) -> None: ...


class ClickHouseEventRepository:
    def __init__(self, client: ClickHouseInsertClient) -> None:
        self._client = client

    def record(self, event: ConsentEvent) -> None:
        self._client.insert(
            "production_events",
            [[event.session_id, event.media_id, event.event_type, event.render_id]],
            ["session_id", "media_id", "event_type", "render_id"],
        )


def repository_from_credentials(
    credentials_json: str,
    *,
    client_factory: Callable[..., ClickHouseInsertClient] | None = None,
) -> ClickHouseEventRepository:
    """Create the narrowly scoped ClickHouse writer from Secret Manager payload."""
    try:
        credentials: dict[str, Any] = json.loads(credentials_json)
        host = str(credentials["host"])
        port = int(credentials.get("port", 8443))
        username = str(credentials["username"])
        password = str(credentials["password"])
        database = str(credentials.get("database", "default"))
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise ValueError("ClickHouse event writer credentials are invalid") from error

    if client_factory is None:
        import clickhouse_connect

        client_factory = clickhouse_connect.get_client

    return ClickHouseEventRepository(
        client_factory(
            host=host,
            port=port,
            username=username,
            password=password,
            database=database,
            secure=True,
        )
    )
