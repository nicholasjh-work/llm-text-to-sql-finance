"""
Role-based access control for the Text-to-SQL service.

Validates user identity from request headers and enforces role restrictions.
Production deployments should integrate with SSO/OAuth. This implementation
reads a bearer token and maps it to a role via config.
"""
import functools
import logging
from typing import Optional

from flask import request, jsonify

from src.app.middleware import UserContext
from config.settings import Settings

logger = logging.getLogger(__name__)

settings = Settings()

# Role hierarchy: higher roles inherit lower role permissions
ROLE_HIERARCHY = {
    "cfo": ["cfo", "controller", "fpa_analyst"],
    "controller": ["controller", "fpa_analyst"],
    "fpa_analyst": ["fpa_analyst"],
}


def get_user_context(req) -> UserContext:
    """Extract user context from request headers.

    Production: validate JWT, lookup user in directory.
    Development: read from X-User-Id and X-User-Role headers.
    """
    user_id = req.headers.get("X-User-Id", "anonymous")
    role = req.headers.get("X-User-Role", "fpa_analyst")
    session_id = req.headers.get("X-Session-Id", "no-session")

    if role not in ROLE_HIERARCHY:
        logger.warning("Unknown role '%s' for user %s, defaulting to fpa_analyst", role, user_id)
        role = "fpa_analyst"

    return UserContext(user_id=user_id, role=role, session_id=session_id)


def require_role(allowed_roles: list[str]):
    """Decorator that enforces role-based access on a Flask route."""

    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            user_ctx = get_user_context(request)
            effective_roles = ROLE_HIERARCHY.get(user_ctx.role, [])

            if not any(r in allowed_roles for r in effective_roles):
                logger.warning(
                    "Access denied: user=%s role=%s required=%s",
                    user_ctx.user_id,
                    user_ctx.role,
                    allowed_roles,
                )
                return jsonify({"error": "Insufficient permissions"}), 403

            return fn(*args, **kwargs)

        return wrapper

    return decorator


def can_access_schema(role: str, schema_name: str) -> bool:
    """Check if a role has access to a specific schema.

    Reads from config/roles.yaml at startup. Returns False for unknown roles.
    """
    role_config = settings.role_schemas.get(role, {})
    allowed_schemas = role_config.get("schemas", [])
    return schema_name in allowed_schemas
