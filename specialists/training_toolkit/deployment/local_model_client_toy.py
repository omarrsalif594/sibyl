"""
Local model client for deploying trained specialist models.

This module provides a simple client interface for loading and using
trained specialist models locally.

Usage:
    from local_model_client_toy import run_toy_specialist, SpecialistClient

    # Quick usage
    response = run_toy_specialist("Debug this code: ...", mode="fast")

    # Advanced usage
    client = SpecialistClient("outputs/toy_fast_1_5b/final_model")
    client.load()
    response = client.generate("Your prompt here")

Extension Points:
- Add batched inference
- Implement model caching
- Add API server wrapper (FastAPI, Flask)
- Integrate with model serving platforms
"""

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


@dataclass
class GenerationConfig:
    """Configuration for text generation."""

    max_new_tokens: int = 512
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 50
    repetition_penalty: float = 1.1
    do_sample: bool = True


class SpecialistClient:
    """
    Client for interacting with trained specialist models.

    Provides a simple interface for loading models and generating responses.
    Supports both real models (with Unsloth) and mock mode (for testing).
    """

    def __init__(self, model_path: str, use_mock: bool = False, device: str = "mps") -> None:
        """
        Initialize specialist client.

        Args:
            model_path: Path to trained model checkpoint
            use_mock: If True, use mock model (for testing)
            device: Device to load model on ("mps", "cuda", "cpu")
        """
        self.model_path = Path(model_path)
        self.use_mock = use_mock or not self.model_path.exists()
        self.device = device
        self.model = None
        self.tokenizer = None
        self.is_loaded = False

        if self.use_mock:
            pass

    def load(self) -> None:
        """
        Load the model into memory.

        Extension Point:
            - Add model quantization options
            - Implement model pooling for multiple specialists
            - Add warmup for first inference
        """
        if self.is_loaded:
            return

        if self.use_mock:
            self.model = MockModel()
            self.tokenizer = MockTokenizer()
            self.is_loaded = True
            return

        try:
            from unsloth import FastLanguageModel  # noqa: PLC0415 - optional dependency

        except ImportError:
            self.use_mock = True
            self.model = MockModel()
            self.tokenizer = MockTokenizer()
            self.is_loaded = True
            return

        try:
            self.model, self.tokenizer = FastLanguageModel.from_pretrained(
                model_name=str(self.model_path),
                max_seq_length=2048,
                dtype=None,
                load_in_4bit=True,
            )

            # Set to inference mode
            FastLanguageModel.for_inference(self.model)

            self.is_loaded = True

        except Exception:
            self.use_mock = True
            self.model = MockModel()
            self.tokenizer = MockTokenizer()
            self.is_loaded = True

    def unload(self) -> None:
        """
        Unload model from memory.

        Extension Point:
            - Add proper cleanup for GPU memory
            - Implement model swapping for multiple specialists
        """
        if not self.is_loaded:
            return

        self.model = None
        self.tokenizer = None
        self.is_loaded = False

        # Clear GPU cache if applicable
        try:
            import torch  # noqa: PLC0415 - optional dependency

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:
            pass

    def generate(
        self, prompt: str, config: GenerationConfig | None = None, return_metadata: bool = False
    ) -> str:
        """
        Generate a response for the given prompt.

        Args:
            prompt: Input prompt
            config: Generation configuration (uses defaults if None)
            return_metadata: If True, return dict with response and metadata

        Returns:
            Generated response text (or dict if return_metadata=True)

        Extension Point:
            - Add streaming generation
            - Implement prompt caching
            - Add response validation
        """
        if not self.is_loaded:
            self.load()

        if config is None:
            config = GenerationConfig()

        # Mock response
        if self.use_mock:
            response = self._generate_mock_response(prompt)
            if return_metadata:
                return {
                    "response": response,
                    "inference_time_seconds": 0.1,
                    "tokens_generated": len(response.split()),
                    "model_path": str(self.model_path),
                    "is_mock": True,
                }
            return response

        # Format prompt
        formatted_prompt = self._format_prompt(prompt)

        # Generate
        start_time = time.time()

        inputs = self.tokenizer(formatted_prompt, return_tensors="pt")

        outputs = self.model.generate(
            **inputs,
            max_new_tokens=config.max_new_tokens,
            temperature=config.temperature,
            top_p=config.top_p,
            top_k=config.top_k,
            repetition_penalty=config.repetition_penalty,
            do_sample=config.do_sample,
        )

        response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)

        # Extract just the response part
        if "### Response:" in response:
            response = response.split("### Response:")[-1].strip()

        inference_time = time.time() - start_time

        if return_metadata:
            return {
                "response": response,
                "inference_time_seconds": inference_time,
                "tokens_generated": len(outputs[0]),
                "model_path": str(self.model_path),
                "is_mock": False,
            }

        return response

    def _format_prompt(self, prompt: str) -> str:
        """
        Format prompt according to training template.

        Extension Point:
            - Add different prompt templates for different use cases
            - Implement few-shot prompting
            - Add system messages
        """
        return f"### Instruction:\n{prompt}\n\n### Response:\n"

    def _generate_mock_response(self, prompt: str) -> str:
        """Generate mock response for testing."""
        # Simple mock responses based on keywords
        prompt_lower = prompt.lower()

        if "debug" in prompt_lower or "fix" in prompt_lower:
            return "This appears to be a debugging task. In a real deployment, the trained model would analyze the code and provide specific fixes."

        if "sql" in prompt_lower or "query" in prompt_lower:
            return "This is a SQL-related question. The trained model would generate appropriate SQL queries based on the requirements."

        if "optimize" in prompt_lower or "improve" in prompt_lower:
            return "This is an optimization task. The trained model would suggest specific improvements and best practices."

        if "write" in prompt_lower or "implement" in prompt_lower:
            return "This is a code generation task. The trained model would provide a complete implementation with explanations."

        return "This is a mock response. In production, the trained specialist model would provide a detailed, contextual answer based on its training."


# Mock classes for testing
class MockModel:
    """Mock model for testing."""

    def generate(self, **kwargs) -> Any:
        return [[1, 2, 3]]


class MockTokenizer:
    """Mock tokenizer for testing."""

    def __call__(self, text: Any, **kwargs):
        return {"input_ids": [[1, 2, 3]]}

    def decode(self, tokens: Any, **kwargs) -> str:
        return "### Response:\nMock response for testing"


# Convenience functions
_SPECIALIST_CACHE: dict[str, SpecialistClient] = {}


def get_specialist_client(
    mode: Literal["fast", "deep"] = "fast", force_reload: bool = False
) -> SpecialistClient:
    """
    Get or create a specialist client.

    Args:
        mode: Which specialist to use ("fast" or "deep")
        force_reload: If True, reload model even if cached

    Returns:
        SpecialistClient instance

    Extension Point:
        - Add automatic model discovery
        - Implement smart routing based on query complexity
        - Add load balancing for multiple models
    """
    # Determine model path based on mode
    toolkit_root = Path(__file__).parent.parent
    if mode == "fast":
        model_path = toolkit_root / "outputs" / "toy_fast_1_5b" / "final_model"
    elif mode == "deep":
        model_path = toolkit_root / "outputs" / "toy_deep_3b" / "final_model"
    else:
        msg = f"Unknown mode: {mode}. Use 'fast' or 'deep'"
        raise ValueError(msg)

    cache_key = str(model_path)

    # Check cache
    if cache_key in _SPECIALIST_CACHE and not force_reload:
        return _SPECIALIST_CACHE[cache_key]

    # Create new client
    client = SpecialistClient(str(model_path))
    _SPECIALIST_CACHE[cache_key] = client

    return client


def run_toy_specialist(
    prompt: str, mode: Literal["fast", "deep"] = "fast", return_metadata: bool = False
) -> str:
    """
    Quick function to run a toy specialist model.

    This is the simplest way to use trained specialists.

    Args:
        prompt: Input prompt/question
        mode: Which specialist to use ("fast" = 1.5B, "deep" = 3B)
        return_metadata: If True, return dict with response and metadata

    Returns:
        Generated response (or dict if return_metadata=True)

    Example:
        >>> response = run_toy_specialist("Debug this Python code: ...", mode="fast")
        >>> print(response)

    Extension Point:
        - Add automatic mode selection based on prompt complexity
        - Implement prompt preprocessing
        - Add response post-processing
    """
    client = get_specialist_client(mode=mode)

    if not client.is_loaded:
        client.load()

    return client.generate(prompt, return_metadata=return_metadata)


def clear_specialist_cache() -> None:
    """Clear all cached specialist clients."""
    global _SPECIALIST_CACHE
    for client in _SPECIALIST_CACHE.values():
        client.unload()
    _SPECIALIST_CACHE.clear()


# Example usage
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Test specialist model client")
    parser.add_argument(
        "--prompt",
        type=str,
        default="Debug this Python code: for i in range(len(list)): print(list[i])",
        help="Prompt to test with",
    )
    parser.add_argument(
        "--mode", type=str, choices=["fast", "deep"], default="fast", help="Which specialist to use"
    )
    parser.add_argument(
        "--model-path", type=str, default=None, help="Custom model path (overrides mode)"
    )

    args = parser.parse_args()

    if args.model_path:
        # Use custom model path
        client = SpecialistClient(args.model_path)
        client.load()
        result = client.generate(args.prompt, return_metadata=True)
    else:
        # Use convenience function
        result = run_toy_specialist(args.prompt, mode=args.mode, return_metadata=True)
