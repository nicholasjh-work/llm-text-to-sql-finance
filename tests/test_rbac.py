"""Tests for role-based access control."""
import pytest

from src.auth.rbac import ROLE_HIERARCHY, can_access_schema
from src.sql_engine.schema_resolver import resolve_schema


class TestRoleHierarchy:
    def test_cfo_inherits_all_roles(self):
        assert "cfo" in ROLE_HIERARCHY["cfo"]
        assert "controller" in ROLE_HIERARCHY["cfo"]
        assert "fpa_analyst" in ROLE_HIERARCHY["cfo"]

    def test_controller_inherits_analyst(self):
        assert "fpa_analyst" in ROLE_HIERARCHY["controller"]
        assert "cfo" not in ROLE_HIERARCHY["controller"]

    def test_analyst_has_only_own_role(self):
        assert ROLE_HIERARCHY["fpa_analyst"] == ["fpa_analyst"]


class TestSchemaResolution:
    def test_analyst_gets_reporting_only(self):
        ctx = resolve_schema("fpa_analyst")
        assert "finance_reporting" in ctx.schemas
        assert "finance_detail" not in ctx.schemas

    def test_controller_gets_both_schemas(self):
        ctx = resolve_schema("controller")
        assert "finance_reporting" in ctx.schemas
        assert "finance_detail" in ctx.schemas

    def test_analyst_cannot_see_journal_entries(self):
        ctx = resolve_schema("fpa_analyst")
        table_names = [t.name for t in ctx.tables]
        assert "v_journal_entries" not in table_names
        assert "v_revenue" in table_names

    def test_controller_can_see_journal_entries(self):
        ctx = resolve_schema("controller")
        table_names = [t.name for t in ctx.tables]
        assert "v_journal_entries" in table_names

    def test_unknown_role_defaults_to_analyst(self):
        ctx = resolve_schema("unknown_role")
        assert "finance_reporting" in ctx.schemas
        assert "finance_detail" not in ctx.schemas

    def test_prompt_text_includes_columns(self):
        ctx = resolve_schema("fpa_analyst")
        prompt = ctx.to_prompt_text()
        assert "v_revenue" in prompt
        assert "revenue" in prompt
        assert "DECIMAL" in prompt
