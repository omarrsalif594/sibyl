"""
Adaptive learning and pattern discovery
"""

from pathlib import Path
from typing import Any

from sibyl.techniques.protocols import BaseTechnique


class LearningTechnique(BaseTechnique):
    """Adaptive learning and pattern discovery."""

    def __init__(self, config_path: Path | None = None) -> None:
        self._name = "learning"
        self._config_path = config_path or Path(__file__).parent / "config.yaml"
        self._subtechniques: dict[str, Any] = {}
        self._discover_subtechniques()

    @property
    def name(self) -> str:
        return self._name

    @property
    def subtechniques(self) -> dict[str, Any]:
        return self._subtechniques

    def register_subtechnique(self, subtechnique: Any, implementation: str) -> None:
        """Register a subtechnique implementation."""
        key = f"{subtechnique.name}:{implementation}"
        self._subtechniques[key] = subtechnique

    def execute(
        self,
        input_data: Any,
        subtechnique: str,
        implementation: str = "default",
        config: dict | None = None,
        **kwargs,
    ) -> Any:
        """Execute technique.

        Args:
            input_data: Input data
            subtechnique: Subtechnique name
            implementation: Implementation name (from default/, provider/, or custom/)
            config: Optional configuration override
            **kwargs: Additional arguments

        Returns:
            Result from subtechnique execution
        """
        # TODO: Implement in Phase 2
        msg = f"{self._name} not yet implemented"
        raise NotImplementedError(msg)

    def calculate_confidence(
        self,
        verdict_status: str,
        base_confidence: float,
        implementation: str | None = None,
        **kwargs,
    ) -> float:
        """
        Convenience method to calculate confidence from verdict.

        Args:
            verdict_status: Verdict status (GREEN, YELLOW, RED)
            base_confidence: Base confidence from classification (0.0-1.0)
            implementation: Optional implementation name
            **kwargs: Additional arguments

        Returns:
            Adjusted confidence score (0.0-1.0)
        """
        impl = implementation or "verdict_based"
        result = self.execute(
            {"verdict_status": verdict_status, "base_confidence": base_confidence},
            "confidence_calculation",
            impl,
            **kwargs,
        )
        return result.result.get("confidence", base_confidence)

    def extract_fix_description(
        self, suggested_fixes: list[str], feedback: str, implementation: str | None = None, **kwargs
    ) -> str:
        """
        Convenience method to extract fix description.

        Args:
            suggested_fixes: List of suggested fixes
            feedback: Fallback feedback text
            implementation: Optional implementation name
            **kwargs: Additional arguments

        Returns:
            Formatted fix description
        """
        impl = implementation or "top_n_fixes"
        result = self.execute(
            {"suggested_fixes": suggested_fixes, "feedback": feedback},
            "fix_extraction",
            impl,
            **kwargs,
        )
        return result.result.get("fix_description", feedback)

    def _discover_subtechniques(self) -> None:
        """Auto-discover and register subtechniques."""
        # TODO: Implement auto-discovery in Phase 2
