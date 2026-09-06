"""Smoke-test a deployed Agent Engine without exposing media or credentials."""

import argparse
import asyncio
import json
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import vertexai

from app.agent_engine import _plan_candidates, validate_resource_name
from app.agent_planner import (
    AgentPlanningRequest,
    AgentProductionPlan,
    PlannerMedia,
    validate_agent_plan,
)


PREFERENCE_TOOL_NAME = "lookup_approved_music_preference"


def smoke_request() -> AgentPlanningRequest:
    return AgentPlanningRequest(
        user_id="agent-engine-smoke-user",
        occasion="A warm family lunch",
        target_duration_seconds=60,
        moods=["warm", "joyful"],
        music_constraints=["library instrumental"],
        media=[
            PlannerMedia(
                media_id="clip-1",
                quality_score=0.9,
                duplicate_of=None,
            )
        ],
    )


def _contains_named_function(value: object, name: str) -> bool:
    if isinstance(value, Mapping):
        if value.get("name") == name and any(
            key in value for key in ("args", "arguments", "function_call", "functionCall")
        ):
            return True
        return any(_contains_named_function(child, name) for child in value.values())
    if isinstance(value, (list, tuple)):
        return any(_contains_named_function(child, name) for child in value)
    if hasattr(value, "model_dump"):
        return _contains_named_function(value.model_dump(), name)
    return False


def validate_smoke_events(
    events: list[object],
    *,
    resource_name: str,
    request: AgentPlanningRequest,
) -> dict[str, Any]:
    validate_resource_name(resource_name)
    if not any(_contains_named_function(event, PREFERENCE_TOOL_NAME) for event in events):
        raise RuntimeError("Agent Engine did not invoke the approved preference tool.")

    candidates: list[object] = []
    for event in events:
        candidates.extend(_plan_candidates(event))
    plan = None
    for candidate in reversed(candidates):
        try:
            plan = (
                AgentProductionPlan.model_validate_json(candidate)
                if isinstance(candidate, str)
                else AgentProductionPlan.model_validate(candidate)
            )
            break
        except (TypeError, ValueError):
            continue
    if plan is None:
        raise RuntimeError("Agent Engine did not return a schema-valid production plan.")
    validate_agent_plan(request, plan)
    return {
        "agent_engine_resource": resource_name,
        "agent_engine_runtime": True,
        "preference_tool_invoked": True,
        "selected_duration_seconds": sum(
            segment.duration_seconds for segment in plan.selected_segments
        ),
        "selected_media_ids": [segment.media_id for segment in plan.selected_segments],
        "music_direction": plan.music_direction,
    }


async def run_smoke(resource_name: str) -> dict[str, Any]:
    match = validate_resource_name(resource_name)
    client = vertexai.Client(project=match["project"], location=match["location"])
    remote_agent = client.agent_engines.get(name=resource_name)
    request = smoke_request()
    events = [
        event
        async for event in remote_agent.async_stream_query(
            message=request.model_dump_json(),
            user_id=request.user_id,
        )
    ]
    return validate_smoke_events(events, resource_name=resource_name, request=request)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--resource",
        default=os.environ.get("MEMORY_FILM_PLANNER_RESOURCE"),
        required=os.environ.get("MEMORY_FILM_PLANNER_RESOURCE") is None,
    )
    parser.add_argument("--evidence-file", type=Path)
    arguments = parser.parse_args()
    evidence = asyncio.run(run_smoke(arguments.resource))
    payload = json.dumps(evidence, indent=2, sort_keys=True)
    if arguments.evidence_file:
        arguments.evidence_file.write_text(f"{payload}\n", encoding="utf-8")
    print(payload)


if __name__ == "__main__":
    main()
