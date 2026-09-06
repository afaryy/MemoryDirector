from dataclasses import dataclass
import re

from app.clickhouse_preferences import ClickHousePreferenceTool


@dataclass
class RecordedCall:
    name: str
    arguments: dict[str, str]


class RecordingMcpToolCaller:
    def __init__(self, result: str) -> None:
        self.result = result
        self.calls: list[RecordedCall] = []

    def call_tool(self, name: str, arguments: dict[str, str]) -> str:
        self.calls.append(RecordedCall(name, arguments))
        return self.result


class FailingMcpToolCaller:
    def call_tool(self, name: str, arguments: dict[str, str]) -> str:
        raise RuntimeError("MCP unavailable")


def test_tool_uses_only_fixed_read_only_query_through_mcp() -> None:
    caller = RecordingMcpToolCaller('[{"value":"warm acoustic","evidence_count":2}]')

    result = ClickHousePreferenceTool(caller).lookup_approved_music_preference(
        "user'7", "family ' lunch"
    )

    assert result == {"music_direction": "warm acoustic", "evidence_count": 2}
    assert caller.calls[0].name == "run_query"
    query = " ".join(caller.calls[0].arguments["query"].split())
    assert re.match(r"SELECT value, count\(\) AS evidence_count FROM creative_preferences", query)
    assert "user_id = 'user''7'" in query
    assert "occasion = 'family '' lunch'" in query
    assert "decision = 'accepted'" in query
    assert re.search(r"GROUP BY value ORDER BY evidence_count DESC, value ASC LIMIT 1$", query)
    assert ";" not in query
    assert not re.search(r"\b(?:INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE)\b", query, re.I)


def test_query_escapes_backslashes_quotes_and_control_characters_as_literals() -> None:
    caller = RecordingMcpToolCaller("[]")
    user_id = "x\\' OR 1=1 --\x00"
    occasion = "family\\' lunch\nOR decision = 'rejected'"

    ClickHousePreferenceTool(caller).lookup_approved_music_preference(user_id, occasion)

    query = caller.calls[0].arguments["query"]
    assert "user_id = 'x\\\\'' OR 1=1 --\\0'" in query
    assert "occasion = 'family\\\\'' lunch\\nOR decision = ''rejected'''" in query
    assert query.count("AND decision = 'accepted'") == 1


def test_tool_returns_none_when_mcp_is_unavailable() -> None:
    assert (
        ClickHousePreferenceTool(FailingMcpToolCaller()).lookup_approved_music_preference(
            "user-7", "family lunch"
        )
        is None
    )


def test_tool_returns_none_for_malformed_mcp_response() -> None:
    caller = RecordingMcpToolCaller("not-json-or-a-table")

    assert (
        ClickHousePreferenceTool(caller).lookup_approved_music_preference(
            "user-7", "family lunch"
        )
        is None
    )


def test_tool_returns_only_normalized_public_fields() -> None:
    caller = RecordingMcpToolCaller(
        '{"rows":[{"value":"gentle festive","evidence_count":"3",'
        '"user_id":"user-7","password":"do-not-return"}]}'
    )

    result = ClickHousePreferenceTool(caller).lookup_approved_music_preference(
        "user-7", "family lunch"
    )

    assert result == {"music_direction": "gentle festive", "evidence_count": 3}
