from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel

from app.models import Storyboard
from app.render import ApprovalRequired, RenderRequest, create_render_request

app = FastAPI(title="Memory Director API")


class RenderPayload(BaseModel):
    storyboard: Storyboard
    approved: bool


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/renders", response_model=RenderRequest, status_code=status.HTTP_201_CREATED)
def request_render(payload: RenderPayload) -> RenderRequest:
    try:
        return create_render_request(payload.storyboard, payload.approved)
    except ApprovalRequired as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
