from pathlib import Path

import pytest

from app.render import TARGET_VIDEO_SECONDS, allocate_timeline


@pytest.mark.parametrize("source_count", range(1, 16))
def test_allocate_timeline_is_exactly_sixty_seconds_with_in_segment_transitions(
    source_count: int, tmp_path: Path
) -> None:
    sources = [tmp_path / f"moment-{index}.jpg" for index in range(source_count)]
    timeline = allocate_timeline(sources)

    assert [segment.source_path for segment in timeline.segments] == sources
    assert all(segment.duration_seconds >= 3 for segment in timeline.segments)
    assert timeline.rendered_duration_seconds == TARGET_VIDEO_SECONDS
    assert sum(segment.duration_seconds for segment in timeline.segments) == TARGET_VIDEO_SECONDS


@pytest.mark.parametrize("suffix", [".heic", ".heif"])
def test_allocate_timeline_treats_phone_photo_formats_as_still_images(suffix: str, tmp_path: Path) -> None:
    timeline = allocate_timeline([tmp_path / f"phone-photo{suffix}"])

    assert timeline.segments[0].source_kind == "photo"
