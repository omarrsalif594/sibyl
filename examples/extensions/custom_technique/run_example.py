#!/usr/bin/env python3
"""
Standalone example demonstrating custom reranking technique.

This script shows how to:
1. Register a custom technique
2. Use it programmatically
3. Compare different reranking strategies
"""

from simple_reranker import SimpleRerankingTechnique, register


def main() -> None:
    # Register the technique
    register()

    # Create technique instance
    technique = SimpleRerankingTechnique()

    # Prepare sample data
    search_results = [
        {"text": "Python is a great programming language for beginners", "score": 0.92},
        {"text": "Python is excellent for data science and ML", "score": 0.88},
        {
            "text": "Python has great libraries like NumPy and Pandas",
            "score": 0.85,
        },
        {"text": "Java is a statically typed object-oriented language", "score": 0.72},
        {"text": "JavaScript is used for web development", "score": 0.68},
        {"text": "Ruby is known for its elegant syntax", "score": 0.65},
        {"text": "Go is efficient for concurrent programming", "score": 0.62},
        {"text": "Rust provides memory safety without garbage collection", "score": 0.58},
    ]

    # Demonstrate score-based reranking

    score_based_results = technique.execute(
        input_data=search_results,
        subtechnique="score_based",
        config={"min_score": 0.7, "max_results": 5},
    )

    for _i, _result in enumerate(score_based_results, 1):
        pass

    # Demonstrate diversity reranking

    diversity_results = technique.execute(
        input_data=search_results,
        subtechnique="diversity",
        config={"diversity_weight": 0.5, "max_results": 5},
    )

    for _i, _result in enumerate(diversity_results, 1):
        pass

    # Compare strategies

    for _i, _result in enumerate(score_based_results[:3], 1):
        pass

    for _i, _result in enumerate(diversity_results[:3], 1):
        pass

    # Configuration validation

    try:
        technique.execute(
            input_data=search_results,
            subtechnique="score_based",
            config={"min_score": 1.5},  # Invalid
        )
    except ValueError:
        pass

    # Load from registry
    from sibyl.techniques.registry import get_technique  # noqa: PLC0415

    get_technique("simple_reranking")

    # Summary


if __name__ == "__main__":
    main()
