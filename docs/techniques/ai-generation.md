# AI Generation Techniques

Complete guide to AI text generation, consensus, and validation techniques in Sibyl.

## Overview

The AI Generation shop provides techniques for generating high-quality text responses using Large Language Models (LLMs). It includes three main techniques:

1. **Generation** - Core text generation
2. **Consensus** - Multi-model consensus for reliability
3. **Validation** - Quality and accuracy verification

## Generation Technique

### Standard Generation

Basic LLM completion with full control over parameters.

```yaml
pipelines:
  simple_generation:
    shop: ai_generation
    steps:
      - use: ai_generation.generation
        config:
          subtechnique: standard
          provider: primary
          temperature: 0.7
          max_tokens: 2000
          top_p: 1.0
          frequency_penalty: 0.0
          presence_penalty: 0.0
          stop_sequences: ["\n\n", "---"]
```

**Parameters**:

- **temperature** (0.0-2.0): Controls randomness
  - `0.0`: Deterministic, same output every time
  - `0.7`: Balanced creativity and coherence (recommended)
  - `1.5+`: Very creative, less predictable

- **max_tokens**: Maximum response length
  - Short answers: `500-1000`
  - Medium answers: `1000-2000`
  - Long-form: `2000-4000`

- **top_p** (0.0-1.0): Nucleus sampling
  - `1.0`: Consider all tokens (default)
  - `0.9`: Only top 90% probability mass (more focused)

- **frequency_penalty** (-2.0 to 2.0): Reduce repetition
  - `0.0`: No penalty
  - `0.5`: Moderate penalty (recommended)
  - `1.0+`: Strong penalty against repetition

- **presence_penalty** (-2.0 to 2.0): Encourage topic diversity
  - `0.0`: No penalty
  - `0.5`: Moderate penalty
  - `1.0+`: Strong penalty for repeated topics

**Example**:
```python
result = await pipeline.execute({
    "prompt": "Explain quantum computing in simple terms",
    "temperature": 0.7,
    "max_tokens": 1000
})

print(result["text"])
# Output: "Quantum computing is a revolutionary approach..."
```

### Streaming Generation

Stream responses in real-time for better UX.

```yaml
steps:
  - use: ai_generation.generation
    config:
      subtechnique: streaming
      provider: primary
      temperature: 0.7
      chunk_size: 10                   # Tokens per chunk
```

**Benefits**:
- Immediate user feedback
- Better perceived performance
- Can start processing before completion

**Example**:
```python
async for chunk in pipeline.execute_stream({
    "prompt": "Write a short story about AI"
}):
    print(chunk["text"], end="", flush=True)
# Output: "Once upon a time..." (streamed word by word)
```

### Structured Generation

Generate JSON or structured output.

```yaml
steps:
  - use: ai_generation.generation
    config:
      subtechnique: structured
      provider: primary
      temperature: 0.3                 # Lower temp for structured output
      output_schema:
        type: object
        properties:
          title:
            type: string
          summary:
            type: string
          tags:
            type: array
            items:
              type: string
          sentiment:
            type: string
            enum: ["positive", "negative", "neutral"]
        required: ["title", "summary"]
```

**Example**:
```python
result = await pipeline.execute({
    "text": "This product is amazing! Best purchase ever.",
    "task": "analyze"
})

print(result["structured_output"])
# Output:
# {
#   "title": "Product Review Analysis",
#   "summary": "Highly positive review praising the product",
#   "tags": ["product", "review", "positive"],
#   "sentiment": "positive"
# }
```

### Chat-Based Generation

Multi-turn conversation generation.

```yaml
steps:
  - use: ai_generation.generation
    config:
      subtechnique: chat
      provider: primary
      temperature: 0.8
      system_prompt: |
        You are a helpful AI assistant that answers questions clearly and concisely.
        Always cite your sources when providing factual information.
```

**Example**:
```python
result = await pipeline.execute({
    "messages": [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is the capital of France?"},
        {"role": "assistant", "content": "The capital of France is Paris."},
        {"role": "user", "content": "What's the population?"}
    ]
})

print(result["message"]["content"])
# Output: "Paris has a population of approximately 2.2 million..."
```

### Instruction-Following Generation

Optimized for following specific instructions.

```yaml
steps:
  - use: ai_generation.generation
    config:
      subtechnique: instruct
      provider: primary
      temperature: 0.5
      instruction_template: |
        Task: {task}
        Input: {input}
        Instructions: {instructions}
        Output:
```

**Example**:
```python
result = await pipeline.execute({
    "task": "summarize",
    "input": "Long article text here...",
    "instructions": "Summarize in 3 bullet points"
})
# Output: Well-structured bullet point summary
```

## Prompt Engineering Best Practices

### Clear Instructions

```yaml
# Bad
prompt: "Tell me about AI"

# Good
prompt: |
  Explain artificial intelligence to a beginner.
  Include:
  1. A simple definition
  2. Three real-world applications
  3. One potential concern

  Keep the explanation under 200 words.
```

### Few-Shot Examples

```yaml
prompt: |
  Extract key information from customer reviews.

  Example 1:
  Review: "Great product, fast shipping!"
  Output: {"sentiment": "positive", "mentions": ["product quality", "shipping speed"]}

  Example 2:
  Review: "Product broke after one week."
  Output: {"sentiment": "negative", "mentions": ["durability"]}

  Now extract from this review:
  Review: {review}
  Output:
```

### Role Prompting

```yaml
system_prompt: |
  You are an expert software architect with 20 years of experience.
  You provide clear, practical advice on system design.
  You always consider scalability, maintainability, and cost.

user_prompt: "How should I design a real-time chat application?"
```

### Chain-of-Thought

```yaml
prompt: |
  Question: {question}

  Let's solve this step by step:
  1. First, identify the key components
  2. Then, analyze each component
  3. Finally, synthesize the answer

  Answer:
```

## Consensus Technique

Generate multiple responses and reach consensus for higher reliability.

### Majority Vote

Most common consensus method.

```yaml
steps:
  - use: ai_generation.consensus
    config:
      subtechnique: majority_vote
      num_generations: 3               # Generate 3 responses
      providers: [primary, fallback]   # Use multiple providers
      temperature: 0.7
      agreement_threshold: 0.66        # 2/3 must agree
```

**How it works**:
1. Generate 3 independent responses
2. Compare responses for agreement
3. Return majority answer
4. If no majority, return most common or fail

**Example**:
```python
result = await pipeline.execute({
    "question": "What is 2+2?"
})

# Generation 1: "4"
# Generation 2: "4"
# Generation 3: "4"
# Consensus: "4" (unanimous)
```

**Best for**: Factual questions, mathematical problems, classification

### Weighted Consensus

Weight responses by model confidence.

```yaml
steps:
  - use: ai_generation.consensus
    config:
      subtechnique: weighted
      num_generations: 3
      providers:
        - name: primary
          weight: 1.0                  # GPT-4 gets full weight
        - name: fallback
          weight: 0.8                  # Claude gets 80% weight
        - name: emergency
          weight: 0.5                  # Llama2 gets 50% weight
      temperature: 0.7
```

**How it works**:
1. Generate responses from multiple providers
2. Weight each response by provider weight
3. Combine responses with weights
4. Return highest-weighted answer

**Best for**: When provider quality varies

### LLM Judge

Use an LLM to judge which response is best.

```yaml
steps:
  - use: ai_generation.consensus
    config:
      subtechnique: llm_judge
      num_generations: 3
      judge_provider: primary
      judge_criteria:
        - accuracy
        - clarity
        - completeness
        - conciseness
```

**How it works**:
1. Generate multiple candidate responses
2. LLM judge evaluates each against criteria
3. Return highest-scored response

**Judge prompt**:
```yaml
judge_template: |
  Evaluate these responses to the question: "{question}"

  Response 1: {response_1}
  Response 2: {response_2}
  Response 3: {response_3}

  Criteria:
  - Accuracy (0-10)
  - Clarity (0-10)
  - Completeness (0-10)

  Which response is best? Explain why.
```

**Best for**: Complex questions, subjective evaluation

### Ensemble

Combine multiple responses into a single answer.

```yaml
steps:
  - use: ai_generation.consensus
    config:
      subtechnique: ensemble
      num_generations: 3
      combination_method: synthesis    # synthesis, concatenate, summarize
      provider: primary
```

**How it works**:
1. Generate multiple responses
2. Use LLM to synthesize best answer from all responses
3. Return synthesized answer

**Synthesis prompt**:
```yaml
ensemble_template: |
  Here are multiple answers to the question: "{question}"

  Answer 1: {answer_1}
  Answer 2: {answer_2}
  Answer 3: {answer_3}

  Synthesize the best answer incorporating insights from all responses:
```

**Best for**: Research questions, comprehensive answers

## Validation Technique

Verify generated responses for quality and accuracy.

### Fact Checking

Verify factual accuracy against source documents.

```yaml
steps:
  - use: ai_generation.validation
    config:
      subtechnique: fact_check
      provider: primary
      strict_mode: true                # Reject if any facts wrong
      source_documents: "${retrieved_docs}"
```

**How it works**:
1. Extract claims from generated answer
2. Check each claim against source documents
3. Flag unsupported claims
4. Return validation results

**Example**:
```python
result = await pipeline.execute({
    "answer": "Paris is the capital of France with a population of 10 million.",
    "sources": ["Paris has approximately 2.2 million residents."]
})

print(result["validation"])
# {
#   "factual": false,
#   "errors": ["Population claim incorrect: 10M vs 2.2M"],
#   "supported_claims": ["Paris is the capital of France"],
#   "unsupported_claims": ["population of 10 million"]
# }
```

### Citation Validation

Ensure all facts are properly cited.

```yaml
steps:
  - use: ai_generation.validation
    config:
      subtechnique: citation
      require_citations: true
      citation_format: "[1]"           # [1], (Source: X), etc.
      min_citations: 2
```

**How it works**:
1. Parse citations from answer
2. Verify each citation references a source
3. Check all facts have citations
4. Return validation results

**Example**:
```python
result = await pipeline.execute({
    "answer": "Paris is the capital [1] with 2.2M people [2].",
    "sources": [
        {"id": 1, "text": "Paris is France's capital"},
        {"id": 2, "text": "Paris: 2.2 million residents"}
    ]
})

print(result["validation"])
# {
#   "citations_found": 2,
#   "citations_valid": 2,
#   "all_facts_cited": true,
#   "valid": true
# }
```

### Hallucination Detection

Detect AI hallucinations (made-up facts).

```yaml
steps:
  - use: ai_generation.validation
    config:
      subtechnique: hallucination
      threshold: 0.8                   # Confidence threshold
      provider: primary
      check_against: sources           # sources, knowledge_base, web
```

**Detection methods**:

1. **Source-based**: Check if facts appear in sources
2. **Self-consistency**: Generate multiple times, check consistency
3. **LLM-based**: Ask LLM to verify its own claims

**Example**:
```python
result = await pipeline.execute({
    "answer": "The Eiffel Tower was built in 1889 and is 324m tall.",
    "sources": ["The Eiffel Tower was completed in 1889."]
})

print(result["validation"])
# {
#   "hallucinations": [
#     {
#       "claim": "324m tall",
#       "confidence": 0.3,  # Low confidence - likely hallucination
#       "in_sources": false
#     }
#   ],
#   "score": 0.7  # Overall hallucination score
# }
```

### Consistency Validation

Check internal consistency of the answer.

```yaml
steps:
  - use: ai_generation.validation
    config:
      subtechnique: consistency
      provider: primary
```

**Checks**:
- No contradictory statements
- Logical flow
- Consistent tone and style
- Consistent terminology

**Example**:
```python
result = await pipeline.execute({
    "answer": """
    Python is a compiled language. It's great for beginners because
    it's interpreted and doesn't need compilation.
    """
})

print(result["validation"])
# {
#   "consistent": false,
#   "contradictions": [
#     "Claims both compiled and interpreted"
#   ]
# }
```

## Complete Generation Pipelines

### High-Quality Q&A Pipeline

```yaml
pipelines:
  quality_qa:
    shop: ai_generation
    steps:
      # 1. Generate with consensus
      - use: ai_generation.consensus
        config:
          subtechnique: majority_vote
          num_generations: 3
          temperature: 0.7

      # 2. Fact check
      - use: ai_generation.validation
        config:
          subtechnique: fact_check
          source_documents: "${context_docs}"

      # 3. Citation check
      - use: ai_generation.validation
        config:
          subtechnique: citation
          require_citations: true

      # 4. Hallucination detection
      - use: ai_generation.validation
        config:
          subtechnique: hallucination
          threshold: 0.8
```

### Multi-Model Ensemble

```yaml
pipelines:
  ensemble_generation:
    shop: ai_generation
    steps:
      # Generate from multiple models
      - use: ai_generation.generation
        config:
          provider: openai_gpt4
        output: response_gpt4

      - use: ai_generation.generation
        config:
          provider: anthropic_claude
        output: response_claude

      - use: ai_generation.generation
        config:
          provider: local_llama
        output: response_llama

      # Synthesize best answer
      - use: ai_generation.consensus
        config:
          subtechnique: llm_judge
          responses:
            - ${response_gpt4}
            - ${response_claude}
            - ${response_llama}
```

### Iterative Refinement

```yaml
pipelines:
  iterative_generation:
    shop: ai_generation
    steps:
      # 1. Initial generation
      - use: ai_generation.generation
        config:
          temperature: 0.8
        output: draft_1

      # 2. Critique
      - use: ai_generation.generation
        config:
          prompt: |
            Review this answer and suggest improvements:
            {draft_1}

            Critique:
        output: critique

      # 3. Refine
      - use: ai_generation.generation
        config:
          prompt: |
            Original answer: {draft_1}
            Critique: {critique}

            Improved answer:
          temperature: 0.7
        output: draft_2

      # 4. Final validation
      - use: ai_generation.validation
        config:
          subtechnique: fact_check
```

## Provider-Specific Configurations

### OpenAI (GPT-4)

```yaml
providers:
  llm:
    gpt4:
      kind: openai
      model: gpt-4
      api_key: "${OPENAI_API_KEY}"

steps:
  - use: ai_generation.generation
    config:
      provider: gpt4
      temperature: 0.7
      max_tokens: 2000
      top_p: 1.0
      frequency_penalty: 0.0
      presence_penalty: 0.0
```

**Best for**: Complex reasoning, coding, analysis

**Cost**: ~$0.03 per 1K tokens (expensive)

### Anthropic (Claude)

```yaml
providers:
  llm:
    claude:
      kind: anthropic
      model: claude-3-opus-20240229
      api_key: "${ANTHROPIC_API_KEY}"

steps:
  - use: ai_generation.generation
    config:
      provider: claude
      temperature: 1.0
      max_tokens: 4096
```

**Best for**: Long context (200K tokens), safety, nuanced writing

**Cost**: ~$0.015 per 1K tokens (moderate)

### Ollama (Local)

```yaml
providers:
  llm:
    local:
      kind: ollama
      base_url: "http://localhost:11434"
      model: llama2

steps:
  - use: ai_generation.generation
    config:
      provider: local
      temperature: 0.7
      num_ctx: 4096                    # Context window
```

**Best for**: Privacy, offline, zero cost

**Cost**: $0 (but requires local compute)

## Performance Optimization

### Caching

```yaml
shops:
  infrastructure:
    config:
      caching:
        enabled: true
        backend: redis
        ttl: 3600

pipelines:
  cached_generation:
    steps:
      # Check cache first
      - use: infrastructure.caching
        config:
          cache_key: "generation:${prompt}"

      # Generate if not cached
      - use: ai_generation.generation
        config:
          provider: primary
        cache: true
```

### Batch Processing

```yaml
steps:
  - use: ai_generation.generation
    config:
      batch_size: 10                   # Process 10 prompts at once
      parallel: true
      max_concurrent: 5
```

### Prompt Compression

```yaml
steps:
  # Compress long context
  - use: infrastructure.compression
    config:
      method: summarization
      target_length: 2000

  # Generate with compressed context
  - use: ai_generation.generation
    config:
      context: "${compressed_context}"
```

## Cost Management

### Token Budgets

```yaml
budget:
  max_tokens_per_request: 4000
  max_tokens_per_day: 100000
  max_cost_usd: 50.0

steps:
  - use: ai_generation.generation
    config:
      max_tokens: 2000
      stop_on_budget_exceeded: true
```

### Model Selection

```yaml
# Use cheaper model for simple queries
pipelines:
  simple_qa:
    steps:
      - use: ai_generation.generation
        config:
          provider: gpt35_turbo         # $0.002/1K tokens

# Use expensive model for complex queries
pipelines:
  complex_analysis:
    steps:
      - use: ai_generation.generation
        config:
          provider: gpt4                # $0.03/1K tokens
```

## Troubleshooting

### Low-Quality Outputs

**Solutions**:
1. Lower temperature: `0.7` → `0.3`
2. Add few-shot examples
3. Use more specific instructions
4. Try different model
5. Use consensus for reliability

### Hallucinations

**Solutions**:
1. Enable hallucination detection
2. Require citations
3. Use fact-checking validation
4. Lower temperature
5. Add source documents to prompt

### High Latency

**Solutions**:
1. Reduce `max_tokens`
2. Use streaming
3. Enable caching
4. Use faster model (GPT-3.5 vs GPT-4)
5. Batch requests

### High Costs

**Solutions**:
1. Use cheaper models
2. Enable caching
3. Reduce `max_tokens`
4. Compress prompts
5. Set budget limits

## Further Reading

- **[RAG Pipeline](rag-pipeline.md)** - Retrieval-augmented generation
- **[Technique Catalog](catalog.md)** - All techniques
- **[Provider Configuration](../workspaces/providers.md)** - LLM setup
- **[Prompt Engineering Guide](../advanced/prompt-engineering.md)** - Advanced prompting

---

**Previous**: [RAG Pipeline](rag-pipeline.md) | **Next**: [Workflow Orchestration](workflow-orchestration.md)
