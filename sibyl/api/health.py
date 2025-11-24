"""Detailed health endpoints for the Sibyl API."""

import os
from datetime import datetime
from typing import Any

import psutil
import requests
from fastapi import APIRouter

from sibyl.techniques.registry import iter_technique_classes

router = APIRouter()


@router.get("/health/detailed")
def detailed_health() -> dict[str, Any]:
    """Comprehensive health check including external services."""
    health: dict[str, Any] = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "0.1.0",
        "techniques": {},
        "external_services": {},
        "storage": {},
        "dependencies": {},
    }

    # Check techniques
    for name, technique_class in iter_technique_classes():
        health["techniques"][name] = check_technique_health(name, technique_class)

    # Check external services
    health["external_services"] = {
        "openai_api": check_openai_api(),
        "anthropic_api": check_anthropic_api(),
        "cohere_api": check_cohere_api(),
    }

    # Check storage and dependencies
    health["storage"] = check_storage_health()
    health["dependencies"] = check_dependencies()

    # Overall status
    if any(t.get("status") == "unhealthy" for t in health["techniques"].values()):
        health["status"] = "degraded"

    if any(s.get("status") == "down" for s in health["external_services"].values()):
        health["status"] = "degraded"

    if health["dependencies"].get("status") == "degraded":
        health["status"] = "degraded"

    if health["storage"].get("status") == "down":
        health["status"] = "degraded"

    return health


def _call_external(url: str) -> dict[str, Any]:
    """Helper to call an external HTTP endpoint with timeouts."""
    if os.getenv("SIBYL_SKIP_EXTERNAL_HEALTH", "").lower() in {"1", "true", "yes"}:
        return {
            "status": "skipped",
            "last_check": datetime.utcnow().isoformat(),
            "message": "External health checks disabled",
        }

    try:
        response = requests.get(url, timeout=5)
        status = "up" if response.status_code < 500 else "down"
        return {
            "status": status,
            "latency_ms": response.elapsed.total_seconds() * 1000,
            "status_code": response.status_code,
            "last_check": datetime.utcnow().isoformat(),
        }
    except Exception as exc:
        return {
            "status": "down",
            "error": str(exc),
            "last_check": datetime.utcnow().isoformat(),
        }


def check_openai_api() -> dict[str, Any]:
    """Check OpenAI API health."""
    return _call_external("https://api.openai.com/v1/models")


def check_anthropic_api() -> dict[str, Any]:
    """Check Anthropic API health."""
    return _call_external("https://api.anthropic.com/v1/models")


def check_cohere_api() -> dict[str, Any]:
    """Check Cohere API health."""
    return _call_external("https://api.cohere.ai/v1/models")


def check_storage_health() -> dict[str, Any]:
    """Basic storage health using local disk statistics."""
    try:
        usage = psutil.disk_usage("/")
        return {
            "status": "up",
            "free_gb": round(usage.free / 1024 / 1024 / 1024, 2),
            "used_percent": usage.percent,
            "last_check": datetime.utcnow().isoformat(),
        }
    except Exception as exc:
        return {
            "status": "down",
            "error": str(exc),
            "last_check": datetime.utcnow().isoformat(),
        }


def check_dependencies() -> dict[str, Any]:
    """Check presence of critical dependencies."""
    deps = {
        "requests": {"status": "ok"},
        "psutil": {"status": "ok"},
    }

    overall_status = "ok"
    for dep in list(deps.keys()):
        try:
            __import__(dep)
        except Exception as exc:
            deps[dep] = {"status": "missing", "error": str(exc)}
            overall_status = "degraded"

    deps["status"] = overall_status
    deps["last_check"] = datetime.utcnow().isoformat()
    return deps


def check_technique_health(name: str, technique_class: type) -> dict[str, Any]:
    """Check technique initialization and configuration access."""
    try:
        instance = technique_class()
        try:
            config = instance.get_config() if hasattr(instance, "get_config") else {}
        except Exception as exc:
            config = {"error": str(exc)}

        subtechniques = []
        if hasattr(instance, "list_subtechniques"):
            try:
                listing = instance.list_subtechniques()
                if isinstance(listing, dict):
                    subtechniques = list(listing.keys())
                elif isinstance(listing, (list, tuple, set)):
                    subtechniques = list(listing)
            except Exception:
                subtechniques = []

        return {
            "status": "healthy",
            "subtechniques": subtechniques,
            "config_keys": list(config.keys()) if isinstance(config, dict) else [],
        }
    except Exception as exc:
        return {"status": "unhealthy", "error": str(exc)}
