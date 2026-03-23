"""Tests for SQL safety validator."""
import pytest

from src.sql_engine.validator import validate_query

AUTHORIZED_TABLES = ["v_revenue", "v_opex", "v_margin_by_division", "fact_revenue"]


class TestSelectOnly:
    def test_valid_select(self):
        result = validate_query("SELECT division, SUM(revenue) FROM v_revenue WHERE month >= '2024-01-01' GROUP BY division", AUTHORIZED_TABLES)
        assert result.is_safe is True

    def test_rejects_drop(self):
        result = validate_query("DROP TABLE v_revenue", AUTHORIZED_TABLES)
        assert result.is_safe is False
        assert result.rule == "select_only"

    def test_rejects_delete(self):
        result = validate_query("DELETE FROM v_revenue WHERE month < '2024-01-01'", AUTHORIZED_TABLES)
        assert result.is_safe is False

    def test_rejects_insert(self):
        result = validate_query("INSERT INTO v_revenue VALUES ('test', '2024-01-01', 100)", AUTHORIZED_TABLES)
        assert result.is_safe is False


class TestBlockedKeywords:
    def test_rejects_update_in_select(self):
        result = validate_query("SELECT * FROM v_revenue; UPDATE v_revenue SET revenue = 0", AUTHORIZED_TABLES)
        assert result.is_safe is False

    def test_allows_column_named_updated(self):
        """Column names containing blocked words should not trigger rejection."""
        result = validate_query("SELECT updated_at FROM v_revenue WHERE month >= '2024-01-01'", AUTHORIZED_TABLES)
        assert result.is_safe is True


class TestTableAuthorization:
    def test_rejects_unauthorized_table(self):
        result = validate_query("SELECT * FROM secret_salaries WHERE id = 1", AUTHORIZED_TABLES)
        assert result.is_safe is False
        assert result.rule == "table_authorization"
        assert "secret_salaries" in result.reason

    def test_allows_authorized_table(self):
        result = validate_query("SELECT division, revenue FROM v_revenue WHERE month = '2024-06-01'", AUTHORIZED_TABLES)
        assert result.is_safe is True


class TestSelectStar:
    def test_rejects_select_star(self):
        result = validate_query("SELECT * FROM v_revenue WHERE month = '2024-01-01'", AUTHORIZED_TABLES)
        assert result.is_safe is False
        assert result.rule == "no_select_star"

    def test_allows_count_star(self):
        result = validate_query("SELECT COUNT(*) FROM v_revenue WHERE month >= '2024-01-01'", AUTHORIZED_TABLES)
        assert result.is_safe is True


class TestFactTableWhere:
    def test_rejects_fact_table_without_where(self):
        result = validate_query("SELECT division, SUM(revenue) FROM fact_revenue GROUP BY division", AUTHORIZED_TABLES)
        assert result.is_safe is False
        assert result.rule == "fact_table_where"

    def test_allows_fact_table_with_where(self):
        result = validate_query("SELECT division, SUM(revenue) FROM fact_revenue WHERE month >= '2024-01-01' GROUP BY division", AUTHORIZED_TABLES)
        assert result.is_safe is True


class TestEmptyQuery:
    def test_rejects_empty(self):
        result = validate_query("", AUTHORIZED_TABLES)
        assert result.is_safe is False

    def test_rejects_whitespace(self):
        result = validate_query("   ", AUTHORIZED_TABLES)
        assert result.is_safe is False


class TestInjectionPatterns:
    def test_rejects_multistatement(self):
        result = validate_query("SELECT 1 FROM v_revenue WHERE 1=1; DROP TABLE v_revenue", AUTHORIZED_TABLES)
        assert result.is_safe is False

    def test_rejects_comment_injection(self):
        result = validate_query("SELECT division FROM v_revenue -- WHERE restricted = true", AUTHORIZED_TABLES)
        assert result.is_safe is False

    def test_rejects_information_schema(self):
        result = validate_query("SELECT table_name FROM INFORMATION_SCHEMA.TABLES", AUTHORIZED_TABLES)
        assert result.is_safe is False
