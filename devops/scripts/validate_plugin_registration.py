"""Validate that plugin registration follows framework/example split."""

import sys
from pathlib import Path


def check_core_plugin_registration() -> bool:
    """Core should only register core plugins."""
    core_init = Path("sibyl/core/platform/extensibility/__init__.py")
    if not core_init.exists():
        return False

    content = core_init.read_text()

    if "retailflow" in content.lower():
        return False

    return "examples.retailflow" not in content


def check_example_plugin_registration() -> bool:
    """Example should have its own registration."""
    example_reg = Path("examples/retailflow/plugins/registration.py")
    if not example_reg.exists():
        return False

    content = example_reg.read_text()

    return "register_retailflow_plugins" in content


if __name__ == "__main__":
    checks = [
        check_core_plugin_registration(),
        check_example_plugin_registration(),
    ]

    if all(checks):
        sys.exit(0)
    else:
        sys.exit(1)
