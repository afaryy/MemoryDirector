from dataclasses import dataclass
from typing import Literal


EventType = Literal["media_selected", "media_held_back", "render_started", "export_completed", "export_failed"]
_ALLOWED_EVENT_TYPES = frozenset(EventType.__args__)


@dataclass(frozen=True)
class ConsentEvent:
    session_id: str
    media_id: str
    event_type: EventType
    render_id: str | None = None

    def __post_init__(self) -> None:
        if not self.session_id.strip() or not self.media_id.strip():
            raise ValueError("session and media identifiers are required")
        if self.event_type not in _ALLOWED_EVENT_TYPES:
            raise ValueError("event type is not allowed")
