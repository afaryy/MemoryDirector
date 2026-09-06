import inspect

from app.adk_memory_film_agent import build_memory_film_agent
from app.clickhouse_preferences import LazyClickHousePreferenceTool
from app.agent_planner import AgentPlanningRequest


class FakePreferenceTool:
    def lookup_approved_music_preference(
        self, user_id: str, occasion: str
    ) -> dict[str, str | int] | None:
        return None


def test_memory_film_agent_exposes_only_preference_tool() -> None:
    agent = build_memory_film_agent(FakePreferenceTool())

    assert agent.name == "memory_film_planner"
    assert [tool.__name__ for tool in agent.tools] == [
        "lookup_approved_music_preference"
    ]
    assert agent.input_schema is AgentPlanningRequest
    assert agent.output_schema is None
    assert '"selected_segments"' in agent.instruction
    assert '"held_back_media_ids"' in agent.instruction
    assert "Always call the approved music preference lookup once" in agent.instruction
    assert "exactly 60 seconds" in agent.instruction
    assert "gs://" in agent.instruction


def test_memory_film_agent_uses_deterministic_single_candidate_generation() -> None:
    agent = build_memory_film_agent(FakePreferenceTool())

    assert agent.generate_content_config is not None
    assert agent.generate_content_config.temperature == 0
    assert agent.generate_content_config.candidate_count == 1


def test_agent_engine_preference_tool_describes_its_read_only_boundary() -> None:
    description = inspect.getdoc(
        LazyClickHousePreferenceTool.lookup_approved_music_preference
    )

    assert description is not None
    assert "read-only" in description
    assert "music preference" in description
