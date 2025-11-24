"""Session Management Technique Module

Provides pluggable session lifecycle management with:
- Rotation strategies (token-based, time-based, message-count)
- Context preservation (sliding-window, importance-based, full-history)
- Summarization (extractive, abstractive, no-summarize)
"""

from .technique import SessionManagementTechnique

__all__ = ["SessionManagementTechnique"]
