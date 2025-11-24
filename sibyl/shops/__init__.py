"""
Sibyl Shops: User-facing facades for technique categories.

This module provides the STABLE PUBLIC API for high-level technique access.

Stability: STABLE - This is part of the public API with semantic versioning guarantees.
Breaking changes will only occur in major version releases.

The shops module provides high-level, organized access to Sibyl's techniques
grouped by functional area:

- rag: Retrieval-augmented generation techniques
- ai_generation: AI generation and validation techniques
- workflow: Workflow orchestration and session management
- infrastructure: Infrastructure, security, and operational techniques
- agents: Agent framework primitives

Usage:
    from sibyl.shops import rag, agents
    from sibyl.shops.rag import ChunkingTechnique
    from sibyl.shops.agents import Agent

    # Use shop techniques
    from sibyl.runtime import load_workspace_runtime
    runtime = load_workspace_runtime("config/workspaces/my_workspace.yaml")

    chunker = ChunkingTechnique(runtime)
    chunks = await chunker.execute(document="...", strategy="fixed_size")

Note: Always import techniques from shops for stability. Do not import
directly from sibyl.techniques.* as those are internal implementation details.
"""

from . import agents, ai_generation, infrastructure, rag, workflow

__all__ = ["agents", "ai_generation", "infrastructure", "rag", "workflow"]
