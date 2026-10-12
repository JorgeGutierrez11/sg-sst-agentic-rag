"""Compatibility import for the unified agent API."""

from agents.api.main import ALLOWED_ORIGINS, app, create_app


__all__ = ["ALLOWED_ORIGINS", "app", "create_app"]
