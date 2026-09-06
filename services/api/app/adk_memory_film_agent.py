import json
import os

from google.adk.agents import Agent

from app.agent_planner import AgentPlanningRequest, AgentProductionPlan
from app.clickhouse_preferences import PreferenceLookup


PRODUCTION_PLAN_SCHEMA = json.dumps(
    AgentProductionPlan.model_json_schema(), separators=(",", ":")
)


MEMORY_FILM_INSTRUCTION = f"""You are the memory film planner.

Accept an AgentPlanningRequest and return only JSON matching this schema:
{PRODUCTION_PLAN_SCHEMA}
Use only known media IDs from the request. The selected segments must total exactly 60 seconds.
Never include a private storage URI such as gs:// in the response.
Always call the approved music preference lookup once before choosing a library
instrumental music direction. Do not render, export, publish, or take any action
beyond creating the production plan.
"""


def build_memory_film_agent(preference_tool: PreferenceLookup) -> Agent:
    """Build the bounded ADK agent used to plan a memory film."""
    return Agent(
        name="memory_film_planner",
        model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        instruction=MEMORY_FILM_INSTRUCTION,
        input_schema=AgentPlanningRequest,
        tools=[preference_tool.lookup_approved_music_preference],
    )
