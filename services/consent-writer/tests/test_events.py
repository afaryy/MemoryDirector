import pytest

from app.events import ConsentEvent


def test_event_rejects_a_disallowed_event_type() -> None:
    with pytest.raises(ValueError, match="event type"):
        ConsentEvent(session_id="session-1", media_id="media-1", event_type="delete_media")

