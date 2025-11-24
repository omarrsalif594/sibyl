"""
Sliding Window Rate Limiting Implementation

Uses a sliding window algorithm to track requests over time.
"""

import time
from collections import defaultdict, deque
from typing import Any

# Global state for rate limiting (in production, use Redis or similar)
_request_state: dict[tuple, deque] = defaultdict(deque)


def execute_sliding_window(
    client_ip: str, endpoint: str, default_rpm: int, window_seconds: int, **kwargs
) -> dict[str, Any]:
    """
    Execute sliding window rate limiting.

    Args:
        client_ip: Client IP address
        endpoint: Request endpoint
        default_rpm: Requests per minute limit
        window_seconds: Time window in seconds
        **kwargs: Additional parameters

    Returns:
        Result dictionary with rate limit status
    """
    current_time = time.time()
    cutoff_time = current_time - window_seconds

    # Get request history for this (IP, endpoint)
    key = (client_ip, endpoint)
    request_times = _request_state[key]

    # Remove expired requests (outside window)
    while request_times and request_times[0] < cutoff_time:
        request_times.popleft()

    # Check if over limit
    current_count = len(request_times)
    limit = default_rpm

    if current_count >= limit:
        return {
            "allowed": False,
            "reason": "rate_limit_exceeded",
            "limit": limit,
            "current": current_count,
            "remaining": 0,
            "reset_at": request_times[0] + window_seconds if request_times else current_time,
            "window_seconds": window_seconds,
        }

    # Record this request
    request_times.append(current_time)

    return {
        "allowed": True,
        "reason": "within_limit",
        "limit": limit,
        "current": current_count + 1,
        "remaining": limit - current_count - 1,
        "reset_at": current_time + window_seconds,
        "window_seconds": window_seconds,
    }


def reset_state() -> None:
    """Reset rate limiting state (for testing)."""
    _request_state.clear()
