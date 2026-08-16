import os
from typing import Literal

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.gemini_client import GeminiProductionPlanner, GoogleGenAiGateway
from app.models import PlaceCandidate, ProductionBrief, ProductionProposal, Storyboard
from app.production import ProductionOrchestrator
from app.render import ApprovalRequired, RenderRequest, create_render_request

app = FastAPI(title="Memory Director API")
allowed_origins = [origin.strip() for origin in os.environ.get("WEB_ORIGINS", "http://localhost:3000").split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["POST"],
    allow_headers=["Content-Type"],
)


class RenderPayload(BaseModel):
    storyboard: Storyboard
    approved: bool


class StoryboardPayload(BaseModel):
    occasion: str
    moods: list[str]
    media_count: int = Field(gt=0)
    media_consent: Literal[True]


class ProductionProposalPayload(BaseModel):
    brief: ProductionBrief
    places: list[PlaceCandidate]


def get_production_planner() -> GeminiProductionPlanner:
    try:
        return GeminiProductionPlanner(GoogleGenAiGateway())
    except KeyError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Gemini production planning is not configured.",
        ) from error


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/renders", response_model=RenderRequest, status_code=status.HTTP_201_CREATED)
def request_render(payload: RenderPayload) -> RenderRequest:
    try:
        return create_render_request(payload.storyboard, payload.approved)
    except ApprovalRequired as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error


@app.post("/storyboards", response_model=Storyboard, status_code=status.HTTP_201_CREATED)
def create_storyboard(
    payload: StoryboardPayload,
) -> Storyboard:
    return get_production_planner().plan(payload.occasion, payload.moods)


@app.post("/production-proposals", response_model=ProductionProposal, status_code=status.HTTP_201_CREATED)
def create_production_proposal(payload: ProductionProposalPayload) -> ProductionProposal:
    return ProductionOrchestrator(get_production_planner()).produce(payload.brief, payload.places)
