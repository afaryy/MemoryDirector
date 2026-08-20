import pytest
from pydantic import ValidationError

from app.media_analysis import MediaAnalysis, media_id_for_bytes


def test_media_id_is_stable_for_identical_bytes() -> None:
    assert media_id_for_bytes(b"same") == media_id_for_bytes(b"same")
    assert media_id_for_bytes(b"same").startswith("sha256:")
    assert media_id_for_bytes(b"same") != media_id_for_bytes(b"different")


def test_analysis_rejects_unknown_orientation_and_out_of_range_quality() -> None:
    with pytest.raises(ValidationError):
        MediaAnalysis(
            media_id="sha256:x",
            description="visible content",
            quality_score=1.1,
            duplicate_of=None,
            privacy_flags=[],
            orientation="diagonal",
            duration_seconds=None,
        )

