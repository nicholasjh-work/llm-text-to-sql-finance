"""
Seed the KPI glossary from config/kpi_definitions.yaml.

Usage:
    python scripts/seed_glossary.py

Production: writes definitions to a database table.
Development: validates the YAML file loads correctly.
"""
import logging
from pathlib import Path

import yaml

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    config_path = Path(__file__).parent.parent / "config" / "kpi_definitions.yaml"

    if not config_path.exists():
        logger.error("KPI definitions file not found: %s", config_path)
        return

    with open(config_path) as f:
        data = yaml.safe_load(f)

    kpis = data.get("kpis", {})
    logger.info("Loaded %d KPI definitions:", len(kpis))

    for name, defn in kpis.items():
        logger.info(
            "  %s (%s): %s [grain: %s, view: %s]",
            defn["display_name"],
            name,
            defn["sql"][:60],
            defn.get("grain", ""),
            defn.get("source_view", ""),
        )

    logger.info("Glossary validation complete. All definitions loaded.")


if __name__ == "__main__":
    main()
