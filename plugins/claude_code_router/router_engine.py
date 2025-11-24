"""
Router Engine for Claude Code Router.

This module implements a purely config-driven routing engine that matches
requests against rules without any LLM calls or dynamic policy decisions.

The routing logic is intentionally simple:
1. Load routing rules from configuration
2. Match request tags against rule tags
3. Return the first matching rule's route decision

No automatic policy, no local/remote selection, no smart routing.
Just explicit, transparent, config-driven rule matching.
"""

import logging
from pathlib import Path

import yaml

from plugins.claude_code_router.router_types import (
    RouteDecision,
    RouterConfig,
    RouteRequest,
    RouteRule,
)

logger = logging.getLogger(__name__)


def load_router_config(config_path: str | None = None) -> RouterConfig:
    """
    Load router configuration from a YAML file.

    Args:
        config_path: Path to the router config YAML file.
            If None, uses the default config in this plugin directory.

    Returns:
        RouterConfig instance with all rules loaded

    Raises:
        FileNotFoundError: If the config file doesn't exist
        ValueError: If the config file is invalid

    Example:
        >>> config = load_router_config()
        >>> config = load_router_config("custom_router_config.yaml")
    """
    if config_path is None:
        # Use default config in this plugin directory
        plugin_dir = Path(__file__).parent
        config_path = plugin_dir / "router_config.yaml"
    else:
        config_path = Path(config_path)

    if not config_path.exists():
        msg = f"Router config not found: {config_path}"
        raise FileNotFoundError(msg)

    logger.info("Loading router config from: %s", config_path)

    try:
        with open(config_path) as f:
            config_dict = yaml.safe_load(f)

        # Validate and parse the config using Pydantic
        config = RouterConfig(**config_dict)
        logger.info("Loaded %s routing rules", len(config.rules))

        return config

    except yaml.YAMLError as e:
        msg = f"Invalid YAML in router config: {e}"
        raise ValueError(msg) from None
    except Exception as e:
        msg = f"Failed to load router config: {e}"
        raise ValueError(msg) from e


def _matches_rule(request: RouteRequest, rule: RouteRule) -> bool:
    """
    Check if a request matches a routing rule.

    Matching logic:
    - If rule has empty when_tags, it always matches (fallback)
    - If rule has when_tags and request has no tags, no match
    - If rule has when_tags and request has tags, check for intersection

    Args:
        request: The routing request
        rule: The rule to match against

    Returns:
        True if the request matches the rule, False otherwise

    Example:
        >>> request = RouteRequest(question="test", tags=["analytics"])
        >>> rule = RouteRule(name="test", when_tags=["analytics"], route=...)
        >>> _matches_rule(request, rule)
        True
    """
    # Empty when_tags means this is a fallback rule that always matches
    if not rule.when_tags:
        logger.debug("Rule '%s' is a fallback rule (empty when_tags)", rule.name)
        return True

    # If rule has tags but request doesn't, no match
    if not request.tags:
        logger.debug("Rule '%s' requires tags but request has none", rule.name)
        return False

    # Check for intersection between request tags and rule tags
    request_tags_set = set(request.tags)
    rule_tags_set = set(rule.when_tags)
    intersection = request_tags_set & rule_tags_set

    if intersection:
        logger.debug("Rule '%s' matches - overlapping tags: %s", rule.name, intersection)
        return True
    logger.debug("Rule '%s' does not match - no overlapping tags", rule.name)
    return False


def route(request: RouteRequest, config: RouterConfig) -> RouteDecision:
    """
    Route a request based on config-driven rules.

    This is a purely deterministic routing function that:
    1. Evaluates rules in order
    2. Returns the first matching rule's route decision
    3. Never makes LLM calls or dynamic policy decisions

    The routing logic is intentionally simple and transparent.
    All routing behavior is explicit in the configuration.

    Args:
        request: The routing request with question, tags, and context
        config: The router configuration with rules

    Returns:
        RouteDecision describing where to send the request

    Example:
        >>> config = load_router_config()
        >>> request = RouteRequest(
        ...     question="What are the top customers?",
        ...     tags=["analytics"]
        ... )
        >>> decision = route(request, config)
        >>> decision.target
        'sibyl_pipeline'
        >>> decision.workspace
        'examples/companies/northwind_analytics/config/workspace.yaml'
    """
    logger.info("Routing request with tags: %s", request.tags)

    # Evaluate rules in order
    for rule in config.rules:
        if _matches_rule(request, rule):
            logger.info("Matched rule '%s' -> target: %s", rule.name, rule.route.target)
            return rule.route

    # This should never happen if config has a fallback rule with empty when_tags
    logger.warning("No rules matched! This indicates a config issue.")
    return RouteDecision(target="noop")


def route_with_config_path(request: RouteRequest, config_path: str | None = None) -> RouteDecision:
    """
    Convenience function to route with a config file path.

    This combines load_router_config() and route() into a single call.

    Args:
        request: The routing request
        config_path: Optional path to router config (uses default if None)

    Returns:
        RouteDecision describing where to send the request

    Example:
        >>> request = RouteRequest(question="test", tags=["analytics"])
        >>> decision = route_with_config_path(request)
        >>> decision.target
        'sibyl_pipeline'
    """
    config = load_router_config(config_path)
    return route(request, config)


def validate_config(config_path: str | None = None) -> dict:
    """
    Validate a router configuration file and return diagnostics.

    Checks:
    - File exists and is valid YAML
    - All required fields are present
    - Rule ordering makes sense (fallback rules at end)
    - Target types are valid

    Args:
        config_path: Path to config file (uses default if None)

    Returns:
        Dictionary with validation results:
        - valid: bool
        - errors: list of error messages
        - warnings: list of warning messages
        - rule_count: number of rules
        - fallback_rules: list of fallback rule names

    Example:
        >>> result = validate_config()
        >>> result['valid']
        True
        >>> result['rule_count']
        8
    """
    result = {
        "valid": True,
        "errors": [],
        "warnings": [],
        "rule_count": 0,
        "fallback_rules": [],
    }

    try:
        config = load_router_config(config_path)
        result["rule_count"] = len(config.rules)

        # Check for fallback rules (empty when_tags)
        fallback_indices = []
        for i, rule in enumerate(config.rules):
            if not rule.when_tags:
                result["fallback_rules"].append(rule.name)
                fallback_indices.append(i)

        # Warn if fallback rules aren't at the end
        if fallback_indices and fallback_indices[0] != len(config.rules) - 1:
            result["warnings"].append(
                f"Fallback rules should be at the end. Found at indices: {fallback_indices}"
            )

        # Warn if no fallback rule exists
        if not fallback_indices:
            result["warnings"].append(
                "No fallback rule (empty when_tags) defined. Some requests may not match any rule."
            )

        # Check for duplicate rule names
        rule_names = [rule.name for rule in config.rules]
        duplicates = [name for name in rule_names if rule_names.count(name) > 1]
        if duplicates:
            result["warnings"].append(f"Duplicate rule names found: {set(duplicates)}")

    except FileNotFoundError as e:
        result["valid"] = False
        result["errors"].append(str(e))
    except ValueError as e:
        result["valid"] = False
        result["errors"].append(str(e))
    except Exception as e:
        result["valid"] = False
        result["errors"].append(f"Unexpected error: {e}")

    return result
