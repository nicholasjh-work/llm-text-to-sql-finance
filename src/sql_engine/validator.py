"""
SQL Validator: enforces safety rules on generated queries before execution.

Every query must pass all rules to execute. Failed validations are logged
with the specific rule that triggered rejection.
"""
import logging
import re
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

# Blocked SQL patterns
BLOCKED_KEYWORDS = [
    "DROP", "DELETE", "TRUNCATE", "ALTER", "CREATE", "INSERT",
    "UPDATE", "GRANT", "REVOKE", "EXEC", "EXECUTE", "MERGE",
    "CALL", "COPY", "UNLOAD", "PUT",
]

# Patterns that indicate potentially dangerous queries
BLOCKED_PATTERNS = [
    re.compile(r";\s*\w", re.IGNORECASE),  # multi-statement
    re.compile(r"--", re.IGNORECASE),        # SQL comments (injection risk)
    re.compile(r"/\*.*?\*/", re.DOTALL),     # block comments
    re.compile(r"INFORMATION_SCHEMA", re.IGNORECASE),  # schema enumeration
    re.compile(r"pg_catalog|pg_stat", re.IGNORECASE),  # postgres internals
    re.compile(r"ACCOUNT_USAGE", re.IGNORECASE),       # snowflake internals
]


@dataclass
class ValidationResult:
    is_safe: bool
    reason: Optional[str] = None
    rule: Optional[str] = None


def validate_query(sql: str, authorized_tables: list[str]) -> ValidationResult:
    """Validate a generated SQL query against safety rules.

    Returns ValidationResult with is_safe=True if all rules pass.
    Stops at the first failing rule.
    """
    if not sql or not sql.strip():
        return ValidationResult(is_safe=False, reason="Empty query", rule="non_empty")

    sql_clean = sql.strip().rstrip(";")
    sql_upper = sql_clean.upper()

    # Rule 1: Must be a SELECT statement
    if not sql_upper.startswith("SELECT"):
        return ValidationResult(
            is_safe=False,
            reason="Only SELECT statements are allowed",
            rule="select_only",
        )

    # Rule 2: No blocked keywords
    for keyword in BLOCKED_KEYWORDS:
        # Match as whole word to avoid false positives (e.g., "UPDATED_AT")
        pattern = re.compile(rf"\b{keyword}\b", re.IGNORECASE)
        if pattern.search(sql_clean):
            return ValidationResult(
                is_safe=False,
                reason=f"Blocked keyword detected: {keyword}",
                rule="blocked_keyword",
            )

    # Rule 3: No blocked patterns
    for pattern in BLOCKED_PATTERNS:
        if pattern.search(sql_clean):
            return ValidationResult(
                is_safe=False,
                reason=f"Blocked pattern detected: {pattern.pattern}",
                rule="blocked_pattern",
            )

    # Rule 4: All referenced tables must be in the authorized list
    unauthorized = _find_unauthorized_tables(sql_clean, authorized_tables)
    if unauthorized:
        return ValidationResult(
            is_safe=False,
            reason=f"Unauthorized table(s): {', '.join(unauthorized)}",
            rule="table_authorization",
        )

    # Rule 5: No SELECT * on large tables (require explicit columns)
    if _has_select_star(sql_upper):
        return ValidationResult(
            is_safe=False,
            reason="SELECT * is not allowed. Specify columns explicitly.",
            rule="no_select_star",
        )

    # Rule 6: Fact tables must have a WHERE clause
    fact_tables = [t for t in authorized_tables if t.lower().startswith(("fact_", "f_"))]
    if _references_fact_table(sql_upper, fact_tables) and "WHERE" not in sql_upper:
        return ValidationResult(
            is_safe=False,
            reason="Queries on fact tables require a WHERE clause",
            rule="fact_table_where",
        )

    logger.info("Query passed all validation rules")
    return ValidationResult(is_safe=True)


def _find_unauthorized_tables(sql: str, authorized_tables: list[str]) -> list[str]:
    """Extract table names from SQL and check against authorized list."""
    authorized_lower = {t.lower() for t in authorized_tables}

    # Extract table names from FROM and JOIN clauses
    table_pattern = re.compile(
        r"(?:FROM|JOIN)\s+([a-zA-Z_][\w.]*)",
        re.IGNORECASE,
    )
    referenced = {m.group(1).lower() for m in table_pattern.finditer(sql)}

    # Strip schema prefixes for comparison (e.g., "finance.v_revenue" -> "v_revenue")
    stripped = set()
    for t in referenced:
        parts = t.split(".")
        stripped.add(parts[-1])

    return sorted(stripped - authorized_lower)


def _has_select_star(sql_upper: str) -> bool:
    """Check if query uses SELECT * (not inside COUNT(*) or similar)."""
    # Remove aggregate function uses of *
    cleaned = re.sub(r"\w+\s*\(\s*\*\s*\)", "", sql_upper)
    return bool(re.search(r"SELECT\s+\*", cleaned))


def _references_fact_table(sql_upper: str, fact_tables: list[str]) -> bool:
    """Check if the query references any fact table."""
    for table in fact_tables:
        if table.upper() in sql_upper:
            return True
    return False
