"""Provider-specific execute implementation stub."""

from typing import Never


def build_subtechnique() -> Never:
    """Build provider-specific execute subtechnique.

    Raises:
        NotImplementedError: Provider variant not yet implemented
    """
    msg = "Provider-specific execute not implemented. Use 'default' variant or implement custom provider."
    raise NotImplementedError(msg)
