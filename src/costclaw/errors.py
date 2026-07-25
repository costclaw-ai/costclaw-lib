"""Exceptions raised by the CostClaw client."""

from __future__ import annotations

from typing import Optional


class CostClawError(Exception):
    """Base class for all client errors."""


class APIError(CostClawError):
    """The API returned a non-2xx response.

    ``status_code`` is the HTTP status; ``detail`` is the server's message
    (parsed from the JSON ``detail``/``error`` field when present)."""

    def __init__(self, status_code: int, detail: Optional[str] = None):
        self.status_code = status_code
        self.detail = detail or ""
        super().__init__(f"[{status_code}] {self.detail}".strip())


class AuthenticationError(APIError):
    """401 — the API key is missing or invalid."""


class PermissionDeniedError(APIError):
    """403 — the API key's role is too low for this action (e.g. a read-only
    key attempting a write, or a non-admin key deleting documents)."""


class NotFoundError(APIError):
    """404 — the resource doesn't exist or isn't in the key's project."""
