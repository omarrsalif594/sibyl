#!/usr/bin/env python3
"""
Custom Sibyl Plugin Example

This example demonstrates how to integrate any custom application with Sibyl's
OpenAI-compatible facade. It shows various integration patterns and best practices.

Prerequisites:
- Sibyl server running on http://localhost:8000
- OpenAI Python SDK installed: pip install openai

Usage:
    python custom_plugin_example.py

Features Demonstrated:
1. Basic chat completion
2. Routing profiles (fast, balanced, think)
3. Context-aware requests with metadata
4. Multi-turn conversations
5. Streaming responses
6. Error handling
7. Retry logic
8. Custom helper classes
"""

import os
import time
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

from openai import OpenAI, OpenAIError, RateLimitError

# =============================================================================
# Configuration
# =============================================================================

SIBYL_API_URL = os.getenv("SIBYL_API_URL", "http://localhost:8000/v1")
SIBYL_API_KEY = os.getenv("SIBYL_API_KEY", "sibyl_key")


# =============================================================================
# Data Models
# =============================================================================


@dataclass
class Message:
    """Chat message."""

    role: str  # "system", "user", "assistant"
    content: str


@dataclass
class EditorContext:
    """Editor context metadata."""

    file: str | None = None
    line: int | None = None
    column: int | None = None
    language: str | None = None
    selection: dict[str, Any] | None = None


@dataclass
class ProjectContext:
    """Project context metadata."""

    framework: str | None = None
    language: str | None = None
    version: str | None = None
    dependencies: list[str] | None = None


@dataclass
class SibylMetadata:
    """Sibyl-specific metadata."""

    workspace: str | None = None
    pipeline: str | None = None
    editor: EditorContext | None = None
    project_context: ProjectContext | None = None
    custom: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API request."""
        result = {}

        if self.workspace:
            result["workspace"] = self.workspace

        if self.pipeline:
            result["pipeline"] = self.pipeline

        if self.editor:
            editor_dict = {}
            if self.editor.file:
                editor_dict["file"] = self.editor.file
            if self.editor.line is not None:
                editor_dict["line"] = self.editor.line
            if self.editor.column is not None:
                editor_dict["column"] = self.editor.column
            if self.editor.language:
                editor_dict["language"] = self.editor.language
            if self.editor.selection:
                editor_dict["selection"] = self.editor.selection
            if editor_dict:
                result["editor"] = editor_dict

        if self.project_context:
            project_dict = {}
            if self.project_context.framework:
                project_dict["framework"] = self.project_context.framework
            if self.project_context.language:
                project_dict["language"] = self.project_context.language
            if self.project_context.version:
                project_dict["version"] = self.project_context.version
            if self.project_context.dependencies:
                project_dict["dependencies"] = self.project_context.dependencies
            if project_dict:
                result["project_context"] = project_dict

        if self.custom:
            result["custom"] = self.custom

        return result


# =============================================================================
# Sibyl Client
# =============================================================================


class SibylClient:
    """Client for interacting with Sibyl's OpenAI-compatible facade."""

    def __init__(
        self,
        base_url: str = SIBYL_API_URL,
        api_key: str = SIBYL_API_KEY,
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        """Initialize Sibyl client.

        Args:
            base_url: Sibyl API base URL
            api_key: API key for authentication (optional)
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries for rate limit errors
        """
        self.client = OpenAI(base_url=base_url, api_key=api_key, timeout=timeout)
        self.max_retries = max_retries
        self.conversation_history: list[dict[str, str]] = []

    def chat(  # noqa: PLR0913
        self,
        message: str,
        model: str = "sibyl/code-balanced",
        temperature: float = 0.7,
        max_tokens: int = 2000,
        metadata: SibylMetadata | None = None,
        system_message: str | None = None,
    ) -> str:
        """Send a chat message to Sibyl.

        Args:
            message: User message
            model: Model or routing profile
            temperature: Sampling temperature (0.0-2.0)
            max_tokens: Maximum completion tokens
            metadata: Sibyl-specific metadata
            system_message: Optional system message

        Returns:
            Assistant's response
        """
        messages = []

        # Add system message if provided
        if system_message:
            messages.append({"role": "system", "content": system_message})

        # Add user message
        messages.append({"role": "user", "content": message})

        # Prepare request parameters
        params = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        # Add metadata if provided
        if metadata:
            params["extra_body"] = {"metadata": metadata.to_dict()}

        # Send request with retry logic
        response = self._request_with_retry(params)

        # Extract response text
        return response.choices[0].message.content

    def chat_conversation(
        self,
        message: str,
        model: str = "sibyl/code-balanced",
        temperature: float = 0.7,
        max_tokens: int = 2000,
        metadata: SibylMetadata | None = None,
    ) -> str:
        """Send a message as part of a conversation (maintains history).

        Args:
            message: User message
            model: Model or routing profile
            temperature: Sampling temperature
            max_tokens: Maximum completion tokens
            metadata: Sibyl-specific metadata

        Returns:
            Assistant's response
        """
        # Add user message to history
        self.conversation_history.append({"role": "user", "content": message})

        # Prepare request parameters
        params = {
            "model": model,
            "messages": self.conversation_history,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        # Add metadata if provided
        if metadata:
            params["extra_body"] = {"metadata": metadata.to_dict()}

        # Send request
        response = self._request_with_retry(params)

        # Extract response
        assistant_message = response.choices[0].message.content

        # Add assistant response to history
        self.conversation_history.append({"role": "assistant", "content": assistant_message})

        return assistant_message

    def chat_stream(
        self,
        message: str,
        model: str = "sibyl/code-balanced",
        temperature: float = 0.7,
        max_tokens: int = 2000,
        metadata: SibylMetadata | None = None,
    ) -> Iterator[str]:
        """Send a chat message with streaming response.

        Args:
            message: User message
            model: Model or routing profile
            temperature: Sampling temperature
            max_tokens: Maximum completion tokens
            metadata: Sibyl-specific metadata

        Yields:
            Response chunks as they arrive
        """
        messages = [{"role": "user", "content": message}]

        # Prepare request parameters
        params = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }

        # Add metadata if provided
        if metadata:
            params["extra_body"] = {"metadata": metadata.to_dict()}

        # Send streaming request
        response = self.client.chat.completions.create(**params)

        # Yield chunks
        for chunk in response:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def reset_conversation(self) -> None:
        """Reset conversation history."""
        self.conversation_history = []

    def _request_with_retry(self, params: dict[str, Any]) -> Any:
        """Send request with retry logic for rate limits.

        Args:
            params: Request parameters

        Returns:
            API response

        Raises:
            OpenAIError: If request fails after retries
        """
        for attempt in range(self.max_retries):
            try:
                return self.client.chat.completions.create(**params)
            except RateLimitError:
                if attempt < self.max_retries - 1:
                    wait_time = 2**attempt  # Exponential backoff
                    time.sleep(wait_time)
                else:
                    raise
            except OpenAIError:
                raise
        return None


# =============================================================================
# Example Use Cases
# =============================================================================


def example_basic_chat() -> None:
    """Example 1: Basic chat completion."""

    client = SibylClient()

    client.chat(message="What is Sibyl?", model="sibyl/code-fast")


def example_routing_profiles() -> None:
    """Example 2: Using different routing profiles."""

    client = SibylClient()

    # Fast profile for simple queries
    client.chat(message="How do I reverse a string in Python?", model="sibyl/code-fast")

    # Balanced profile for general tasks
    client.chat(
        message="Explain how Python decorators work with an example", model="sibyl/code-balanced"
    )

    # Think profile for complex reasoning
    client.chat(
        message="Design a scalable microservices architecture for a real-time chat app",
        model="sibyl/code-think",
    )


def example_context_aware() -> None:
    """Example 3: Context-aware requests with metadata."""

    client = SibylClient()

    # Create metadata
    metadata = SibylMetadata(
        workspace="/Users/dev/myproject",
        editor=EditorContext(file="src/main.py", line=42, language="python"),
        project_context=ProjectContext(
            framework="fastapi",
            language="python",
            version="3.11",
            dependencies=["pydantic", "sqlalchemy"],
        ),
    )

    client.chat(
        message="Show me how to create a Pydantic model for this project",
        model="sibyl/code-balanced",
        metadata=metadata,
    )


def example_multi_turn_conversation() -> None:
    """Example 4: Multi-turn conversation."""

    client = SibylClient()

    # First message
    client.chat_conversation(
        message="How do I create a REST API with FastAPI?", model="sibyl/code-balanced"
    )

    # Follow-up message
    client.chat_conversation(message="Now add Pydantic validation", model="sibyl/code-balanced")

    # Another follow-up
    client.chat_conversation(message="How do I add authentication?", model="sibyl/code-balanced")


def example_streaming() -> None:
    """Example 5: Streaming responses."""

    client = SibylClient()

    for _chunk in client.chat_stream(
        message="Explain the SOLID principles in software engineering", model="sibyl/code-balanced"
    ):
        pass


def example_error_handling() -> None:
    """Example 6: Error handling."""

    client = SibylClient()

    try:
        # Try with invalid model
        client.chat(message="Test", model="invalid-model")
    except OpenAIError:
        pass


def example_code_generation() -> None:
    """Example 7: Code generation with specific instructions."""

    client = SibylClient()

    client.chat(
        message="""Generate a Python class for a User model with:
- Fields: id (UUID), email (str), name (str), created_at (datetime)
- Methods: validate_email(), to_dict()
- Use Pydantic for validation
- Include type hints""",
        model="sibyl/code-balanced",
        temperature=0.5,
    )


def example_code_review() -> None:
    """Example 8: Code review request."""

    client = SibylClient()

    # ⚠️ SECURITY WARNING: This code contains INTENTIONAL VULNERABILITIES for demonstration purposes.
    # This example is used to test code review capabilities. DO NOT use this code in production!
    #
    # Vulnerabilities demonstrated:
    # 1. SQL Injection: Using string formatting in SQL queries
    # 2. Plain text password storage/comparison
    # 3. No input validation
    #
    # Secure alternative:
    # query = "SELECT * FROM users WHERE username=? AND password_hash=?"
    # cursor.execute(query, (username, hash_password(password)))
    code = """
def authenticate_user(username, password):
    query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
    cursor.execute(query)
    user = cursor.fetchone()
    if user:
        session['user_id'] = user[0]
        return True
    return False
"""

    client.chat(
        message=f"Review this code for security issues and best practices:\n{code}",
        model="sibyl/code-think",
        system_message="You are a senior code reviewer. Identify issues and suggest improvements.",
    )


def example_custom_pipeline() -> None:
    """Example 9: Using a specific pipeline."""

    client = SibylClient()

    metadata = SibylMetadata(pipeline="code_refactor", workspace="/Users/dev/myproject")

    client.chat(
        message="Refactor this code to use dependency injection:\n\nclass UserService:\n    def __init__(self):\n        self.db = Database('postgresql://localhost/mydb')\n        self.cache = Redis('localhost:6379')",
        model="sibyl/code-balanced",
        metadata=metadata,
    )


def example_project_aware() -> None:
    """Example 10: Project-aware assistance."""

    client = SibylClient()

    # Detect current project context
    workspace = os.getcwd()

    metadata = SibylMetadata(
        workspace=workspace,
        project_context=ProjectContext(language="python", framework="fastapi", version="3.11"),
    )

    client.chat(
        message="What's the recommended project structure for this FastAPI project?",
        model="sibyl/code-balanced",
        metadata=metadata,
    )


# =============================================================================
# Main
# =============================================================================


def main() -> None:
    """Run all examples."""

    # Check if server is running
    try:
        client = SibylClient()
        client.chat("test", model="sibyl/code-fast")
    except Exception:
        return

    # Run examples
    try:
        example_basic_chat()
        example_routing_profiles()
        example_context_aware()
        example_multi_turn_conversation()
        example_streaming()
        example_error_handling()
        example_code_generation()
        example_code_review()
        example_custom_pipeline()
        example_project_aware()
    except KeyboardInterrupt:
        pass
    except Exception:
        raise


if __name__ == "__main__":
    main()
