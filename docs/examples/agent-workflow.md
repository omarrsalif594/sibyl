# Agent Workflow Example

Build sophisticated AI agents that can use tools, make decisions, and execute multi-step workflows.

## Overview

Create agents that:
- Use multiple tools (RAG, SQL, web search, code execution)
- Make autonomous decisions
- Handle complex multi-step tasks
- Recover from errors

**Time:** 25-30 minutes | **Difficulty:** Advanced

---

## Architecture

```
User Query → Agent → [Planning] → [Tool Selection] → [Execution] → [Synthesis]
                ↓                                                        ↑
                └────────────── Feedback Loop ─────────────────────────┘
```

---

## Workspace Configuration

**workspace_config.yaml:**
```yaml
workspace_name: agent_workflow
workspace_description: "Multi-tool AI agent"

shops:
  # Enable all techniques
  rag_pipeline:
    retrieval:
      technique: semantic_search

  data_integration:
    query_sql:
      query:
        technique: query

  workflow_orchestration:
    orchestration:
      routing:
        technique: routing
        config:
          routing_strategy: "dynamic"

  ai_generation:
    generation:
      technique: chain_of_thought
      config:
        model: "claude-3-5-sonnet-20241022"

providers:
  anthropic:
    api_key_env: ANTHROPIC_API_KEY
```

---

## Implementation

**agent_workflow.py:**
```python
#!/usr/bin/env python3
"""Multi-tool agent with workflow orchestration."""

import asyncio
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Any

from sibyl.core.application.context import ApplicationContext
from sibyl.techniques.rag_pipeline import retrieval
from sibyl.techniques.data_integration import query_sql
from sibyl.techniques.ai_generation import generation
from sibyl.techniques.workflow_orchestration import orchestration


class ToolType(Enum):
    """Available tools."""
    RAG = "rag"
    SQL = "sql"
    WEB_SEARCH = "web_search"
    CODE_EXECUTOR = "code_executor"


@dataclass
class ToolCall:
    """A tool invocation."""
    tool: ToolType
    params: dict
    result: Optional[Any] = None
    error: Optional[str] = None


@dataclass
class WorkflowStep:
    """A step in the workflow."""
    step_number: int
    description: str
    tool_calls: List[ToolCall]
    reasoning: str


class AgentWorkflow:
    """Orchestrate multi-step agent workflows."""

    def __init__(self, workspace_path: str):
        self.ctx = ApplicationContext.from_workspace(workspace_path)
        self.workflow_history: List[WorkflowStep] = []

    async def plan_workflow(self, task: str) -> List[dict]:
        """Plan workflow steps for a task."""

        prompt = f"""Given this task, create a step-by-step plan.

Task: {task}

Available tools:
- rag: Search documentation and knowledge base
- sql: Query structured databases
- web_search: Search the internet
- code_executor: Execute Python code

Create a plan as a JSON array with steps:
[
  {{
    "step": 1,
    "description": "Search knowledge base for X",
    "tool": "rag",
    "params": {{"query": "..."}}
  }},
  ...
]

Return ONLY the JSON array."""

        result = await generation.execute(
            ctx=self.ctx,
            technique="chain_of_thought",
            params={"prompt": prompt}
        )

        if result.is_success:
            import json
            plan_text = result.value.strip()
            # Extract JSON from markdown if needed
            if "```" in plan_text:
                plan_text = plan_text.split("```")[1]
                if plan_text.startswith("json"):
                    plan_text = plan_text[4:]
            return json.loads(plan_text)
        return []

    async def execute_tool(self, tool: ToolType, params: dict) -> Any:
        """Execute a tool call."""

        if tool == ToolType.RAG:
            result = await retrieval.execute(
                ctx=self.ctx,
                technique="semantic_search",
                params=params
            )
            return result.value if result.is_success else None

        elif tool == ToolType.SQL:
            result = await query_sql.execute(
                ctx=self.ctx,
                technique="query",
                params=params
            )
            return result.value if result.is_success else None

        elif tool == ToolType.WEB_SEARCH:
            # Implement web search
            return {"results": "web search results..."}

        elif tool == ToolType.CODE_EXECUTOR:
            # Implement code execution
            return {"output": "code execution results..."}

        return None

    async def execute_workflow(self, task: str):
        """Execute complete workflow."""

        print(f"🎯 Task: {task}\n")

        # Plan
        print("📋 Planning workflow...")
        plan = await self.plan_workflow(task)
        print(f"✅ Created {len(plan)} step plan\n")

        # Execute each step
        for step_config in plan:
            step_num = step_config["step"]
            description = step_config["description"]
            tool_name = step_config["tool"]
            params = step_config.get("params", {})

            print(f"Step {step_num}: {description}")
            print(f"   Tool: {tool_name}")

            # Execute tool
            try:
                tool = ToolType(tool_name)
                result = await self.execute_tool(tool, params)

                tool_call = ToolCall(
                    tool=tool,
                    params=params,
                    result=result
                )
                print(f"   ✅ Success")

            except Exception as e:
                tool_call = ToolCall(
                    tool=ToolType(tool_name),
                    params=params,
                    error=str(e)
                )
                print(f"   ❌ Error: {e}")

            # Record step
            workflow_step = WorkflowStep(
                step_number=step_num,
                description=description,
                tool_calls=[tool_call],
                reasoning=step_config.get("reasoning", "")
            )
            self.workflow_history.append(workflow_step)
            print()

        # Synthesize final answer
        print("🤖 Synthesizing final answer...")
        answer = await self.synthesize_answer(task)
        print(f"\n💡 Answer:\n{answer}\n")

        return answer

    async def synthesize_answer(self, task: str) -> str:
        """Synthesize final answer from workflow results."""

        # Build context from workflow history
        context_parts = []
        for step in self.workflow_history:
            context_parts.append(f"Step {step.step_number}: {step.description}")
            for tool_call in step.tool_calls:
                if tool_call.result:
                    context_parts.append(f"  Result: {tool_call.result}")
                elif tool_call.error:
                    context_parts.append(f"  Error: {tool_call.error}")

        context = "\n".join(context_parts)

        prompt = f"""Given the task and workflow results, provide a comprehensive answer.

Task: {task}

Workflow Results:
{context}

Provide a clear, complete answer to the original task."""

        result = await generation.execute(
            ctx=self.ctx,
            technique="basic_generation",
            params={"prompt": prompt}
        )

        return result.value if result.is_success else "Unable to synthesize answer"


async def main():
    """Example usage."""

    agent = AgentWorkflow("workspaces/agent_workflow")

    # Example tasks
    tasks = [
        "Find information about our pricing in the docs and compare it with our database records",
        "Search for customer complaints in documentation and analyze the order data for those customers"
    ]

    for task in tasks:
        await agent.execute_workflow(task)
        print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
```

---

## Advanced Patterns

### Self-Healing Workflows

```python
async def execute_with_retry(self, tool: ToolType, params: dict, max_retries: int = 3):
    """Execute with automatic retry and error recovery."""

    for attempt in range(max_retries):
        try:
            result = await self.execute_tool(tool, params)
            return result
        except Exception as e:
            if attempt < max_retries - 1:
                # Modify params based on error
                params = await self.adjust_params_for_error(params, str(e))
            else:
                raise
```

### Dynamic Tool Selection

```python
async def select_best_tool(self, query: str) -> ToolType:
    """Dynamically select the best tool for a query."""

    prompt = f"""Select the best tool for this query:

Query: {query}

Tools:
- rag: For knowledge base and documentation
- sql: For structured data queries
- web_search: For current information
- code_executor: For computations

Return: rag, sql, web_search, or code_executor"""

    result = await generation.execute(
        ctx=self.ctx,
        technique="basic_generation",
        params={"prompt": prompt, "temperature": 0}
    )

    return ToolType(result.value.strip())
```

---

## Learn More

- [Workflow Orchestration](../techniques/workflow-orchestration.md)
- [Graph-Based Workflows](../techniques/workflow-orchestration.md#graph-techniques)
- [Advanced Topics](../advanced/agent-patterns.md)
