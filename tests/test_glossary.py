"""Tests for KPI glossary lookup."""
import pytest

from src.knowledge.kpi_glossary import lookup_kpi_terms, _build_index, _KPI_INDEX


@pytest.fixture(autouse=True)
def reset_index():
    """Reset the KPI index before each test."""
    _KPI_INDEX.clear()
    _build_index()
    yield
    _KPI_INDEX.clear()


class TestKPILookup:
    def test_matches_gross_margin(self):
        results = lookup_kpi_terms("Show me gross margin by division for Q3")
        assert len(results) >= 1
        assert any(k.name == "gross_margin" for k in results)

    def test_matches_opex_variance(self):
        results = lookup_kpi_terms("What is the OPEX variance for engineering this month?")
        assert any(k.name == "opex_variance" for k in results)

    def test_no_match_for_unrelated_question(self):
        results = lookup_kpi_terms("How many employees are in the Boston office?")
        assert len(results) == 0

    def test_multiple_kpis_in_one_question(self):
        results = lookup_kpi_terms("Compare net revenue and gross margin by division")
        names = [k.name for k in results]
        assert "net_revenue" in names
        assert "gross_margin" in names

    def test_kpi_has_sql_definition(self):
        results = lookup_kpi_terms("What is gross margin?")
        assert len(results) >= 1
        kpi = results[0]
        assert "SUM(revenue)" in kpi.sql
        assert kpi.source_view == "v_revenue"

    def test_case_insensitive(self):
        results = lookup_kpi_terms("GROSS MARGIN for last quarter")
        assert any(k.name == "gross_margin" for k in results)
