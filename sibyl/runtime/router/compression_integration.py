"""Compression integration for routing.

Provides helper classes that run compression chains before routing
based on profile configuration.
"""

import logging
from typing import Any

from sibyl.core.compression import CompressionChain, CompressionResult, Compressor
from sibyl.core.contracts.providers import CompletionOptions, CompletionResult, LLMProvider
from sibyl.runtime.compression import AlgorithmicCompressor, LLMSummarizer
from sibyl.shops.compression import GlobalIntentExtractor, MultiPassSummary
from sibyl.techniques.infrastructure.llm.router import LLMRouter

logger = logging.getLogger(__name__)


def create_compression_chain(
    chain_config: list[dict[str, Any]],
    llm_provider: LLMProvider | None = None,
) -> CompressionChain:
    """Create a compression chain from configuration.

    Args:
        chain_config: List of compressor configs with 'name' and 'params'
        llm_provider: Optional LLM provider for compressors that need it

    Returns:
        CompressionChain instance

    Example config:
        [
            {"name": "global_intent_extractor", "params": {"max_intent_length": 300}},
            {"name": "multi_pass_summary", "params": {"num_passes": 2}},
        ]
    """
    compressors: list[Compressor] = []

    for config in chain_config:
        name = config.get("name", "")
        params = config.get("params", {})

        if name == "global_intent_extractor":
            compressor = GlobalIntentExtractor(**params)
        elif name == "multi_pass_summary":
            compressor = MultiPassSummary(llm_provider=llm_provider, **params)
        elif name == "llm_summarizer":
            compressor = LLMSummarizer(llm_provider=llm_provider, **params)
        elif name == "algorithmic_compressor":
            compressor = AlgorithmicCompressor(**params)
        else:
            logger.warning("Unknown compressor type: %s, skipping", name)
            continue

        compressors.append(compressor)

    if not compressors:
        msg = "No valid compressors configured in chain"
        raise ValueError(msg)

    return CompressionChain(compressors)


class CompressionRouter:
    """Router with integrated compression wall.

    This class wraps LLMRouter and adds compression before routing.
    Compression is configured per routing profile.

    Usage:
        router = CompressionRouter(
            llm_router=llm_router,
            compression_config=compression_config,
        )

        result = await router.route_with_compression(
            provider="anthropic",
            model="claude-sonnet-4",
            prompt=long_prompt,
            options=options,
            profile="think",  # Uses compression config for "think" profile
        )
    """

    def __init__(
        self,
        llm_router: LLMRouter,
        compression_config: dict[str, Any],
        llm_provider: LLMProvider | None = None,
    ) -> None:
        """Initialize compression router.

        Args:
            llm_router: Underlying LLM router
            compression_config: Compression configuration by profile
            llm_provider: Optional LLM provider for compressors
        """
        self.llm_router = llm_router
        self.compression_config = compression_config
        self.llm_provider = llm_provider

        # Cache compression chains by profile
        self._chains: dict[str, CompressionChain | None] = {}

        logger.info(
            "CompressionRouter initialized with profiles: %s",
            list(compression_config.get("profiles", {}).keys()),
        )

    async def route_with_compression(
        self,
        provider: str,
        model: str,
        prompt: str,
        options: CompletionOptions,
        profile: str = "default",
        priority: int = 5,
    ) -> tuple[CompletionResult, CompressionResult | None]:
        """Route request with optional compression.

        Args:
            provider: Provider name
            model: Model name
            prompt: Input prompt (may be compressed)
            options: Completion options
            profile: Routing profile (determines compression config)
            priority: Priority level

        Returns:
            Tuple of (completion_result, compression_result)
            compression_result is None if compression not enabled
        """
        # Get compression chain for profile
        compression_chain = self._get_compression_chain(profile)

        compression_result = None

        # Apply compression if enabled
        if compression_chain:
            logger.info("Applying compression for profile '%s' before routing", profile)

            try:
                compression_result = await compression_chain.compress(
                    prompt,
                    profile=profile,
                    provider=provider,
                    model=model,
                )

                # Use compressed prompt for routing
                compressed_prompt = compression_result.compressed_text

                logger.info(
                    f"Compression complete: {compression_result.metrics.original_size} -> "
                    f"{compression_result.metrics.compressed_size} chars "
                    f"({compression_result.metrics.space_saved_percent:.1f}% saved, "
                    f"{compression_result.metrics.duration_ms:.0f}ms)"
                )

                # Update options with compression metadata if needed
                if not hasattr(options, "metadata"):
                    options.metadata = {}
                options.metadata["compression_applied"] = True
                options.metadata["compression_ratio"] = compression_result.compression_ratio

            except Exception as e:
                logger.exception("Compression failed: %s, proceeding with original prompt", e)
                compressed_prompt = prompt
                compression_result = None
        else:
            compressed_prompt = prompt

        # Route to LLM
        completion_result = await self.llm_router.route(
            provider=provider,
            model=model,
            prompt=compressed_prompt,
            options=options,
            priority=priority,
        )

        return completion_result, compression_result

    def _get_compression_chain(self, profile: str) -> CompressionChain | None:
        """Get or create compression chain for profile.

        Args:
            profile: Routing profile name

        Returns:
            CompressionChain or None if compression disabled
        """
        # Check cache
        if profile in self._chains:
            return self._chains[profile]

        # Load from config
        profiles_config = self.compression_config.get("profiles", {})
        profile_config = profiles_config.get(profile, profiles_config.get("default", {}))

        enabled = profile_config.get("enabled", False)

        if not enabled:
            self._chains[profile] = None
            return None

        # Build chain from config
        chain_config = profile_config.get("chain", [])

        if not chain_config:
            logger.warning("Compression enabled for profile '%s' but no chain configured", profile)
            self._chains[profile] = None
            return None

        try:
            chain = create_compression_chain(chain_config, self.llm_provider)
            self._chains[profile] = chain
            logger.info("Created compression chain for profile '%s': %s", profile, chain.name)
            return chain
        except Exception as e:
            logger.exception("Failed to create compression chain for profile '%s': %s", profile, e)
            self._chains[profile] = None
            return None

    def get_stats(self, provider: str | None = None) -> dict[str, Any]:
        """Get router statistics including compression info.

        Args:
            provider: Optional provider filter

        Returns:
            Dict with router and compression stats
        """
        # Get base router stats
        router_stats = self.llm_router.get_stats(provider)

        # Add compression info
        compression_stats = {
            "enabled_profiles": [
                profile for profile, chain in self._chains.items() if chain is not None
            ],
            "total_profiles": len(self._chains),
        }

        return {
            "router": router_stats,
            "compression": compression_stats,
        }
