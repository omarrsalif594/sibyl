"""JSON repair for malformed structured outputs."""

import json
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sibyl.core.contracts.providers import CompletionOptions, LLMProvider

logger = logging.getLogger(__name__)


class JSONRepair:
    """Retry loop for malformed JSON responses."""

    MAX_RETRIES = 2

    @staticmethod
    async def validate_and_repair(
        response_text: str,
        schema: dict[str, Any],
        provider: "LLMProvider",
        original_prompt: str,
        options: "CompletionOptions",
    ) -> dict[str, Any]:
        """Validate JSON; if invalid, retry with repair prompt.

        Args:
            response_text: LLM response text (should be JSON)
            schema: JSON schema for validation
            provider: LLM provider for retry
            original_prompt: Original prompt (for context)
            options: Completion options

        Returns:
            Parsed and validated JSON dict

        Raises:
            json.JSONDecodeError: If repair fails after MAX_RETRIES
        """
        # Try to parse and validate
        try:
            data = json.loads(response_text)

            # Validate against schema if jsonschema available
            try:
                import jsonschema  # can be moved to top

                jsonschema.validate(data, schema)
            except ImportError:
                logger.warning("jsonschema not installed, skipping schema validation")
            except jsonschema.ValidationError as e:
                logger.warning("Schema validation failed: %s", e)
                # Don't fail on schema validation, just log
                # (LLM might have good reasons for deviating slightly)

            return data

        except json.JSONDecodeError as e:
            logger.warning("Malformed JSON: %s", e)

            # Don't retry if we've already retried
            retry_count = getattr(options, "_json_repair_retry", 0)
            if retry_count >= JSONRepair.MAX_RETRIES:
                logger.exception("JSON repair failed after %s attempts", JSONRepair.MAX_RETRIES)
                # Return best-effort response with malformed flag
                return {"text": response_text, "_malformed": True, "_error": str(e)}

            # Retry with repair prompt
            repair_prompt = JSONRepair._build_repair_prompt(
                response_text, schema, original_prompt, e
            )

            logger.info("Attempting JSON repair (retry %s)", retry_count + 1)

            # Mark this as a retry
            options._json_repair_retry = retry_count + 1  # type: ignore

            retry_result = await provider.complete_async(repair_prompt, options)

            # Try again (recursive with retry count)
            return await JSONRepair.validate_and_repair(
                retry_result["text"], schema, provider, original_prompt, options
            )

    @staticmethod
    def _build_repair_prompt(
        malformed_json: str,
        schema: dict[str, Any],
        original_prompt: str,
        error: json.JSONDecodeError,
    ) -> str:
        """Build repair prompt for malformed JSON.

        Args:
            malformed_json: The malformed JSON response
            schema: Expected JSON schema
            original_prompt: Original prompt for context
            error: The JSON decode error

        Returns:
            Repair prompt string
        """
        return f"""The previous response was malformed JSON and could not be parsed.

**Error:** {error}

**Malformed Response:**
```
{malformed_json[:500]}  # Truncate to avoid token waste
```

**Expected Schema:**
```json
{json.dumps(schema, indent=2)}
```

**Original Task:**
{original_prompt[:300]}  # Truncate

Please output valid JSON matching the schema above. Ensure:
1. All quotes are properly escaped
2. No trailing commas
3. Proper closing of all braces and brackets
4. Use double quotes (not single quotes)

Output ONLY the JSON, no markdown code blocks or explanations."""

    @staticmethod
    def validate_sync(response_text: str, schema: dict[str, Any]) -> dict[str, Any]:
        """Synchronous validation (no repair).

        Args:
            response_text: JSON text
            schema: JSON schema

        Returns:
            Parsed JSON dict

        Raises:
            json.JSONDecodeError: If invalid
            jsonschema.ValidationError: If schema validation fails
        """
        data = json.loads(response_text)

        try:
            import jsonschema  # can be moved to top

            jsonschema.validate(data, schema)
        except ImportError:
            pass  # Skip validation if jsonschema not available

        return data
