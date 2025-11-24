"""
Top-N Fix Extraction

Original logic from sibyl/core/learning/hook.py:252-263:
    if verdict.suggested_fixes:
        return "; ".join(verdict.suggested_fixes[:3])  # Top 3 fixes
    return verdict.feedback

This extracts the top N suggested fixes from a verdict and formats them
as a single string for learning record storage.
"""

from typing import Any

from sibyl.techniques.protocols import SubtechniqueImplementation, SubtechniqueResult


class TopNFixExtraction(SubtechniqueImplementation):
    """Extract top N fixes from verdict."""

    def execute(self, context: dict[str, Any], **kwargs) -> SubtechniqueResult:
        """
        Extract and format top N suggested fixes.

        Args:
            context: Must contain:
                - 'suggested_fixes': List of fix descriptions (optional)
                - 'feedback': Fallback feedback text
            **kwargs: Additional arguments (ignored)

        Returns:
            SubtechniqueResult with fix_description and metadata

        Example:
            >>> impl = TopNFixExtraction(config)
            >>> result = impl.execute({
            ...     'suggested_fixes': ['Fix A', 'Fix B', 'Fix C', 'Fix D'],
            ...     'feedback': 'General feedback'
            ... })
            >>> result.result['fix_description']  # 'Fix A; Fix B; Fix C'
        """
        suggested_fixes = context.get("suggested_fixes", [])
        feedback = context.get("feedback", "")

        # Get config parameters
        max_fixes = self.config.get("max_fixes", 3)
        delimiter = self.config.get("delimiter", "; ")
        use_feedback_fallback = self.config.get("use_feedback_fallback", True)

        # Extract top N fixes
        if suggested_fixes:
            top_fixes = suggested_fixes[:max_fixes]
            fix_description = delimiter.join(top_fixes)
            source = "suggested_fixes"
        elif use_feedback_fallback:
            fix_description = feedback
            source = "feedback"
        else:
            fix_description = ""
            source = "none"

        return SubtechniqueResult(
            success=True,
            result={
                "fix_description": fix_description,
                "source": source,
                "num_fixes": len(suggested_fixes) if suggested_fixes else 0,
                "truncated": len(suggested_fixes) > max_fixes if suggested_fixes else False,
            },
            metadata={
                "max_fixes": max_fixes,
                "delimiter": delimiter,
                "use_feedback_fallback": use_feedback_fallback,
                "available_fixes": len(suggested_fixes) if suggested_fixes else 0,
            },
        )
