"""Additional API routers exposed outside of the versioned namespace."""

from .metrics import attach_metrics_endpoint

__all__ = ["attach_metrics_endpoint"]
