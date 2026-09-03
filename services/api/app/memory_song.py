from dataclasses import dataclass
import re


class UnsafeSongRequest(ValueError):
    """Raised when a song request would copy protected material or a person."""


@dataclass(frozen=True)
class MemorySongBrief:
    prompt: str
    fallback: str = "instrumental"


_UNSAFE_PHRASES = (
    "lyrics from",
    "lyrics of",
    "clone",
    "voice imitation",
    "sound like",
    "cover",
    "in the style of",
    "imitate",
)


def _requests_named_imitation(requested_style: str) -> bool:
    normalized_style = requested_style.casefold()
    if any(phrase in normalized_style for phrase in _UNSAFE_PHRASES):
        return True
    return re.search(r"\blike\s+[A-Z][\w'-]*(?:\s+[A-Z][\w'-]*){0,3}\b", requested_style) is not None


def build_memory_song_brief(*, memory_details: list[str], requested_style: str) -> MemorySongBrief:
    if _requests_named_imitation(requested_style):
        raise UnsafeSongRequest("Use an original style without an artist, existing lyrics, or voice imitation.")
    details = "; ".join(detail.strip() for detail in memory_details if detail.strip())
    if not details:
        raise ValueError("At least one approved memory detail is required.")
    return MemorySongBrief(
        prompt=(
            "Create an original 60-second memory song with gentle vocals. "
            f"Approved memory details: {details}. Style: {requested_style.strip() or 'warm acoustic'}. "
            "Do not imitate an artist, existing song, lyrics, or real person's voice."
        )
    )
