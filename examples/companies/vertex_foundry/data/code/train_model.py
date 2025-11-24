"""
Training script for ConvNet on CIFAR-10.
Contains a subtle bug in the loss function configuration.
"""

import argparse
import json
import os
from datetime import datetime
from typing import Any

import torch
from data_loader import get_data_loaders
from model import ConvNet
from torch import nn, optim
from torch.utils.tensorboard import SummaryWriter


def train_epoch(
    model, train_loader: Any, criterion: Any, optimizer: Any, device: Any, epoch: Any, writer: Any
) -> Any:  # noqa: PLR0913
    """Train for one epoch."""
    model.train()
    running_loss = 0.0
    correct = 0
    total = 0

    for batch_idx, (inputs, targets) in enumerate(train_loader):
        inputs, targets = inputs.to(device), targets.to(device)

        optimizer.zero_grad()
        outputs = model(inputs)
        loss = criterion(outputs, targets)
        loss.backward()
        optimizer.step()

        running_loss += loss.item()
        _, predicted = outputs.max(1)
        total += targets.size(0)
        correct += predicted.eq(targets).sum().item()

        if batch_idx % 100 == 0:
            step = epoch * len(train_loader) + batch_idx
            writer.add_scalar("train/loss", loss.item(), step)
            writer.add_scalar("train/accuracy", 100.0 * correct / total, step)

    return running_loss / len(train_loader), 100.0 * correct / total


def validate(model, val_loader: Any, criterion: Any, device: Any, epoch: Any, writer: Any) -> Any:  # noqa: PLR0913
    """Validate the model."""
    model.eval()
    val_loss = 0.0
    correct = 0
    total = 0

    with torch.no_grad():
        for inputs, targets in val_loader:
            inputs, targets = inputs.to(device), targets.to(device)
            outputs = model(inputs)
            loss = criterion(outputs, targets)

            val_loss += loss.item()
            _, predicted = outputs.max(1)
            total += targets.size(0)
            correct += predicted.eq(targets).sum().item()

    val_loss = val_loss / len(val_loader)
    val_acc = 100.0 * correct / total

    writer.add_scalar("val/loss", val_loss, epoch)
    writer.add_scalar("val/accuracy", val_acc, epoch)

    return val_loss, val_acc


def main() -> None:
    parser = argparse.ArgumentParser(description="Train ConvNet on CIFAR-10")
    parser.add_argument("--learning-rate", type=float, default=0.001, help="Learning rate")
    parser.add_argument("--batch-size", type=int, default=32, help="Batch size")
    parser.add_argument("--epochs", type=int, default=50, help="Number of epochs")
    parser.add_argument("--dropout", type=float, default=0.5, help="Dropout rate")
    parser.add_argument("--weight-decay", type=float, default=1e-4, help="Weight decay")
    parser.add_argument("--run-id", type=str, default=None, help="Run ID for tracking")
    parser.add_argument("--log-dir", type=str, default="./logs", help="Tensorboard log directory")
    args = parser.parse_args()

    # Setup
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    run_id = args.run_id or f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    log_dir = os.path.join(args.log_dir, run_id)
    os.makedirs(log_dir, exist_ok=True)
    writer = SummaryWriter(log_dir)

    # Save hyperparameters
    hparams = vars(args)
    with open(os.path.join(log_dir, "hparams.json"), "w") as f:
        json.dump(hparams, f, indent=2)

    # Data loaders
    train_loader, val_loader = get_data_loaders(batch_size=args.batch_size)

    # Model
    model = ConvNet(num_classes=10, dropout_rate=args.dropout).to(device)

    # BUG: Using wrong reduction for loss function
    # This will cause training instability and poor convergence
    # Should be 'mean' but set to 'sum' which scales loss incorrectly
    criterion = nn.CrossEntropyLoss(reduction="sum")

    optimizer = optim.Adam(
        model.parameters(), lr=args.learning_rate, weight_decay=args.weight_decay
    )

    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs)

    # Training loop
    best_val_acc = 0.0

    for epoch in range(args.epochs):
        _train_loss, _train_acc = train_epoch(
            model, train_loader, criterion, optimizer, device, epoch, writer
        )
        _val_loss, val_acc = validate(model, val_loader, criterion, device, epoch, writer)

        scheduler.step()

        # Save checkpoint if best
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            checkpoint_path = os.path.join(log_dir, "best_model.pth")
            torch.save(
                {
                    "epoch": epoch,
                    "model_state_dict": model.state_dict(),
                    "optimizer_state_dict": optimizer.state_dict(),
                    "val_acc": val_acc,
                    "hparams": hparams,
                },
                checkpoint_path,
            )

        # Log current learning rate
        current_lr = optimizer.param_groups[0]["lr"]
        writer.add_scalar("train/learning_rate", current_lr, epoch)

    writer.close()

    # Save final results
    results = {
        "run_id": run_id,
        "best_val_acc": best_val_acc,
        "hyperparameters": hparams,
        "final_epoch": args.epochs,
    }

    with open(os.path.join(log_dir, "results.json"), "w") as f:
        json.dump(results, f, indent=2)


if __name__ == "__main__":
    main()
