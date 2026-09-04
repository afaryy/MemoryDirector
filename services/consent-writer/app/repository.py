from typing import Protocol

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
