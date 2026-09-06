import asyncio
import json

import cloudpickle
import pytest

import app.agent_engine as agent_engine_module
from app.agent_engine import (
    AgentEnginePlanner,
    AgentPlannerUnavailable,
    InvalidAgentPlanError,
)
from app.agent_planner import AgentPlanningRequest, AgentProductionPlan, PlannerMedia
from app.adk_memory_film_agent import build_memory_film_agent
from app.clickhouse_preferences import LazyClickHousePreferenceTool
import app.clickhouse_preferences as clickhouse_preferences_module
from scripts import deploy_agent_engine, smoke_agent_engine


def valid_plan_payload() -> dict[str, object]:
    return {
        "title": "A sunny afternoon",
        "caption": "A small day worth keeping.",
        "music_direction": "warm acoustic instrumental",
        "selected_segments": [
            {"media_id": "clip-1", "trim_start_seconds": 0, "trim_end_seconds": 60}
        ],
        "held_back_media_ids": [],
        "user_explanation": "I kept the clearest moment.",
    }


class FakeRemoteAgent:
    async def async_stream_query(self, *, message: str, user_id: str):
        yield {"content": {"parts": [{"text": json.dumps(valid_plan_payload())}]}}


class FakeAgentEngines:
    def get(self, *, name: str) -> FakeRemoteAgent:
        return FakeRemoteAgent()


class FakeClient:
    agent_engines = FakeAgentEngines()


class RecordingAgentEngines:
    def __init__(self, remote_agent=None, error: Exception | None = None) -> None:
        self.get_calls: list[str] = []
        self._remote_agent = remote_agent
        self._error = error

    def get(self, *, name: str):
        self.get_calls.append(name)
        if self._error is not None:
            raise self._error
        return self._remote_agent


class RecordingAgentEngineClient:
    def __init__(self, agent_engines: RecordingAgentEngines) -> None:
        self.agent_engines = agent_engines


class FailingStreamRemoteAgent:
    async def async_stream_query(self, *, message: str, user_id: str):
        raise RuntimeError("Agent Engine stream is unavailable")
        yield


class PayloadRemoteAgent:
    def __init__(self, payload: object) -> None:
        self._payload = payload

    async def async_stream_query(self, *, message: str, user_id: str):
        yield self._payload


class RecordingRemoteAgent:
    def __init__(self) -> None:
        self.user_ids: list[str] = []

    async def async_stream_query(self, *, message: str, user_id: str):
        self.user_ids.append(user_id)
        yield {"content": {"parts": [{"text": json.dumps(valid_plan_payload())}]}}


class SlowRemoteAgent:
    async def async_stream_query(self, *, message: str, user_id: str):
        await asyncio.sleep(1)
        yield {"content": {"parts": [{"text": json.dumps(valid_plan_payload())}]}}


class ExcessiveEventsRemoteAgent:
    async def async_stream_query(self, *, message: str, user_id: str):
        for _ in range(129):
            yield {"text": "{}"}


def planning_request() -> AgentPlanningRequest:
    return AgentPlanningRequest(
        occasion="A sunny afternoon",
        target_duration_seconds=60,
        moods=["warm"],
        music_constraints=["acoustic"],
        media=[PlannerMedia(media_id="clip-1", quality_score=0.9, duplicate_of=None)],
    )


def test_agent_engine_planner_rejects_invalid_resource_name() -> None:
    with pytest.raises(ValueError, match="reasoningEngines"):
        AgentEnginePlanner(resource_name="not-an-agent", client=FakeClient())


@pytest.mark.parametrize(
    "resource_name",
    [
        "projects/a b/locations/us-central1/reasoningEngines/123",
        "projects/demo-project/locations/../reasoningEngines/123",
        "projects/demo-project/locations/us-central1/reasoningEngines/agent.name",
    ],
)
def test_agent_engine_planner_rejects_invalid_resource_components(resource_name: str) -> None:
    with pytest.raises(ValueError, match="reasoningEngines"):
        AgentEnginePlanner(resource_name=resource_name, client=FakeClient())


def test_invalid_resource_rejects_before_agent_engine_get() -> None:
    engines = RecordingAgentEngines(error=AssertionError("client must not be called"))
    client = RecordingAgentEngineClient(engines)

    with pytest.raises(ValueError, match="reasoningEngines"):
        AgentEnginePlanner(
            resource_name="projects/a b/locations/us-central1/reasoningEngines/123",
            client=client,
        )

    assert engines.get_calls == []


def test_invalid_environment_resource_rejects_before_vertex_client_construction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client_construction_calls: list[tuple[object, ...]] = []

    def forbidden_client(*args, **kwargs):
        client_construction_calls.append(args)
        raise AssertionError("invalid configuration must not construct a Vertex client")

    monkeypatch.setenv(
        "MEMORY_FILM_PLANNER_RESOURCE",
        "projects/a b/locations/us-central1/reasoningEngines/123",
    )
    monkeypatch.setattr(agent_engine_module.vertexai, "Client", forbidden_client)

    with pytest.raises(ValueError, match="reasoningEngines"):
        AgentEnginePlanner.from_environment()

    assert client_construction_calls == []


def test_agent_engine_planner_parses_closed_production_plan() -> None:
    plan = AgentEnginePlanner(
        resource_name="projects/demo-project/locations/us-central1/reasoningEngines/123",
        client=FakeClient(),
    ).plan(planning_request())

    assert isinstance(plan, AgentProductionPlan)
    assert plan.title == "A sunny afternoon"


def test_agent_engine_planner_accepts_one_json_code_fence() -> None:
    fenced = f"```json\n{json.dumps(valid_plan_payload())}\n```"
    plan = AgentEnginePlanner(
        resource_name="projects/demo-project/locations/us-central1/reasoningEngines/123",
        client=RecordingAgentEngineClient(
            RecordingAgentEngines(
                remote_agent=PayloadRemoteAgent({"text": fenced})
            )
        ),
    ).plan(planning_request())

    assert plan.title == "A sunny afternoon"


def test_agent_engine_planner_rejects_prose_around_json_code_fence() -> None:
    fenced = f"Here is the plan:\n```json\n{json.dumps(valid_plan_payload())}\n```"
    planner = AgentEnginePlanner(
        resource_name="projects/demo-project/locations/us-central1/reasoningEngines/123",
        client=RecordingAgentEngineClient(
            RecordingAgentEngines(
                remote_agent=PayloadRemoteAgent({"text": fenced})
            )
        ),
    )

    with pytest.raises(InvalidAgentPlanError, match="schema-valid"):
        planner.plan(planning_request())


def test_agent_engine_planner_rejects_incomplete_json_code_fence() -> None:
    incomplete = f"```json\n{json.dumps(valid_plan_payload())}"
    planner = AgentEnginePlanner(
        resource_name="projects/demo-project/locations/us-central1/reasoningEngines/123",
        client=RecordingAgentEngineClient(
            RecordingAgentEngines(
                remote_agent=PayloadRemoteAgent({"text": incomplete})
            )
        ),
    )

    with pytest.raises(InvalidAgentPlanError, match="schema-valid"):
        planner.plan(planning_request())


def test_agent_engine_planner_rejects_multiple_valid_plan_candidates() -> None:
    payload = json.dumps(valid_plan_payload())

    class MultiplePlansRemoteAgent:
        async def async_stream_query(self, *, message: str, user_id: str):
            yield {"text": payload}
            yield {"text": f"```json\n{payload}\n```"}

    planner = AgentEnginePlanner(
        resource_name="projects/demo-project/locations/us-central1/reasoningEngines/123",
        client=RecordingAgentEngineClient(
            RecordingAgentEngines(remote_agent=MultiplePlansRemoteAgent())
        ),
    )

    with pytest.raises(InvalidAgentPlanError, match="multiple"):
        planner.plan(planning_request())


def test_agent_engine_uses_distinct_privacy_safe_user_partitions() -> None:
    remote_agent = RecordingRemoteAgent()
    planner = AgentEnginePlanner(
        resource_name="projects/demo-project/locations/us-central1/reasoningEngines/123",
        client=RecordingAgentEngineClient(RecordingAgentEngines(remote_agent=remote_agent)),
    )

    planner.plan(planning_request().model_copy(update={"user_id": "alice@example.test"}))
    planner.plan(planning_request().model_copy(update={"user_id": "bob@example.test"}))

    assert len(remote_agent.user_ids) == 2
    assert remote_agent.user_ids[0] != remote_agent.user_ids[1]
    assert "alice" not in remote_agent.user_ids[0]
    assert "bob" not in remote_agent.user_ids[1]


def test_agent_engine_stream_has_an_explicit_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(agent_engine_module, "AGENT_TIMEOUT_SECONDS", 0.001)
    planner = AgentEnginePlanner(
        resource_name="projects/demo-project/locations/us-central1/reasoningEngines/123",
        client=RecordingAgentEngineClient(
            RecordingAgentEngines(remote_agent=SlowRemoteAgent())
        ),
    )

    with pytest.raises(AgentPlannerUnavailable, match="unavailable"):
        planner.plan(planning_request())


def test_agent_engine_rejects_an_excessive_event_stream() -> None:
    planner = AgentEnginePlanner(
        resource_name="projects/demo-project/locations/us-central1/reasoningEngines/123",
        client=RecordingAgentEngineClient(
            RecordingAgentEngines(remote_agent=ExcessiveEventsRemoteAgent())
        ),
    )

    with pytest.raises(InvalidAgentPlanError, match="event limit"):
        planner.plan(planning_request())


def test_agent_engine_rejects_an_oversized_plan_candidate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(agent_engine_module, "MAX_PLAN_CANDIDATE_BYTES", 32)
    planner = AgentEnginePlanner(
        resource_name="projects/demo-project/locations/us-central1/reasoningEngines/123",
        client=RecordingAgentEngineClient(
            RecordingAgentEngines(
                remote_agent=PayloadRemoteAgent({"text": json.dumps(valid_plan_payload())})
            )
        ),
    )

    with pytest.raises(InvalidAgentPlanError, match="payload limit"):
        planner.plan(planning_request())


def test_agent_engine_lookup_failure_becomes_planner_unavailable() -> None:
    engines = RecordingAgentEngines(error=RuntimeError("Agent Engine is unavailable"))
    planner = AgentEnginePlanner(
        resource_name="projects/demo-project/locations/us-central1/reasoningEngines/123",
        client=RecordingAgentEngineClient(engines),
    )

    with pytest.raises(AgentPlannerUnavailable, match="unavailable"):
        planner.plan(planning_request())

    assert engines.get_calls == ["projects/demo-project/locations/us-central1/reasoningEngines/123"]


def test_agent_engine_stream_failure_becomes_planner_unavailable() -> None:
    engines = RecordingAgentEngines(remote_agent=FailingStreamRemoteAgent())
    planner = AgentEnginePlanner(
        resource_name="projects/demo-project/locations/us-central1/reasoningEngines/123",
        client=RecordingAgentEngineClient(engines),
    )

    with pytest.raises(AgentPlannerUnavailable, match="unavailable"):
        planner.plan(planning_request())


def test_malformed_agent_engine_payload_becomes_invalid_plan_error() -> None:
    engines = RecordingAgentEngines(remote_agent=PayloadRemoteAgent({"content": {"parts": [{"text": "not-json"}]}}))
    planner = AgentEnginePlanner(
        resource_name="projects/demo-project/locations/us-central1/reasoningEngines/123",
        client=RecordingAgentEngineClient(engines),
    )

    with pytest.raises(InvalidAgentPlanError, match="schema-valid"):
        planner.plan(planning_request())


class FakeSecretPayload:
    data = b'{"CLICKHOUSE_MCP_AUTH_TOKEN":"runtime-token"}'


class FakeSecretResponse:
    payload = FakeSecretPayload()


class FakeSecretManagerClient:
    def __init__(self, accessed_names: list[str]) -> None:
        self._accessed_names = accessed_names

    def access_secret_version(self, *, name: str) -> FakeSecretResponse:
        self._accessed_names.append(name)
        return FakeSecretResponse()


class FakeMcpCaller:
    def __init__(self, endpoint: str, auth_token: str, *, identity_token: str | None = None) -> None:
        self.endpoint = endpoint
        self.auth_token = auth_token
        self.identity_token = identity_token

    def call_tool(self, name: str, arguments: dict[str, str]) -> str:
        return '[{"value":"warm acoustic","evidence_count":2}]'


def test_lazy_preference_tool_fetches_secret_only_when_called(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    accessed_names: list[str] = []
    constructed_callers: list[FakeMcpCaller] = []
    monkeypatch.setattr(
        clickhouse_preferences_module.secretmanager,
        "SecretManagerServiceClient",
        lambda: FakeSecretManagerClient(accessed_names),
        raising=False,
    )

    def make_caller(*args, **kwargs) -> FakeMcpCaller:
        caller = FakeMcpCaller(*args, **kwargs)
        constructed_callers.append(caller)
        return caller

    monkeypatch.setattr(clickhouse_preferences_module, "McpHttpToolCaller", make_caller)
    tool = LazyClickHousePreferenceTool(
        endpoint="https://mcp.example.test",
        credentials_secret_version_name="projects/demo-project/secrets/clickhouse-credentials/versions/latest",
    )
    agent = build_memory_film_agent(tool)

    assert accessed_names == []
    assert tool.__dict__ == {
        "_endpoint": "https://mcp.example.test",
        "_credentials_secret_version_name": "projects/demo-project/secrets/clickhouse-credentials/versions/latest",
    }
    assert agent.tools[0].__self__ is tool

    assert tool.lookup_approved_music_preference("user-1", "A sunny afternoon") == {
        "music_direction": "warm acoustic instrumental",
        "evidence_count": 2,
    }
    assert accessed_names == ["projects/demo-project/secrets/clickhouse-credentials/versions/latest"]
    assert [(caller.endpoint, caller.auth_token, caller.identity_token) for caller in constructed_callers] == [
        ("https://mcp.example.test", "runtime-token", None)
    ]


def test_deployment_preference_tool_uses_safe_fallback_when_secret_reference_is_unconfigured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CLICKHOUSE_MCP_ENDPOINT", "https://mcp.example.test")
    monkeypatch.delenv("CLICKHOUSE_CREDENTIALS_SECRET", raising=False)

    assert deploy_agent_engine.preference_tool_from_environment() is None


def test_deployment_preference_tool_carries_only_runtime_secret_reference(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CLICKHOUSE_MCP_ENDPOINT", "https://mcp.example.test")
    monkeypatch.setenv(
        "CLICKHOUSE_CREDENTIALS_SECRET",
        "projects/demo-project/secrets/clickhouse-credentials/versions/latest",
    )
    monkeypatch.setenv("CLICKHOUSE_CREDENTIALS_JSON", "credentials-json-must-not-be-serialized")
    monkeypatch.setenv("CLICKHOUSE_MCP_IDENTITY_TOKEN", "identity-token-must-not-be-serialized")

    tool = deploy_agent_engine.preference_tool_from_environment()

    assert isinstance(tool, LazyClickHousePreferenceTool)
    assert tool.__dict__ == {
        "_endpoint": "https://mcp.example.test",
        "_credentials_secret_version_name": "projects/demo-project/secrets/clickhouse-credentials/versions/latest",
    }
    serialized_agent = cloudpickle.dumps(build_memory_film_agent(tool))
    assert b"credentials-json-must-not-be-serialized" not in serialized_agent
    assert b"identity-token-must-not-be-serialized" not in serialized_agent


def test_deploy_uses_dedicated_identity_and_reproducible_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    create_calls: list[dict[str, object]] = []

    class FakeCreatedAgent:
        class api_resource:
            name = "projects/demo-project/locations/us-central1/reasoningEngines/123"

    class FakeDeployingAgentEngines:
        def create(self, **kwargs):
            create_calls.append(kwargs)
            return FakeCreatedAgent()

    class FakeDeployClient:
        agent_engines = FakeDeployingAgentEngines()

    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "demo-project")
    monkeypatch.setenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    monkeypatch.setenv("AGENT_ENGINE_MODEL_LOCATION", "australia-southeast1")
    monkeypatch.setenv("AGENT_ENGINE_STAGING_BUCKET", "gs://demo-agent-staging")
    monkeypatch.setenv(
        "AGENT_ENGINE_SERVICE_ACCOUNT",
        "memory-director-agent@demo-project.iam.gserviceaccount.com",
    )
    monkeypatch.setattr(deploy_agent_engine.vertexai, "Client", lambda **_: FakeDeployClient())
    monkeypatch.setattr(deploy_agent_engine.agent_engines, "AdkApp", lambda **kwargs: kwargs)

    assert deploy_agent_engine.deploy().endswith("/reasoningEngines/123")
    assert len(create_calls) == 1
    assert create_calls[0]["config"] == {
        "display_name": "Memory Director Film Planner",
        "description": "Creates safe reviewable 60-second memory-film plans.",
        "requirements": [
            "cloudpickle==3.1.2",
            "google-adk==1.35.2",
            "google-cloud-aiplatform[adk,agent_engines]==1.148.1",
            "google-cloud-secret-manager==2.30.0",
            "pydantic==2.13.4",
        ],
        "staging_bucket": "gs://demo-agent-staging",
        "service_account": "memory-director-agent@demo-project.iam.gserviceaccount.com",
        "extra_packages": ["app"],
        "min_instances": 0,
        "env_vars": {
            "GOOGLE_CLOUD_LOCATION": "australia-southeast1",
            "GOOGLE_GENAI_USE_VERTEXAI": "true",
        },
    }


def test_lazy_preference_tool_returns_none_when_secret_manager_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unavailable_secret_manager():
        raise RuntimeError("Secret Manager is temporarily unavailable")

    monkeypatch.setattr(
        clickhouse_preferences_module.secretmanager,
        "SecretManagerServiceClient",
        unavailable_secret_manager,
    )
    tool = LazyClickHousePreferenceTool(
        endpoint="https://mcp.example.test",
        credentials_secret_version_name="projects/demo-project/secrets/clickhouse-credentials/versions/latest",
    )

    assert tool.lookup_approved_music_preference("user-1", "A sunny afternoon") is None


def test_smoke_requires_preference_tool_invocation_and_exact_plan() -> None:
    events = [
        {
            "content": {
                "parts": [
                    {
                        "function_call": {
                            "name": "lookup_approved_music_preference",
                            "args": {"user_id": "smoke-user", "occasion": "family lunch"},
                        }
                    }
                ]
            }
        },
        {"content": {"parts": [{"text": json.dumps(valid_plan_payload())}]}},
    ]

    evidence = smoke_agent_engine.validate_smoke_events(
        events,
        resource_name="projects/demo-project/locations/us-central1/reasoningEngines/123",
        request=planning_request(),
    )

    assert evidence == {
        "agent_engine_resource": "projects/demo-project/locations/us-central1/reasoningEngines/123",
        "agent_engine_runtime": True,
        "preference_tool_invoked": True,
        "selected_duration_seconds": 60,
        "selected_media_ids": ["clip-1"],
        "music_direction": "warm acoustic instrumental",
    }


def test_smoke_rejects_plan_without_preference_tool_invocation() -> None:
    events = [{"content": {"parts": [{"text": json.dumps(valid_plan_payload())}]}}]

    with pytest.raises(RuntimeError, match="preference tool"):
        smoke_agent_engine.validate_smoke_events(
            events,
            resource_name="projects/demo-project/locations/us-central1/reasoningEngines/123",
            request=planning_request(),
        )


def test_smoke_enforces_production_event_limit() -> None:
    events = [
        {
            "content": {
                "parts": [
                    {
                        "function_call": {
                            "name": "lookup_approved_music_preference",
                            "args": {},
                        }
                    }
                ]
            }
        }
        for _ in range(agent_engine_module.MAX_AGENT_EVENTS + 1)
    ]

    with pytest.raises(InvalidAgentPlanError, match="event limit"):
        smoke_agent_engine.validate_smoke_events(
            events,
            resource_name="projects/demo-project/locations/us-central1/reasoningEngines/123",
            request=planning_request(),
        )


def test_hosted_smoke_stream_stops_at_production_event_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engines = RecordingAgentEngines(remote_agent=ExcessiveEventsRemoteAgent())
    monkeypatch.setattr(
        smoke_agent_engine.vertexai,
        "Client",
        lambda **_: RecordingAgentEngineClient(engines),
    )

    with pytest.raises(InvalidAgentPlanError, match="event limit"):
        asyncio.run(
            smoke_agent_engine.run_smoke(
                "projects/demo-project/locations/us-central1/reasoningEngines/123"
            )
        )


def test_smoke_enforces_production_candidate_payload_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(agent_engine_module, "MAX_PLAN_CANDIDATE_BYTES", 32)
    events = [
        {
            "content": {
                "parts": [
                    {
                        "function_call": {
                            "name": "lookup_approved_music_preference",
                            "args": {},
                        }
                    },
                    {"text": json.dumps(valid_plan_payload())},
                ]
            }
        }
    ]

    with pytest.raises(InvalidAgentPlanError, match="payload limit"):
        smoke_agent_engine.validate_smoke_events(
            events,
            resource_name="projects/demo-project/locations/us-central1/reasoningEngines/123",
            request=planning_request(),
        )


def test_smoke_reports_remote_status_before_missing_tool_without_echoing_message() -> None:
    events = [
        {
            "error": {
                "code": 400,
                "status": "FAILED_PRECONDITION",
                "message": "sensitive remote detail must not be echoed",
            }
        }
    ]

    with pytest.raises(
        RuntimeError,
        match=r"Agent Engine runtime error: FAILED_PRECONDITION \(400\)",
    ) as raised:
        smoke_agent_engine.validate_smoke_events(
            events,
            resource_name="projects/demo-project/locations/us-central1/reasoningEngines/123",
            request=planning_request(),
        )

    assert "sensitive remote detail" not in str(raised.value)


def test_smoke_replaces_unknown_remote_status_with_fixed_code() -> None:
    events = [{"error": {"code": 499, "status": "PRIVATE_TOKEN_ABC"}}]

    with pytest.raises(RuntimeError, match=r"REMOTE_ERROR \(499\)") as raised:
        smoke_agent_engine.validate_smoke_events(
            events,
            resource_name="projects/demo-project/locations/us-central1/reasoningEngines/123",
            request=planning_request(),
        )

    assert "PRIVATE_TOKEN_ABC" not in str(raised.value)


def test_smoke_hides_raw_sdk_exception_message(monkeypatch: pytest.MonkeyPatch) -> None:
    secret_message = "SDK failure containing a private endpoint and token"
    engines = RecordingAgentEngines(error=RuntimeError(secret_message))
    monkeypatch.setattr(
        smoke_agent_engine.vertexai,
        "Client",
        lambda **_: RecordingAgentEngineClient(engines),
    )

    with pytest.raises(
        RuntimeError,
        match="Agent Engine request failed before smoke evidence",
    ) as raised:
        asyncio.run(
            smoke_agent_engine.run_smoke(
                "projects/demo-project/locations/us-central1/reasoningEngines/123"
            )
        )

    assert secret_message not in str(raised.value)
    assert raised.value.__cause__ is None
