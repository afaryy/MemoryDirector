from typing import Literal

from pydantic import BaseModel, Field


class MediaAsset(BaseModel):
    media_id: str
    quality_score: float = Field(ge=0, le=1)
    duplicate_of: str | None


class ProductionBrief(BaseModel):
    occasion: str
    target_duration_seconds: int
    moods: list[str]
    music_constraints: list[str]
    media: list[MediaAsset]


class PlaceCandidate(BaseModel):
    label: str
    confidence: float = Field(ge=0, le=1)
    evidence: list[str]


class MediaDecision(BaseModel):
    media_id: str
    status: Literal["selected", "held_back"]
    reason: str


class CurationPlan(BaseModel):
    items: list[MediaDecision]
