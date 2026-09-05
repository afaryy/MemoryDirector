from pathlib import Path

import pytest

from app.render import DeterministicVerticalRenderer, RenderRequest, RenderVerificationError


class RecordingExecutor:
    def run(self, command: list[str]) -> None:
        output = Path(command[-1])
        if output.suffix in {".mp4", ".jpg"}:
            output.write_bytes(b"rendered")


class FixedDurationProbe:
    def __init__(self, duration_seconds: float) -> None:
        self.duration_seconds = duration_seconds

    def duration_seconds_for(self, video_path: Path) -> float:
        return self.duration_seconds


def test_renderer_rejects_a_completed_video_outside_the_sixty_second_tolerance(tmp_path: Path) -> None:
    source = tmp_path / "moment.jpg"
    source.write_bytes(b"media")
    renderer = DeterministicVerticalRenderer(RecordingExecutor(), duration_probe=FixedDurationProbe(59.4))

    with pytest.raises(RenderVerificationError, match="duration"):
        renderer.render(RenderRequest(title="A day", caption="Together."), source, tmp_path / "exports")
