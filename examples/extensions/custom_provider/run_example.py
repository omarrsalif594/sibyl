#!/usr/bin/env python3
"""
Standalone example demonstrating custom Echo LLM provider.

This script shows how to:
1. Create custom provider instances
2. Use them programmatically
3. Test different completion modes
4. Compare provider features
"""

import asyncio
import contextlib

from echo_llm import EchoLLMProvider, TransformLLMProvider

from sibyl.core.protocols.infrastructure.llm import CompletionOptions


def main() -> None:
    # Create provider instances
    echo_provider = EchoLLMProvider(model="echo-1", prefix="[ECHO] ", simulate_latency_ms=5)
    transform_provider = TransformLLMProvider(model="transform-1", transform="uppercase")

    # Test synchronous completion

    options = CompletionOptions(model="echo-1", temperature=0.0, max_tokens=100)

    prompt = "Hello, world!"

    echo_provider.complete(prompt, options)

    # Test transform provider

    prompt = "this will be uppercase"

    transform_provider.complete(prompt, options)

    # Test async completion

    async def test_async() -> None:
        prompt = "Async completion test"

        await echo_provider.complete_async(prompt, options)

    asyncio.run(test_async())

    # Test streaming

    prompt = "This is a streaming test"

    chunks = []
    for chunk in echo_provider.complete_stream(prompt, options):
        chunks.append(chunk)

    # Test token counting

    test_texts = [
        "Short text",
        "This is a longer text with more words",
        "This is an even longer text that should have significantly more tokens than the previous examples",
    ]

    for text in test_texts:
        echo_provider.count_tokens(text, "echo-1")

    # Show provider features

    echo_provider.get_features()

    transform_provider.get_features()

    # Test error handling

    with contextlib.suppress(NotImplementedError):
        await echo_provider.structured_complete("Test", {}, options)

    # Compare with different configurations

    configs = [
        {"prefix": "[TEST] ", "simulate_latency_ms": 0},
        {"prefix": ">>> ", "simulate_latency_ms": 10},
        {"prefix": "", "simulate_latency_ms": 5},
    ]

    prompt = "Configuration test"

    for _i, config in enumerate(configs, 1):
        provider = EchoLLMProvider(**config)
        provider.complete(prompt, options)

    # Summary


if __name__ == "__main__":
    main()
