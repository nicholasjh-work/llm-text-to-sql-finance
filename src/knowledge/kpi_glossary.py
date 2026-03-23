"""
KPI Glossary: maps finance business terms to governed SQL definitions.

When the SQL generator detects a KPI term in a user's question,
it injects the exact SQL definition into the LLM prompt. This ensures
consistent metric calculations regardless of who asks the question.
"""
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml

logger = logging.getLogger(__name__)

CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "kpi_definitions.yaml"


@dataclass
class KPIDefinition:
    name: str
    display_name: str
    sql: str
    grain: str
    source_view: str
    description: str = ""


# Default KPI definitions. Production: load from kpi_definitions.yaml or a metadata catalog.
_DEFAULT_KPIS = [
    KPIDefinition(
        name="gross_margin",
        display_name="Gross Margin",
        sql="(SUM(revenue) - SUM(cogs)) / NULLIF(SUM(revenue), 0)",
        grain="division, month",
        source_view="v_revenue",
        description="Gross margin percentage calculated as (revenue - COGS) / revenue",
    ),
    KPIDefinition(
        name="net_revenue",
        display_name="Net Revenue",
        sql="SUM(revenue)",
        grain="division, month",
        source_view="v_revenue",
        description="Total net revenue after returns and adjustments",
    ),
    KPIDefinition(
        name="opex_variance",
        display_name="OPEX Variance",
        sql="SUM(actual_opex) - SUM(budget_opex)",
        grain="cost_center, month",
        source_view="v_opex",
        description="Actual OPEX minus budgeted OPEX. Positive = over budget.",
    ),
    KPIDefinition(
        name="opex_variance_pct",
        display_name="OPEX Variance %",
        sql="(SUM(actual_opex) - SUM(budget_opex)) / NULLIF(SUM(budget_opex), 0)",
        grain="cost_center, month",
        source_view="v_opex",
        description="OPEX variance as a percentage of budget",
    ),
    KPIDefinition(
        name="revenue_per_unit",
        display_name="Revenue per Unit",
        sql="SUM(revenue) / NULLIF(SUM(units_sold), 0)",
        grain="division, product_line, month",
        source_view="v_revenue",
        description="Average revenue per unit sold",
    ),
]

# Build lookup index: map display names and aliases to definitions
_KPI_INDEX: dict[str, KPIDefinition] = {}


def _build_index() -> None:
    """Build the KPI lookup index from definitions."""
    global _KPI_INDEX
    kpis = _load_kpis()
    for kpi in kpis:
        # Index by canonical name and display name (lowercased)
        _KPI_INDEX[kpi.name.lower()] = kpi
        _KPI_INDEX[kpi.display_name.lower()] = kpi
        # Also index common variations
        _KPI_INDEX[kpi.display_name.lower().replace(" ", "_")] = kpi


def _load_kpis() -> list[KPIDefinition]:
    """Load KPI definitions from YAML config or defaults."""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            data = yaml.safe_load(f)
        kpis = []
        for name, entry in data.get("kpis", {}).items():
            kpis.append(KPIDefinition(
                name=name,
                display_name=entry.get("display_name", name),
                sql=entry["sql"],
                grain=entry.get("grain", ""),
                source_view=entry.get("source_view", ""),
                description=entry.get("description", ""),
            ))
        return kpis
    return list(_DEFAULT_KPIS)


def lookup_kpi_terms(question: str) -> list[KPIDefinition]:
    """Find KPI definitions that match terms in the user's question.

    Scans the question for known KPI names and returns matching definitions.
    These get injected into the LLM prompt to ensure governed calculations.
    """
    if not _KPI_INDEX:
        _build_index()

    question_lower = question.lower()
    matched = []
    seen = set()

    for term, kpi in _KPI_INDEX.items():
        if term in question_lower and kpi.name not in seen:
            matched.append(kpi)
            seen.add(kpi.name)

    if matched:
        logger.info("KPI terms matched: %s", [k.display_name for k in matched])

    return matched
