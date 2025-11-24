"""Token pricing configuration for cost estimation.

This module provides pricing information for various LLM models to enable
cost estimation for pipeline execution. Prices are based on public pricing
as of January 2025.

Pricing can be overridden via environment variables or configuration files.

Example:
    from sibyl.runtime.pipeline.pricing import estimate_cost, get_model_pricing

    # Estimate cost for a completion
    cost = estimate_cost(
        model="gpt-4",
        prompt_tokens=1000,
        completion_tokens=500,
    )

    # Get pricing for a model
    pricing = get_model_pricing("gpt-4")
"""

import os
from dataclasses import dataclass


@dataclass
class ModelPricing:
    """Pricing information for a model.

    Attributes:
        prompt_price_per_1k: Price per 1000 prompt tokens in USD
        completion_price_per_1k: Price per 1000 completion tokens in USD
        currency: Currency code (default: USD)
    """

    prompt_price_per_1k: float
    completion_price_per_1k: float
    currency: str = "USD"


# Default pricing table (prices in USD per 1K tokens)
# Source: Public pricing from providers as of January 2025
DEFAULT_PRICING: dict[str, ModelPricing] = {
    # OpenAI GPT-4 models
    "gpt-4": ModelPricing(prompt_price_per_1k=0.03, completion_price_per_1k=0.06),
    "gpt-4-turbo": ModelPricing(prompt_price_per_1k=0.01, completion_price_per_1k=0.03),
    "gpt-4-turbo-preview": ModelPricing(prompt_price_per_1k=0.01, completion_price_per_1k=0.03),
    "gpt-4-1106-preview": ModelPricing(prompt_price_per_1k=0.01, completion_price_per_1k=0.03),
    "gpt-4-0125-preview": ModelPricing(prompt_price_per_1k=0.01, completion_price_per_1k=0.03),
    # OpenAI GPT-3.5 models
    "gpt-3.5-turbo": ModelPricing(prompt_price_per_1k=0.0005, completion_price_per_1k=0.0015),
    "gpt-3.5-turbo-16k": ModelPricing(prompt_price_per_1k=0.003, completion_price_per_1k=0.004),
    "gpt-3.5-turbo-1106": ModelPricing(prompt_price_per_1k=0.001, completion_price_per_1k=0.002),
    "gpt-3.5-turbo-0125": ModelPricing(prompt_price_per_1k=0.0005, completion_price_per_1k=0.0015),
    # Anthropic Claude models
    "claude-3-opus-20240229": ModelPricing(
        prompt_price_per_1k=0.015, completion_price_per_1k=0.075
    ),
    "claude-3-sonnet-20240229": ModelPricing(
        prompt_price_per_1k=0.003, completion_price_per_1k=0.015
    ),
    "claude-3-haiku-20240307": ModelPricing(
        prompt_price_per_1k=0.00025, completion_price_per_1k=0.00125
    ),
    "claude-sonnet-4-5-20250929": ModelPricing(
        prompt_price_per_1k=0.003, completion_price_per_1k=0.015
    ),
    # Embeddings models
    "text-embedding-3-small": ModelPricing(
        prompt_price_per_1k=0.00002, completion_price_per_1k=0.0
    ),
    "text-embedding-3-large": ModelPricing(
        prompt_price_per_1k=0.00013, completion_price_per_1k=0.0
    ),
    "text-embedding-ada-002": ModelPricing(prompt_price_per_1k=0.0001, completion_price_per_1k=0.0),
    # Local/test models (no cost)
    "local-deterministic": ModelPricing(prompt_price_per_1k=0.0, completion_price_per_1k=0.0),
    "ollama": ModelPricing(prompt_price_per_1k=0.0, completion_price_per_1k=0.0),
}


def get_model_pricing(model: str) -> ModelPricing | None:
    """Get pricing information for a model.

    Checks environment variables first, then falls back to default pricing table.

    Environment variables (per model):
    - SIBYL_PRICING_{MODEL}_PROMPT: Prompt price per 1K tokens
    - SIBYL_PRICING_{MODEL}_COMPLETION: Completion price per 1K tokens

    Args:
        model: Model name (e.g., "gpt-4", "claude-3-opus")

    Returns:
        ModelPricing instance or None if pricing not available
    """
    # Normalize model name for env var lookup
    model_env = model.replace("-", "_").replace(".", "_").upper()

    # Check environment variables first
    prompt_env = f"SIBYL_PRICING_{model_env}_PROMPT"
    completion_env = f"SIBYL_PRICING_{model_env}_COMPLETION"

    prompt_price = os.environ.get(prompt_env)
    completion_price = os.environ.get(completion_env)

    if prompt_price is not None and completion_price is not None:
        try:
            return ModelPricing(
                prompt_price_per_1k=float(prompt_price),
                completion_price_per_1k=float(completion_price),
            )
        except ValueError:
            pass  # Fall back to default pricing

    # Check default pricing table
    return DEFAULT_PRICING.get(model)


def estimate_cost(
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
) -> float | None:
    """Estimate cost for a completion.

    Args:
        model: Model name
        prompt_tokens: Number of prompt tokens
        completion_tokens: Number of completion tokens

    Returns:
        Estimated cost in USD, or None if pricing not available
    """
    pricing = get_model_pricing(model)
    if pricing is None:
        return None

    prompt_cost = (prompt_tokens / 1000.0) * pricing.prompt_price_per_1k
    completion_cost = (completion_tokens / 1000.0) * pricing.completion_price_per_1k

    return prompt_cost + completion_cost


def estimate_cost_from_usage(
    model: str,
    tokens_in: int,
    tokens_out: int,
) -> float | None:
    """Estimate cost from token usage (alias for estimate_cost with clearer names).

    Args:
        model: Model name
        tokens_in: Number of input/prompt tokens
        tokens_out: Number of output/completion tokens

    Returns:
        Estimated cost in USD, or None if pricing not available
    """
    return estimate_cost(model, tokens_in, tokens_out)


def add_custom_pricing(model: str, prompt_price: float, completion_price: float) -> None:
    """Add custom pricing for a model.

    This allows runtime addition of pricing for custom or new models.

    Args:
        model: Model name
        prompt_price: Prompt price per 1K tokens in USD
        completion_price: Completion price per 1K tokens in USD
    """
    DEFAULT_PRICING[model] = ModelPricing(
        prompt_price_per_1k=prompt_price,
        completion_price_per_1k=completion_price,
    )


def get_all_model_pricing() -> dict[str, ModelPricing]:
    """Get pricing for all known models.

    Returns:
        Dictionary mapping model names to pricing information
    """
    return DEFAULT_PRICING.copy()
