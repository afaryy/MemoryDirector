import json
from typing import Protocol

from google.cloud import secretmanager

from app.agent_planner import APPLICATION_MUSIC_DIRECTIONS
from app.preferences import ClickHouseMcpPreferenceRepository, McpHttpToolCaller, McpToolCaller


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
        stored_direction = recommendation.music_direction.strip().casefold()
        while stored_direction.endswith(" instrumental"):
            stored_direction = stored_direction.removesuffix(" instrumental").rstrip()
        music_direction = next(
            (
                candidate
                for candidate in APPLICATION_MUSIC_DIRECTIONS
                if stored_direction
                == candidate.removesuffix(" instrumental").casefold()
            ),
            None,
        )
        if music_direction is None:
            return None
        return {
            "music_direction": music_direction,
            "evidence_count": recommendation.evidence_count,
        }


class LazyClickHousePreferenceTool:
    """Resolve the MCP token inside Agent Engine instead of serializing a secret."""

    def __init__(self, *, endpoint: str, credentials_secret_version_name: str) -> None:
        if not endpoint or not credentials_secret_version_name:
            raise ValueError("MCP endpoint and credentials secret version are required")
        self._endpoint = endpoint
        self._credentials_secret_version_name = credentials_secret_version_name

    def lookup_approved_music_preference(
        self, user_id: str, occasion: str
    ) -> dict[str, str | int] | None:
        """Read the user's approved music preference through a read-only lookup."""
        try:
            response = secretmanager.SecretManagerServiceClient().access_secret_version(
                name=self._credentials_secret_version_name
            )
            credentials = json.loads(response.payload.data.decode())
            auth_token = credentials["CLICKHOUSE_MCP_AUTH_TOKEN"]
            if not isinstance(auth_token, str) or not auth_token:
                return None
            return ClickHousePreferenceTool(
                McpHttpToolCaller(self._endpoint, auth_token)
            ).lookup_approved_music_preference(user_id, occasion)
        except Exception:
            return None
