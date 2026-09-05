from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import subprocess
from typing import Literal, Protocol

from app.models import Storyboard

TARGET_VIDEO_SECONDS = 60
TRANSITION_SECONDS = 1
PHOTO_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


class ApprovalRequired(Exception):
    """Raised when a render is requested before the user approves its plan."""


class RenderVerificationError(Exception):
    """Raised when the encoded video does not satisfy the output contract."""


@dataclass(frozen=True)
class RenderRequest:
    title: str
    caption: str
    output_format: str = "vertical-mp4"
    audio_path: Path | None = None


@dataclass(frozen=True)
class RenderArtifact:
    render_id: str
    video_path: Path
    cover_path: Path
    caption_path: Path


@dataclass(frozen=True)
class TimelineSegment:
    source_path: Path
    source_kind: Literal["photo", "video"]
    start_offset_seconds: int
    duration_seconds: int


@dataclass(frozen=True)
class RenderTimeline:
    segments: tuple[TimelineSegment, ...]
    transition_seconds: int

    @property
    def transition_total_seconds(self) -> int:
        return self.transition_seconds * max(0, len(self.segments) - 1)

    @property
    def rendered_duration_seconds(self) -> int:
        return sum(segment.duration_seconds for segment in self.segments) - self.transition_total_seconds


class RenderExecutor(Protocol):
    def run(self, command: list[str]) -> None: ...


class VideoDurationProbe(Protocol):
    def duration_seconds_for(self, video_path: Path) -> float: ...


class SubprocessRenderExecutor:
    """Run the pinned ffmpeg commands used by the deterministic renderer."""

    def run(self, command: list[str]) -> None:
        # A fixed 60-second 1080x1920 render can take longer than two minutes on
        # the smallest Cloud Run instance. Keep the request bounded, but allow
        # enough time for the user-approved export to complete.
        subprocess.run(command, check=True, capture_output=True, text=True, timeout=300)


class SubprocessVideoDurationProbe:
    def duration_seconds_for(self, video_path: Path) -> float:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(video_path),
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        try:
            return float(result.stdout.strip())
        except ValueError as error:
            raise RenderVerificationError("The finished video duration could not be verified.") from error


def create_render_request(storyboard: Storyboard, approved: bool) -> RenderRequest:
    if not approved:
        raise ApprovalRequired("Approve the plan before creating a video.")

    return RenderRequest(title=storyboard.title, caption=storyboard.caption)


def allocate_timeline(source_paths: list[Path]) -> RenderTimeline:
    if not source_paths:
        raise ValueError("At least one media source is required")
    if len(source_paths) > 15:
        raise ValueError("A film can include at most 15 media sources")

    transition_total = TRANSITION_SECONDS * max(0, len(source_paths) - 1)
    segment_total = TARGET_VIDEO_SECONDS + transition_total
    base_duration, remainder = divmod(segment_total, len(source_paths))
    segments = tuple(
        TimelineSegment(
            source_path=source_path,
            source_kind="photo" if source_path.suffix.lower() in PHOTO_SUFFIXES else "video",
            start_offset_seconds=0,
            duration_seconds=base_duration + (1 if index < remainder else 0),
        )
        for index, source_path in enumerate(source_paths)
    )
    return RenderTimeline(segments=segments, transition_seconds=TRANSITION_SECONDS)


class DeterministicVerticalRenderer:
    def __init__(self, executor: RenderExecutor, *, duration_probe: VideoDurationProbe | None = None) -> None:
        self._executor = executor
        self._duration_probe = duration_probe

    def render(self, request: RenderRequest, source_path: Path, output_directory: Path) -> RenderArtifact:
        return self.render_many(request, [source_path], output_directory)

    def render_many(self, request: RenderRequest, source_paths: list[Path], output_directory: Path) -> RenderArtifact:
        if not source_paths:
            raise ValueError("At least one media source is required")
        source_digest = "\0".join(_source_digest(path) for path in source_paths)
        render_id = sha256(f"{request.title}\0{request.caption}\0{source_digest}".encode()).hexdigest()[:12]
        output_directory.mkdir(parents=True, exist_ok=True)
        video_path = output_directory / f"{render_id}.mp4"
        cover_path = output_directory / f"{render_id}.jpg"
        caption_path = output_directory / f"{render_id}.txt"
        caption_path.write_text(f"{request.title}\n\n{request.caption}\n")

        if len(source_paths) == 1:
            command = [
                "ffmpeg",
                "-y",
                "-stream_loop",
                "-1",
                "-i",
                str(source_paths[0]),
            ]
            if request.audio_path is not None:
                command.extend(["-stream_loop", "-1", "-i", str(request.audio_path), "-map", "0:v:0", "-map", "1:a:0"])
            command.extend(
                [
                    "-t",
                    str(TARGET_VIDEO_SECONDS),
                    "-r",
                    "30",
                    "-c:v",
                    "libx264",
                    "-preset",
                    "veryfast",
                    "-crf",
                    "23",
                    "-pix_fmt",
                    "yuv420p",
                    "-vf",
                    "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1",
                    "-s",
                    "1080:1920",
                ]
            )
            if request.audio_path is not None:
                command.extend(["-af", "afade=t=out:st=59:d=1", "-c:a", "aac"])
            command.append(str(video_path))
            self._executor.run(command)
        else:
            timeline = allocate_timeline(source_paths)
            command = ["ffmpeg", "-y"]
            for segment in timeline.segments:
                if segment.source_kind == "photo":
                    command.extend(["-loop", "1"])
                else:
                    command.extend(["-stream_loop", "-1", "-ss", str(segment.start_offset_seconds)])
                command.extend(["-i", str(segment.source_path)])
            audio_input_index = len(source_paths)
            if request.audio_path is not None:
                command.extend(["-stream_loop", "-1", "-i", str(request.audio_path)])
            filters = []
            for index, segment in enumerate(timeline.segments):
                filters.append(
                    f"[{index}:v]scale=1080:1920:force_original_aspect_ratio=increase,"
                    f"crop=1080:1920,setsar=1,"
                    f"trim=duration={segment.duration_seconds},setpts=PTS-STARTPTS[v{index}]"
                )
            current_label = "v0"
            cumulative_offset = 0
            for index, segment in enumerate(timeline.segments[1:], start=1):
                previous_duration = timeline.segments[index - 1].duration_seconds
                cumulative_offset += previous_duration - timeline.transition_seconds
                next_label = f"xfade{index - 1}"
                filters.append(
                    f"[{current_label}][v{index}]xfade=transition=fade:duration={timeline.transition_seconds}:"
                    f"offset={cumulative_offset}[{next_label}]"
                )
                current_label = next_label
            command.extend(
                [
                    "-filter_complex",
                    ";".join(filters),
                    "-map",
                    f"[{current_label}]",
                ]
            )
            if request.audio_path is not None:
                command.extend(["-map", f"{audio_input_index}:a:0"])
            command.extend(
                [
                    "-t",
                    str(TARGET_VIDEO_SECONDS),
                    "-r",
                    "30",
                    "-c:v",
                    "libx264",
                    "-preset",
                    "veryfast",
                    "-crf",
                    "23",
                    "-pix_fmt",
                    "yuv420p",
                ]
            )
            if request.audio_path is not None:
                command.extend(["-af", "afade=t=out:st=59:d=1", "-c:a", "aac"])
            else:
                command.append("-an")
            command.append(str(video_path))
            self._executor.run(command)
        self._verify_duration(video_path)
        self._executor.run(
            [
                "ffmpeg",
                "-y",
                "-ss",
                "00:00:01",
                "-i",
                str(video_path),
                "-frames:v",
                "1",
                str(cover_path),
            ]
        )

        return RenderArtifact(
            render_id=render_id,
            video_path=video_path,
            cover_path=cover_path,
            caption_path=caption_path,
        )

    def _verify_duration(self, video_path: Path) -> None:
        if self._duration_probe is None:
            return
        duration_seconds = self._duration_probe.duration_seconds_for(video_path)
        if not 59.5 <= duration_seconds <= 60.5:
            raise RenderVerificationError("The finished video duration is outside the 60-second tolerance.")


def _source_digest(source_path: Path) -> str:
    digest = sha256()
    with source_path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
