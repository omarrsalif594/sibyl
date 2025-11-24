"""Provider-specific query implementation stub."""

from typing import Never


def build_subtechnique() -> Never:
    """Build provider-specific query subtechnique.

    Raises:
        NotImplementedError: Provider variant not yet implemented
    """
    msg = "Provider-specific query not implemented. Use 'default' variant or implement custom provider."
    raise NotImplementedError(msg)
