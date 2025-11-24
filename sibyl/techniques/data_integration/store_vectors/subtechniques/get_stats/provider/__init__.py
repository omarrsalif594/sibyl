"""Provider-specific get_stats implementation stub."""

from typing import Never


def build_subtechnique() -> Never:
    """Build provider-specific get_stats subtechnique.

    Raises:
        NotImplementedError: Provider variant not yet implemented
    """
    msg = "Provider-specific get_stats not implemented. Use 'default' variant or implement custom provider."
    raise NotImplementedError(msg)
