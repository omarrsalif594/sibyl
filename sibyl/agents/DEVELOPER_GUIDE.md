# Agents Developer Guide

## Architecture overview
- `protocol.py` and `types.py` define the shared interfaces and data structures used by all agents.
- `base/agent.py` contains `BaseAgent`, wiring common services (LLM, QC, search, budget tracking).
- `implementations/` hosts the shipped agents: planner, executor, reviewer, and search.
- `factory/agent_factory.py` assembles agents with injected services and profile-aware tool catalogs.
- `tools/catalog.py` owns tool discovery, validation, and profile-specific composition.

## Creating a new agent
1. Subclass `BaseAgent` (import from `sibyl.core.agents.base`) and implement `async execute(self, request)` returning a dictionary payload.
2. Use the shared services from the base class instead of creating your own clients (LLM, QC, search, budget).
3. (Optional) Define a protocol for your agent in `protocol.py` if you need to type narrow behaviors.
4. Add the implementation under `implementations/` and export it from `implementations/__init__.py`.

Example:
```python
from sibyl.core.agents.base import BaseAgent
from sibyl.core.agents.types import AgentResponsePayload

class SummarizationAgent(BaseAgent):
    agent_id = "summarizer"

    async def execute(self, request) -> AgentResponsePayload:
        content = request.get("content", "")
        summary = await self.call_llm(prompt=f"Summarize:\n{content}")
        return {"summary": summary, "length": len(summary)}
```

## Registering agents with the factory
- Extend `AgentFactory` or provide a helper that composes your agent alongside the defaults.
- Use `extend_tool_catalog` to attach additional tools to a factory instance when profile-based tools are not enough.

```python
from sibyl.core.agents.factory import AgentFactory, extend_tool_catalog

factory = AgentFactory(profile="default", llm_client=llm)
factory = extend_tool_catalog({"summarize": {...}}, factory)
factory.create_all_agents()["planner"]
```

## Tool registration and validation
- Add new tools through `get_profile_tools` (profile-aware) or by merging dictionaries with `merge_tool_catalogs`.
- Use `validate_tool_call` to guard dynamic tool invocations before execution.

## Testing guidelines
- Mock dependencies passed into `AgentFactory` (LLM client, search service, plugin registry) to keep tests deterministic.
- Prefer validating agent behavior through their public `execute` methods using `AgentRequest.from_mapping` for ergonomic request creation.
- Integration tests should verify factory wiring (all core agents created) and catalog availability for expected profiles.
