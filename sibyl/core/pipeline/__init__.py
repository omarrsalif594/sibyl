"""Pipeline infrastructure for Sibyl.

This module provides core pipeline components including:
- Template engine for parameter interpolation
- Pipeline execution primitives
"""

from sibyl.core.pipeline.template_engine import (
    PipelineTemplateEngine,
    TemplateRenderError,
)

__all__ = [
    "PipelineTemplateEngine",
    "TemplateRenderError",
]
