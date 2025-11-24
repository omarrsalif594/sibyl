"""
Common utilities for Sibyl plugins.

This module provides shared functionality for all plugin adapters,
including the core sibyl_runner for executing pipelines.
"""

from plugins.common.sibyl_runner import load_pipeline_config, run_pipeline

__all__ = ["load_pipeline_config", "run_pipeline"]
