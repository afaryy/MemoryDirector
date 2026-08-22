from pathlib import Path

from app.models import Storyboard
from app.render import DeterministicVerticalRenderer, RenderRequest, create_render_request


class RecordingExecutor:
    def __init__(self) -> None:
        self.commands: list[list[str]] = []

    def run(self, command: list[str]) -> None:
        self.commands.append(command)


def test_renderer_builds_a_deterministic_vertical_export_package(tmp_path: Path) -> None:
    executor = RecordingExecutor()
    request = create_render_request(Storyboard(title="Weekend", caption="A bright trip."), approved=True)
    source_path = tmp_path / "source.mp4"
    source_path.write_bytes(b"seeded-media")

    artifact = DeterministicVerticalRenderer(executor).render(
        request=request,
        source_path=source_path,
        output_directory=tmp_path / "exports",
    )

    assert artifact.video_path.name.endswith(".mp4")
    assert artifact.cover_path.name.endswith(".jpg")
    assert artifact.caption_path.read_text().splitlines() == ["Weekend", "", "A bright trip."]
    assert executor.commands[0][:5] == ["ffmpeg", "-y", "-stream_loop", "-1", "-i"]
    assert "1080:1920" in executor.commands[0]
    assert executor.commands[0][executor.commands[0].index("-t") + 1] == "60"
    assert "-frames:v" in executor.commands[1]


def test_renderer_is_repeatable_for_same_media_and_unique_for_different_media(tmp_path: Path) -> None:
    first_source = tmp_path / "first" / "source.mp4"
    second_source = tmp_path / "second" / "source.mp4"
    first_source.parent.mkdir()
    second_source.parent.mkdir()
    first_source.write_bytes(b"seeded-media-a")
    second_source.write_bytes(b"seeded-media-b")

    first = DeterministicVerticalRenderer(RecordingExecutor()).render(
        request=RenderRequest(title="Weekend", caption="A bright trip."),
        source_path=first_source,
        output_directory=tmp_path / "exports-a",
    )
    same_media = DeterministicVerticalRenderer(RecordingExecutor()).render(
        request=RenderRequest(title="Weekend", caption="A bright trip."),
        source_path=first_source,
        output_directory=tmp_path / "exports-b",
    )
    different_media = DeterministicVerticalRenderer(RecordingExecutor()).render(
        request=RenderRequest(title="Weekend", caption="A bright trip."),
        source_path=second_source,
        output_directory=tmp_path / "exports-c",
    )

    assert same_media.render_id == first.render_id
    assert different_media.render_id != first.render_id


def test_renderer_can_sequence_multiple_media_sources(tmp_path: Path) -> None:
    executor = RecordingExecutor()
    first_source = tmp_path / "first.jpg"
    second_source = tmp_path / "second.mp4"
    first_source.write_bytes(b"first")
    second_source.write_bytes(b"second")

    artifact = DeterministicVerticalRenderer(executor).render_many(
        request=RenderRequest(title="Weekend", caption="Two moments."),
        source_paths=[first_source, second_source],
        output_directory=tmp_path / "exports",
    )

    assert artifact.video_path.name.endswith(".mp4")
    command = executor.commands[0]
    assert command.count("-i") == 2
    assert "concat=n=2:v=1:a=0" in " ".join(command)
    assert "trim=duration=30" in " ".join(command)
    assert command[command.index("-t") + 1] == "60"
