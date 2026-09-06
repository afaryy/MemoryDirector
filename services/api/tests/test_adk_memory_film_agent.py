from app.adk_memory_film_agent import build_memory_film_agent
from app.agent_planner import AgentPlanningRequest, AgentProductionPlan


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
    assert agent.output_schema is AgentProductionPlan
    assert "exactly 60 seconds" in agent.instruction
    assert "gs://" in agent.instruction
