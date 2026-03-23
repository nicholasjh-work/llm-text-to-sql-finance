"""Shared test fixtures."""
import pytest


@pytest.fixture
def authorized_tables():
    return ["v_revenue", "v_opex", "v_margin_by_division", "v_journal_entries", "v_trial_balance"]


@pytest.fixture
def sample_question():
    return "Show me gross margin by division for Q3 2024"
