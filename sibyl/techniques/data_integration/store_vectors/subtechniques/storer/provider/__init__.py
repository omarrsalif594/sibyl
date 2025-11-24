"""Provider-specific storer implementation stub."""

from typing import Never


def build_subtechnique() -> Never:
    """Build provider-specific storer subtechnique.

    Raises:
        NotImplementedError: Provider variant not yet implemented
    """
    msg = "Provider-specific storer not implemented. Use 'default' variant or implement custom provider."
    raise NotImplementedError(msg)
