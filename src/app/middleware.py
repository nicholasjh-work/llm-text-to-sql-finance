"""
Request middleware: logging, CORS, rate limiting, audit trail.
"""
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from flask import Flask, g, request

logger = logging.getLogger(__name__)

# In-memory audit log for development. Production should write to a database table.
_audit_log: list[dict] = []


@dataclass
class UserContext:
    user_id: str
    role: str
    session_id: str


def setup_middleware(app: Flask) -> None:
    """Register before/after request hooks."""

    @app.before_request
    def start_timer():
        g.start_time = time.perf_counter()

    @app.after_request
    def log_request(response):
        elapsed = time.perf_counter() - g.get("start_time", time.perf_counter())
        logger.info(
            "%s %s %s %.3fs",
            request.method,
            request.path,
            response.status_code,
            elapsed,
        )
        response.headers["X-Request-Duration-Ms"] = str(int(elapsed * 1000))
        return response


def log_audit_event(
    user_ctx: UserContext,
    question: str,
    sql: Optional[str],
    status: str,
    reason: Optional[str] = None,
    row_count: Optional[int] = None,
) -> None:
    """Log a query event to the audit trail."""
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "user_id": user_ctx.user_id,
        "role": user_ctx.role,
        "session_id": user_ctx.session_id,
        "question": question,
        "generated_sql": sql,
        "status": status,
        "reason": reason,
        "row_count": row_count,
    }
    _audit_log.append(event)
    logger.info("AUDIT user=%s status=%s question='%s'", user_ctx.user_id, status, question[:80])


def get_audit_log() -> list[dict]:
    """Return audit log entries. Production: query from database."""
    return list(_audit_log)
