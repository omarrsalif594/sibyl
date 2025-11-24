"""
Data augmentation module for training data.

This module provides simple deterministic augmentation techniques.
It includes stubs for more advanced LLM-based augmentation.

Extension Points:
- Add domain-specific augmentation rules
- Integrate with LLM APIs for semantic paraphrasing
- Implement backtranslation or other NLP techniques
"""

import random
import re
from copy import deepcopy


class ToyDataAugmentor:
    """
    Augments training data using deterministic transformations.

    This class provides basic augmentation without external dependencies.
    Can be extended with LLM-based augmentation for production use.
    """

    def __init__(self, seed: int = 42) -> None:
        """
        Initialize the augmentor.

        Args:
            seed: Random seed for reproducibility
        """
        self.seed = seed
        random.seed(seed)

    def augment_example(
        self, example: dict[str, str], num_variations: int = 1, techniques: list[str] | None = None
    ) -> list[dict[str, str]]:
        """
        Generate augmented variations of a single example.

        Args:
            example: Original example with 'prompt' and 'completion'
            num_variations: Number of variations to generate
            techniques: List of augmentation techniques to apply
                       Options: ['paraphrase', 'synonym', 'reorder']

        Returns:
            List of augmented examples (includes original)

        Extension Point:
            Add custom augmentation techniques:
            - LLM-based paraphrasing
            - Backtranslation
            - Domain-specific transformations
            - Context injection
        """
        if techniques is None:
            techniques = ["paraphrase", "synonym"]

        variations = [example]  # Include original

        for _ in range(num_variations):
            augmented = deepcopy(example)

            # Apply random technique
            # S311: Using random for data augmentation (not security-sensitive)
            technique = random.choice(techniques)

            if technique == "paraphrase":
                augmented = self._simple_paraphrase(augmented)
            elif technique == "synonym":
                augmented = self._simple_synonym_replacement(augmented)
            elif technique == "reorder":
                augmented = self._simple_reorder(augmented)

            variations.append(augmented)

        return variations

    def _simple_paraphrase(self, example: dict[str, str]) -> dict[str, str]:
        """
        Apply simple paraphrasing transformations.

        Extension Point: Replace with LLM-based paraphrasing
        """
        prompt = example["prompt"]

        # Simple deterministic paraphrasing rules
        paraphrase_rules = [
            (r"\bfix this\b", "correct this"),
            (r"\bfix\b", "repair"),
            (r"\bdebug\b", "troubleshoot"),
            (r"\bwhy doesn\'t this work\b", "why is this failing"),
            (r"\bwhat\'s wrong with\b", "what is the issue with"),
            (r"\boptimize\b", "improve"),
            (r"\bwrite code to\b", "implement"),
            (r"\bgiven a table\b", "given the table"),
            (r"\bwrite a function\b", "create a function"),
        ]

        for pattern, replacement in paraphrase_rules:
            prompt = re.sub(pattern, replacement, prompt, flags=re.IGNORECASE, count=1)

        return {"prompt": prompt, "completion": example["completion"]}

    def _simple_synonym_replacement(self, example: dict[str, str]) -> dict[str, str]:
        """
        Replace words with simple synonyms.

        Extension Point: Use WordNet or word embeddings for better synonyms
        """
        prompt = example["prompt"]

        # Simple synonym mappings
        synonyms = {
            "function": "method",
            "code": "script",
            "error": "issue",
            "problem": "issue",
            "query": "statement",
            "list": "array",
            "variable": "identifier",
        }

        words = prompt.split()
        for i, word in enumerate(words):
            word_lower = word.lower().strip(".,!?;:")  # noqa: PLR2004
            # S311: Using random for data augmentation (not security-sensitive)
            if word_lower in synonyms and random.random() < 0.3:  # 30% chance
                # Preserve original case
                replacement = synonyms[word_lower]
                if word[0].isupper():
                    replacement = replacement.capitalize()
                words[i] = word.replace(word_lower, replacement)

        return {"prompt": " ".join(words), "completion": example["completion"]}

    def _simple_reorder(self, example: dict[str, str]) -> dict[str, str]:
        """
        Reorder parts of the prompt if possible.

        Extension Point: Use syntax parsing for smarter reordering
        """
        prompt = example["prompt"]

        # Only works for compound questions
        if " and " in prompt.lower() or " or " in prompt.lower():
            # Split on conjunctions and reverse (simple approach)  # noqa: PLR2004
            parts = re.split(r"\s+(and|or)\s+", prompt, maxsplit=1, flags=re.IGNORECASE)
            if len(parts) >= 3:
                # parts = [before, conjunction, after]
                prompt = f"{parts[2]} {parts[1]} {parts[0]}"

        return {"prompt": prompt, "completion": example["completion"]}

    def augment_dataset(
        self,
        examples: list[dict[str, str]],
        augmentation_factor: float = 0.5,
        techniques: list[str] | None = None,
    ) -> list[dict[str, str]]:
        """
        Augment entire dataset.

        Args:
            examples: List of original examples
            augmentation_factor: Fraction of dataset to augment (0.0 to 1.0)
            techniques: Augmentation techniques to use

        Returns:
            Original examples plus augmented variations
        """
        augmented_dataset = list(examples)  # Start with originals

        num_to_augment = int(len(examples) * augmentation_factor)
        examples_to_augment = random.sample(examples, num_to_augment)

        for example in examples_to_augment:
            variations = self.augment_example(example, num_variations=1, techniques=techniques)
            # Add variations (excluding original which is already in dataset)
            augmented_dataset.extend(variations[1:])

        return augmented_dataset


class LLMAugmentor:
    """
    Stub for LLM-based augmentation.

    This class provides a template for integrating with LLM APIs
    for high-quality paraphrasing and augmentation.

    Extension Point: Integrate with OpenAI, Anthropic, or local models
    """

    def __init__(self, api_key: str | None = None, model: str = "gpt-3.5-turbo") -> None:
        """
        Initialize LLM augmentor.

        Args:
            api_key: API key for LLM service (not used in stub)
            model: Model to use for augmentation
        """
        self.api_key = api_key
        self.model = model
        self._enabled = False  # Disabled by default in stub

    def paraphrase_prompt(self, prompt: str) -> str:
        """
        Paraphrase prompt using LLM.

        Extension Point: Implement actual LLM call
        """
        if not self._enabled:
            msg = (
                "LLM augmentation is not enabled. "
                "Implement API integration or use ToyDataAugmentor for deterministic augmentation."
            )
            raise NotImplementedError(msg)

        # Stub implementation
        # TODO: Integrate with LLM API
        # Example:
        # response = openai.ChatCompletion.create(
        #     model=self.model,
        #     messages=[{
        #         "role": "user",
        #         "content": f"Paraphrase the following while preserving meaning: {prompt}"
        #     }]
        # )
        # return response.choices[0].message.content

        return prompt

    def generate_similar_example(self, example: dict[str, str]) -> dict[str, str]:
        """
        Generate similar example using LLM.

        Extension Point: Use LLM to generate semantically similar examples
        """
        if not self._enabled:
            msg = "LLM augmentation not enabled"
            raise NotImplementedError(msg)

        # Stub - would call LLM to generate similar example
        return example


# Convenience functions
def augment_toy_data(
    examples: list[dict[str, str]], augmentation_factor: float = 0.5, seed: int = 42
) -> list[dict[str, str]]:
    """
    Convenience function to augment toy data.

    Args:
        examples: Original training examples
        augmentation_factor: How much to augment (0.0-1.0)
        seed: Random seed

    Returns:
        Augmented dataset
    """
    augmentor = ToyDataAugmentor(seed=seed)
    return augmentor.augment_dataset(examples, augmentation_factor)


# Example usage
if __name__ == "__main__":
    # Example data
    example = {
        "prompt": "Debug this Python code: x = [1, 2, 3]\nfor i in range(4):\n    print(x[i])",
        "completion": "The issue is an IndexError. The list has 3 elements.",
    }

    # Test augmentation
    augmentor = ToyDataAugmentor(seed=42)

    variations = augmentor.augment_example(example, num_variations=3)
    for _i, _var in enumerate(variations[1:], 1):
        pass

    # Test dataset augmentation
    examples = [example] * 5
    augmented = augmentor.augment_dataset(examples, augmentation_factor=0.4)
