"""
Data extraction module for toy synthetic data.

This module provides a simple interface for loading synthetic training data.
It's designed to be easily extended for real data sources.

Extension Points:
- Replace load_jsonl_data() with your own data loader
- Add custom filtering/preprocessing in extract_examples()
- Implement domain-specific extraction logic
"""

import json
from pathlib import Path
from typing import Any


class ToyDataExtractor:
    """
    Extracts and loads toy synthetic data for training specialists.

    This class provides a template for data extraction that can be adapted
    for real data sources (databases, APIs, file systems, etc.).
    """

    def __init__(self, data_dir: str) -> None:
        """
        Initialize the data extractor.

        Args:
            data_dir: Path to directory containing JSONL data files
        """
        self.data_dir = Path(data_dir)

    def load_jsonl_data(self, split: str = "train") -> list[dict[str, str]]:
        """
        Load data from JSONL file.

        Args:
            split: Data split to load (train, dev, or test)

        Returns:
            List of dictionaries with 'prompt' and 'completion' keys

        Extension Point:
            Replace this method to load from your data source:
            - Database queries
            - API calls
            - CSV/Parquet files
            - Custom formats
        """
        file_path = self.data_dir / f"{split}.jsonl"

        if not file_path.exists():
            msg = f"Data file not found: {file_path}"
            raise FileNotFoundError(msg)

        examples = []
        with open(file_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    examples.append(json.loads(line))

        return examples

    def extract_examples(
        self,
        split: str = "train",
        max_examples: int | None = None,
        filter_fn: callable | None = None,
    ) -> list[dict[str, str]]:
        """
        Extract training examples with optional filtering.

        Args:
            split: Data split to extract (train, dev, or test)
            max_examples: Maximum number of examples to return
            filter_fn: Optional function to filter examples

        Returns:
            List of training examples

        Extension Point:
            Add domain-specific filtering:
            - Filter by quality scores
            - Remove duplicates
            - Balance class distributions
            - Apply domain-specific rules
        """
        examples = self.load_jsonl_data(split)

        # Apply custom filtering if provided
        if filter_fn:
            examples = [ex for ex in examples if filter_fn(ex)]

        # Limit number of examples if specified
        if max_examples:
            examples = examples[:max_examples]

        return examples

    def validate_example(self, example: dict[str, str]) -> bool:
        """
        Validate that an example has required fields.

        Args:
            example: Dictionary containing training example

        Returns:
            True if example is valid, False otherwise

        Extension Point:
            Add custom validation:
            - Check prompt/completion length
            - Validate data quality
            - Check for required metadata
            - Domain-specific constraints
        """
        required_fields = ["prompt", "completion"]

        # Check required fields exist
        if not all(field in example for field in required_fields):
            return False

        # Check fields are non-empty strings
        return all(
            isinstance(example[field], str) and example[field].strip() for field in required_fields
        )

    def get_statistics(self, split: str = "train") -> dict[str, Any]:
        """
        Get statistics about the dataset.

        Args:
            split: Data split to analyze

        Returns:
            Dictionary containing dataset statistics
        """
        examples = self.load_jsonl_data(split)

        if not examples:
            return {"total_examples": 0}

        prompt_lengths = [len(ex["prompt"]) for ex in examples]
        completion_lengths = [len(ex["completion"]) for ex in examples]

        return {
            "total_examples": len(examples),
            "avg_prompt_length": sum(prompt_lengths) / len(prompt_lengths),
            "avg_completion_length": sum(completion_lengths) / len(completion_lengths),
            "max_prompt_length": max(prompt_lengths),
            "max_completion_length": max(completion_lengths),
            "min_prompt_length": min(prompt_lengths),
            "min_completion_length": min(completion_lengths),
        }


def load_toy_data(
    data_dir: str, split: str = "train", max_examples: int | None = None
) -> list[dict[str, str]]:
    """
    Convenience function to load toy data.

    Args:
        data_dir: Path to data directory
        split: Data split to load
        max_examples: Maximum number of examples

    Returns:
        List of training examples
    """
    extractor = ToyDataExtractor(data_dir)
    return extractor.extract_examples(split=split, max_examples=max_examples)


# Example usage and extension templates
if __name__ == "__main__":
    # Example: Load training data
    data_dir = Path(__file__).parent.parent / "data" / "toy_assistant"
    extractor = ToyDataExtractor(data_dir)

    # Get statistics
    for split in ["train", "dev", "test"]:
        stats = extractor.get_statistics(split)

    # Example: Custom filtering
    def filter_sql_examples(example: dict[str, str]) -> bool:
        """Filter to only SQL-related examples"""
        return "SQL" in example["prompt"] or "query" in example["prompt"].lower()

    sql_examples = extractor.extract_examples(split="train", filter_fn=filter_sql_examples)

    # Example: Load limited data for quick testing
    quick_test = extractor.extract_examples(split="train", max_examples=10)
