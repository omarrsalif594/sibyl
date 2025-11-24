"""
Training script for specialist models using Unsloth.

This script provides a complete training pipeline that works with
toy synthetic data and can be easily adapted for real domains.

Supports:
- Apple Silicon M1 optimization
- Remote GPU training (Colab, Paperspace, Lambda Labs)
- LoRA fine-tuning for memory efficiency
- Configurable via YAML files
"""

import logging
import time
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ModelConfig(BaseModel):
    """Model configuration with validation."""

    base_model: str = Field(..., description="Base model name or path")
    lora_rank: int = Field(..., gt=0, le=256, description="LoRA rank (1-256)")
    lora_alpha: int = Field(..., gt=0, description="LoRA alpha parameter")
    lora_dropout: float = Field(..., ge=0.0, le=1.0, description="LoRA dropout (0-1)")
    target_modules: list[str] = Field(..., min_length=1, description="Target modules for LoRA")
    load_in_4bit: bool = Field(default=True, description="Load model in 4-bit quantization")


class TrainingSettings(BaseModel):
    """Training settings with validation."""

    num_epochs: int = Field(..., gt=0, le=100, description="Number of training epochs")
    batch_size: int = Field(..., gt=0, le=128, description="Training batch size")
    gradient_accumulation_steps: int = Field(..., gt=0, description="Gradient accumulation steps")
    learning_rate: float = Field(..., gt=0, description="Learning rate")
    max_seq_length: int = Field(..., gt=0, le=32768, description="Maximum sequence length")
    output_dir: str = Field(..., description="Output directory for model checkpoints")


class DataConfig(BaseModel):
    """Data configuration with validation."""

    train_path: str = Field(..., description="Path to training data")
    dev_path: str = Field(..., description="Path to development/validation data")
    test_path: str = Field(..., description="Path to test data")
    prompt_template: str = Field(..., description="Prompt template for formatting examples")


class HardwareConfig(BaseModel):
    """Hardware configuration."""

    device: str = Field(default="mps", description="Device to use (mps, cuda, cpu)")


class TrainingConfig(BaseModel):
    """Complete training configuration with validation."""

    model: ModelConfig
    training: TrainingSettings
    data: DataConfig
    hardware: HardwareConfig = Field(default_factory=HardwareConfig)

    @classmethod
    def from_yaml(cls, config_path: str) -> "TrainingConfig":
        """Load and validate configuration from YAML file."""
        logger.info("Loading configuration from %s", config_path)

        with open(config_path) as f:
            config_dict = yaml.safe_load(f)

        try:
            config = cls(**config_dict)
            logger.info("Configuration validated successfully")
            return config
        except Exception as e:
            logger.exception("Configuration validation failed: %s", e)
            raise


class SpecialistTrainer:
    """
    Trainer for specialist models using Unsloth.

    This class handles model initialization, data loading, and training.
    Designed to work on M1 Macs and cloud GPUs.
    """

    def __init__(self, config: TrainingConfig, toolkit_root: Path | None = None) -> None:
        """
        Initialize the trainer.

        Args:
            config: Training configuration
            toolkit_root: Root directory of training toolkit (for resolving relative paths)
        """
        self.config = config
        self.toolkit_root = toolkit_root or Path(__file__).parent.parent
        self.model = None
        self.tokenizer = None
        self.trainer = None

    def load_model(self) -> None:
        """
        Load and prepare model for training.

        Extension Point:
            - Add custom model architectures
            - Integrate different quantization schemes
            - Support for different LoRA configurations
        """
        try:
            # Lazy import to avoid dependency errors in tests
            from unsloth import FastLanguageModel  # noqa: PLC0415 - optional dependency

        except ImportError:
            logger.warning("Unsloth not installed. This is expected in test mode.")
            logger.info("To actually train, install: pip install unsloth")
            # Return mock objects for testing
            self.model = MockModel()
            self.tokenizer = MockTokenizer()
            return

        logger.info("Loading model: %s", self.config.model.base_model)

        self.model, self.tokenizer = FastLanguageModel.from_pretrained(
            model_name=self.config.model.base_model,
            max_seq_length=self.config.training.max_seq_length,
            dtype=None,  # Auto-detect
            load_in_4bit=self.config.model.load_in_4bit,
        )

        # Add LoRA adapters
        self.model = FastLanguageModel.get_peft_model(
            self.model,
            r=self.config.model.lora_rank,
            target_modules=self.config.model.target_modules,
            lora_alpha=self.config.model.lora_alpha,
            lora_dropout=self.config.model.lora_dropout,
            bias="none",
            use_gradient_checkpointing=True,
        )

        logger.info("Model loaded successfully")

    def load_data(self) -> dict[str, Any]:
        """
        Load and prepare training data.

        Returns:
            Dictionary containing train, dev, and test datasets

        Extension Point:
            - Add custom data preprocessing
            - Implement data filtering/sampling
            - Add domain-specific formatting
        """
        try:
            from .data_extraction_toy import ToyDataExtractor  # noqa: PLC0415 - optional dependency

        except ImportError:
            # Fall back to absolute import when run as script
            from data_extraction_toy import ToyDataExtractor  # noqa: PLC0415

        # Resolve data paths
        data_dir = self.toolkit_root / Path(self.config.data.train_path).parent

        extractor = ToyDataExtractor(str(data_dir))

        # Load datasets
        train_data = extractor.extract_examples(split="train")
        dev_data = extractor.extract_examples(split="dev")
        test_data = extractor.extract_examples(split="test")

        logger.info("Loaded %s training examples", len(train_data))
        logger.info("Loaded %s dev examples", len(dev_data))
        logger.info("Loaded %s test examples", len(test_data))

        # Format data with prompt template
        train_formatted = self._format_data(train_data)
        dev_formatted = self._format_data(dev_data)
        test_formatted = self._format_data(test_data)

        return {"train": train_formatted, "dev": dev_formatted, "test": test_formatted}

    def _format_data(self, examples: list[dict[str, str]]) -> list[dict[str, str]]:
        """Format examples using prompt template."""
        formatted = []
        for ex in examples:
            text = self.config.data.prompt_template.format(
                prompt=ex["prompt"], completion=ex["completion"]
            )
            formatted.append({"text": text})
        return formatted

    def build_trainer(self, datasets: dict[str, Any]) -> None:
        """
        Build the Unsloth/HuggingFace trainer.

        Args:
            datasets: Dictionary with train/dev/test datasets

        Extension Point:
            - Add custom training callbacks
            - Implement custom evaluation metrics
            - Add learning rate scheduling
        """
        try:
            from datasets import Dataset  # noqa: PLC0415 - optional dependency
            from unsloth import (  # noqa: PLC0415 - optional dependency
                UnslothTrainer,
                UnslothTrainingArguments,
            )

        except ImportError:
            logger.warning("Unsloth/datasets not installed. Using mock trainer.")
            self.trainer = MockTrainer()
            return

        # Convert to HuggingFace datasets
        train_dataset = Dataset.from_list(datasets["train"])
        eval_dataset = Dataset.from_list(datasets["dev"])

        # Create output directory
        output_dir = self.toolkit_root / self.config.training.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        # Training arguments
        training_args = UnslothTrainingArguments(
            output_dir=str(output_dir),
            num_train_epochs=self.config.training.num_epochs,
            per_device_train_batch_size=self.config.training.batch_size,
            gradient_accumulation_steps=self.config.training.gradient_accumulation_steps,
            learning_rate=self.config.training.learning_rate,
            logging_steps=10,
            save_steps=100,
            evaluation_strategy="steps",
            eval_steps=50,
            save_total_limit=3,
            bf16=True,
            optim="adamw_8bit",
            weight_decay=0.01,
            lr_scheduler_type="cosine",
            warmup_ratio=0.03,
            seed=42,
        )

        # Create trainer
        self.trainer = UnslothTrainer(
            model=self.model,
            tokenizer=self.tokenizer,
            train_dataset=train_dataset,
            eval_dataset=eval_dataset,
            args=training_args,
        )

        logger.info("Trainer initialized")

    def train(self) -> None:
        """
        Execute the training loop.

        Extension Point:
            - Add custom training callbacks
            - Implement early stopping
            - Add checkpointing logic
        """
        if self.trainer is None:
            msg = "Trainer not initialized. Call build_trainer() first."
            raise RuntimeError(msg)

        logger.info("=" * 60)
        logger.info("Starting training...")
        logger.info("=" * 60)

        start_time = time.time()

        # Run training
        self.trainer.train()

        elapsed = time.time() - start_time
        logger.info("Training completed in %s minutes", elapsed / 60)

    def save_model(self, save_path: str | None = None) -> None:
        """
        Save the trained model.

        Args:
            save_path: Path to save model (defaults to config output_dir)
        """
        if save_path is None:
            save_path = self.toolkit_root / self.config.training.output_dir / "final_model"
        else:
            save_path = Path(save_path)

        save_path.mkdir(parents=True, exist_ok=True)

        logger.info("Saving model to: %s", save_path)

        if hasattr(self.model, "save_pretrained"):
            self.model.save_pretrained(str(save_path))
            self.tokenizer.save_pretrained(str(save_path))
            logger.info("Model saved successfully")
        else:
            logger.warning("Mock model - skipping save")

    def run_full_pipeline(self) -> None:
        """Run the complete training pipeline."""
        logger.info("=" * 60)
        logger.info("Specialist Training Pipeline")
        logger.info("=" * 60)
        logger.info("Config: %s", self.config.model.base_model)
        logger.info("Output: %s", self.config.training.output_dir)
        logger.info("=" * 60)

        # Step 1: Load model
        logger.info("Step 1: Loading model...")
        self.load_model()

        # Step 2: Load data
        logger.info("Step 2: Loading data...")
        datasets = self.load_data()

        # Step 3: Build trainer
        logger.info("Step 3: Building trainer...")
        self.build_trainer(datasets)

        # Step 4: Train
        logger.info("Step 4: Training...")
        self.train()

        # Step 5: Save
        logger.info("Step 5: Saving model...")
        self.save_model()

        logger.info("=" * 60)
        logger.info("Pipeline completed successfully!")
        logger.info("=" * 60)


# Mock classes for testing without dependencies
class MockModel:
    """Mock model for testing."""

    def save_pretrained(self, path: Any) -> None:
        pass


class MockTokenizer:
    """Mock tokenizer for testing."""

    def save_pretrained(self, path: Any) -> None:
        pass


class MockTrainer:
    """Mock trainer for testing."""

    def train(self) -> None:
        logger.warning("Mock training (dependencies not installed)")
        logger.info("Install unsloth to run actual training")


def main() -> None:
    """Main entry point for training script."""
    import argparse  # noqa: PLC0415 - can be moved to top

    parser = argparse.ArgumentParser(description="Train a specialist model")
    parser.add_argument(
        "--config", type=str, required=True, help="Path to training config YAML file"
    )
    parser.add_argument(
        "--toolkit-root", type=str, default=None, help="Root directory of training toolkit"
    )

    args = parser.parse_args()

    # Load config
    config = TrainingConfig.from_yaml(args.config)

    # Set toolkit root
    toolkit_root = Path(args.toolkit_root) if args.toolkit_root else Path(__file__).parent.parent

    # Create trainer and run
    trainer = SpecialistTrainer(config, toolkit_root)
    trainer.run_full_pipeline()


if __name__ == "__main__":
    main()
