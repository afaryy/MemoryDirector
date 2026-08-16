from app.models import MediaAsset, PlaceCandidate, ProductionBrief
from app.production import build_curation_plan, needs_place_confirmation


def sample_brief() -> ProductionBrief:
    return ProductionBrief(
        occasion="Melbourne weekend",
        target_duration_seconds=45,
        moods=["cheerful"],
        music_constraints=["gentle"],
        media=[
            MediaAsset(media_id="clip-1", quality_score=0.95, duplicate_of=None),
            MediaAsset(media_id="clip-2", quality_score=0.20, duplicate_of="clip-1"),
        ],
    )


def test_low_confidence_place_requires_confirmation() -> None:
    candidate = PlaceCandidate(
        label="Eiffel Tower, Paris",
        confidence=0.62,
        evidence=["visual landmark"],
    )

    assert needs_place_confirmation(candidate) is True


def test_curation_never_marks_media_deleted() -> None:
    plan = build_curation_plan(sample_brief())

    assert [item.status for item in plan.items] == ["selected", "held_back"]
