import os
from typing import Protocol

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

from app.events import ConsentEvent, EventType
from app.repository import repository_from_credentials


class EventRepository(Protocol):
    def record(self, event: ConsentEvent) -> None: ...


class UnavailableEventRepository:
    def record(self, event: ConsentEvent) -> None:
        raise RuntimeError("ClickHouse event writer is not configured")


def get_repository() -> EventRepository:
    credentials_json = os.environ.get("CLICKHOUSE_EVENT_WRITER_CREDENTIALS_JSON")
    if not credentials_json:
        return UnavailableEventRepository()
    return repository_from_credentials(credentials_json)


class EventPayload(BaseModel):
    session_id: str = Field(min_length=1, max_length=120)
    media_id: str = Field(min_length=1, max_length=128)
    event_type: EventType
    render_id: str | None = Field(default=None, max_length=128)


app = FastAPI(title="Memory Director consent event writer")


@app.post("/events", status_code=status.HTTP_201_CREATED)
def record_event(payload: EventPayload) -> dict[str, str]:
    try:
        get_repository().record(ConsentEvent(**payload.model_dump()))
    except (RuntimeError, ValueError) as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Consent event recording is unavailable.") from error
    return {"status": "recorded"}
