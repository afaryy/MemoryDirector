"""Runtime adapter for the deployed Memory Director Agent Engine."""

import asyncio
import hashlib
import json
import os
import re
from collections.abc import AsyncIterable, Mapping
from typing import Any, Protocol

import vertexai

from app.agent_planner import AgentPlanningRequest, AgentProductionPlan


RESOURCE_NAME_PATTERN = re.compile(
    r"^projects/(?P<project>(?:[a-z][a-z0-9-]{4,28}[a-z0-9]|[0-9]{6,30}))/"
    r"locations/(?P<location>[a-z]+(?:-[a-z0-9]+)*)/"
    r"reasoningEngines/(?P<id>[0-9]+)$"
)
AGENT_TIMEOUT_SECONDS = 30.0
MAX_AGENT_EVENTS = 128
MAX_PLAN_CANDIDATES = 128
MAX_PLAN_CANDIDATE_BYTES = 64 * 1024


class AgentEnginesClient(Protocol):
    def get(self, *, name: str) -> "RemoteAgent": ...


class RemoteAgent(Protocol):
    def async_stream_query(self, *, message: str, user_id: str) -> AsyncIterable[object]: ...


class AgentEngineClient(Protocol):
    agent_engines: AgentEnginesClient


class AgentPlannerUnavailable(RuntimeError):
    """The configured Agent Engine could not serve a planning request."""


class InvalidAgentPlanError(ValueError):
    """The Agent Engine response was not a closed production-plan payload."""


def validate_resource_name(resource_name: str) -> re.Match[str]:
    match = RESOURCE_NAME_PATTERN.fullmatch(resource_name)
    if match is None:
        raise ValueError(
            "Agent Engine resource name must use projects/{project}/locations/{region}/reasoningEngines/{id}."
        )
    return match


class AgentEnginePlanner:
    """Request a closed production plan from an already-deployed ADK application."""

    def __init__(self, *, resource_name: str, client: AgentEngineClient) -> None:
        validate_resource_name(resource_name)
        self._resource_name = resource_name
        self._client = client

    @classmethod
    def from_environment(cls) -> "AgentEnginePlanner":
        resource_name = os.environ["MEMORY_FILM_PLANNER_RESOURCE"]
        match = validate_resource_name(resource_name)
        return cls(
            resource_name=resource_name,
            client=vertexai.Client(
                project=match["project"], location=match["location"]
            ),
        )

    def plan(self, request: AgentPlanningRequest) -> AgentProductionPlan:
        try:
            remote_agent = self._client.agent_engines.get(name=self._resource_name)
            return asyncio.run(self._request_plan(remote_agent, request))
        except InvalidAgentPlanError:
            raise
        except Exception as error:
            raise AgentPlannerUnavailable("Agent Engine planning is unavailable.") from error

    async def _request_plan(
        self, remote_agent: RemoteAgent, request: AgentPlanningRequest
    ) -> AgentProductionPlan:
        candidates: list[object] = []
        try:
            async with asyncio.timeout(AGENT_TIMEOUT_SECONDS):
                event_count = 0
                async for event in remote_agent.async_stream_query(
                    message=request.model_dump_json(),
                    user_id=_privacy_safe_user_partition(request.user_id),
                ):
                    event_count += 1
                    if event_count > MAX_AGENT_EVENTS:
                        raise InvalidAgentPlanError(
                            "Agent Engine response exceeded the event limit."
                        )
                    for candidate in _plan_candidates(event):
                        if len(candidates) >= MAX_PLAN_CANDIDATES:
                            raise InvalidAgentPlanError(
                                "Agent Engine response exceeded the candidate limit."
                            )
                        if _candidate_size_bytes(candidate) > MAX_PLAN_CANDIDATE_BYTES:
                            raise InvalidAgentPlanError(
                                "Agent Engine response exceeded the payload limit."
                            )
                        candidates.append(candidate)
        except InvalidAgentPlanError:
            raise
        except Exception as error:
            raise AgentPlannerUnavailable("Agent Engine planning is unavailable.") from error
        for candidate in reversed(candidates):
            try:
                return _parse_plan(candidate)
            except (TypeError, ValueError):
                continue
        raise InvalidAgentPlanError("Agent Engine did not return a schema-valid production plan.")


def _plan_candidates(event: object) -> list[object]:
    if isinstance(event, str):
        return [event]
    if not isinstance(event, Mapping):
        return []

    candidates: list[object] = []
    for key in ("output", "text"):
        if key in event:
            candidates.append(event[key])
    content = event.get("content")
    if isinstance(content, Mapping):
        parts = content.get("parts")
        if isinstance(parts, list):
            candidates.extend(
                part["text"]
                for part in parts
                if isinstance(part, Mapping) and isinstance(part.get("text"), str)
            )
    if {"title", "caption", "music_direction", "selected_segments", "held_back_media_ids", "user_explanation"} <= set(event):
        candidates.append(dict(event))
    return candidates


def _parse_plan(candidate: object) -> AgentProductionPlan:
    if isinstance(candidate, str):
        return AgentProductionPlan.model_validate_json(candidate)
    if isinstance(candidate, Mapping):
        return AgentProductionPlan.model_validate(dict(candidate))
    raise TypeError("Agent Engine plan response was not JSON.")


def _privacy_safe_user_partition(user_id: str) -> str:
    digest = hashlib.sha256(f"memory-director:{user_id}".encode()).hexdigest()
    return f"md-{digest[:32]}"


def _candidate_size_bytes(candidate: object) -> int:
    if isinstance(candidate, str):
        return len(candidate.encode())
    return len(
        json.dumps(candidate, separators=(",", ":"), ensure_ascii=False).encode()
    )
