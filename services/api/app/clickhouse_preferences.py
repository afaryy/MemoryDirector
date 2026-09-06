from typing import Protocol

from app.preferences import ClickHouseMcpPreferenceRepository, McpToolCaller


class PreferenceLookup(Protocol):
    def lookup_approved_music_preference(
        self, user_id: str, occasion: str
    ) -> dict[str, str | int] | None: ...


class ClickHousePreferenceTool:
    """Expose only the approved, read-only music preference lookup to the agent."""

    def __init__(self, caller: McpToolCaller) -> None:
        self._repository = ClickHouseMcpPreferenceRepository(caller)

    def lookup_approved_music_preference(
        self, user_id: str, occasion: str
    ) -> dict[str, str | int] | None:
        try:
            recommendation = self._repository.recommend(user_id, occasion)
        except Exception:
            return None
        if recommendation is None:
            return None
        return {
            "music_direction": recommendation.music_direction.removesuffix(" instrumental"),
            "evidence_count": recommendation.evidence_count,
        }
