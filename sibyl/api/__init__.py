"""Public API routers for the Sibyl FastAPI server."""

from .health import router as health_router

__all__ = ["health_router"]
