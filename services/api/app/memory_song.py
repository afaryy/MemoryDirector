from dataclasses import dataclass


class UnsafeSongRequest(ValueError):
    """Raised when a song request would copy protected material or a person."""


@dataclass(frozen=True)
class MemorySongBrief:
    prompt: str
    fallback: str = "instrumental"


_UNSAFE_PHRASES = ("like ", "lyrics from", "lyrics of", "clone", "voice imitation", "sound like")


def build_memory_song_brief(*, memory_details: list[str], requested_style: str) -> MemorySongBrief:
    normalized_style = requested_style.casefold()
    if any(phrase in normalized_style for phrase in _UNSAFE_PHRASES):
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
