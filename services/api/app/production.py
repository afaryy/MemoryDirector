from typing import Protocol

from app.models import (
    CurationPlan,
    MediaDecision,
    MusicDirection,
    PlaceCandidate,
    ProductionBrief,
    ProductionProposal,
    Storyboard,
)


class StoryboardPlanner(Protocol):
    def plan(self, occasion: str, moods: list[str]) -> Storyboard: ...


def needs_place_confirmation(candidate: PlaceCandidate) -> bool:
    return candidate.confidence < 0.85


def build_curation_plan(brief: ProductionBrief) -> CurationPlan:
    return CurationPlan(
        items=[
            MediaDecision(
                media_id=asset.media_id,
                status="held_back" if asset.duplicate_of else "selected",
                reason="Similar to an earlier selection" if asset.duplicate_of else "Best available version",
            )
            for asset in brief.media
        ]
    )


class ProductionOrchestrator:
    def __init__(self, storyboard_planner: StoryboardPlanner) -> None:
        self._storyboard_planner = storyboard_planner

    def produce(self, brief: ProductionBrief, places: list[PlaceCandidate]) -> ProductionProposal:
        return ProductionProposal(
            curation=build_curation_plan(brief),
            place_confirmation_required=any(needs_place_confirmation(place) for place in places),
            music_directions=[
                MusicDirection(
                    name="Gentle festive instrumental",
                    description="Warm celebration without loud vocals.",
                ),
                MusicDirection(
                    name="Warm traditional-inspired instrumental",
                    description="A calm, dignified direction for family memories.",
                ),
                MusicDirection(
                    name="Bright calm instrumental",
                    description="A light, modern pace that keeps the story clear.",
                ),
            ],
            storyboard=self._storyboard_planner.plan(brief.occasion, brief.moods),
            privacy_checks=["Review visible addresses, dates, and sensitive faces before export."],
        )
