import json
import os
from dataclasses import dataclass
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class ConsentEvent:
    session_id: str
    media_id: str
    event_type: str
    render_id: str | None = None


class ConsentEventPublisher:
    def __init__(self, endpoint: str, timeout: float = 5) -> None:
        self._endpoint = endpoint.rstrip("/") + "/events"
        self._timeout = timeout

    def publish(self, event: ConsentEvent) -> None:
        headers = {"Content-Type": "application/json"}
        identity_token = self._identity_token()
        if identity_token:
            headers["Authorization"] = f"Bearer {identity_token}"
        request = Request(
            self._endpoint,
            data=json.dumps(event.__dict__).encode(),
            headers=headers,
            method="POST",
        )
        with urlopen(request, timeout=self._timeout) as response:
            if response.status != 201:
                raise RuntimeError("consent event writer rejected the event")

    def _identity_token(self) -> str | None:
        try:
            from google.auth.transport.requests import Request as GoogleAuthRequest
            from google.oauth2 import id_token

            return id_token.fetch_id_token(GoogleAuthRequest(), self._endpoint.removesuffix("/events"))
        except Exception:
            return None


def consent_event_publisher_from_environment() -> ConsentEventPublisher | None:
    endpoint = os.environ.get("CONSENT_EVENT_WRITER_ENDPOINT", "").strip()
    return ConsentEventPublisher(endpoint) if endpoint else None
