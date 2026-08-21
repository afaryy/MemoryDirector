from collections import Counter
from dataclasses import dataclass
import json
import os
from typing import Any
from typing import Protocol
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class PreferenceRecommendation:
    music_direction: str
    evidence_count: int
    explanation: str


class McpToolCaller(Protocol):
    def call_tool(self, name: str, arguments: dict[str, str]) -> str: ...


class McpHttpToolCaller:
    """Minimal authenticated MCP Streamable HTTP client for the Cloud Run server."""

    def __init__(
        self,
        endpoint: str,
        auth_token: str,
        *,
        identity_token: str | None = None,
        timeout: float = 5,
    ) -> None:
        if not endpoint or not auth_token:
            raise ValueError("MCP endpoint and auth token are required")
        self._url = endpoint.rstrip("/") if endpoint.rstrip("/").endswith("/mcp") else f"{endpoint.rstrip('/')}/mcp"
        self._audience = endpoint.rstrip("/").removesuffix("/mcp")
        self._auth_token = auth_token
        self._identity_token = identity_token
        self._timeout = timeout
        self._session_id: str | None = None
        self._next_id = 1

    def call_tool(self, name: str, arguments: dict[str, str]) -> str:
        if self._session_id is None:
            self._initialize()
        response = self._post(
            {
                "jsonrpc": "2.0",
                "id": self._next_request_id(),
                "method": "tools/call",
                "params": {"name": name, "arguments": arguments},
            },
            include_session=True,
        )
        if response.get("error"):
            raise RuntimeError("MCP tool call failed")
        content = response.get("result", {}).get("content", [])
        for item in content:
            if item.get("type") == "text" and isinstance(item.get("text"), str):
                return item["text"]
        return json.dumps(response.get("result", {}), separators=(",", ":"))

    def _initialize(self) -> None:
        response, session_id = self._post_with_headers(
            {
                "jsonrpc": "2.0",
                "id": self._next_request_id(),
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": {"name": "memory-director-api", "version": "1"},
                },
            },
            include_session=False,
        )
        if response.get("error") or not response.get("result", {}).get("serverInfo", {}).get("name"):
            raise RuntimeError("MCP initialize failed")
        if not session_id:
            raise RuntimeError("MCP server did not return a session")
        self._session_id = session_id

    def _post(self, payload: dict[str, Any], *, include_session: bool) -> dict[str, Any]:
        response, _ = self._post_with_headers(payload, include_session=include_session)
        return response

    def _post_with_headers(self, payload: dict[str, Any], *, include_session: bool) -> tuple[dict[str, Any], str | None]:
        headers = {
            "Authorization": f"Bearer {self._auth_token}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if include_session and self._session_id:
            headers["Mcp-Session-Id"] = self._session_id
        identity_token = self._identity_token or self._fetch_identity_token()
        if identity_token:
            headers["X-Serverless-Authorization"] = f"Bearer {identity_token}"
        request = Request(self._url, data=json.dumps(payload).encode(), headers=headers, method="POST")
        try:
            with urlopen(request, timeout=self._timeout) as response:
                body = response.read().decode()
                session_id = response.headers.get("Mcp-Session-Id")
        except Exception as error:
            raise RuntimeError("MCP server is unavailable") from error
        return _decode_mcp_response(body), session_id

    def _fetch_identity_token(self) -> str | None:
        try:
            from google.auth.transport.requests import Request as GoogleAuthRequest
            from google.oauth2 import id_token

            return id_token.fetch_id_token(GoogleAuthRequest(), self._audience)
        except Exception:
            return None

    def _next_request_id(self) -> int:
        request_id = self._next_id
        self._next_id += 1
        return request_id


class FakePreferenceRepository:
    def __init__(self, history: list[str]) -> None:
        self._history = history

    def recommend(self, user_id: str, occasion: str) -> PreferenceRecommendation:
        accepted = [choice for choice in self._history if not choice.endswith(" rejected")]
        top_choice, evidence_count = Counter(accepted).most_common(1)[0]
        return PreferenceRecommendation(
            music_direction=f"{top_choice} instrumental",
            evidence_count=evidence_count,
            explanation=f"You chose {top_choice} {number_word(evidence_count)} before for similar memories.",
        )


class ClickHouseMcpPreferenceRepository:
    def __init__(self, caller: McpToolCaller) -> None:
        self._caller = caller

    def recommendation_query(self, user_id: str, occasion: str) -> str:
        safe_user_id = user_id.replace("'", "''")
        safe_occasion = occasion.replace("'", "''")
        return f"""
SELECT value, count() AS evidence_count
FROM creative_preferences
WHERE user_id = '{safe_user_id}'
  AND occasion = '{safe_occasion}'
  AND decision = 'accepted'
GROUP BY value
ORDER BY evidence_count DESC, value ASC
LIMIT 1
""".strip()

    def load_raw_recommendation(self, user_id: str, occasion: str) -> str:
        return self._caller.call_tool(
            "run_query",
            {"query": self.recommendation_query(user_id, occasion)},
        )

    def recommend(self, user_id: str, occasion: str) -> PreferenceRecommendation | None:
        raw = self.load_raw_recommendation(user_id, occasion)
        rows = _extract_rows(raw)
        if not rows:
            return None
        top = rows[0]
        value = str(top.get("value", "")).strip()
        if not value:
            return None
        try:
            evidence_count = int(top.get("evidence_count", 0))
        except (TypeError, ValueError):
            evidence_count = 0
        return PreferenceRecommendation(
            music_direction=f"{value} instrumental",
            evidence_count=evidence_count,
            explanation=f"You chose {value} {number_word(evidence_count)} before for similar memories.",
        )


def preference_repository_from_environment() -> ClickHouseMcpPreferenceRepository | None:
    endpoint = os.environ.get("CLICKHOUSE_MCP_ENDPOINT")
    credentials_json = os.environ.get("CLICKHOUSE_CREDENTIALS_JSON")
    if not endpoint or not credentials_json:
        return None
    try:
        credentials = json.loads(credentials_json)
        token = credentials["CLICKHOUSE_MCP_AUTH_TOKEN"]
    except (KeyError, TypeError, json.JSONDecodeError) as error:
        raise RuntimeError("ClickHouse MCP credentials are invalid") from error
    return ClickHouseMcpPreferenceRepository(
        McpHttpToolCaller(
            endpoint,
            token,
            identity_token=os.environ.get("CLICKHOUSE_MCP_IDENTITY_TOKEN"),
        )
    )


def _decode_mcp_response(body: str) -> dict[str, Any]:
    stripped = body.strip()
    if stripped.startswith("data:") or "\ndata:" in stripped:
        data_lines = [line[5:].strip() for line in stripped.splitlines() if line.startswith("data:")]
        stripped = data_lines[-1] if data_lines else ""
    try:
        decoded = json.loads(stripped)
    except json.JSONDecodeError as error:
        raise RuntimeError("MCP response was not JSON") from error
    if not isinstance(decoded, dict):
        raise RuntimeError("MCP response was not an object")
    return decoded


def _extract_rows(raw: str) -> list[dict[str, Any]]:
    try:
        decoded = json.loads(raw)
    except json.JSONDecodeError:
        return _extract_table_rows(raw)
    if isinstance(decoded, dict) and isinstance(decoded.get("rows"), list):
        return [row for row in decoded["rows"] if isinstance(row, dict)]
    if isinstance(decoded, list):
        return [row for row in decoded if isinstance(row, dict)]
    return []


def _extract_table_rows(raw: str) -> list[dict[str, Any]]:
    lines = [line.strip() for line in raw.splitlines() if "|" in line]
    if len(lines) < 2:
        return []
    headers = [part.strip() for part in lines[0].strip("|").split("|")]
    rows: list[dict[str, Any]] = []
    for line in lines[1:]:
        values = [part.strip() for part in line.strip("|").split("|")]
        if not values or all(set(value) <= {"-", ":", " "} for value in values):
            continue
        if len(values) == len(headers):
            rows.append(dict(zip(headers, values)))
    return rows


def number_word(value: int) -> str:
    return {1: "once", 2: "twice"}.get(value, f"{value} times")
