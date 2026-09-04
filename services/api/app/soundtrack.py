import os
from pathlib import Path


SUPPORTED_AUDIO_SUFFIXES = {".aac", ".m4a", ".mp3", ".wav"}


class SoundtrackConfigurationError(Exception):
    """Raised when a requested safe soundtrack asset is unavailable."""


def resolve_instrumental_track() -> Path:
    configured_path = os.environ.get("INSTRUMENTAL_AUDIO_PATH", "").strip()
    if not configured_path:
        raise SoundtrackConfigurationError("Instrumental music is not configured.")
    audio_path = Path(configured_path)
    if not audio_path.is_absolute():
        raise SoundtrackConfigurationError("Instrumental music must use an absolute local asset path.")
    if audio_path.suffix.lower() not in SUPPORTED_AUDIO_SUFFIXES or not audio_path.is_file():
        raise SoundtrackConfigurationError("Instrumental music asset is unavailable or unsupported.")
    return audio_path
