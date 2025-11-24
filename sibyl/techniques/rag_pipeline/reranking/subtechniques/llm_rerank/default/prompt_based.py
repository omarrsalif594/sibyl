"""LLM-based reranking using simulated prompt-based scoring.

This implementation simulates LLM-based relevance assessment using
heuristics like keyword matching, semantic indicators, and content quality.
"""

import re
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

from sibyl.techniques.rag_pipeline.reranking.protocols import RankedItem, RerankingResult


class PromptBasedReranking:
    """LLM-based reranking using simulated relevance scoring."""

    def __init__(self) -> None:
        self._name = "prompt_based"
        self._description = "LLM-based reranking using simulated prompt-based scoring"
        self._config_path = Path(__file__).parent.parent / "config.yaml"

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    async def execute(self, input_data: Any, config: dict[str, Any]) -> RerankingResult:
        """Execute LLM-based reranking.

        Args:
            input_data: Dict with 'query', 'items', 'top_k'
            config: Merged configuration

        Returns:
            RerankingResult with reranked items
        """
        query: str = input_data.get("query", "")
        items: list[dict[str, Any]] = input_data.get("items", [])
        top_k: int = input_data.get("top_k", 10)

        if not query or not items:
            return RerankingResult(
                ranked_items=[],
                query=query,
                reranking_method="llm_rerank:prompt_based",
                total_items=0,
                metadata={"error": "Empty query or no items"},
            )

        # Calculate LLM-based relevance scores
        scored_items = []
        for idx, item in enumerate(items):
            content = item.get("content", "")
            original_score = item.get("score", 0.0)

            # Simulate LLM relevance assessment
            llm_score = self._calculate_llm_score(query, content, config)

            # Combine with original score if configured
            use_original = config.get("use_original_score", True)
            original_weight = config.get("original_score_weight", 0.2)

            if use_original:
                final_score = (1 - original_weight) * llm_score + original_weight * original_score
            else:
                final_score = llm_score

            scored_items.append({"item": item, "score": final_score, "original_rank": idx + 1})

        # Sort by score descending
        scored_items.sort(key=lambda x: x["score"], reverse=True)

        # Create ranked items
        ranked_items = []
        for rank, scored_item in enumerate(scored_items[:top_k], start=1):
            item = scored_item["item"]
            ranked_items.append(
                RankedItem(
                    id=item.get("id", ""),
                    content=item.get("content", ""),
                    score=float(scored_item["score"]),
                    rank=rank,
                    original_rank=scored_item["original_rank"],
                    metadata=item.get("metadata", {}),
                )
            )

        return RerankingResult(
            ranked_items=ranked_items,
            query=query,
            reranking_method="llm_rerank:prompt_based",
            total_items=len(items),
            metadata={
                "top_k": top_k,
                "reranked_items": len(ranked_items),
                "use_original_score": config.get("use_original_score", True),
            },
        )

    def _calculate_llm_score(self, query: str, content: str, config: dict[str, Any]) -> float:
        """Simulate LLM-based relevance scoring.

        Uses multiple heuristics to simulate LLM assessment:
        - Keyword relevance
        - Content completeness (length, structure)
        - Question answering capability (for question queries)
        - Semantic indicators (definitions, explanations)
        - Information quality signals
        """
        score_components = {}

        # 1. Keyword relevance
        score_components["keyword"] = self._score_keyword_relevance(query, content)

        # 2. Content completeness
        score_components["completeness"] = self._score_completeness(content, config)

        # 3. Question answering capability
        score_components["qa"] = self._score_qa_capability(query, content)

        # 4. Semantic indicators
        score_components["semantic"] = self._score_semantic_indicators(query, content)

        # 5. Information quality
        score_components["quality"] = self._score_information_quality(content)

        # Combine scores with configurable weights
        weights = {
            "keyword": config.get("keyword_weight", 0.3),
            "completeness": config.get("completeness_weight", 0.2),
            "qa": config.get("qa_weight", 0.2),
            "semantic": config.get("semantic_weight", 0.15),
            "quality": config.get("quality_weight", 0.15),
        }

        final_score = sum(
            weights[component] * score for component, score in score_components.items()
        )

        return min(1.0, final_score)

    def _score_keyword_relevance(self, query: str, content: str) -> float:
        """Score based on keyword matching."""
        query_terms = set(self._tokenize(query.lower()))
        content_terms = Counter(self._tokenize(content.lower()))

        if not query_terms:
            return 0.0

        # Calculate coverage and density
        matches = sum(1 for term in query_terms if term in content_terms)
        coverage = matches / len(query_terms)

        # Boost for exact phrase matches
        phrase_bonus = 0.2 if query.lower() in content.lower() else 0.0

        return min(1.0, coverage + phrase_bonus)

    def _score_completeness(self, content: str, config: dict[str, Any]) -> float:
        """Score based on content completeness and structure."""
        min_length = config.get("min_length", 50)
        ideal_length = config.get("ideal_length", 200)

        length = len(content)

        # Length score (sigmoid-like curve)
        if length < min_length:
            length_score = length / min_length * 0.5
        elif length < ideal_length:
            length_score = 0.5 + (length - min_length) / (ideal_length - min_length) * 0.5
        else:
            length_score = 1.0

        # Structure indicators (sentences, paragraphs)
        has_sentences = "." in content or "!" in content or "?" in content
        has_structure = "\n" in content
        structure_score = 0.5 * has_sentences + 0.5 * has_structure

        return 0.7 * length_score + 0.3 * structure_score

    def _score_qa_capability(self, query: str, content: str) -> float:
        """Score capability to answer question queries."""
        # Check if query is a question
        is_question = (
            any(
                query.lower().startswith(q)
                for q in [
                    "what",
                    "how",
                    "why",
                    "when",
                    "where",
                    "who",
                    "which",
                    "is",
                    "are",
                    "can",
                    "does",
                ]
            )
            or "?" in query
        )

        if not is_question:
            return 0.5  # Neutral score for non-questions

        # Check for answer indicators in content
        answer_indicators = [
            "is",
            "are",
            "because",
            "due to",
            "result",
            "definition",
            "means",
            "refers to",
            "therefore",
            "thus",
            "example",
            "such as",
        ]

        content_lower = content.lower()
        indicator_count = sum(1 for indicator in answer_indicators if indicator in content_lower)

        return min(1.0, indicator_count / 5.0)

    def _score_semantic_indicators(self, query: str, content: str) -> float:
        """Score based on semantic relevance indicators."""
        # Look for definitional/explanatory content
        semantic_patterns = [
            r"\bis\b.*\b(a|an|the)\b",  # Definition pattern
            r"\bmeans?\b",
            r"\brefer[s]? to\b",
            r"\bdefined as\b",
            r"\bexample[s]?\b",
            r"\bsuch as\b",
            r"\binclude[s]?\b",
        ]

        content_lower = content.lower()
        pattern_matches = sum(
            1 for pattern in semantic_patterns if re.search(pattern, content_lower)
        )

        return min(1.0, pattern_matches / 4.0)

    def _score_information_quality(self, content: str) -> float:
        """Score based on information quality signals."""
        # Quality indicators
        has_numbers = bool(re.search(r"\d", content))
        has_proper_nouns = bool(re.search(r"\b[A-Z][a-z]+\b", content))
        has_dates = bool(re.search(r"\b(19|20)\d{2}\b", content))
        well_formatted = bool(re.search(r"[.!?]\s+[A-Z]", content))

        return (
            0.25 * has_numbers + 0.25 * has_proper_nouns + 0.25 * has_dates + 0.25 * well_formatted
        )

    def _tokenize(self, text: str) -> list[str]:
        """Simple tokenization by splitting on whitespace and punctuation."""
        text = re.sub(r"[^\w\s]", " ", text)
        return [token for token in text.split() if token]

    def get_config(self) -> dict[str, Any]:
        """Load default configuration."""
        defaults = {
            "use_original_score": True,
            "original_score_weight": 0.2,
            "keyword_weight": 0.3,
            "completeness_weight": 0.2,
            "qa_weight": 0.2,
            "semantic_weight": 0.15,
            "quality_weight": 0.15,
            "min_length": 50,
            "ideal_length": 200,
        }

        if self._config_path.exists():
            with open(self._config_path) as f:
                loaded = yaml.safe_load(f) or {}
                defaults.update(loaded)

        return defaults

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate configuration."""
        # Validate weight parameters
        weight_keys = [
            "original_score_weight",
            "keyword_weight",
            "completeness_weight",
            "qa_weight",
            "semantic_weight",
            "quality_weight",
        ]

        for key in weight_keys:
            if key in config and not (0 <= config[key] <= 1):
                return False

        # Validate length parameters
        if "min_length" in config and config["min_length"] < 0:
            return False
        return not ("ideal_length" in config and config["ideal_length"] < 0)
