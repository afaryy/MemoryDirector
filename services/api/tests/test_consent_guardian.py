import json

import pytest

from app.consent_guardian import ConsentDenied, ClickHouseMcpConsentGuardian


class RecordingCaller:
    def __init__(self, response: str) -> None:
        self.response = response
        self.calls: list[tuple[str, dict[str, str]]] = []

    def call_tool(self, name: str, arguments: dict[str, str]) -> str:
        self.calls.append((name, arguments))
        return self.response


def test_guardian_allows_only_when_every_selected_media_id_has_evidence() -> None:
    caller = RecordingCaller(json.dumps({"rows": [{"selected_media_count": 2}]}))
    guardian = ClickHouseMcpConsentGuardian(caller)

    guardian.allow_export(media_ids=["media-a", "media-b"], soundtrack_mode="no_sound", stage="render")

    assert caller.calls[0][0] == "run_query"
    assert "media-a" in caller.calls[0][1]["query"]
    assert "media-b" in caller.calls[0][1]["query"]


def test_guardian_denies_missing_selected_media_evidence() -> None:
    guardian = ClickHouseMcpConsentGuardian(RecordingCaller(json.dumps({"rows": [{"selected_media_count": 1}]})))

    with pytest.raises(ConsentDenied, match="consent evidence"):
        guardian.allow_export(media_ids=["media-a", "media-b"], soundtrack_mode="original_song", stage="export")

