import json
import os
from typing import Literal, Protocol, Sequence

from app.preferences import McpHttpToolCaller, McpToolCaller, _extract_rows

SoundtrackMode = Literal["original_song", "instrumental", "no_sound"]
ExportStage = Literal["render", "export"]


class ConsentDenied(Exception):
    """Raised when the consent record required for export is absent or invalid."""


class ConsentGuardian(Protocol):
    def allow_export(self, *, media_ids: Sequence[str], soundtrack_mode: SoundtrackMode, stage: ExportStage) -> None: ...


class ClickHouseMcpConsentGuardian:
    def __init__(self, caller: McpToolCaller) -> None:
        self._caller = caller

    def allow_export(self, *, media_ids: Sequence[str], soundtrack_mode: SoundtrackMode, stage: ExportStage) -> None:
        if not media_ids:
            raise ConsentDenied("Selected media consent evidence is required.")
        if soundtrack_mode not in {"original_song", "instrumental", "no_sound"}:
            raise ConsentDenied("The soundtrack choice is not recognised.")
        try:
            raw = self._caller.call_tool("run_query", {"query": self._selected_media_query(media_ids)})
            rows = _extract_rows(raw)
            selected_count = int(rows[0].get("selected_media_count", 0)) if rows else 0
        except Exception as error:
            raise ConsentDenied("Consent evidence is unavailable; please try again later.") from error
        if selected_count != len(set(media_ids)):
            raise ConsentDenied("Selected media consent evidence is missing.")

    @staticmethod
    def _selected_media_query(media_ids: Sequence[str]) -> str:
        quoted_ids = ", ".join("'" + media_id.replace("'", "''") + "'" for media_id in sorted(set(media_ids)))
        return (
            "SELECT countDistinct(media_id) AS selected_media_count "
            "FROM production_events "
            "WHERE event_type = 'media_selected' "
            f"AND media_id IN ({quoted_ids})"
        )


def consent_guardian_from_environment() -> ConsentGuardian | None:
    endpoint = os.environ.get("CLICKHOUSE_MCP_ENDPOINT")
    credentials_json = os.environ.get("CLICKHOUSE_CREDENTIALS_JSON")
    if not endpoint or not credentials_json:
        return None
    try:
        credentials = json.loads(credentials_json)
        token = credentials["CLICKHOUSE_MCP_AUTH_TOKEN"]
    except (KeyError, TypeError, json.JSONDecodeError) as error:
        raise RuntimeError("ClickHouse MCP credentials are invalid") from error
    return ClickHouseMcpConsentGuardian(
        McpHttpToolCaller(endpoint, token, identity_token=os.environ.get("CLICKHOUSE_MCP_IDENTITY_TOKEN"))
    )
