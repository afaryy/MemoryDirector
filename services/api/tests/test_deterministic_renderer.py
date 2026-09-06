from pathlib import Path
import subprocess

import pytest

from app.models import Storyboard
from app.render import (
    DeterministicVerticalRenderer,
    RenderRequest,
    RenderExecutionError,
    SubprocessHeifConverter,
    RenderVerificationError,
    SubprocessRenderExecutor,
    SubprocessVideoDurationProbe,
    create_render_request,
)


class RecordingExecutor:
    def __init__(self) -> None:
        self.commands: list[list[str]] = []

    def run(self, command: list[str]) -> None:
        self.commands.append(command)


class RecordingHeifConverter:
    def __init__(self) -> None:
        self.calls: list[tuple[Path, Path]] = []

    def convert(self, source_path: Path, output_path: Path) -> None:
        self.calls.append((source_path, output_path))
        output_path.write_bytes(b"converted-jpeg")


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
    assert executor.commands[0][executor.commands[0].index("-preset") + 1] == "ultrafast"
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


def test_renderer_sequences_media_with_fade_through_black_and_an_exact_duration(tmp_path: Path) -> None:
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
    filter_graph = command[command.index("-filter_complex") + 1]
    assert "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1" in filter_graph
    assert filter_graph.count("fps=30,format=yuv420p,settb=AVTB") == 2
    assert "trim=duration=30" in filter_graph
    assert "fade=t=in:st=0:d=0.5,fade=t=out:st=29.5:d=0.5" in filter_graph
    assert "[v0][v1]concat=n=2:v=1:a=0[concat]" in filter_graph
    assert "xfade=" not in filter_graph
    assert command[command.index("-filter_complex_threads") + 1] == "1"
    assert command.index("-filter_complex_threads") < command.index("-filter_complex")
    assert command[command.index("-t") + 1] == "60"
    assert command[command.index("-preset") + 1] == "ultrafast"


def test_renderer_mixes_optional_memory_song(tmp_path: Path) -> None:
    executor = RecordingExecutor()
    source = tmp_path / "source.mp4"
    song = tmp_path / "song.mp3"
    source.write_bytes(b"video")
    song.write_bytes(b"audio")

    DeterministicVerticalRenderer(executor).render(
        request=RenderRequest(title="Weekend", caption="A bright trip.", audio_path=song),
        source_path=source,
        output_directory=tmp_path / "exports",
    )

    command = executor.commands[0]
    audio_input_index = command.index(str(song))
    assert command[audio_input_index - 3 : audio_input_index] == ["-stream_loop", "-1", "-i"]
    assert command[command.index("-t") + 1] == "60"
    assert command[command.index("-map", command.index("-map") + 1) + 1] == "1:a:0"
    assert "afade=t=out:st=59:d=1" in command
    assert "-shortest" not in command


def test_renderer_uses_optional_memory_song_for_a_combined_film(tmp_path: Path) -> None:
    executor = RecordingExecutor()
    first = tmp_path / "first.jpg"
    second = tmp_path / "second.mp4"
    song = tmp_path / "song.mp3"
    first.write_bytes(b"first")
    second.write_bytes(b"second")
    song.write_bytes(b"audio")

    DeterministicVerticalRenderer(executor).render_many(
        request=RenderRequest(title="Weekend", caption="Two moments.", audio_path=song),
        source_paths=[first, second],
        output_directory=tmp_path / "exports",
    )

    command = executor.commands[0]
    assert command[command.index(str(song)) - 3 : command.index(str(song))] == ["-stream_loop", "-1", "-i"]
    assert command[command.index("-map", command.index("-map") + 1) + 1] == "2:a:0"
    assert command[command.index("-t") + 1] == "60"
    assert "afade=t=out:st=59:d=1" in command
    assert "-an" not in command


def test_renderer_converts_heic_to_temporary_jpeg_before_combining_media(tmp_path: Path) -> None:
    executor = RecordingExecutor()
    converter = RecordingHeifConverter()
    heic = tmp_path / "phone-photo.heic"
    video = tmp_path / "moment.mov"
    heic.write_bytes(b"synthetic-heic")
    video.write_bytes(b"synthetic-video")

    DeterministicVerticalRenderer(executor, heif_converter=converter).render_many(
        request=RenderRequest(title="Phone memory", caption="Together."),
        source_paths=[heic, video],
        output_directory=tmp_path / "exports",
    )

    assert converter.calls[0][0] == heic
    converted_path = converter.calls[0][1]
    assert converted_path.suffix == ".jpg"
    render_command = executor.commands[0]
    assert str(converted_path) in render_command
    assert render_command[render_command.index(str(converted_path)) - 3 : render_command.index(str(converted_path))] == [
        "-loop",
        "1",
        "-i",
    ]


def test_renderer_loops_a_single_phone_photo_as_a_still_image(tmp_path: Path) -> None:
    executor = RecordingExecutor()
    converter = RecordingHeifConverter()
    heic = tmp_path / "phone-photo.heic"
    heic.write_bytes(b"synthetic-heic")

    DeterministicVerticalRenderer(executor, heif_converter=converter).render(
        request=RenderRequest(title="Phone memory", caption="Together."),
        source_path=heic,
        output_directory=tmp_path / "exports",
    )

    converted_path = converter.calls[0][1]
    render_command = executor.commands[0]
    assert render_command[render_command.index(str(converted_path)) - 3 : render_command.index(str(converted_path))] == [
        "-loop",
        "1",
        "-i",
    ]
    assert "-stream_loop" not in render_command


def test_subprocess_executor_allows_sixty_second_export_to_finish(monkeypatch) -> None:
    calls = []

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))

    monkeypatch.setattr("app.render.subprocess.run", fake_run)

    SubprocessRenderExecutor().run(["ffmpeg", "-version"])

    assert calls[0][1]["timeout"] == 300


def test_subprocess_executor_logs_only_sanitized_ffmpeg_error_lines(monkeypatch, caplog) -> None:
    source_path = "/tmp/memory-director-sensitive/source-0.jpg"
    metadata_sentinel = "family-error-secret"

    def fake_run(command, **kwargs):
        raise subprocess.CalledProcessError(
            234,
            command,
            stderr=(
                f"Input #0 from {source_path}\n"
                "[Parsed_xfade_0] First input link main timebase does not match\n"
                f"metadata error: {metadata_sentinel}\n"
                f"Error while processing {source_path}\n"
            ),
        )

    monkeypatch.setattr("app.render.subprocess.run", fake_run)

    with pytest.raises(RuntimeError, match="Video rendering failed"):
        SubprocessRenderExecutor().run(["ffmpeg", "-i", source_path])

    assert "input-timebase-mismatch" in caplog.text
    assert source_path not in caplog.text
    assert metadata_sentinel not in caplog.text


def test_subprocess_executor_classifies_only_fixed_filter_stage_names(monkeypatch, caplog) -> None:
    source_path = "/tmp/memory-director-sensitive/source-1.mov"
    metadata_sentinel = "private-family-caption"

    def fake_run(command, **kwargs):
        raise subprocess.CalledProcessError(
            234,
            command,
            stderr=(
                "[Parsed_scale_8] Failed to configure output pad on Parsed_scale_8\n"
                "[auto_scale_0] Error reinitializing filters\n"
                "[Parsed_xfade_16] Invalid argument\n"
                f"Input metadata: {metadata_sentinel} at {source_path}\n"
            ),
        )

    monkeypatch.setattr("app.render.subprocess.run", fake_run)

    with pytest.raises(RuntimeError, match="Video rendering failed"):
        SubprocessRenderExecutor().run(["ffmpeg", "-i", source_path])

    assert "scale-stage" in caplog.text
    assert "automatic-scale-stage" in caplog.text
    assert "crossfade-stage" in caplog.text
    assert source_path not in caplog.text
    assert metadata_sentinel not in caplog.text


def test_subprocess_executor_translates_timeout_without_command_leakage(monkeypatch, caplog) -> None:
    source_path = "/tmp/memory-director-sensitive/source-0.jpg"

    def fake_run(command, **kwargs):
        raise subprocess.TimeoutExpired(command, 300)

    monkeypatch.setattr("app.render.subprocess.run", fake_run)

    with pytest.raises(RuntimeError, match="Video rendering failed") as captured:
        SubprocessRenderExecutor().run(["ffmpeg", "-i", source_path])

    assert source_path not in str(captured.value)
    assert "timeout" in caplog.text
    assert source_path not in caplog.text


def test_duration_probe_translates_subprocess_failure_without_path_leakage(monkeypatch, caplog) -> None:
    video_path = Path("/tmp/memory-director-sensitive/output.mp4")

    def fake_run(command, **kwargs):
        raise subprocess.CalledProcessError(1, command, stderr=f"probe failed for {video_path}")

    monkeypatch.setattr("app.render.subprocess.run", fake_run)

    with pytest.raises(RenderVerificationError, match="could not be verified") as captured:
        SubprocessVideoDurationProbe().duration_seconds_for(video_path)

    assert str(video_path) not in str(captured.value)
    assert "duration-probe-failed" in caplog.text
    assert str(video_path) not in caplog.text


def test_heif_converter_translates_failure_without_path_or_metadata_leakage(monkeypatch, caplog) -> None:
    source_path = Path("/tmp/memory-director-sensitive/family.heic")
    output_path = Path("/tmp/memory-director-sensitive/converted.jpg")
    metadata_sentinel = "private-family-caption"

    def fake_run(command, **kwargs):
        raise subprocess.CalledProcessError(1, command, stderr=f"{metadata_sentinel}: {source_path}")

    monkeypatch.setattr("app.render.subprocess.run", fake_run)

    with pytest.raises(RenderExecutionError, match="Phone photo conversion failed") as captured:
        SubprocessHeifConverter().convert(source_path, output_path)

    assert str(source_path) not in str(captured.value)
    assert str(output_path) not in caplog.text
    assert metadata_sentinel not in caplog.text
    assert "heif-convert failed (exit-1)" in caplog.text


def test_heif_converter_promotes_first_numbered_image_to_requested_output(monkeypatch, tmp_path: Path) -> None:
    source_path = tmp_path / "phone-sequence.heic"
    output_path = tmp_path / "converted.jpg"
    source_path.write_bytes(b"synthetic-heif-sequence")

    def fake_run(command, **kwargs):
        (tmp_path / "converted-2.jpg").write_bytes(b"second-image")
        (tmp_path / "converted-1.jpg").write_bytes(b"primary-image")

    monkeypatch.setattr("app.render.subprocess.run", fake_run)

    SubprocessHeifConverter().convert(source_path, output_path)

    assert output_path.read_bytes() == b"primary-image"


def test_heif_converter_rejects_success_without_a_nonempty_output(monkeypatch, tmp_path: Path, caplog) -> None:
    source_path = tmp_path / "malformed.heic"
    output_path = tmp_path / "converted.jpg"
    source_path.write_bytes(b"malformed")

    monkeypatch.setattr("app.render.subprocess.run", lambda command, **kwargs: None)

    with pytest.raises(RenderExecutionError, match="Phone photo conversion failed"):
        SubprocessHeifConverter().convert(source_path, output_path)

    assert str(source_path) not in caplog.text
    assert str(output_path) not in caplog.text
    assert "heif-convert failed (missing-output)" in caplog.text
