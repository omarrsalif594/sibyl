"""Provider-specific loader implementation stub.

To implement a provider-specific loader:
1. Create impl.py in this directory
2. Implement LoadDocumentsSubtechnique with provider-specific logic
3. Export build_subtechnique() function
"""

from typing import Never


def build_subtechnique() -> Never:
    """Build provider-specific loader subtechnique.

    Raises:
        NotImplementedError: Provider variant not yet implemented
    """
    msg = "Provider-specific loader not implemented. Use 'default' variant or implement custom provider."
    raise NotImplementedError(msg)
