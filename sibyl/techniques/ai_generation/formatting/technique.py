"""
Formatting Technique

TODO: Implement technique class
"""

from typing import Any

from sibyl.techniques.protocols import BaseTechnique


class FormattingTechnique(BaseTechnique):
    """TODO: Add description"""

    def execute(
        self, subtechnique: str, implementation: str, context: dict[str, Any], **kwargs
    ) -> Any:
        """
        Execute a formatting subtechnique.

        Args:
            subtechnique: One of ['checkpoint_naming', 'category_naming']
            implementation: Implementation name
            context: Input data for algorithm
            **kwargs: Additional arguments

        Returns:
            Result with calculated values
        """
        impl = self.get_subtechnique(subtechnique, implementation)
        return impl.execute(context, **kwargs)
