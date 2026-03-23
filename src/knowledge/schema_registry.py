"""
Schema Registry: stores table and column metadata with descriptions.

Production: populate from Snowflake INFORMATION_SCHEMA or dbt catalog.
Development: uses static definitions matching the schema resolver.
"""
from src.sql_engine.schema_resolver import SchemaContext

# Re-export for clean imports
__all__ = ["SchemaContext"]
