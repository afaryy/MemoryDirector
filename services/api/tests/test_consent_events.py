import pytest

import app.consent_events as consent_events
from app.consent_events import ConsentEvent, ConsentEventPublisher


class CreatedResponse:
    status = 201

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False


def test_publisher_sends_the_identity_token_as_bearer_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    publisher = ConsentEventPublisher("https://writer.example")
    requests = []

    monkeypatch.setattr(publisher, "_identity_token", lambda: "identity-token")
    monkeypatch.setattr(
        consent_events,
        "urlopen",
        lambda request, timeout: requests.append((request, timeout)) or CreatedResponse(),
    )

    publisher.publish(ConsentEvent("session-1", "media-1", "media_selected"))

    assert len(requests) == 1
    request, _ = requests[0]
    assert request.get_header("Authorization") == "Bearer identity-token"


def test_publisher_allows_the_writer_cold_start_window(monkeypatch: pytest.MonkeyPatch) -> None:
    publisher = ConsentEventPublisher("https://writer.example")
    timeouts = []

    monkeypatch.setattr(publisher, "_identity_token", lambda: "identity-token")
    monkeypatch.setattr(
        consent_events,
        "urlopen",
        lambda request, timeout: timeouts.append(timeout) or CreatedResponse(),
    )

    publisher.publish(ConsentEvent("session-1", "media-1", "media_selected"))

    assert timeouts == [30]


def test_publisher_fails_closed_when_identity_token_is_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    publisher = ConsentEventPublisher("https://writer.example")
    requests = []

    monkeypatch.setattr(publisher, "_identity_token", lambda: None)
    monkeypatch.setattr(consent_events, "urlopen", lambda request, timeout: requests.append(request))

    with pytest.raises(RuntimeError, match="identity token"):
        publisher.publish(ConsentEvent("session-1", "media-1", "media_selected"))

    assert requests == []
