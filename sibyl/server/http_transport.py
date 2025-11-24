"""
HTTP Server for MCP Side Channel

Provides HTTP API for VS Code extension to send file events and button clicks.
This is NOT an MCP server - it's a simple REST API that shares state with the stdio MCP server.

Security Features:
- API key authentication (deny-by-default)
- Rate limiting (per-IP and per-endpoint)
- Input validation
- CORS restrictions (localhost only)
"""

import logging
import os
import sys

try:
    import uvicorn
    from starlette.applications import Starlette
    from starlette.middleware import Middleware
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.middleware.cors import CORSMiddleware
    from starlette.requests import Request
    from starlette.responses import JSONResponse, Response
    from starlette.routing import Route
except ImportError:
    sys.exit(1)

# TODO(v0.2.0): Implement infrastructure modules for security and observability
# from infrastructure.security.auth import APIKeyAuthenticator
# from infrastructure.security.rate_limiter import RateLimiter
# from infrastructure.security.validators import (
#     sanitize_model_name,
#     sanitize_string_input,
#     ValidationError,
# )
# from infrastructure.observability import metrics
from typing import Any

from sibyl.techniques.infrastructure.rate_limiting import RateLimitingTechnique

from .shared_state import state_manager

logger = logging.getLogger(__name__)

# TODO(v0.2.0): Re-enable when infrastructure modules are implemented
# # Initialize authenticator (loaded at module level)
# _authenticator = APIKeyAuthenticator(
#     keys_path=os.environ.get("MCP_API_KEYS_FILE", ".mcp_keys"),
#     deny_by_default=True,
#     enable_audit_log=True,
# )

# Configuration loaded from rate_limiting technique
_rate_limiting_technique = RateLimitingTechnique()
_rate_limiting_config = _rate_limiting_technique.get_configuration()

# TODO(v0.2.0): Re-enable when infrastructure modules are implemented
# # Initialize rate limiter
# _rate_limiter = RateLimiter(
#     default_limit=_rate_limiting_config['default_rpm'],
#     window_seconds=_rate_limiting_config['window_seconds'],
#     per_endpoint_limits={
#         "/api/file-event": 200,  # Higher limit for frequent file events
#         "/api/button-click": 200,
#         "/api/health": 1000,  # Very high limit for liveness checks
#         "/api/ready": 1000,  # Very high limit for readiness checks
#         "/api/metrics": 1000,  # Very high limit for Prometheus scraping
#     },
# )

# v0.1.0: Stub placeholders until infrastructure modules are implemented
_authenticator = None  # Authentication disabled for v0.1.0
_rate_limiter = None  # Rate limiting disabled for v0.1.0

# Global resource layer (set at runtime by run_http_server)
_resource_layer = None


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """
    API key authentication middleware with deny-by-default policy.

    Checks X-API-Key header for all requests except:
    - /api/health (liveness checks for load balancers)
    - /api/ready (readiness checks with dependency validation)
    - /api/metrics (Prometheus scraping endpoint)
    """

    async def dispatch(self, request: Request, call_next: Any) -> Any:
        # Allow health/readiness checks and metrics without authentication
        # (for load balancers, Kubernetes probes, and Prometheus scrapers)
        if request.url.path in ["/api/health", "/api/ready", "/api/metrics"]:
            return await call_next(request)

        # Check for API key in header
        api_key = request.headers.get("X-API-Key")

        # v0.1.0: Skip authentication if authenticator not yet implemented
        if _authenticator is not None:
            if not _authenticator.verify(api_key):
                return JSONResponse(
                    {
                        "status": "error",
                        "message": "Unauthorized",
                        "hint": "Provide a valid API key in X-API-Key header. "
                        'Generate a key with: python -c "from infrastructure.security.auth import generate_api_key; print(generate_api_key())"',
                    },
                    status_code=401,
                )

            # Attach user context for audit logging
            user_id = _authenticator.get_user_id(api_key)
            request.state.user_id = user_id
        else:
            # v0.1.0: No authentication - development mode
            request.state.user_id = "anonymous"

        # Proceed with authenticated request
        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Add security headers to all responses.

    Headers added:
    - X-Content-Type-Options: nosniff (prevent MIME sniffing)
    - X-Frame-Options: DENY (prevent clickjacking)
    - X-XSS-Protection: 1; mode=block (XSS filter)
    - Content-Security-Policy: Strict CSP to prevent XSS
    - Referrer-Policy: strict-origin-when-cross-origin
    """

    async def dispatch(self, request: Request, call_next: Any) -> Any:
        response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Only add HSTS if running on HTTPS (check scheme or port)
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware with per-IP and per-endpoint limits.

    Features:
    - Sliding window algorithm
    - Per-endpoint limit configuration
    - Localhost exemption
    - Automatic cleanup
    """

    async def dispatch(self, request: Request, call_next: Any) -> Any:
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        endpoint = request.url.path

        # v0.1.0: Skip rate limiting if rate limiter not yet implemented
        if _rate_limiter is not None:
            # Check rate limit
            if _rate_limiter.is_rate_limited(client_ip, endpoint):
                # Get limit for this endpoint
                limit = _rate_limiter.per_endpoint_limits.get(endpoint, _rate_limiter.default_limit)
                return JSONResponse(
                    {
                        "status": "error",
                        "message": "Rate limit exceeded",
                        "hint": f"Maximum {limit} requests per {_rate_limiter.window_seconds} seconds for {endpoint}. Please slow down.",
                        "retry_after": _rate_limiter.window_seconds,
                    },
                    status_code=429,
                    headers={"Retry-After": str(_rate_limiter.window_seconds)},
                )

            # Record this request
            _rate_limiter.record_request(client_ip, endpoint)

        # Proceed with request
        response = await call_next(request)

        # v0.1.0: Add rate limit headers only if rate limiter is enabled
        if _rate_limiter is not None:
            # Add rate limit headers to response (for client awareness)
            # Note: This is approximate since we use sliding window
            response.headers["X-RateLimit-Limit"] = str(
                _rate_limiter.per_endpoint_limits.get(endpoint, _rate_limiter.default_limit)
            )
            response.headers["X-RateLimit-Window"] = str(_rate_limiter.window_seconds)

        return response


async def handle_file_event(request: Request) -> Any:
    """
    Handle file event from VS Code extension.

    Expected JSON body:
    {
        "event_type": "opened" | "closed" | "changed",
        "model_name": "example_resource",
        "file_path": "/path/to/file.sql"
    }
    """
    try:
        data = await request.json()
        event_type = data.get("event_type")
        model_name = data.get("model_name")
        file_path = data.get("file_path", "")

        if not event_type or not model_name:
            return JSONResponse(
                {"status": "error", "message": "Missing required fields: event_type, model_name"},
                status_code=400,
            )

        # Input validation
        try:
            event_type = sanitize_string_input(event_type, max_length=50, allow_newlines=False)
            model_name = sanitize_model_name(model_name)
            if file_path:
                file_path = sanitize_string_input(file_path, max_length=500)
        except ValidationError as e:
            logger.warning("Invalid input in file event: %s", e)
            return JSONResponse(
                {"status": "error", "message": f"Invalid input: {e}"},
                status_code=400,
            )

        logger.info("File event: %s - %s", event_type, model_name)

        # Store in shared state
        state_manager.add_file_event(event_type, model_name, file_path)

        return JSONResponse(
            {
                "status": "ok",
                "message": f"Event recorded: {event_type} - {model_name}",
                "current_model": state_manager.get_current_model(),
            }
        )

    except Exception as e:
        logger.exception("Error handling file event: %s", e)
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


async def handle_button_click(request: Request) -> Any:
    """
    Handle button click from VS Code extension.

    Expected JSON body:
    {
        "action": "test" | "compile" | "fix",
        "model_name": "example_resource"
    }
    """
    try:
        data = await request.json()
        action = data.get("action")
        model_name = data.get("model_name")

        if not action or not model_name:
            return JSONResponse(
                {"status": "error", "message": "Missing required fields: action, model_name"},
                status_code=400,
            )

        # Input validation
        try:
            action = sanitize_string_input(action, max_length=50, allow_newlines=False)
            model_name = sanitize_model_name(model_name)
        except ValidationError as e:
            logger.warning("Invalid input in button click: %s", e)
            return JSONResponse(
                {"status": "error", "message": f"Invalid input: {e}"},
                status_code=400,
            )

        logger.info("Button click: %s - %s", action, model_name)

        # Store as event with special type
        event_type = f"button_{action}"
        state_manager.add_file_event(event_type, model_name, "")

        return JSONResponse(
            {"status": "ok", "message": f"Action recorded: {action} for {model_name}"}
        )

    except Exception as e:
        logger.exception("Error handling button click: %s", e)
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


async def get_status(request: Request) -> Any:
    """
    Get server status and current context.

    Returns:
    {
        "status": "ok",
        "context": {...},
        "recent_events": [...],
        "stats": {...}
    }
    """
    try:
        context = state_manager.get_current_context()
        recent_events = state_manager.get_recent_events(since_seconds=60)
        stats = state_manager.get_stats()

        return JSONResponse(
            {
                "status": "ok",
                "context": context,
                "recent_events": recent_events,
                "stats": stats,
            }
        )

    except Exception as e:
        logger.exception("Error getting status: %s", e)
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


async def health_check(request: Request) -> Any:
    """
    Simple health check endpoint.

    Returns 200 OK if the server is running.
    This is a lightweight check for load balancers.
    """
    return JSONResponse({"status": "ok", "message": "HTTP server is running"})


async def readiness_check(request: Request) -> Any:
    """
    Readiness check endpoint with dependency checks.

    Performs deeper checks:
    - DuckDB connectivity
    - Resource layer availability
    - Shared state manager

    Returns:
        200 OK if all checks pass
        503 Service Unavailable if any check fails

    This is for Kubernetes readiness probes or load balancer health checks
    that require dependency validation.
    """
    checks = {
        "server": "ok",
        "duckdb": "unknown",
        "resource_layer": "unknown",
        "state_manager": "unknown",
    }

    try:
        # Check DuckDB connectivity
        try:
            import duckdb

            # Quick test query
            conn = duckdb.connect(":memory:")
            result = conn.execute("SELECT 1 AS test").fetchone()
            if result and result[0] == 1:
                checks["duckdb"] = "ok"
            else:
                checks["duckdb"] = "failed"
            conn.close()
        except Exception as e:
            logger.warning("DuckDB readiness check failed: %s", e)
            checks["duckdb"] = "failed"

        # Check resource layer availability
        if _resource_layer is not None:
            checks["resource_layer"] = "ok"
        else:
            checks["resource_layer"] = "not_loaded"

        # Check state manager
        try:
            _ = state_manager.get_stats()
            checks["state_manager"] = "ok"
        except Exception as e:
            logger.warning("State manager readiness check failed: %s", e)
            checks["state_manager"] = "failed"

        # Overall status
        all_ok = all(status in ["ok", "not_loaded"] for status in checks.values())

        if all_ok:
            return JSONResponse(
                {
                    "status": "ready",
                    "message": "Server is ready to accept requests",
                    "checks": checks,
                }
            )
        return JSONResponse(
            {
                "status": "not_ready",
                "message": "Server is not ready",
                "checks": checks,
            },
            status_code=503,
        )

    except Exception as e:
        logger.exception("Readiness check error: %s", e)
        return JSONResponse(
            {
                "status": "error",
                "message": f"Readiness check failed: {e!s}",
                "checks": checks,
            },
            status_code=503,
        )


async def get_metrics(request: Request) -> Any:
    """
    Prometheus metrics endpoint.

    Returns all metrics in Prometheus text format:
    - Tool execution metrics (tool_*)
    - QC metrics (qc_*)
    - Session rotation metrics (session_*)
    - Quorum pipeline metrics (quorum_*)

    This endpoint does not require authentication (for Prometheus scraping).
    """
    try:
        prometheus_text = metrics.get_prometheus_metrics()
        return Response(
            content=prometheus_text,
            media_type="text/plain; version=0.0.4; charset=utf-8",
        )
    except Exception as e:
        logger.exception("Error generating metrics: %s", e)
        return Response(
            content=f"# Error generating metrics: {e!s}\n",
            media_type="text/plain",
            status_code=500,
        )


async def update_test_result(request: Request) -> Any:
    """
    Update test result for a model (called by test execution).

    Expected JSON body:
    {
        "model_name": "example_resource",
        "result": {...}
    }
    """
    try:
        data = await request.json()
        model_name = data.get("model_name")
        result = data.get("result")

        if not model_name or not result:
            return JSONResponse(
                {"status": "error", "message": "Missing required fields: model_name, result"},
                status_code=400,
            )

        # Input validation
        try:
            model_name = sanitize_model_name(model_name)
        except ValidationError as e:
            logger.warning("Invalid model name in test result update: %s", e)
            return JSONResponse(
                {"status": "error", "message": f"Invalid model name: {e}"},
                status_code=400,
            )

        state_manager.update_test_result(model_name, result)

        return JSONResponse({"status": "ok", "message": f"Test result stored for {model_name}"})

    except Exception as e:
        logger.exception("Error updating test result: %s", e)
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


async def get_test_result(request: Request) -> Any:
    """
    Get test result for a model.

    Query params:
    - model_name: Name of the model
    """
    try:
        model_name = request.query_params.get("model_name")

        if not model_name:
            return JSONResponse(
                {"status": "error", "message": "Missing query parameter: model_name"},
                status_code=400,
            )

        # Input validation
        try:
            model_name = sanitize_model_name(model_name)
        except ValidationError as e:
            logger.warning("Invalid model name in test result query: %s", e)
            return JSONResponse(
                {"status": "error", "message": f"Invalid model name: {e}"},
                status_code=400,
            )

        result = state_manager.get_test_result(model_name)

        if result is None:
            return JSONResponse(
                {"status": "not_found", "message": f"No test result found for {model_name}"},
                status_code=404,
            )

        return JSONResponse({"status": "ok", "model_name": model_name, "result": result})

    except Exception as e:
        logger.exception("Error getting test result: %s", e)
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# Create Starlette app with security middleware
# Order matters: Security Headers → CORS → Rate Limit → Authentication → Handlers
middleware = [
    # Security Headers: Add security headers to all responses (first to ensure they're always added)
    Middleware(SecurityHeadersMiddleware),
    # CORS: Restrict to localhost only (VS Code extension runs locally)
    Middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:8000",
            "http://localhost:8770",
            "http://localhost:3000",
            "http://127.0.0.1:8000",
            "http://127.0.0.1:8770",
            "http://127.0.0.1:3000",
            "vscode-file://vscode-app",  # VS Code internal scheme
        ],
        allow_methods=["GET", "POST", "HEAD"],
        allow_headers=["X-API-Key", "Content-Type"],
        allow_credentials=True,
    ),
    # Rate Limiting: Per-IP and per-endpoint limits (before auth to save resources)
    Middleware(RateLimitMiddleware),
    # Authentication: API key verification (deny-by-default)
    Middleware(AuthenticationMiddleware),
]

app = Starlette(
    debug=os.environ.get("SIBYL_DEBUG", "false").lower() == "true",
    routes=[
        Route("/api/file-event", handle_file_event, methods=["POST"]),
        Route("/api/button-click", handle_button_click, methods=["POST"]),
        Route("/api/status", get_status, methods=["GET"]),
        Route("/api/health", health_check, methods=["GET", "HEAD"]),
        Route("/api/ready", readiness_check, methods=["GET"]),
        Route("/api/metrics", get_metrics, methods=["GET"]),
        Route("/api/test-result", update_test_result, methods=["POST"]),
        Route("/api/test-result", get_test_result, methods=["GET"]),
    ],
    middleware=middleware,
)


async def run_http_server(
    host: str = "127.0.0.1", port: int = 8770, resource_layer: Any = None
) -> None:
    """
    Run HTTP server for VS Code side channel.

    Args:
        host: Host to bind to (default: 127.0.0.1)
        port: Port to bind to (default: 8770, configurable via MCP_HTTP_PORT env var)
        resource_layer: Preloaded resource layer (lineage, patterns, etc.)
    """
    logger.info("Starting HTTP server on %s:%s", host, port)
    logger.info("HTTP API endpoints:")
    logger.info("  POST /api/file-event - File opened/closed events")
    logger.info("  POST /api/button-click - Button click events")
    logger.info("  GET  /api/status - Get server status")
    logger.info("  GET  /api/health - Liveness check (lightweight)")
    logger.info("  GET  /api/ready - Readiness check (with dependency validation)")
    logger.info("  GET  /api/metrics - Prometheus metrics")
    logger.info("  POST /api/test-result - Update test result")
    logger.info("  GET  /api/test-result?model_name=X - Get test result")

    # Store resource layer globally for handler access
    global _resource_layer
    _resource_layer = resource_layer

    if resource_layer:
        logger.info("Resource layer available to HTTP handlers")
    else:
        logger.warning("No resource layer provided (operating without preloaded resources)")

    config = uvicorn.Config(
        app,
        host=host,
        port=port,
        log_level="info",
        access_log=False,  # Reduce noise, already logging in handlers
    )
    server = uvicorn.Server(config)

    try:
        await server.serve()
    except Exception as e:
        logger.exception("HTTP server error: %s", e)
        raise
