from pathlib import Path

import pytest

from app.render import TARGET_VIDEO_SECONDS, allocate_timeline


@pytest.mark.parametrize("source_count", range(1, 16))
def test_allocate_timeline_is_exactly_sixty_seconds_after_transitions(source_count: int, tmp_path: Path) -> None:
    sources = [tmp_path / f"moment-{index}.jpg" for index in range(source_count)]
    timeline = allocate_timeline(sources)

    assert [segment.source_path for segment in timeline.segments] == sources
    assert all(segment.duration_seconds >= 3 for segment in timeline.segments)
    assert timeline.rendered_duration_seconds == TARGET_VIDEO_SECONDS
    assert sum(segment.duration_seconds for segment in timeline.segments) - timeline.transition_total_seconds == TARGET_VIDEO_SECONDS

