import pytest

from app.agent_planner import (
    AgentPlanningRequest,
    AgentPlanAdapter,
    AgentProductionPlan,
    PlannerMedia,
    SelectedSegment,
    validate_agent_plan,
)
from app.models import MediaAsset, ProductionBrief


def sample_brief(target_duration_seconds: int = 60) -> ProductionBrief:
    return ProductionBrief(
        occasion="A sunny afternoon",
        target_duration_seconds=target_duration_seconds,
        moods=["warm"],
        music_constraints=["acoustic"],
        media=[
            MediaAsset(media_id="clip-1", quality_score=0.9, duplicate_of=None),
            MediaAsset(media_id="clip-2", quality_score=0.8, duplicate_of=None),
            MediaAsset(media_id="clip-3", quality_score=0.7, duplicate_of=None),
        ],
    )


def valid_plan() -> AgentProductionPlan:
    return AgentProductionPlan(
        title="A sunny afternoon",
        caption="A small day worth keeping.",
        music_direction="warm acoustic instrumental",
        selected_segments=[
            SelectedSegment(media_id="clip-1", trim_start_seconds=0, trim_end_seconds=40),
            SelectedSegment(media_id="clip-2", trim_start_seconds=0, trim_end_seconds=20),
        ],
        held_back_media_ids=["clip-3"],
        user_explanation="I kept the clearest moments.",
    )


def test_accepts_a_known_exactly_sixty_second_plan() -> None:
    request = AgentPlanningRequest.from_brief(sample_brief(target_duration_seconds=60))
    plan = valid_plan()

    assert validate_agent_plan(request, plan) == plan


def test_rejects_unknown_media_id() -> None:
    request = AgentPlanningRequest.from_brief(sample_brief())
    plan = valid_plan().model_copy(
        update={"selected_segments": [SelectedSegment(media_id="unknown", trim_start_seconds=0, trim_end_seconds=60)]}
    )

    with pytest.raises(ValueError, match="unknown media ID"):
        validate_agent_plan(request, plan)


def test_rejects_non_sixty_second_plan() -> None:
    request = AgentPlanningRequest.from_brief(sample_brief())
    plan = valid_plan().model_copy(
        update={"selected_segments": [SelectedSegment(media_id="clip-1", trim_start_seconds=0, trim_end_seconds=59)]}
    )

    with pytest.raises(ValueError, match="60 seconds"):
        validate_agent_plan(request, plan)


def test_planner_media_excludes_storage_uri() -> None:
    assert set(PlannerMedia.model_fields) == {"media_id", "quality_score", "duplicate_of"}


def test_rejects_private_google_storage_uri_in_agent_output() -> None:
    request = AgentPlanningRequest.from_brief(sample_brief())
    with pytest.raises(ValueError, match="private URI"):
        AgentProductionPlan.model_validate({**valid_plan().model_dump(), "caption": "gs://private-bucket/clip-1.mp4"})


def test_rejects_unexpected_agent_plan_fields() -> None:
    with pytest.raises(ValueError):
        AgentProductionPlan.model_validate({**valid_plan().model_dump(), "private_uri": "gs://private-bucket/clip-1.mp4"})


def test_rejects_unknown_nested_segment_fields_and_private_uri() -> None:
    payload = valid_plan().model_dump()
    payload["selected_segments"][0]["uri"] = "gs://private-bucket/clip-1.mp4"
    with pytest.raises(ValueError):
        AgentProductionPlan.model_validate(payload)


def test_rejects_uppercase_private_google_storage_uri_in_agent_text() -> None:
    payload = {**valid_plan().model_dump(), "caption": "GS://private-bucket/clip-1.mp4"}
    with pytest.raises(ValueError, match="private URI"):
        AgentProductionPlan.model_validate(payload)


def test_rejects_music_track_outside_library() -> None:
    with pytest.raises(ValueError, match="music_direction"):
        AgentProductionPlan.model_validate(
            {**valid_plan().model_dump(), "music_direction": "copyrighted-song-identifier"}
        )


def test_plan_boundary_rechecks_music_library_after_model_construction() -> None:
    request = AgentPlanningRequest.from_brief(sample_brief())
    bypassed_model_validation = valid_plan().model_copy(
        update={"music_direction": "copyrighted-song-identifier"}
    )

    with pytest.raises(ValueError, match="music direction"):
        validate_agent_plan(request, bypassed_model_validation)


@pytest.mark.parametrize(
    "private_uri",
    [
        "https://storage.googleapis.com/private-bucket/clip.mp4",
        "https://storage.cloud.google.com/private-bucket/clip.mp4",
        "https://private-bucket.storage.googleapis.com/clip.mp4?X-Goog-Signature=secret",
    ],
)
def test_rejects_private_google_storage_https_uri_in_agent_output(
    private_uri: str,
) -> None:
    with pytest.raises(ValueError, match="private URI"):
        AgentProductionPlan.model_validate(
            {**valid_plan().model_dump(), "caption": private_uri}
        )


@pytest.mark.parametrize(
    "media_id",
    [
        "gs://private-bucket/clip.mp4",
        "https://storage.googleapis.com/private-bucket/clip.mp4",
        "https://example.test/clip.mp4",
        "data:video/mp4;base64,AAAA",
        "mailto:private@example.test",
        "urn:media:private-clip",
        "//storage.googleapis.com/private-bucket/clip.mp4",
        " clip-1",
        "clip-1 ",
    ],
)
def test_rejects_uri_shaped_media_identifier(media_id: str) -> None:
    with pytest.raises(ValueError, match="media ID"):
        PlannerMedia(media_id=media_id, quality_score=0.9, duplicate_of=None)


def test_accepts_application_sha256_media_identifier() -> None:
    media = PlannerMedia(
        media_id="sha256:garden", quality_score=0.9, duplicate_of=None
    )

    assert media.media_id == "sha256:garden"


def test_agent_request_rejects_unbounded_text_and_media_lists() -> None:
    with pytest.raises(ValueError):
        AgentPlanningRequest(
            user_id="user-1",
            occasion="x" * 501,
            target_duration_seconds=60,
            moods=["warm"],
            music_constraints=[],
            media=[],
        )
    with pytest.raises(ValueError):
        AgentPlanningRequest(
            user_id="user-1",
            occasion="A day",
            target_duration_seconds=60,
            moods=["warm"] * 9,
            music_constraints=[],
            media=[],
        )
    with pytest.raises(ValueError):
        AgentPlanningRequest(
            user_id="user-1",
            occasion="A day",
            target_duration_seconds=60,
            moods=["warm"],
            music_constraints=[],
            media=[
                PlannerMedia(
                    media_id=f"clip-{index}", quality_score=0.9, duplicate_of=None
                )
                for index in range(101)
            ],
        )


def test_segment_requires_non_negative_start_and_positive_end() -> None:
    with pytest.raises(ValueError):
        SelectedSegment(media_id="clip-1", trim_start_seconds=-1, trim_end_seconds=2)
    with pytest.raises(ValueError):
        SelectedSegment(media_id="clip-1", trim_start_seconds=2, trim_end_seconds=2)


def test_adapter_maps_segments_holds_back_other_media_and_builds_storyboard() -> None:
    request = AgentPlanningRequest.from_brief(sample_brief())
    proposal = AgentPlanAdapter().to_proposal(request, valid_plan())

    assert [(item.media_id, item.status) for item in proposal.curation.items] == [
        ("clip-1", "selected"),
        ("clip-2", "selected"),
        ("clip-3", "held_back"),
    ]
    assert proposal.storyboard.title == "A sunny afternoon"
    assert proposal.storyboard.caption == "A small day worth keeping."
    assert proposal.storyboard.music_direction == "warm acoustic instrumental"
    assert [(segment.media_id, segment.trim_start_seconds, segment.trim_end_seconds) for segment in proposal.selected_segments] == [
        ("clip-1", 0, 40),
        ("clip-2", 0, 20),
    ]
    assert proposal.privacy_checks == ["Review visible addresses, dates, and sensitive faces before export."]


def test_accepts_fractional_segments_without_float_rounding_failure() -> None:
    request = AgentPlanningRequest.from_brief(sample_brief())
    plan = valid_plan().model_copy(
        update={
            "selected_segments": [
                SelectedSegment(media_id="clip-1", trim_start_seconds=0.1, trim_end_seconds=30.1),
                SelectedSegment(media_id="clip-2", trim_start_seconds=0.2, trim_end_seconds=30.2),
            ]
        }
    )
    assert validate_agent_plan(request, plan) == plan
