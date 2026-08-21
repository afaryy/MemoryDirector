import json

from app.preferences import ClickHouseMcpPreferenceRepository, FakePreferenceRepository, McpHttpToolCaller


def test_recommendation_explains_user_history() -> None:
    repository = FakePreferenceRepository(
        ["gentle festive", "gentle festive", "loud pop rejected"]
    )

    recommendation = repository.recommend("demo-user", "travel")

    assert recommendation.music_direction == "gentle festive instrumental"
    assert "twice" in recommendation.explanation


class RecordingCaller:
    def __init__(self, result: str) -> None:
        self.result = result
        self.calls: list[tuple[str, dict[str, str]]] = []

    def call_tool(self, name: str, arguments: dict[str, str]) -> str:
        self.calls.append((name, arguments))
        return self.result


def test_clickhouse_repository_turns_mcp_result_into_explainable_recommendation() -> None:
    caller = RecordingCaller(json.dumps({"rows": [{"value": "gentle festive", "evidence_count": 2}]}))
    repository = ClickHouseMcpPreferenceRepository(caller)

    recommendation = repository.recommend("demo-user", "travel")

    assert recommendation.music_direction == "gentle festive instrumental"
    assert recommendation.evidence_count == 2
    assert "twice" in recommendation.explanation
    assert caller.calls[0][0] == "run_query"
    assert "creative_preferences" in caller.calls[0][1]["query"]


def test_mcp_http_caller_initializes_session_then_calls_tool(monkeypatch) -> None:
    responses = [
        (200, {"Mcp-Session-Id": "session-1"}, {"result": {"serverInfo": {"name": "mcp-clickhouse"}}}),
        (200, {}, {"result": {"content": [{"type": "text", "text": '{"rows": []}'}]}}),
    ]

    class FakeResponse:
        def __init__(self, status: int, headers: dict[str, str], payload: dict) -> None:
            self.status = status
            self.headers = headers
            self._payload = payload

        def read(self) -> bytes:
            return json.dumps(self._payload).encode()

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    def fake_urlopen(request, timeout):
        status, headers, payload = responses.pop(0)
        assert request.full_url == "https://mcp.example/mcp"
        assert request.headers["Authorization"] == "Bearer mcp-token"
        assert timeout == 5
        return FakeResponse(status, headers, payload)

    monkeypatch.setattr("app.preferences.urlopen", fake_urlopen)
    caller = McpHttpToolCaller("https://mcp.example", "mcp-token", identity_token="identity-token")

    result = caller.call_tool("run_query", {"query": "SELECT 1"})

    assert json.loads(result) == {"rows": []}
    assert responses == []
