from app.models import CurationPlan, MediaDecision, PlaceCandidate, ProductionBrief


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
