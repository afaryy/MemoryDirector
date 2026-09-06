import os

from google.adk.agents import Agent

from app.agent_planner import AgentPlanningRequest, AgentProductionPlan
from app.clickhouse_preferences import PreferenceLookup


MEMORY_FILM_INSTRUCTION = """You are the memory film planner.

Accept an AgentPlanningRequest and return only schema-valid AgentProductionPlan JSON.
Use only known media IDs from the request. The selected segments must total exactly 60 seconds.
Never include a private storage URI such as gs:// in the response.
Choose a library instrumental music direction, optionally using the approved music
preference lookup. Do not render, export, publish, or take any action beyond creating
the production plan.
"""


def build_memory_film_agent(preference_tool: PreferenceLookup) -> Agent:
    """Build the bounded ADK agent used to plan a memory film."""
    return Agent(
        name="memory_film_planner",
        model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        instruction=MEMORY_FILM_INSTRUCTION,
        input_schema=AgentPlanningRequest,
        output_schema=AgentProductionPlan,
        tools=[preference_tool.lookup_approved_music_preference],
    )
