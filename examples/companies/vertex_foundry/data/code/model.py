"""
Simple neural network model for image classification.
"""

from typing import Any

import torch.nn.functional as F
from torch import nn


class ConvNet(nn.Module):
    """Convolutional Neural Network for CIFAR-10 classification."""

    def __init__(self, num_classes: Any = 10, dropout_rate: Any = 0.5) -> None:
        super().__init__()
        self.conv1 = nn.Conv2d(3, 32, kernel_size=3, padding=1)
        self.conv2 = nn.Conv2d(32, 64, kernel_size=3, padding=1)
        self.conv3 = nn.Conv2d(64, 128, kernel_size=3, padding=1)

        self.pool = nn.MaxPool2d(2, 2)
        self.dropout = nn.Dropout(dropout_rate)

        self.fc1 = nn.Linear(128 * 4 * 4, 256)
        self.fc2 = nn.Linear(256, num_classes)

    def forward(self, x: Any) -> Any:
        """Forward pass through the network."""
        x = self.pool(F.relu(self.conv1(x)))
        x = self.pool(F.relu(self.conv2(x)))
        x = self.pool(F.relu(self.conv3(x)))

        x = x.view(-1, 128 * 4 * 4)
        x = self.dropout(F.relu(self.fc1(x)))
        return self.fc2(x)

    def get_num_params(self) -> Any:
        """Return the number of parameters in the model."""
        return sum(p.numel() for p in self.parameters() if p.requires_grad)
