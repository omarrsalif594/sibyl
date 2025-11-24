"""Custom loader implementation stub.

To implement a custom loader:
1. Create impl.py in this directory
2. Implement LoadDocumentsSubtechnique with custom logic
3. Export build_subtechnique() function

See README.md for details.
"""

from typing import Never


def build_subtechnique() -> Never:
    """Build custom loader subtechnique.

    Raises:
        NotImplementedError: Custom variant not yet implemented
    """
    msg = "Custom loader not implemented. Use 'default' variant or implement custom override."
    raise NotImplementedError(msg)
