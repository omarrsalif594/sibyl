"""
Evaluation test suite for trained specialist models.

This module provides tools to evaluate trained models on test data
and generate comprehensive metrics reports.

Usage:
    python test_suite_toy.py --model-path outputs/toy_fast_1_5b/final_model --test-data data/toy_assistant/test.jsonl

Extension Points:
- Add domain-specific evaluation metrics
- Implement custom scoring functions
- Add visualization of results
- Integrate with experiment tracking (MLflow, W&B, etc.)
"""

import argparse
import json
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class EvaluationResult:
    """Results from evaluating a model on test data."""

    model_path: str
    test_data_path: str
    total_examples: int
    evaluation_time_seconds: float
    metrics: dict[str, float]
    timestamp: str

    # Per-example results (optional)
    example_results: list[dict[str, Any]] | None = None


class ToySpecialistEvaluator:
    """
    Evaluator for toy specialist models.

    Provides basic evaluation metrics and can be extended
    for production use with more sophisticated metrics.
    """

    def __init__(self, model_path: str, use_mock: bool = False) -> None:
        """
        Initialize evaluator.

        Args:
            model_path: Path to trained model checkpoint
            use_mock: If True, use mock model (for testing without dependencies)
        """
        self.model_path = Path(model_path)
        self.use_mock = use_mock or not self.model_path.exists()
        self.model = None
        self.tokenizer = None

        if self.use_mock:
            pass

    def load_model(self) -> None:
        """
        Load trained model for evaluation.

        Extension Point:
            - Add support for different model formats
            - Implement model quantization for inference
            - Add GPU/CPU selection logic
        """
        if self.use_mock:
            self.model = MockModel()
            self.tokenizer = MockTokenizer()
            return

        try:
            from unsloth import FastLanguageModel  # noqa: PLC0415 - optional dependency

        except ImportError:
            self.use_mock = True
            self.model = MockModel()
            self.tokenizer = MockTokenizer()
            return

        try:
            self.model, self.tokenizer = FastLanguageModel.from_pretrained(
                model_name=str(self.model_path),
                max_seq_length=2048,
                dtype=None,
                load_in_4bit=True,
            )
        except Exception:
            self.use_mock = True
            self.model = MockModel()
            self.tokenizer = MockTokenizer()

    def load_test_data(self, test_data_path: str) -> list[dict[str, str]]:
        """
        Load test data from JSONL file.

        Args:
            test_data_path: Path to test data JSONL file

        Returns:
            List of test examples
        """
        test_path = Path(test_data_path)

        if not test_path.exists():
            msg = f"Test data not found: {test_path}"
            raise FileNotFoundError(msg)

        examples = []
        with open(test_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    examples.append(json.loads(line))

        return examples

    def generate_response(self, prompt: str, max_length: int = 512) -> str:
        """
        Generate model response for a prompt.

        Args:
            prompt: Input prompt
            max_length: Maximum response length

        Returns:
            Generated response text

        Extension Point:
            - Add temperature/sampling parameters
            - Implement beam search
            - Add response post-processing
        """
        if self.use_mock:
            # Mock response for testing
            return f"[Mock response to: {prompt[:50]}...]"

        # Format prompt
        formatted_prompt = f"### Instruction:\n{prompt}\n\n### Response:\n"

        # Tokenize
        inputs = self.tokenizer(formatted_prompt, return_tensors="pt")

        # Generate
        outputs = self.model.generate(
            **inputs,
            max_new_tokens=max_length,
            temperature=0.7,
            top_p=0.9,
            do_sample=True,
        )

        # Decode
        response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)

        # Extract just the response part (after "### Response:")
        if "### Response:" in response:
            response = response.split("### Response:")[-1].strip()

        return response

    def evaluate_example(
        self, example: dict[str, str], metrics_to_compute: list[str] | None = None
    ) -> dict[str, Any]:
        """
        Evaluate model on a single example.

        Args:
            example: Test example with 'prompt' and 'completion'
            metrics_to_compute: List of metrics to compute

        Returns:
            Dictionary with evaluation results for this example

        Extension Point:
            - Add semantic similarity metrics
            - Implement domain-specific scoring
            - Add error analysis categories
        """
        if metrics_to_compute is None:
            metrics_to_compute = ["exact_match", "length_ratio", "has_output"]

        prompt = example["prompt"]
        expected = example["completion"]

        # Generate response
        start_time = time.time()
        generated = self.generate_response(prompt)
        inference_time = time.time() - start_time

        # Compute metrics
        results = {
            "prompt": prompt[:100] + "..." if len(prompt) > 100 else prompt,  # noqa: PLR2004
            "expected": expected[:100] + "..." if len(expected) > 100 else expected,  # noqa: PLR2004
            "generated": generated[:100] + "..." if len(generated) > 100 else generated,  # noqa: PLR2004
            "inference_time_seconds": inference_time,
            "metrics": {},
        }

        # Exact match
        if "exact_match" in metrics_to_compute:
            results["metrics"]["exact_match"] = float(
                generated.strip().lower() == expected.strip().lower()
            )

        # Length ratio (how close is generated length to expected)
        if "length_ratio" in metrics_to_compute:
            expected_len = len(expected.split())
            generated_len = len(generated.split())
            ratio = (
                min(expected_len, generated_len) / max(expected_len, generated_len)
                if max(expected_len, generated_len) > 0
                else 0.0
            )
            results["metrics"]["length_ratio"] = ratio

        # Has output (did model generate anything?)
        if "has_output" in metrics_to_compute:
            results["metrics"]["has_output"] = float(len(generated.strip()) > 0)

        # Token overlap (simple word-level)
        if "token_overlap" in metrics_to_compute:
            expected_tokens = set(expected.lower().split())
            generated_tokens = set(generated.lower().split())

            if len(expected_tokens) > 0:
                overlap = len(expected_tokens & generated_tokens) / len(expected_tokens)
            else:
                overlap = 0.0

            results["metrics"]["token_overlap"] = overlap

        return results

    def evaluate(
        self, test_data_path: str, max_examples: int | None = None, save_path: str | None = None
    ) -> EvaluationResult:
        """
        Evaluate model on test dataset.

        Args:
            test_data_path: Path to test data
            max_examples: Maximum number of examples to evaluate (None = all)
            save_path: Path to save results JSON

        Returns:
            EvaluationResult object
        """

        # Load model
        if self.model is None:
            self.load_model()

        # Load test data
        test_examples = self.load_test_data(test_data_path)

        if max_examples:
            test_examples = test_examples[:max_examples]

        # Evaluate each example
        start_time = time.time()
        example_results = []

        for i, example in enumerate(test_examples, 1):
            if i % 10 == 0 or i == 1:
                pass

            result = self.evaluate_example(example)
            example_results.append(result)

        elapsed_time = time.time() - start_time

        # Aggregate metrics
        aggregated_metrics = self._aggregate_metrics(example_results)

        # Create result object
        eval_result = EvaluationResult(
            model_path=str(self.model_path),
            test_data_path=test_data_path,
            total_examples=len(test_examples),
            evaluation_time_seconds=elapsed_time,
            metrics=aggregated_metrics,
            timestamp=datetime.now().isoformat(),
            example_results=example_results,
        )

        # Print results
        self._print_results(eval_result)

        # Save if requested
        if save_path:
            self._save_results(eval_result, save_path)

        return eval_result

    def _aggregate_metrics(self, example_results: list[dict[str, Any]]) -> dict[str, float]:
        """Aggregate metrics across all examples."""
        if not example_results:
            return {}

        # Get all metric names
        metric_names = set()
        for result in example_results:
            metric_names.update(result["metrics"].keys())

        # Compute averages
        aggregated = {}
        for metric_name in metric_names:
            values = [r["metrics"].get(metric_name, 0.0) for r in example_results]
            aggregated[f"avg_{metric_name}"] = sum(values) / len(values) if values else 0.0

        # Add timing metrics
        inference_times = [r["inference_time_seconds"] for r in example_results]
        aggregated["avg_inference_time_seconds"] = sum(inference_times) / len(inference_times)
        aggregated["total_inference_time_seconds"] = sum(inference_times)

        return aggregated

    def _print_results(self, result: EvaluationResult) -> None:
        """Print evaluation results."""

        for metric_name, _value in sorted(result.metrics.items()):
            if metric_name.startswith("avg_"):
                metric_name[4:].replace("_", " ").title()

    def _save_results(self, result: EvaluationResult, save_path: str) -> None:
        """Save evaluation results to JSON file."""
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)

        with open(save_path, "w") as f:
            json.dump(asdict(result), f, indent=2)


# Mock classes for testing
class MockModel:
    """Mock model for testing."""

    def generate(self, **kwargs) -> Any:
        return [[1, 2, 3]]  # Mock token IDs


class MockTokenizer:
    """Mock tokenizer for testing."""

    def __call__(self, text: Any, **kwargs):
        return {"input_ids": [[1, 2, 3]]}

    def decode(self, tokens: Any, **kwargs) -> str:
        return "Mock response for testing"


def main() -> None:
    """Main entry point for evaluation script."""
    parser = argparse.ArgumentParser(description="Evaluate a trained specialist model")
    parser.add_argument(
        "--model-path", type=str, required=True, help="Path to trained model checkpoint"
    )
    parser.add_argument("--test-data", type=str, required=True, help="Path to test data JSONL file")
    parser.add_argument(
        "--max-examples", type=int, default=None, help="Maximum number of examples to evaluate"
    )
    parser.add_argument(
        "--save-path", type=str, default=None, help="Path to save evaluation results JSON"
    )
    parser.add_argument(
        "--use-mock", action="store_true", help="Use mock model (for testing without dependencies)"
    )

    args = parser.parse_args()

    # Create evaluator
    evaluator = ToySpecialistEvaluator(model_path=args.model_path, use_mock=args.use_mock)

    # Run evaluation
    evaluator.evaluate(
        test_data_path=args.test_data, max_examples=args.max_examples, save_path=args.save_path
    )


if __name__ == "__main__":
    main()
