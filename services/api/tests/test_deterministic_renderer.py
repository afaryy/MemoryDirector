from pathlib import Path

from app.models import Storyboard
from app.render import DeterministicVerticalRenderer, create_render_request


class RecordingExecutor:
    def __init__(self) -> None:
        self.commands: list[list[str]] = []

    def run(self, command: list[str]) -> None:
        self.commands.append(command)


def test_renderer_builds_a_deterministic_vertical_export_package(tmp_path: Path) -> None:
    executor = RecordingExecutor()
    request = create_render_request(Storyboard(title="Weekend", caption="A bright trip."), approved=True)

    artifact = DeterministicVerticalRenderer(executor).render(
        request=request,
        source_path=tmp_path / "source.mp4",
        output_directory=tmp_path / "exports",
    )

    assert artifact.video_path.name.endswith(".mp4")
    assert artifact.cover_path.name.endswith(".jpg")
    assert artifact.caption_path.read_text().splitlines() == ["Weekend", "", "A bright trip."]
    assert executor.commands[0][:5] == ["ffmpeg", "-y", "-stream_loop", "-1", "-i"]
    assert "1080:1920" in executor.commands[0]
    assert executor.commands[0][executor.commands[0].index("-t") + 1] == "45"
    assert "-frames:v" in executor.commands[1]
