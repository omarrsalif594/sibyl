"""Simple HyDE (Hypothetical Document Embeddings) implementation.

This implementation generates a simple hypothetical document from a query
using template-based generation.
"""

from pathlib import Path
from typing import Any

import yaml

from sibyl.techniques.rag_pipeline.query_processing.protocols import (
    ProcessedQuery,
    QueryProcessingResult,
)


class SimpleHyDE:
    """Simple HyDE implementation using template-based document generation."""

    def __init__(self) -> None:
        self._name = "simple_hyde"
        self._description = "Generate simple hypothetical documents from queries"
        self._config_path = Path(__file__).parent.parent / "config.yaml"

        # Document templates for different query types
        self._document_templates = {
            "what_is": "{concept} is a {type} that provides {functionality}. It is commonly used for {use_case} and offers {benefits}.",
            "how_to": "To {action}, you need to follow these steps: First, {step1}. Then, {step2}. Finally, {step3}. This approach ensures {outcome}.",
            "best_practices": "The best practices for {topic} include: {practice1}, {practice2}, and {practice3}. These practices help achieve {goal}.",
            "comparison": "When comparing {item1} and {item2}, the main differences are: {diff1}, {diff2}. Choose {item1} when {scenario1}, and {item2} when {scenario2}.",
            "error": "The error '{error}' typically occurs when {cause}. To resolve it, you should {solution}. Common fixes include {fix1} and {fix2}.",
            "generic": "Regarding {topic}, it is important to understand that {statement1}. Additionally, {statement2}. This is relevant because {reason}.",
        }

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    async def execute(self, input_data: Any, config: dict[str, Any]) -> QueryProcessingResult:
        """Generate hypothetical document from query.

        Args:
            input_data: Dict with 'query' key
            config: Merged configuration (global + technique + subtechnique)

        Returns:
            QueryProcessingResult with hypothetical document as query
        """
        query: str = input_data.get("query", "")
        document_length: str = config.get("document_length", "medium")
        custom_templates: dict = config.get("custom_templates", {})

        if not query:
            return QueryProcessingResult(
                processed_queries=[],
                original_query=query,
                processing_method="hyde:simple_hyde",
                metadata={"error": "Empty query"},
            )

        # Merge custom templates with defaults
        templates = {**self._document_templates, **custom_templates}

        # Generate hypothetical document
        hypothetical_doc = self._generate_document(query, templates, document_length)

        return QueryProcessingResult(
            processed_queries=[
                ProcessedQuery(
                    query=hypothetical_doc,
                    method="simple_hyde",
                    original_query=query,
                    metadata={"document_length": document_length, "is_hypothetical": True},
                )
            ],
            original_query=query,
            processing_method="hyde:simple_hyde",
            metadata={
                "document_length": document_length,
                "hypothetical_doc_length": len(hypothetical_doc),
            },
        )

    def _generate_document(self, query: str, templates: dict, length: str) -> str:
        """Generate hypothetical document from query.

        Args:
            query: Original query
            templates: Document templates
            length: Desired document length (short, medium, long)

        Returns:
            Generated hypothetical document
        """
        query_lower = query.lower()

        # Detect query type and generate appropriate document
        if "what is" in query_lower or "what are" in query_lower:
            concept = query_lower.replace("what is", "").replace("what are", "").strip().rstrip("?")
            doc = self._generate_what_is_doc(concept, length)
        elif "how to" in query_lower or "how do" in query_lower or "how can" in query_lower:
            action = (
                query_lower.replace("how to", "")
                .replace("how do i", "")
                .replace("how can i", "")
                .strip()
                .rstrip("?")
            )
            doc = self._generate_how_to_doc(action, length)
        elif "best practice" in query_lower or "recommended" in query_lower:
            topic = (
                query_lower.replace("best practices for", "")
                .replace("best practice", "")
                .strip()
                .rstrip("?")
            )
            doc = self._generate_best_practice_doc(topic, length)
        elif "error" in query_lower or "exception" in query_lower or "bug" in query_lower:
            doc = self._generate_error_doc(query, length)
        else:
            doc = self._generate_generic_doc(query, length)

        return doc

    def _generate_what_is_doc(self, concept: str, length: str) -> str:
        """Generate hypothetical document for 'what is' queries."""
        base = f"{concept.title()} is a concept that provides specific functionality. "
        base += "It is commonly used in various contexts and offers several benefits. "

        if length == "long":
            base += f"{concept.title()} can be applied in multiple scenarios including software development, data processing, and system design. "
            base += "The main advantages include improved efficiency, better organization, and enhanced maintainability. "

        return base

    def _generate_how_to_doc(self, action: str, length: str) -> str:
        """Generate hypothetical document for 'how to' queries."""
        base = f"To {action}, you should follow a systematic approach. "
        base += "First, prepare the necessary prerequisites and environment. "
        base += "Then, execute the main steps carefully. "

        if length == "long":
            base += f"During the process of {action}, it's important to monitor progress and validate each step. "
            base += "Common challenges include configuration issues and dependency problems, which can be resolved through proper setup. "

        return base

    def _generate_best_practice_doc(self, topic: str, length: str) -> str:
        """Generate hypothetical document for best practices queries."""
        base = f"The best practices for {topic} include following industry standards and proven methodologies. "
        base += "Key recommendations are to maintain consistency, ensure proper documentation, and perform regular testing. "

        if length == "long":
            base += f"When working with {topic}, it's crucial to consider scalability, maintainability, and performance. "
            base += "Teams should establish clear guidelines and conduct code reviews to ensure quality. "

        return base

    def _generate_error_doc(self, query: str, length: str) -> str:
        """Generate hypothetical document for error-related queries."""
        base = "This error typically occurs when there is a configuration or runtime issue. "
        base += "To resolve it, you should check the relevant settings and verify that all dependencies are properly installed. "

        if length == "long":
            base += "Common causes include incorrect environment variables, missing libraries, or permission issues. "
            base += "Debugging steps include reviewing logs, validating configuration files, and testing in isolation. "

        return base

    def _generate_generic_doc(self, query: str, length: str) -> str:
        """Generate generic hypothetical document."""
        base = f"Regarding {query}, it is important to understand the core concepts and principles involved. "
        base += "This topic encompasses several key aspects that should be considered carefully. "

        if length == "long":
            base += "Best practices suggest thorough research and testing before implementation. "
            base += "Additional resources and documentation can provide more detailed information on specific use cases. "

        return base

    def get_config(self) -> dict[str, Any]:
        """Load default configuration."""
        defaults = {"document_length": "medium", "custom_templates": {}}

        if self._config_path.exists():
            with open(self._config_path) as f:
                loaded = yaml.safe_load(f) or {}
                defaults.update(loaded)

        return defaults

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate configuration."""
        if "document_length" in config:
            if config["document_length"] not in ["short", "medium", "long"]:
                return False
        return not (
            "custom_templates" in config and not isinstance(config["custom_templates"], dict)
        )
