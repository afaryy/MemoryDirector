"""Deploy the bounded Memory Director ADK application from operator or CI context."""

import os

import vertexai
from vertexai import agent_engines

from app.adk_memory_film_agent import build_memory_film_agent
from app.agent_engine import validate_resource_name
from app.clickhouse_preferences import LazyClickHousePreferenceTool


class UnconfiguredPreferenceTool:
    """Safe fallback when the optional MCP preference integration is unavailable."""

    def lookup_approved_music_preference(
        self, user_id: str, occasion: str
    ) -> dict[str, str | int] | None:
        return None


def preference_tool_from_environment() -> LazyClickHousePreferenceTool | None:
    endpoint = os.environ.get("CLICKHOUSE_MCP_ENDPOINT")
    credentials_secret_version_name = os.environ.get("CLICKHOUSE_CREDENTIALS_SECRET")
    if not endpoint or not credentials_secret_version_name:
        return None
    return LazyClickHousePreferenceTool(
        endpoint=endpoint,
        credentials_secret_version_name=credentials_secret_version_name,
    )


def deploy() -> str:
    project = os.environ["GOOGLE_CLOUD_PROJECT"]
    location = os.environ["GOOGLE_CLOUD_LOCATION"]
    staging_bucket = os.environ["AGENT_ENGINE_STAGING_BUCKET"]
    service_account = os.environ["AGENT_ENGINE_SERVICE_ACCOUNT"]
    client = vertexai.Client(project=project, location=location)
    preference_tool = preference_tool_from_environment() or UnconfiguredPreferenceTool()
    adk_app = agent_engines.AdkApp(
        agent=build_memory_film_agent(preference_tool),
        enable_tracing=True,
    )
    remote_app = client.agent_engines.create(
        agent=adk_app,
        config={
            "display_name": "Memory Director Film Planner",
            "description": "Creates safe reviewable 60-second memory-film plans.",
            "requirements": [
                "cloudpickle==3.1.2",
                "google-adk==1.35.2",
                "google-cloud-aiplatform[adk,agent_engines]==1.148.1",
                "google-cloud-secret-manager==2.30.0",
                "pydantic==2.13.4",
            ],
            "staging_bucket": staging_bucket,
            "service_account": service_account,
            "extra_packages": ["app"],
            "min_instances": 0,
            "env_vars": {"GOOGLE_GENAI_USE_VERTEXAI": "true"},
        },
    )
    resource_name = remote_app.api_resource.name
    validate_resource_name(resource_name)
    return resource_name


def main() -> None:
    print(deploy())


if __name__ == "__main__":
    main()
