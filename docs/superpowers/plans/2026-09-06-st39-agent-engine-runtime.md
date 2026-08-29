# Agent Engine Memory Film Planner Implementation Plan

> For agentic workers: REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

Goal: Add a Gemini ADK / Vertex AI Agent Engine planner that returns a safe, exactly 60-second Memory Director production plan and invokes the official mcp-clickhouse server for a read-only preference lookup at runtime.

Architecture: FastAPI validates consented media metadata and invokes an ADK agent deployed to Vertex AI Agent Engine. The agent uses Gemini and one constrained mcp-clickhouse preference tool, then returns a typed plan. FastAPI verifies the plan and maps it to the existing review/approval flow; rendering remains independent and requires explicit approval.

Tech Stack: Python 3.12, FastAPI, Pydantic v2, google-adk, google-cloud-aiplatform[adk,agent_engines], Vertex AI Gemini, Vertex AI Agent Engine, ClickHouse Cloud, official mcp-clickhouse, Terraform, GitHub Actions, pytest.

Spec: docs/superpowers/specs/2026-08-29-agent-engine-memory-film-planner-design.md

## Global Constraints

- Gemini on Google Cloud is the only product AI provider. Do not add a second model, AI API, or agent framework.
- The runtime must call the official mcp-clickhouse server connected to ClickHouse Cloud; a README reference is insufficient.
- Planning consumes explicit-consent media metadata only; no phone-library search, browser file paths, passwords, tokens, or raw credential values.
- Selected segments must use known media IDs, total exactly 60 seconds, omit private URIs, and recommend an in-app music direction rather than a commercial track.
- ClickHouse planning access is read-only and cannot accept arbitrary SQL from the browser or model.
- Renderer invocation remains blocked until the existing explicit approval gate passes.
- Secrets remain Secret Manager references; never commit, log, summarize, or test with a real value.
- Use `feat/ST-39`, create a PR, pass CI and independent review, then merge.

---

## File structure

| File | Responsibility |
| --- | --- |
| services/api/app/models.py | Shared typed agent request, selected segment, and response models. |
| services/api/app/agent_planner.py | Plan validation and conversion to the existing ProductionProposal. |
| services/api/app/clickhouse_preferences.py | Fixed read-only preference tool over the existing MCP client. |
| services/api/app/adk_memory_film_agent.py | ADK root agent factory and instruction. |
| services/api/app/agent_engine.py | Agent Engine invocation and resource-name validation. |
| services/api/scripts/deploy_agent_engine.py | Repeatable AdkApp deployment entry point. |
| services/api/tests/test_agent_planner.py | Plan safety and exactly-60-second tests. |
| services/api/tests/test_clickhouse_preferences.py | Fixed MCP query and outage tests. |
| services/api/tests/test_adk_memory_film_agent.py | ADK agent-tool and instruction tests. |
| services/api/tests/test_agent_engine.py | Agent Engine adapter tests. |
| infra/terraform/** | Non-secret configuration, runtime IAM, and environment variables. |
| .github/workflows/deploy-agent-engine.yml | Manually approved WIF deployment and sanitized smoke test. |
| docs/operations/AGENT_ENGINE.md | Operator runbook and submission evidence requirements. |

### Task 1: Add typed agent-plan validation

Files:
- Modify: services/api/app/models.py
- Create: services/api/app/agent_planner.py
- Create: services/api/tests/test_agent_planner.py

Interfaces:
- Consumes: existing ProductionBrief, MediaAsset, ProductionProposal, Storyboard.
- Produces: AgentPlanningRequest, SelectedSegment, AgentProductionPlan, validate_agent_plan(), and AgentPlanAdapter.to_proposal().

- [ ] Step 1: Write failing validation tests

    def test_accepts_a_known_exactly_sixty_second_plan() -> None:
        request = AgentPlanningRequest.from_brief(sample_brief(target_duration_seconds=60))
        plan = AgentProductionPlan(
            title="A sunny afternoon",
            caption="A small day worth keeping.",
            music_direction="warm acoustic instrumental",
            selected_segments=[
                SelectedSegment(media_id="clip-1", trim_start_seconds=0, trim_end_seconds=40),
                SelectedSegment(media_id="clip-2", trim_start_seconds=0, trim_end_seconds=20),
            ],
            held_back_media_ids=[],
            user_explanation="I kept the clearest moments.",
        )
        assert validate_agent_plan(request, plan) == plan

    @pytest.mark.parametrize("plan", [
        valid_plan(media_id="unknown", end_seconds=60),
        valid_plan(media_id="clip-1", end_seconds=59),
        valid_plan(media_id="clip-1", end_seconds=60, caption="gs://private/object"),
    ])
    def test_rejects_unsafe_agent_plan(plan: AgentProductionPlan) -> None:
        with pytest.raises(AgentPlanValidationError):
            validate_agent_plan(known_request(), plan)

- [ ] Step 2: Run to verify RED

Run: cd services/api && uv run pytest tests/test_agent_planner.py -q

Expected: FAIL because the agent-plan contract does not exist.

- [ ] Step 3: Implement minimal models, validator, and adapter

    class SelectedSegment(BaseModel):
        media_id: str
        trim_start_seconds: int = Field(ge=0)
        trim_end_seconds: int = Field(gt=0)

        @property
        def duration_seconds(self) -> int:
            return self.trim_end_seconds - self.trim_start_seconds

    def validate_agent_plan(request: AgentPlanningRequest, plan: AgentProductionPlan) -> AgentProductionPlan:
        known_ids = {asset.media_id for asset in request.media}
        if any(segment.media_id not in known_ids for segment in plan.selected_segments):
            raise AgentPlanValidationError("The plan references media not in this request.")
        if sum(segment.duration_seconds for segment in plan.selected_segments) != 60:
            raise AgentPlanValidationError("The plan must be exactly 60 seconds.")
        if "gs://" in plan.model_dump_json():
            raise AgentPlanValidationError("The plan contains a private media reference.")
        return plan

AgentPlanAdapter.to_proposal() marks segment IDs selected, remaining known IDs held back, preserves the existing privacy check, and maps title/caption/music direction into Storyboard.

- [ ] Step 4: Run focused regression tests

Run: cd services/api && uv run pytest tests/test_agent_planner.py tests/test_production_orchestrator.py tests/test_production_proposal_endpoint.py -q

Expected: PASS.

- [ ] Step 5: Commit

    git add services/api/app/models.py services/api/app/agent_planner.py services/api/tests/test_agent_planner.py
    git commit -m "feat(ST-39): validate agent production plans"

### Task 2: Add a constrained official ClickHouse MCP preference tool

Files:
- Create: services/api/app/clickhouse_preferences.py
- Create: services/api/tests/test_clickhouse_preferences.py
- Modify: services/api/app/preferences.py

Interfaces:
- Consumes: McpToolCaller and ClickHouseMcpPreferenceRepository.
- Produces: ClickHousePreferenceTool.lookup_approved_music_preference(user_id, occasion) -> dict[str, str | int] | None.

- [ ] Step 1: Write failing fixed-query and outage tests

    def test_tool_uses_only_fixed_read_only_query_through_mcp() -> None:
        caller = RecordingMcpToolCaller('[{"value":"warm acoustic","evidence_count":2}]')
        result = ClickHousePreferenceTool(caller).lookup_approved_music_preference("user-7", "family lunch")
        assert result == {"music_direction": "warm acoustic", "evidence_count": 2}
        assert caller.calls[0].name == "run_query"
        assert "SELECT value" in caller.calls[0].arguments["query"]
        assert "INSERT" not in caller.calls[0].arguments["query"]

    def test_tool_returns_none_when_mcp_is_unavailable() -> None:
        assert ClickHousePreferenceTool(FailingMcpToolCaller()).lookup_approved_music_preference("user-7", "family lunch") is None

- [ ] Step 2: Run to verify RED

Run: cd services/api && uv run pytest tests/test_clickhouse_preferences.py -q

Expected: FAIL because ClickHousePreferenceTool does not exist.

- [ ] Step 3: Implement the wrapper

    class ClickHousePreferenceTool:
        def lookup_approved_music_preference(self, user_id: str, occasion: str) -> dict[str, str | int] | None:
            try:
                recommendation = self._repository.recommend(user_id, occasion)
            except RuntimeError:
                return None
            if recommendation is None:
                return None
            return {"music_direction": recommendation.music_direction.removesuffix(" instrumental"),
                    "evidence_count": recommendation.evidence_count}

Reuse the existing authenticated McpHttpToolCaller; accept no SQL parameter; invoke run_query only; return no raw query response.

- [ ] Step 4: Add a static deployment assertion

Add a test requiring production MCP configuration to contain official package mcp-clickhouse, omit or disable CLICKHOUSE_ALLOW_WRITE_ACCESS, and source authentication through Secret Manager.

- [ ] Step 5: Run and commit

Run: cd services/api && uv run pytest tests/test_clickhouse_preferences.py tests/test_preferences.py -q

Expected: PASS.

    git add services/api/app/clickhouse_preferences.py services/api/app/preferences.py services/api/tests/test_clickhouse_preferences.py
    git commit -m "feat(ST-39): constrain ClickHouse agent preference tool"

### Task 3: Define the ADK agent with exactly one tool

Files:
- Create: services/api/app/adk_memory_film_agent.py
- Create: services/api/tests/test_adk_memory_film_agent.py
- Modify: services/api/pyproject.toml
- Modify: services/api/uv.lock

Interfaces:
- Consumes: AgentPlanningRequest, AgentProductionPlan, ClickHousePreferenceTool.
- Produces: build_memory_film_agent(preference_tool) -> Agent.

- [ ] Step 1: Write a failing factory test

    def test_memory_film_agent_exposes_only_preference_tool() -> None:
        agent = build_memory_film_agent(FakePreferenceTool())
        assert agent.name == "memory_film_planner"
        assert [tool.__name__ for tool in agent.tools] == ["lookup_approved_music_preference"]
        assert "exactly 60 seconds" in agent.instruction
        assert "gs://" in agent.instruction

- [ ] Step 2: Run to verify RED

Run: cd services/api && uv run pytest tests/test_adk_memory_film_agent.py -q

Expected: FAIL because google.adk and the factory are unavailable.

- [ ] Step 3: Add supported dependencies and lock them

    "google-adk>=1.0,<2.0",
    "google-cloud-aiplatform[adk,agent_engines]>=1.101.0,<2.0",

Run: cd services/api && uv lock. Do not add LangChain, OpenAI, Anthropic, or any non-Google model/agent SDK.

- [ ] Step 4: Implement the ADK factory

    from google.adk.agents import Agent

    def build_memory_film_agent(preference_tool: ClickHousePreferenceTool) -> Agent:
        return Agent(
            name="memory_film_planner",
            model=os.environ.get("GEMINI_MODEL", "gemini-2.5-flash"),
            instruction=MEMORY_FILM_PLANNER_INSTRUCTION,
            tools=[preference_tool.lookup_approved_music_preference],
            output_schema=AgentProductionPlan,
        )

The instruction requires schema-valid JSON, known IDs only, exact 60 seconds, no private URI, library music direction, and no export/publish behavior.

- [ ] Step 5: Run and commit

Run: cd services/api && uv run pytest tests/test_adk_memory_film_agent.py tests/test_agent_planner.py -q && uv run python -c 'import google.adk; from vertexai import agent_engines'

Expected: PASS.

    git add services/api/app/adk_memory_film_agent.py services/api/tests/test_adk_memory_film_agent.py services/api/pyproject.toml services/api/uv.lock
    git commit -m "feat(ST-39): add ADK memory film planner"

### Task 4: Add Agent Engine deployment and runtime adapter

Files:
- Create: services/api/app/agent_engine.py
- Create: services/api/scripts/deploy_agent_engine.py
- Create: services/api/tests/test_agent_engine.py
- Modify: services/api/app/main.py
- Modify: services/api/tests/test_production_proposal_endpoint.py

Interfaces:
- Consumes: build_memory_film_agent, AgentPlanningRequest, AgentPlanAdapter.
- Produces: AgentEnginePlanner.plan(request) -> AgentProductionPlan and an agent-backed production-proposal endpoint.

- [ ] Step 1: Write failing resource and endpoint tests

    def test_agent_engine_planner_rejects_invalid_resource_name() -> None:
        with pytest.raises(ValueError, match="reasoningEngines"):
            AgentEnginePlanner(resource_name="not-an-agent", client=FakeClient())

    @pytest.mark.anyio
    async def test_proposal_endpoint_uses_validated_agent_plan(monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(main_module, "get_agent_planner", lambda: FakeAgentPlanner(valid_plan()))
        response = await post_valid_proposal_request()
        assert response.status_code == 201
        assert response.json()["storyboard"]["title"] == "A sunny afternoon"

- [ ] Step 2: Run to verify RED

Run: cd services/api && uv run pytest tests/test_agent_engine.py tests/test_production_proposal_endpoint.py -q

Expected: FAIL because there is no Agent Engine planner or dependency factory.

- [ ] Step 3: Implement official AdkApp deployment

    from vertexai import agent_engines

    adk_app = agent_engines.AdkApp(agent=build_memory_film_agent(preference_tool), enable_tracing=True)
    remote_app = client.agent_engines.create(
        agent=adk_app,
        config={
            "display_name": "Memory Director Film Planner",
            "description": "Creates safe reviewable 60-second memory-film plans.",
            "requirements": ["google-adk", "google-cloud-aiplatform[adk,agent_engines]"],
            "staging_bucket": staging_bucket,
        },
    )
    print(remote_app.api_resource.name)

The script runs from CI/manual operator context only and validates the returned projects/{project}/locations/{region}/reasoningEngines/{id} name.

- [ ] Step 4: Implement invocation and API wiring

AgentEnginePlanner resolves the configured resource, submits JSON AgentPlanningRequest, parses only schema-valid JSON into AgentProductionPlan, and invokes AgentPlanAdapter. get_agent_planner() returns HTTP 503 when MEMORY_FILM_PLANNER_RESOURCE is missing/invalid. Keep legacy /storyboards during migration.

- [ ] Step 5: Run and commit

Run: cd services/api && uv run pytest tests/test_agent_engine.py tests/test_agent_planner.py tests/test_production_proposal_endpoint.py -q

Expected: PASS; invalid agent output never reaches a render request.

    git add services/api/app/agent_engine.py services/api/scripts/deploy_agent_engine.py services/api/app/main.py services/api/tests/test_agent_engine.py services/api/tests/test_production_proposal_endpoint.py
    git commit -m "feat(ST-39): invoke Agent Engine production planner"

### Task 5: Add configuration, minimal IAM, workflow, and evidence docs

Files:
- Modify: infra/terraform/projects/config/config.schema.json
- Modify: infra/terraform/projects/config/memory-director.json
- Modify: infra/terraform/components/app/main.tf
- Modify: infra/terraform/modules/foundations/app/main.tf, variables.tf, and tests
- Create: .github/workflows/deploy-agent-engine.yml
- Create: docs/operations/AGENT_ENGINE.md
- Modify: docs/ARCHITECTURE.md

Interfaces:
- Consumes: non-secret agent resource name, runtime identity, existing WIF, existing ClickHouse Secret Manager reference, and deployment script.
- Produces: MEMORY_FILM_PLANNER_RESOURCE, least-privilege Agent Engine access, guarded manual deployment, and sanitized evidence.

- [ ] Step 1: Write failing config, Terraform, and workflow tests

Extend config-validator to require agent_engine.memory_film_planner_resource when agent_engine.enabled is true. Add Terraform tests for API environment variable and minimum agent invocation role. Add a static workflow test requiring workflow_dispatch, sandbox, WIF, deployment script, and synthetic smoke request.

- [ ] Step 2: Run to verify RED

Run: cd infra/terraform/tools/config-validator && npm test -- --run && terraform -chdir=../../modules/foundations/app test

Expected: FAIL because config, environment variable, IAM, and workflow do not exist.

- [ ] Step 3: Implement narrow configuration and workflow

Project JSON receives a resource name only. Terraform injects MEMORY_FILM_PLANNER_RESOURCE into API Cloud Run and grants the narrow Google-defined Agent Engine invocation role—never Editor/Owner. The workflow is manual, uses GitHub sandbox, WIF, a confirmation input, and synthetic media IDs; it writes only resource name and redacted smoke summary and provides no destroy operation.

- [ ] Step 4: Document deployment and rollback

Document prerequisites, inputs, rollback to a prior resource, smoke checks for Gemini/Agent Engine and official MCP, and Devpost evidence. In docs/ARCHITECTURE.md, state configured but unverified until the cloud smoke test passes.

- [ ] Step 5: Run full verification and commit

    cd services/api && uv run pytest -q
    cd ../../apps/web && npm run test -- --run && npm run build
    cd ../../infra/terraform/tools/config-validator && npm test -- --run
    cd ../../ && terraform fmt -check -recursive && tflint --recursive
    git diff --check
    git add infra/terraform .github/workflows/deploy-agent-engine.yml docs/operations/AGENT_ENGINE.md docs/ARCHITECTURE.md
    git commit -m "feat(ST-39): deploy memory film planner safely"

Expected: all local checks pass. Run the manual workflow before claiming hosted verification.

### Task 6: Align submission evidence after verified deployment

Files:
- Modify: docs/submission/DEVPOST_PROJECT_PAGE.md
- Modify: docs/submission/DEMO_SCRIPT.md
- Modify: docs/demo/DEMO_RUNBOOK.md
- Modify: infra/terraform/tools/config-validator/test/validate-config.test.mjs

Interfaces:
- Consumes: verified agent resource, successful agent request, official MCP evidence, and approved 60-second export.
- Produces: accurate English submission copy and a three-minute demonstration checklist.

- [ ] Step 1: Write a failing consistency test

Require Gemini/Agent Engine and official mcp-clickhouse in submission docs; require explicit browser media selection and approval-before-export; reject placeholder hosted URLs and secret-shaped values.

- [ ] Step 2: Run to verify RED

Run: cd infra/terraform/tools/config-validator && npm test -- --run

Expected: FAIL until the documents meet evidence gates.

- [ ] Step 3: Update only verified copy

The demo shows consent, selected media, request, agent plan, official MCP preference or safe fallback, review, approval, 60-second export, and saved artifact. Require English subtitles and duration below three minutes. Do not claim whole-library access or an untested hosted result.

- [ ] Step 4: Run final regressions and create PR

    cd infra/terraform/tools/config-validator && npm test -- --run
    cd ../../../services/api && uv run pytest -q
    cd ../../apps/web && npm run test -- --run && npm run build
    git diff --check
    git add docs/submission docs/demo infra/terraform/tools/config-validator/test
    git commit -m "docs(ST-39): align agent evidence for submission"
    git push -u origin feat/ST-39
    gh pr create --base main --head feat/ST-39 --title "feat(ST-39): deploy Agent Engine production crew"

The PR description distinguishes local results from manual cloud evidence. Wait for CI and review before merge.

## Plan self-review

| Requirement | Tasks |
| --- | --- |
| Gemini + ADK + Agent Engine runtime | 3, 4, 5 |
| Official read-only ClickHouse MCP tool | 2, 5 |
| Known assets, privacy, exact 60 seconds | 1, 4 |
| Consent and approval-before-render | 1, 4, 6 |
| Configuration, IAM, and no secrets | 5 |
| Reproducible evidence and submission materials | 5, 6 |

All interfaces are introduced before subsequent tasks consume them, and each task starts with a focused failing test.
