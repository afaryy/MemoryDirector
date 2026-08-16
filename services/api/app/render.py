from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Protocol

from app.models import Storyboard


class ApprovalRequired(Exception):
    """Raised when a render is requested before the user approves its plan."""


@dataclass(frozen=True)
class RenderRequest:
    title: str
    caption: str
    output_format: str = "vertical-mp4"


@dataclass(frozen=True)
class RenderArtifact:
    render_id: str
    video_path: Path
    cover_path: Path
    caption_path: Path


class RenderExecutor(Protocol):
    def run(self, command: list[str]) -> None: ...


def create_render_request(storyboard: Storyboard, approved: bool) -> RenderRequest:
    if not approved:
        raise ApprovalRequired("Approve the plan before creating a video.")

    return RenderRequest(title=storyboard.title, caption=storyboard.caption)


class DeterministicVerticalRenderer:
    def __init__(self, executor: RenderExecutor) -> None:
        self._executor = executor

    def render(self, request: RenderRequest, source_path: Path, output_directory: Path) -> RenderArtifact:
        render_id = sha256(f"{request.title}\0{request.caption}\0{source_path.name}".encode()).hexdigest()[:12]
        output_directory.mkdir(parents=True, exist_ok=True)
        video_path = output_directory / f"{render_id}.mp4"
        cover_path = output_directory / f"{render_id}.jpg"
        caption_path = output_directory / f"{render_id}.txt"
        caption_path.write_text(f"{request.title}\n\n{request.caption}\n")

        self._executor.run(
            [
                "ffmpeg",
                "-y",
                "-stream_loop",
                "-1",
                "-i",
                str(source_path),
                "-t",
                "45",
                "-r",
                "30",
                "-vf",
                "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black",
                "-s",
                "1080:1920",
                str(video_path),
            ]
        )
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
