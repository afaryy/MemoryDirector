from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models import (
    CurationPlan,
    MediaDecision,
    ProductionSegment,
    ProductionBrief,
    ProductionProposal,
    Storyboard,
)


class PlannerMedia(BaseModel):
    media_id: str
    quality_score: float = Field(ge=0, le=1)
    duplicate_of: str | None


class AgentPlanningRequest(BaseModel):
    user_id: str = Field(default="demo-user", min_length=1, max_length=128)
    occasion: str
    target_duration_seconds: int
    moods: list[str]
    music_constraints: list[str]
    media: list[PlannerMedia]

    @classmethod
    def from_brief(
        cls, brief: ProductionBrief, *, user_id: str = "demo-user"
    ) -> "AgentPlanningRequest":
        return cls(
            user_id=user_id,
            occasion=brief.occasion,
            target_duration_seconds=brief.target_duration_seconds,
            moods=brief.moods,
            music_constraints=brief.music_constraints,
            media=[PlannerMedia.model_validate(asset.model_dump()) for asset in brief.media],
        )


class SelectedSegment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    media_id: str
    trim_start_seconds: float = Field(ge=0)
    trim_end_seconds: float = Field(gt=0)

    @model_validator(mode="after")
    def ends_after_start(self) -> "SelectedSegment":
        if self.trim_end_seconds <= self.trim_start_seconds:
            raise ValueError("trim end must be greater than trim start")
        return self

    @property
    def duration_seconds(self) -> float:
        return self.trim_end_seconds - self.trim_start_seconds


class AgentProductionPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    caption: str
    music_direction: str
    selected_segments: list[SelectedSegment]
    held_back_media_ids: list[str]
    user_explanation: str

    @model_validator(mode="after")
    def reject_private_uri_leakage(self) -> "AgentProductionPlan":
        def contains_private_uri(value: object) -> bool:
            if isinstance(value, str):
                return "gs://" in value.lower()
            if isinstance(value, list):
                return any(contains_private_uri(item) for item in value)
            if isinstance(value, dict):
                return any(contains_private_uri(item) for item in value.values())
            return False

        if contains_private_uri(self.model_dump()):
            raise ValueError("private URI is not allowed in an agent plan")
        return self


def validate_agent_plan(
    request: AgentPlanningRequest, plan: AgentProductionPlan
) -> AgentProductionPlan:
    known_media = {asset.media_id: asset for asset in request.media}
    for segment in plan.selected_segments:
        if segment.media_id not in known_media:
            raise ValueError(f"unknown media ID: {segment.media_id}")
    total_duration = sum(
        Decimal(str(segment.trim_end_seconds)) - Decimal(str(segment.trim_start_seconds))
        for segment in plan.selected_segments
    )
    if total_duration != Decimal("60"):
        raise ValueError("agent plan must total exactly 60 seconds")

    if plan.music_direction not in {
        "warm acoustic instrumental",
        "Gentle festive instrumental",
        "Warm traditional-inspired instrumental",
        "Bright calm instrumental",
    }:
        raise ValueError("music direction must be from the application library")

    selected_ids = {segment.media_id for segment in plan.selected_segments}
    held_back_ids = set(plan.held_back_media_ids)
    if selected_ids & held_back_ids:
        raise ValueError("media cannot be both selected and held back")
    if held_back_ids != set(known_media) - selected_ids:
        raise ValueError("held back media must contain every other known media ID")
    return plan


class AgentPlanAdapter:
    @staticmethod
    def to_proposal(
        request: AgentPlanningRequest, plan: AgentProductionPlan
    ) -> ProductionProposal:
        validate_agent_plan(request, plan)
        selected_ids = {segment.media_id for segment in plan.selected_segments}
        return ProductionProposal(
            curation=CurationPlan(
                items=[
                    MediaDecision(
                        media_id=media_id,
                        status="selected" if media_id in selected_ids else "held_back",
                        reason=(
                            "Selected by the agent production plan"
                            if media_id in selected_ids
                            else "Held back by the agent production plan"
                        ),
                    )
                    for media_id in (asset.media_id for asset in request.media)
                ]
            ),
            place_confirmation_required=False,
            music_directions=[],
            storyboard=Storyboard(
                title=plan.title,
                caption=plan.caption,
                music_direction=plan.music_direction,
                preference_explanation=plan.user_explanation,
            ),
            privacy_checks=["Review visible addresses, dates, and sensitive faces before export."],
            selected_segments=[
                ProductionSegment(
                    media_id=segment.media_id,
                    trim_start_seconds=segment.trim_start_seconds,
                    trim_end_seconds=segment.trim_end_seconds,
                )
                for segment in plan.selected_segments
            ],
        )
