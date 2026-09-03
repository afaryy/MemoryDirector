from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import subprocess
from typing import Protocol

from app.models import Storyboard

TARGET_VIDEO_SECONDS = 60


class ApprovalRequired(Exception):
    """Raised when a render is requested before the user approves its plan."""


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


class RenderExecutor(Protocol):
    def run(self, command: list[str]) -> None: ...


class SubprocessRenderExecutor:
    """Run the pinned ffmpeg commands used by the deterministic renderer."""

    def run(self, command: list[str]) -> None:
        # A fixed 60-second 1080x1920 render can take longer than two minutes on
        # the smallest Cloud Run instance. Keep the request bounded, but allow
        # enough time for the user-approved export to complete.
        subprocess.run(command, check=True, capture_output=True, text=True, timeout=300)


def create_render_request(storyboard: Storyboard, approved: bool) -> RenderRequest:
    if not approved:
        raise ApprovalRequired("Approve the plan before creating a video.")

    return RenderRequest(title=storyboard.title, caption=storyboard.caption)


class DeterministicVerticalRenderer:
    def __init__(self, executor: RenderExecutor) -> None:
        self._executor = executor

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
                    "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black",
                    "-s",
                    "1080:1920",
                ]
            )
            if request.audio_path is not None:
                command.extend(["-af", "afade=t=out:st=59:d=1", "-c:a", "aac"])
            command.append(str(video_path))
            self._executor.run(command)
        else:
            segment_seconds = max(3, TARGET_VIDEO_SECONDS // len(source_paths))
            command = ["ffmpeg", "-y"]
            for source_path in source_paths:
                if source_path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
                    command.extend(["-loop", "1"])
                else:
                    command.extend(["-stream_loop", "-1"])
                command.extend(["-i", str(source_path)])
            audio_input_index = len(source_paths)
            if request.audio_path is not None:
                command.extend(["-stream_loop", "-1", "-i", str(request.audio_path)])
            filters = []
            for index in range(len(source_paths)):
                filters.append(
                    f"[{index}:v]scale=1080:1920:force_original_aspect_ratio=decrease,"
                    f"pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black,"
                    f"trim=duration={segment_seconds},setpts=PTS-STARTPTS[v{index}]"
                )
            inputs = "".join(f"[v{index}]" for index in range(len(source_paths)))
            command.extend(
                [
                    "-filter_complex",
                    ";".join(filters) + f";{inputs}concat=n={len(source_paths)}:v=1:a=0[outv]",
                    "-map",
                    "[outv]",
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


def _source_digest(source_path: Path) -> str:
    digest = sha256()
    with source_path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
