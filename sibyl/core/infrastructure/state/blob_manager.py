"""Blob storage with deduplication and redaction support."""

import hashlib
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class BlobManager:
    """Deduplicated external storage for large payloads.

    Features:
    - SHA256-based deduplication
    - Content preview (first 500 chars)
    - Redaction metadata tracking
    - Preimage hash for auditing (HMAC)
    """

    DEFAULT_PREVIEW_LENGTH = 500
    MAX_INLINE_SIZE = 10_000  # 10KB threshold for external storage

    def __init__(self, storage_root: Path, preview_length: int = DEFAULT_PREVIEW_LENGTH) -> None:
        """Initialize blob manager.

        Args:
            storage_root: Root directory for blob storage
            preview_length: Number of characters for preview
        """
        self._root = storage_root
        self._root.mkdir(parents=True, exist_ok=True)
        self._preview_length = preview_length

        logger.info("Blob storage initialized at: %s", self._root)

    def store(
        self,
        content: str,
        kind: str,
        redacted: bool = False,
        redaction_rules: list[str] | None = None,
        preimage_hash: str | None = None,
    ) -> tuple[str, dict[str, Any]]:
        """Store blob with deduplication.

        Args:
            content: Content to store
            kind: Blob kind ("prompt", "response", "context", etc.)
            redacted: Whether content was redacted
            redaction_rules: List of redaction rules applied
            preimage_hash: HMAC of original content (before redaction)

        Returns:
            Tuple of (sha256_ref, metadata_dict)
        """
        # Compute SHA256 (deduplication key)
        sha256 = hashlib.sha256(content.encode()).hexdigest()

        # Compute storage path: {root}/{first2}/{next2}/{hash}
        path = self._root / sha256[:2] / sha256[2:4] / sha256
        storage_url = f"file://{path.absolute()}"

        # Only write if doesn't exist (deduplication)
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            logger.debug("Stored new blob: %s... (%s bytes)", sha256[:8], len(content))
        else:
            logger.debug("Blob already exists (deduplicated): %s...", sha256[:8])

        # Generate preview
        preview = content[: self._preview_length]
        if len(content) > self._preview_length:
            preview += "... [truncated]"

        # Build metadata
        metadata = {
            "ref": sha256,
            "kind": kind,
            "storage_url": storage_url,
            "size_bytes": len(content),
            "content_preview": preview,
            "redacted": redacted,
            "redaction_rules_applied": redaction_rules or [],
            "preimage_hash": preimage_hash,
        }

        return sha256, metadata

    def load(self, ref: str) -> str:
        """Load blob by SHA256 ref.

        Args:
            ref: SHA256 hash

        Returns:
            Blob content

        Raises:
            FileNotFoundError: If blob not found
        """
        path = self._root / ref[:2] / ref[2:4] / ref

        if not path.exists():
            msg = f"Blob not found: {ref}"
            raise FileNotFoundError(msg)

        content = path.read_text(encoding="utf-8")
        logger.debug("Loaded blob: %s... (%s bytes)", ref[:8], len(content))

        return content

    def load_preview(self, ref: str, preview_length: int | None = None) -> str:
        """Load only a preview of the blob (for safety).

        Args:
            ref: SHA256 hash
            preview_length: Optional preview length (uses default if not specified)

        Returns:
            Preview of blob content

        Raises:
            FileNotFoundError: If blob not found
        """
        content = self.load(ref)
        length = preview_length or self._preview_length

        if len(content) <= length:
            return content

        return content[:length] + "... [truncated]"

    def exists(self, ref: str) -> bool:
        """Check if blob exists.

        Args:
            ref: SHA256 hash

        Returns:
            True if blob exists
        """
        path = self._root / ref[:2] / ref[2:4] / ref
        return path.exists()

    def delete(self, ref: str) -> bool:
        """Delete blob.

        Args:
            ref: SHA256 hash

        Returns:
            True if deleted, False if didn't exist
        """
        path = self._root / ref[:2] / ref[2:4] / ref

        if path.exists():
            path.unlink()
            logger.info("Deleted blob: %s...", ref[:8])

            # Clean up empty directories
            try:
                path.parent.rmdir()  # Remove {first2}/{next2}
                path.parent.parent.rmdir()  # Remove {first2}
            except OSError:
                pass  # Directory not empty, that's fine

            return True
        return False

    def get_stats(self) -> dict[str, Any]:
        """Get blob storage statistics.

        Returns:
            Dict with total_blobs, total_bytes, storage_path
        """
        total_blobs = 0
        total_bytes = 0

        # Walk all blob files
        for blob_file in self._root.rglob("*"):
            if blob_file.is_file():
                total_blobs += 1
                total_bytes += blob_file.stat().st_size

        return {
            "total_blobs": total_blobs,
            "total_bytes": total_bytes,
            "storage_path": str(self._root.absolute()),
        }

    def compute_preimage_hash(self, content: str, secret_key: str) -> str:
        """Compute HMAC of original content (for auditing).

        This allows proving that redacted content derives from a specific original
        without storing the original.

        Args:
            content: Original content (before redaction)
            secret_key: Secret key for HMAC

        Returns:
            HMAC hex digest
        """
        import hmac

        return hmac.new(secret_key.encode(), content.encode(), hashlib.sha256).hexdigest()


# Utility function
def compute_content_hash(content: str) -> str:
    """Compute SHA256 hash of content.

    Args:
        content: Content to hash

    Returns:
        SHA256 hex digest
    """
    return hashlib.sha256(content.encode()).hexdigest()
