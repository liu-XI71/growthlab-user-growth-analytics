from __future__ import annotations

import os
from typing import Any

import httpx

API_BASE_URL = os.getenv("GROWTHLAB_API_URL", "http://localhost:8000").rstrip("/")


class APIError(RuntimeError):
    """Raised when the analytics API cannot satisfy a request."""


def _request(method: str, path: str, **kwargs: Any) -> dict[str, Any]:
    try:
        response = httpx.request(
            method,
            f"{API_BASE_URL}{path}",
            timeout=20,
            **kwargs,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        detail = getattr(exc.response, "text", "") if getattr(exc, "response", None) else ""
        raise APIError(f"Analytics API request failed: {exc}. {detail[:300]}") from exc
    payload = response.json()
    if not isinstance(payload, dict):
        raise APIError(f"Expected an object from {path}, received {type(payload).__name__}.")
    return payload


def api_get(path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    return _request("GET", path, params=params)


def api_post(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    return _request("POST", path, json=payload)
