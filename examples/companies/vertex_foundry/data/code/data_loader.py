"""
Data loading and preprocessing utilities.
"""

from typing import Any

import torch
from torch.utils.data import DataLoader, Dataset


class CIFAR10Dataset(Dataset):
    """Mock CIFAR-10 dataset for training."""

    def __init__(self, split: Any = "train", transform: Any = None) -> None:
        self.split = split
        self.transform = transform

        # Mock dataset sizes
        if split == "train":
            self.size = 50000
        elif split == "val":
            self.size = 10000
        else:
            self.size = 10000

    def __len__(self) -> int:
        return self.size

    def __getitem__(self, idx: Any) -> Any:
        """Return a single sample."""
        # Generate synthetic data for demonstration
        image = torch.randn(3, 32, 32)
        label = idx % 10

        if self.transform:
            image = self.transform(image)

        return image, label


def get_data_loaders(batch_size=32, num_workers: Any = 4) -> Any:
    """Create train and validation data loaders."""

    train_dataset = CIFAR10Dataset(split="train")
    val_dataset = CIFAR10Dataset(split="val")

    train_loader = DataLoader(
        train_dataset, batch_size=batch_size, shuffle=True, num_workers=num_workers, pin_memory=True
    )

    val_loader = DataLoader(
        val_dataset, batch_size=batch_size, shuffle=False, num_workers=num_workers, pin_memory=True
    )

    return train_loader, val_loader


def calculate_mean_std(loader) -> Any:
    """Calculate dataset mean and std for normalization."""
    mean = 0.0
    std = 0.0
    total_samples = 0

    for images, _ in loader:
        batch_samples = images.size(0)
        images = images.view(batch_samples, images.size(1), -1)
        mean += images.mean(2).sum(0)
        std += images.std(2).sum(0)
        total_samples += batch_samples

    mean /= total_samples
    std /= total_samples

    return mean, std
