import logging
from pathlib import Path
import subprocess
import tempfile


logger = logging.getLogger(__name__)


class VideoThumbnailError(RuntimeError):
    """Raised without source details when a safe JPEG preview cannot be created."""


class SubprocessVideoThumbnailer:
    """Extract a small representative JPEG from a private video upload."""

    def create(self, contents: bytes, suffix: str) -> bytes:
        input_format = {
            ".3g2": "mov",
            ".3gp": "mov",
            ".avi": "avi",
            ".m4v": "mov",
            ".mkv": "matroska",
            ".mov": "mov",
            ".mp4": "mov",
            ".mpeg": "mpeg",
            ".mpg": "mpeg",
            ".webm": "matroska",
        }.get(suffix.lower())
        if input_format is None:
            raise VideoThumbnailError("Video preview could not be prepared.")
        with tempfile.TemporaryDirectory(prefix="memory-director-thumbnail-") as temporary_directory:
            temporary_root = Path(temporary_directory)
            source_path = temporary_root / f"source{suffix}"
            preview_path = temporary_root / "preview.jpg"
            source_path.write_bytes(contents)
            try:
                subprocess.run(
                    [
                        "ffmpeg",
                        "-y",
                        "-protocol_whitelist",
                        "file,pipe",
                        "-f",
                        input_format,
                        "-i",
                        str(source_path),
                        "-vf",
                        "thumbnail=30,scale=480:480:force_original_aspect_ratio=decrease",
                        "-frames:v",
                        "1",
                        "-q:v",
                        "4",
                        str(preview_path),
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
                logger.warning("Video thumbnail extraction failed")
                raise VideoThumbnailError("Video preview could not be prepared.") from None
            if not preview_path.is_file() or preview_path.stat().st_size == 0:
                logger.warning("Video thumbnail extraction produced no image")
                raise VideoThumbnailError("Video preview could not be prepared.")
            return preview_path.read_bytes()
