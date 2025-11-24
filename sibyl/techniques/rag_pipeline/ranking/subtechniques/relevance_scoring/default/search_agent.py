"""
Search Agent - Provides knowledge base search capabilities.

This agent:
- Wraps knowledge base search
- Handles hybrid search (semantic + keyword)
- Filters and ranks results
- No domain assumptions
"""

import logging
from typing import Any

from sibyl.agents.base.agent import BaseAgent
from sibyl.agents.types import AgentRequestPayload, AgentResponsePayload

logger = logging.getLogger(__name__)


class SearchAgent(BaseAgent):
    """
    Generic search agent for knowledge base queries.

    Provides unified interface to various search backends.
    """

    def __init__(self, hybrid_search_service: Any = None, **kwargs) -> None:
        """
        Initialize search agent.

        Args:
            hybrid_search_service: Hybrid search backend
            **kwargs: Base agent parameters
        """
        super().__init__(agent_id="search", **kwargs)
        self.hybrid_search = hybrid_search_service
        logger.info("Search agent initialized")

    async def execute(self, request: AgentRequestPayload) -> AgentResponsePayload:
        """
        Execute search query.

        Args:
            request: {
                "query": search query string,
                "filters": optional filters,
                "limit": max results (default 10),
                "search_type": "hybrid" | "semantic" | "keyword"
            }

        Returns:
            {
                "results": list of results,
                "count": number of results,
                "query": original query,
                "filters_applied": filters used
            }
        """
        query = request.get("query", "")
        filters = request.get("filters", {})
        limit = request.get("limit", 10)
        search_type = request.get("search_type", "hybrid")

        if not query:
            return {"results": [], "count": 0, "error": "Empty query"}

        logger.info("Searching: '%s' (type=%s, limit=%s)", query, search_type, limit)

        # Execute search based on type
        if search_type == "hybrid" and self.hybrid_search:
            results = await self._hybrid_search(query, filters, limit)
        elif search_type == "semantic":
            results = await self._semantic_search(query, filters, limit)
        else:
            results = await self._keyword_search(query, filters, limit)

        # Post-process results
        results = self._post_process_results(results, query)

        return {
            "results": results,
            "count": len(results),
            "query": query,
            "filters_applied": filters,
            "search_type": search_type,
        }

    async def _hybrid_search(
        self, query: str, filters: dict[str, Any], limit: int
    ) -> list[dict[str, Any]]:
        """
        Perform hybrid search (semantic + keyword).

        Args:
            query: Search query
            filters: Search filters
            limit: Max results

        Returns:
            Search results
        """
        if not self.hybrid_search:
            logger.warning("Hybrid search not available, falling back to keyword")
            return await self._keyword_search(query, filters, limit)

        try:
            return await self.hybrid_search.search(query=query, filters=filters, limit=limit)
        except Exception as e:
            logger.exception("Hybrid search failed: %s", e)
            return []

    async def _semantic_search(
        self, query: str, filters: dict[str, Any], limit: int
    ) -> list[dict[str, Any]]:
        """
        Perform semantic (vector) search.

        Args:
            query: Search query
            filters: Search filters
            limit: Max results

        Returns:
            Search results
        """
        if not self.search_service:
            logger.warning("Search service not available")
            return []

        try:
            return await self.search_service.semantic_search(
                query=query, filters=filters, limit=limit
            )
        except Exception as e:
            logger.exception("Semantic search failed: %s", e)
            return []

    async def _keyword_search(
        self, query: str, filters: dict[str, Any], limit: int
    ) -> list[dict[str, Any]]:
        """
        Perform keyword search.

        Args:
            query: Search query
            filters: Search filters
            limit: Max results

        Returns:
            Search results
        """
        if not self.search_service:
            logger.warning("Search service not available")
            return []

        try:
            return await self.search_service.keyword_search(
                query=query, filters=filters, limit=limit
            )
        except Exception as e:
            logger.exception("Keyword search failed: %s", e)
            return []

    def _post_process_results(
        self, results: list[dict[str, Any]], query: str
    ) -> list[dict[str, Any]]:
        """
        Post-process and enrich results.

        Args:
            results: Raw search results
            query: Original query

        Returns:
            Processed results
        """
        processed = []

        for result in results:
            # Add relevance explanation
            result["relevance_reason"] = self._explain_relevance(result, query)

            # Truncate long content
            if "content" in result and len(result["content"]) > 500:
                result["content_preview"] = result["content"][:500] + "..."
                result["content_truncated"] = True

            processed.append(result)

        return processed

    def _explain_relevance(self, result: dict[str, Any], query: str) -> str:
        """
        Explain why result is relevant.

        Args:
            result: Search result
            query: Original query

        Returns:
            Relevance explanation
        """
        reasons = []

        # Check for query terms in content
        query_terms = query.lower().split()
        content = result.get("content", "").lower()

        matching_terms = [term for term in query_terms if term in content]
        if matching_terms:
            reasons.append(f"Contains: {', '.join(matching_terms[:3])}")

        # Check score
        score = result.get("score", 0)
        if score > 0.8:
            reasons.append("High similarity score")
        elif score > 0.5:
            reasons.append("Moderate similarity")

        # Check metadata matches
        if result.get("resource_type") in query.lower():
            reasons.append("Resource type match")

        return " | ".join(reasons) if reasons else "Semantic similarity"
