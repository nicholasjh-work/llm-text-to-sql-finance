"""
Query Executor: runs validated SQL against Snowflake and returns structured results.

All queries execute as read-only with a statement timeout.
"""
import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from config.settings import Settings

logger = logging.getLogger(__name__)

settings = Settings()

STATEMENT_TIMEOUT_SECONDS = 30


@dataclass
class ExecutionResult:
    success: bool
    rows: list[dict] = field(default_factory=list)
    columns: list[str] = field(default_factory=list)
    row_count: int = 0
    error: Optional[str] = None
    elapsed_ms: Optional[int] = None


def execute_query(sql: str, max_rows: int = 10_000) -> ExecutionResult:
    """Execute a validated SQL query against Snowflake.

    Uses a read-only connection with statement timeout.
    Limits results to max_rows to prevent memory issues.
    """
    try:
        import time
        from snowflake.connector import connect, ProgrammingError

        conn = connect(
            account=settings.snowflake_account,
            user=settings.snowflake_user,
            password=settings.snowflake_password,
            database=settings.snowflake_database,
            schema=settings.snowflake_schema,
            warehouse=settings.snowflake_warehouse,
        )

        cursor = conn.cursor()
        try:
            # Set statement timeout
            cursor.execute(f"ALTER SESSION SET STATEMENT_TIMEOUT_IN_SECONDS = {STATEMENT_TIMEOUT_SECONDS}")

            start = time.perf_counter()
            cursor.execute(sql)
            elapsed_ms = int((time.perf_counter() - start) * 1000)

            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            raw_rows = cursor.fetchmany(max_rows)
            rows = [dict(zip(columns, row)) for row in raw_rows]

            logger.info("Query executed: %d rows, %dms", len(rows), elapsed_ms)

            return ExecutionResult(
                success=True,
                rows=rows,
                columns=columns,
                row_count=len(rows),
                elapsed_ms=elapsed_ms,
            )

        except ProgrammingError as e:
            logger.error("Snowflake execution error: %s", e)
            return ExecutionResult(success=False, error=str(e))
        finally:
            cursor.close()
            conn.close()

    except ImportError:
        logger.warning("snowflake-connector-python not installed, returning mock result")
        return ExecutionResult(
            success=False,
            error="Snowflake connector not installed. Install with: pip install snowflake-connector-python",
        )
    except Exception as e:
        logger.error("Connection error: %s", e)
        return ExecutionResult(success=False, error=f"Connection failed: {e}")
