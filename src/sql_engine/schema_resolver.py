"""
Schema Resolver: maps user roles to authorized Snowflake schemas, tables, and views.

Reads configuration from config/roles.yaml and provides the schema context
that gets injected into the LLM prompt. The LLM only sees tables and columns
the user is authorized to query.
"""
import logging
from dataclasses import dataclass, field
from typing import Optional

import yaml
from pathlib import Path

logger = logging.getLogger(__name__)

CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "roles.yaml"


@dataclass
class ColumnInfo:
    name: str
    data_type: str
    description: str = ""


@dataclass
class TableInfo:
    name: str
    description: str = ""
    columns: list[ColumnInfo] = field(default_factory=list)


@dataclass
class SchemaContext:
    role: str
    schemas: list[str]
    tables: list[TableInfo] = field(default_factory=list)

    @property
    def table_names(self) -> list[str]:
        return [t.name for t in self.tables]

    def to_prompt_text(self) -> str:
        """Format schema context for LLM prompt injection."""
        lines = []
        for table in self.tables:
            cols = ", ".join(f"{c.name} ({c.data_type})" for c in table.columns)
            desc = f" -- {table.description}" if table.description else ""
            lines.append(f"Table: {table.name}{desc}")
            lines.append(f"  Columns: {cols}")
        return "\n".join(lines)


# Default schema definitions for development.
# Production: load from a metadata catalog (Snowflake INFORMATION_SCHEMA, dbt catalog, etc.)
_DEFAULT_TABLES = {
    "finance_reporting": [
        TableInfo(
            name="v_revenue",
            description="Monthly revenue by division and product line",
            columns=[
                ColumnInfo("division", "VARCHAR", "Business division name"),
                ColumnInfo("product_line", "VARCHAR", "Product line"),
                ColumnInfo("month", "DATE", "First day of month"),
                ColumnInfo("revenue", "DECIMAL(15,2)", "Net revenue"),
                ColumnInfo("cogs", "DECIMAL(15,2)", "Cost of goods sold"),
                ColumnInfo("units_sold", "INTEGER", "Units sold"),
            ],
        ),
        TableInfo(
            name="v_opex",
            description="Monthly operating expenses by cost center",
            columns=[
                ColumnInfo("cost_center", "VARCHAR", "Cost center name"),
                ColumnInfo("month", "DATE", "First day of month"),
                ColumnInfo("actual_opex", "DECIMAL(15,2)", "Actual OPEX spend"),
                ColumnInfo("budget_opex", "DECIMAL(15,2)", "Budgeted OPEX"),
                ColumnInfo("category", "VARCHAR", "Expense category"),
            ],
        ),
        TableInfo(
            name="v_margin_by_division",
            description="Gross margin by division, month",
            columns=[
                ColumnInfo("division", "VARCHAR", "Business division"),
                ColumnInfo("month", "DATE", "First day of month"),
                ColumnInfo("gross_margin_pct", "DECIMAL(5,4)", "Gross margin percentage"),
                ColumnInfo("revenue", "DECIMAL(15,2)", "Revenue"),
                ColumnInfo("cogs", "DECIMAL(15,2)", "COGS"),
            ],
        ),
    ],
    "finance_detail": [
        TableInfo(
            name="v_journal_entries",
            description="General ledger journal entries",
            columns=[
                ColumnInfo("journal_id", "VARCHAR", "Journal entry ID"),
                ColumnInfo("posting_date", "DATE", "Posting date"),
                ColumnInfo("account_code", "VARCHAR", "GL account code"),
                ColumnInfo("debit", "DECIMAL(15,2)", "Debit amount"),
                ColumnInfo("credit", "DECIMAL(15,2)", "Credit amount"),
                ColumnInfo("description", "VARCHAR", "Entry description"),
            ],
        ),
        TableInfo(
            name="v_trial_balance",
            description="Monthly trial balance by account",
            columns=[
                ColumnInfo("account_code", "VARCHAR", "GL account code"),
                ColumnInfo("account_name", "VARCHAR", "Account name"),
                ColumnInfo("month", "DATE", "Period"),
                ColumnInfo("balance", "DECIMAL(15,2)", "Ending balance"),
            ],
        ),
    ],
}


def _load_role_config() -> dict:
    """Load role-to-schema mappings from YAML config."""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return yaml.safe_load(f).get("roles", {})

    # Default if config file doesn't exist
    return {
        "fpa_analyst": {"schemas": ["finance_reporting"]},
        "controller": {"schemas": ["finance_reporting", "finance_detail"]},
        "cfo": {"schemas": ["finance_reporting", "finance_detail"]},
    }


def resolve_schema(role: str) -> SchemaContext:
    """Resolve the authorized schema context for a given role.

    Returns only the tables and columns the role is allowed to query.
    """
    role_config = _load_role_config()
    role_entry = role_config.get(role, role_config.get("fpa_analyst", {}))
    allowed_schemas = role_entry.get("schemas", [])

    tables = []
    for schema_name in allowed_schemas:
        schema_tables = _DEFAULT_TABLES.get(schema_name, [])
        tables.extend(schema_tables)

    logger.info("Resolved schema for role=%s: %d tables from %s", role, len(tables), allowed_schemas)

    return SchemaContext(role=role, schemas=allowed_schemas, tables=tables)
