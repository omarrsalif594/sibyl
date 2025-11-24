# Training Toolkit for Local Specialists

A modular, reusable toolkit for training small specialist models using Unsloth on Apple Silicon M1 (32GB) or cloud GPUs.

## Important: This is a Toolkit, Not Trained Models

This toolkit provides the **infrastructure** for training specialists. It does **NOT** include pre-trained models. You need to run the training pipeline to create models for your specific domain.

## Overview

This toolkit is designed for:
- Training small specialists (1.5B - 3B parameters) using LoRA fine-tuning
- Working with generic synthetic data (easily replaceable with your domain data)
- Running on Apple Silicon M1 with 32GB RAM or cloud GPUs
- Easy extension to new domains and use cases

## Quick Start

### 1. Installation

```bash
# Install dependencies
pip install unsloth datasets pyyaml

# For Apple Silicon M1
pip install --upgrade torch torchvision torchaudio

# Verify installation
python -c "from unsloth import FastLanguageModel; print('Unsloth ready!')"
```

### 2. Explore the Toy Data

```bash
# View training data statistics
cd specialists/training_toolkit/pipeline
python data_extraction_toy.py
```

### 3. Train Your First Specialist

```bash
# Fast training (1.5B model, ~30-60 min on M1)
python pipeline/train_specialist.py \
  --config config/training/toy_fast_1_5b.yaml

# Deep training (3B model, ~2-4 hours on M1)
python pipeline/train_specialist.py \
  --config config/training/toy_deep_3b.yaml
```

### 4. Evaluate the Trained Model

```bash
python evaluation/test_suite_toy.py \
  --model-path outputs/toy_fast_1_5b/final_model \
  --test-data data/toy_assistant/test.jsonl \
  --save-path outputs/evaluation_results.json
```

### 5. Use the Trained Model

```python
from deployment.local_model_client_toy import run_toy_specialist

# Quick usage
response = run_toy_specialist(
    "Debug this code: for i in range(len(list)): print(list[i])",
    mode="fast"
)
print(response)
```

## Directory Structure

```
training_toolkit/
├── data/
│   └── toy_assistant/           # Toy synthetic data
│       ├── train.jsonl          # 117 training examples
│       ├── dev.jsonl            # 20 dev examples
│       └── test.jsonl           # 20 test examples
│
├── pipeline/
│   ├── data_extraction_toy.py   # Data loading (easy to extend)
│   ├── data_augmentation_toy.py # Deterministic augmentation
│   ├── train_specialist.py      # Single model training
│   └── train_all_specialists.py # Batch training orchestration
│
├── config/training/
│   ├── toy_fast_1_5b.yaml       # Fast training config (1.5B)
│   └── toy_deep_3b.yaml         # Deep training config (3B)
│
├── evaluation/
│   └── test_suite_toy.py        # Model evaluation suite
│
├── deployment/
│   └── local_model_client_toy.py # Local model inference client
│
└── README.md                     # This file
```

## Extending to Your Domain

### Step 1: Replace the Data

The easiest way to adapt this toolkit is to replace the toy data with your domain data:

**Option A: Use JSONL format (simplest)**

```bash
# Create your data in the same format
cat > data/my_domain/train.jsonl << 'EOF'
{"prompt": "Your question or task", "completion": "Expected answer"}
{"prompt": "Another question", "completion": "Another answer"}
EOF
```

**Option B: Extend the extraction script**

Edit `pipeline/data_extraction_toy.py`:

```python
class MyDomainExtractor(ToyDataExtractor):
    def load_jsonl_data(self, split: str):
        # Your custom data loading logic
        # Could be from:
        # - Database queries
        # - API calls
        # - CSV/Parquet files
        # - Web scraping
        # - Existing datasets
        return examples
```

### Step 2: Create Your Config

Copy and customize a training config:

```bash
cp config/training/toy_fast_1_5b.yaml config/training/my_domain_fast.yaml
```

Edit the paths:

```yaml
data:
  train_path: "data/my_domain/train.jsonl"
  dev_path: "data/my_domain/dev.jsonl"
  test_path: "data/my_domain/test.jsonl"

training:
  output_dir: "outputs/my_domain_fast"
```

### Step 3: Train on Your Data

```bash
python pipeline/train_specialist.py \
  --config config/training/my_domain_fast.yaml
```

### Step 4: Evaluate and Deploy

```bash
# Evaluate
python evaluation/test_suite_toy.py \
  --model-path outputs/my_domain_fast/final_model \
  --test-data data/my_domain/test.jsonl

# Use in code
from deployment.local_model_client_toy import SpecialistClient

client = SpecialistClient("outputs/my_domain_fast/final_model")
client.load()
response = client.generate("Your domain-specific prompt")
```

## Data Requirements

### Format

All data should be JSONL with this format:

```jsonl
{"prompt": "Input/question/task", "completion": "Expected output/answer"}
```

### Size Recommendations

| Dataset Size | Model Size | Expected Quality |
|--------------|------------|------------------|
| 50-100 examples | 1.5B | Basic/proof of concept |
| 100-500 examples | 1.5B | Good for simple tasks |
| 500-1000 examples | 3B | Good for complex tasks |
| 1000+ examples | 3B | Production quality |

### Quality over Quantity

- 100 high-quality examples > 1000 low-quality examples
- Ensure diversity in your examples
- Include edge cases and error scenarios
- Validate that completions are accurate and helpful

## Configuration Guide

### Model Selection

**toy_fast_1_5b.yaml** (Qwen2.5-1.5B-Instruct)
- Training time: 30-60 minutes on M1
- Memory usage: ~12GB
- Best for: Rapid prototyping, simple tasks, quick iterations
- LoRA rank: 16

**toy_deep_3b.yaml** (Qwen2.5-3B-Instruct)
- Training time: 2-4 hours on M1
- Memory usage: ~24-28GB
- Best for: Production deployment, complex tasks, higher quality
- LoRA rank: 32

### Memory Optimization for M1 32GB

If you run out of memory:

1. **Reduce batch size:**
```yaml
training:
  batch_size: 2  # Down from 4
  gradient_accumulation_steps: 8  # Up from 4 to maintain effective batch size
```

2. **Reduce sequence length:**
```yaml
training:
  max_seq_length: 1024  # Down from 2048
```

3. **Close other applications:**
- Close browser tabs
- Quit other memory-intensive apps
- Monitor with Activity Monitor

4. **Use 1.5B model instead of 3B:**
The 1.5B model requires less memory and is often sufficient for many tasks.

### Cloud GPU Training

For faster training on cloud GPUs (Colab, Paperspace, Lambda Labs):

```yaml
hardware:
  device: "cuda"  # Change from "mps"

training:
  batch_size: 8  # Can use larger batches
  bf16: true
  fp16: false
```

Expected times on T4 GPU: 10-20 minutes (1.5B), 30-60 minutes (3B)

## Extension Points

This toolkit is designed to be extended. Here are the key extension points:

### 1. Data Extraction (`pipeline/data_extraction_toy.py`)

```python
class ToyDataExtractor:
    def load_jsonl_data(self, split: str):
        # EXTENSION POINT: Replace with your data source
        # - Database queries
        # - API calls
        # - CSV/Parquet files
        # - Custom formats
        pass

    def extract_examples(self, split: str, filter_fn=None):
        # EXTENSION POINT: Add domain-specific filtering
        # - Quality scores
        # - Deduplication
        # - Class balancing
        pass
```

### 2. Data Augmentation (`pipeline/data_augmentation_toy.py`)

```python
class ToyDataAugmentor:
    def augment_example(self, example):
        # EXTENSION POINT: Add advanced augmentation
        # - LLM-based paraphrasing
        # - Backtranslation
        # - Domain-specific transformations
        pass
```

### 3. Training (`pipeline/train_specialist.py`)

```python
class SpecialistTrainer:
    def load_model(self):
        # EXTENSION POINT: Different model architectures
        # - Different base models
        # - Custom quantization schemes
        pass

    def build_trainer(self, datasets):
        # EXTENSION POINT: Custom training logic
        # - Custom callbacks
        # - Different evaluation metrics
        # - Advanced learning rate schedules
        pass
```

### 4. Evaluation (`evaluation/test_suite_toy.py`)

```python
class ToySpecialistEvaluator:
    def evaluate_example(self, example):
        # EXTENSION POINT: Domain-specific metrics
        # - Semantic similarity (sentence-transformers)
        # - Task-specific accuracy
        # - Custom scoring functions
        pass
```

### 5. Deployment (`deployment/local_model_client_toy.py`)

```python
class SpecialistClient:
    def generate(self, prompt):
        # EXTENSION POINT: Production features
        # - Streaming generation
        # - Batch inference
        # - Response caching
        # - API wrapper (FastAPI/Flask)
        pass
```

## Training Tips for M1 32GB

### Before Training

1. **Monitor memory:** Open Activity Monitor to watch memory usage
2. **Close applications:** Free up RAM by closing unused apps
3. **Check disk space:** Training checkpoints need space (~5-10GB)
4. **Expect fan noise:** M1 will work hard, fan will run

### During Training

1. **Let it run:** Don't interrupt or put Mac to sleep
2. **Monitor logs:** Check for out-of-memory errors
3. **Be patient:** First epoch is slowest (model loading/compilation)
4. **Power connected:** Keep MacBook plugged in

### If Training Fails

1. **Out of memory?** Reduce batch_size or max_seq_length
2. **Too slow?** Use toy_fast_1_5b instead of toy_deep_3b
3. **Errors?** Check that Unsloth is properly installed
4. **Still issues?** Try training on cloud GPU (Colab free tier)

## Typical Training Times

### Apple M1 32GB (with default configs)

| Model | Dataset Size | Time | Memory Usage |
|-------|--------------|------|--------------|
| 1.5B Fast | 100 examples | 30-60 min | ~12GB |
| 1.5B Fast | 500 examples | 1-2 hours | ~12GB |
| 3B Deep | 100 examples | 2-4 hours | ~24GB |
| 3B Deep | 500 examples | 4-8 hours | ~24GB |

### Cloud GPU (T4)

| Model | Dataset Size | Time | Cost (est.) |
|-------|--------------|------|-------------|
| 1.5B Fast | 100 examples | 10-20 min | $0.10-0.20 |
| 1.5B Fast | 500 examples | 30-60 min | $0.30-0.60 |
| 3B Deep | 100 examples | 30-60 min | $0.30-0.60 |
| 3B Deep | 500 examples | 1-2 hours | $0.60-1.20 |

## Model Selection Decision Tree

```
1. What's your use case?
   ├─ Quick prototype/testing → 1.5B Fast
   ├─ Simple domain (code formatting, basic Q&A) → 1.5B Fast
   └─ Complex domain (debugging, reasoning) → 3B Deep

2. What's your hardware?
   ├─ M1 32GB
   │  ├─ Want it done today? → 1.5B Fast
   │  └─ Can wait overnight? → 3B Deep
   └─ Cloud GPU (T4/A10)
      └─ Both work well, 3B Deep recommended

3. How much data do you have?
   ├─ < 100 examples → 1.5B Fast (prevent overfitting)
   ├─ 100-500 examples → Either works
   └─ 500+ examples → 3B Deep (better capacity)
```

## Toy Data Details

The included toy synthetic data consists of:

- **117 training examples:** Generic debugging, SQL, Python, JavaScript tasks
- **20 dev examples:** Validation set for hyperparameter tuning
- **20 test examples:** Held-out evaluation set

### Example Formats

```jsonl
{"prompt": "Debug this Python code: x = [1, 2, 3]\nfor i in range(4):\n    print(x[i])", "completion": "The issue is an IndexError. The list has 3 elements (indices 0-2), but the loop tries to access index 3. Fix: Change range(4) to range(3) or range(len(x))."}

{"prompt": "Given a table with columns [id, name, score], write a query to find the top 3 highest scores", "completion": "SELECT id, name, score FROM table_name ORDER BY score DESC LIMIT 3;"}

{"prompt": "Write a function to check if a string is a palindrome", "completion": "def is_palindrome(s):\n    s = s.lower().replace(' ', '')\n    return s == s[::-1]\n\nThis removes spaces, converts to lowercase, and compares the string with its reverse."}
```

### Data Characteristics

- **No real business data:** All examples are generic
- **No specific vendors/companies:** Can be used anywhere
- **Diverse tasks:** Debugging, SQL, algorithms, optimization
- **Clear completions:** Each has a specific, correct answer
- **Varying lengths:** From short queries to longer explanations

## Testing Without Training

You can test the toolkit without actually training models:

```bash
# Test data pipeline
python pipeline/data_extraction_toy.py

# Test data augmentation
python pipeline/data_augmentation_toy.py

# Test training setup (uses mock model)
pytest tests/specialists/test_training_toolkit_scaffolding.py

# Test evaluation (uses mock model)
python evaluation/test_suite_toy.py \
  --model-path outputs/toy_fast_1_5b/final_model \
  --test-data data/toy_assistant/test.jsonl \
  --use-mock

# Test deployment client (mock mode)
python deployment/local_model_client_toy.py \
  --prompt "Debug this code: ..."
```

## Advanced Usage

### Training Multiple Specialists

```bash
# Train all configured specialists
python pipeline/train_all_specialists.py

# Train specific specialists
python pipeline/train_all_specialists.py \
  --specialists toy_fast_1_5b toy_deep_3b

# Dry run (test orchestration without training)
python pipeline/train_all_specialists.py --dry-run
```

### Custom Generation Parameters

```python
from deployment.local_model_client_toy import SpecialistClient, GenerationConfig

client = SpecialistClient("outputs/toy_fast_1_5b/final_model")
client.load()

# Custom generation config
config = GenerationConfig(
    max_new_tokens=256,
    temperature=0.5,  # More deterministic
    top_p=0.95,
    repetition_penalty=1.2
)

response = client.generate("Your prompt", config=config)
```

### Batch Evaluation

```python
from evaluation.test_suite_toy import ToySpecialistEvaluator

evaluator = ToySpecialistEvaluator("outputs/toy_fast_1_5b/final_model")
evaluator.load_model()

# Evaluate on test set
results = evaluator.evaluate(
    "data/toy_assistant/test.jsonl",
    max_examples=50,  # Limit for quick test
    save_path="outputs/eval_results.json"
)

print(f"Average exact match: {results.metrics['avg_exact_match']:.2%}")
print(f"Average token overlap: {results.metrics['avg_token_overlap']:.2%}")
```

## Troubleshooting

### Common Issues

**"Unsloth not installed"**
- Solution: `pip install unsloth`
- Alternative: Tests/scripts will use mock mode automatically

**"Out of memory" during training**
- Reduce `batch_size` in config
- Reduce `max_seq_length` in config
- Close other applications
- Use 1.5B model instead of 3B

**Training is very slow**
- First epoch is always slowest (compilation)
- Check Activity Monitor - CPU/GPU should be active
- Consider cloud GPU for faster training

**Model generation is nonsense**
- May need more training data
- May need longer training (more epochs)
- May need better quality data
- Try 3B model instead of 1.5B

**"Model not found" when deploying**
- Check that training completed successfully
- Verify model path points to `final_model` directory
- Check that model files exist in the directory

### Getting Help

1. Check the extension point comments in source files
2. Review error messages carefully (they're descriptive)
3. Try with mock mode first to isolate issues
4. Test with toy data before using custom data

## Performance Expectations

### What This Toolkit Can Do

- Train specialists for well-defined tasks
- Handle domains with clear input/output patterns
- Work with 50-1000 training examples
- Run on consumer hardware (M1 Mac)
- Provide reasonable inference speed (1-2 seconds)

### What This Toolkit Cannot Do

- Replace large foundation models for general tasks
- Handle extremely complex reasoning without data
- Train on massive datasets (100K+ examples)
- Achieve GPT-4 level quality with small models
- Work miracles with poor quality data

### Realistic Quality Expectations

| Data Quality | Data Size | Model | Expected Performance |
|--------------|-----------|-------|---------------------|
| High | 50-100 | 1.5B | Good for simple tasks |
| High | 100-500 | 1.5B | Good for most tasks |
| High | 500-1000 | 3B | Very good, production-ready |
| Medium | 100-500 | 3B | Acceptable for many tasks |
| Low | Any | Any | Poor, fix data first |

## License and Attribution

This toolkit is provided as-is for the Sibyl project. Feel free to adapt and extend for your needs.

**Models used:**
- Qwen2.5-1.5B-Instruct (Alibaba Cloud)
- Qwen2.5-3B-Instruct (Alibaba Cloud)

**Key dependencies:**
- Unsloth: Efficient LoRA fine-tuning
- HuggingFace Transformers & Datasets
- PyTorch

## Next Steps

1. **Explore the toy data:** Understand the format and examples
2. **Run a quick training:** Start with toy_fast_1_5b to validate setup
3. **Prepare your domain data:** Collect and format your examples
4. **Create your config:** Copy and customize a training config
5. **Train your specialist:** Run training on your data
6. **Evaluate and iterate:** Test performance, improve data if needed
7. **Deploy locally:** Integrate into your application

## Summary

This toolkit provides everything you need to train local specialists:
- ✓ Modular, extensible architecture
- ✓ Works on M1 Macs and cloud GPUs
- ✓ Complete pipeline: data → training → evaluation → deployment
- ✓ Clear extension points for customization
- ✓ Generic toy data to start experimenting
- ✓ Comprehensive documentation

**Remember:** This is a toolkit, not trained models. You provide the data and domain expertise, the toolkit provides the infrastructure.

Happy training!
