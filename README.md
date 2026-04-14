<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/nh-logo-dark.svg" width="80">
    <source media="(prefers-color-scheme: light)" srcset="assets/nh-logo-light.svg" width="80">
    <img alt="Hidalgo Systems Labs" src="assets/nh-logo-light.svg" width="80">
  </picture>
</p>

<h1 align="center">Governed Text-to-SQL for Finance Teams</h1>
<p align="center"><b>Natural-language query interface with RBAC, audit logging, KPI glossary, and SQL safety validation</b></p>

<p align="center">
  <a href="https://nicholasjh-work.github.io/llm-text-to-sql-finance/"><img src="https://img.shields.io/badge/Demo-Live-2563EB?style=for-the-badge" alt="Demo"></a>
  <a href="https://github.com/nicholasjh-work/llm-text-to-sql-finance/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge" alt="License"></a>
  <a href="https://github.com/nicholasjh-work/llm-text-to-sql-finance/tree/main/tests"><img src="https://img.shields.io/badge/Tests-32_passing-16a34a?style=for-the-badge" alt="Tests"></a>
  <a href="https://github.com/nicholasjh-work/llm-text-to-sql-finance"><img src="https://img.shields.io/badge/Confidence-0.91+-7c3aed?style=for-the-badge" alt="Confidence"></a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11-3776AB?style=flat&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Flask-000000?style=flat&logo=flask&logoColor=white" alt="Flask">
  <img src="https://img.shields.io/badge/Snowflake-29B5E8?style=flat&logo=snowflake&logoColor=white" alt="Snowflake">
  <img src="https://img.shields.io/badge/LLM_API-1C3C3C?style=flat" alt="LLM">
  <img src="https://img.shields.io/badge/YAML-CB171E?style=flat&logo=yaml&logoColor=white" alt="YAML">
  <img src="https://img.shields.io/badge/pytest-0A9EDC?style=flat&logo=pytest&logoColor=white" alt="pytest">
</p>

---

### What This Does

<table>
<tr>
<td>

**5,000+ non-technical users** query a Snowflake data warehouse using plain English. The LLM converts questions into SQL with schema awareness, role-based access control, and a governed KPI glossary that ensures "gross margin" always produces the same calculation regardless of who asks.

Every generated query passes through a **safety validator** (blocks DDL/DML, enforces schema authorization, requires WHERE clauses on large tables) and is logged to an **audit trail** with user, role, query, status, and timestamp.

Built for FP&A teams who depended on analysts for ad-hoc queries, creating 3-5 day delays and inconsistent reporting.

**No unvalidated SQL reaches the database. Every query is governed, logged, and auditable.**

</td>
</tr>
</table>

---

### Key Results

| Metric | Value |
|:-------|:------|
| ![Turnaround](https://img.shields.io/badge/Reporting_Turnaround-7c3aed?style=flat-square) | **3-5 days reduced to 10 seconds** |
| ![Analyst](https://img.shields.io/badge/Analyst_Capacity-2563EB?style=flat-square) | **20+ hours freed per week** |
| ![Errors](https://img.shields.io/badge/Query_Errors-16a34a?style=flat-square) | **Reduced 75%** through governed KPI glossary |
| ![Confidence](https://img.shields.io/badge/Confidence_Threshold-d29922?style=flat-square) | **0.91+ required** before query execution |
| ![Safety](https://img.shields.io/badge/Safety_Tests-f85149?style=flat-square) | **32 passing** (SELECT-only, schema auth, injection detection) |

---

### Architecture

```
User Question
        │
        ▼
┌──────────────────┐
│   Auth Layer     │── RBAC + session validation
└──────────────────┘
        │
        ▼
┌──────────────────┐
│ Schema Resolver  │── maps user role to approved views/tables
└──────────────────┘
        │
        ▼
┌──────────────────┐
│  SQL Generator   │── LLM converts question to SQL with schema context
└──────────────────┘
        │
        ▼
┌──────────────────┐
│ Safety Validator │── blocks DROP, DELETE, UPDATE, unapproved tables
└──────────────────┘
        │
        ▼
┌──────────────────┐
│ Query Executor   │── runs validated SQL against Snowflake
└──────────────────┘
        │
        ▼
┌──────────────────┐
│ Output Formatter │── results + generated SQL + confidence score
└──────────────────┘
        │
        ▼
┌──────────────────┐
│  Audit Logger    │── logs query, user, timestamp, result status
└──────────────────┘
```

---

### Key Design Decisions

| Decision | Rationale |
|:---------|:----------|
| ![Schema](https://img.shields.io/badge/Schema--aware_generation-58a6ff?style=flat-square) | LLM receives only tables/columns the user is authorized to query. Prevents hallucinated references and enforces access at the prompt level. |
| ![Safety](https://img.shields.io/badge/SQL_safety_rules-f85149?style=flat-square) | Every query passes a validator rejecting DDL, DML, unapproved tables, and missing WHERE clauses on large fact tables. |
| ![KPI](https://img.shields.io/badge/KPI_glossary-16a34a?style=flat-square) | Finance terms mapped to exact SQL definitions. "Gross margin" always means `(revenue - cogs) / revenue`, not whatever the LLM guesses. |
| ![Audit](https://img.shields.io/badge/Audit_trail-d29922?style=flat-square) | Every query logged with user ID, role, input, generated SQL, execution status, row count, and timestamp. |

---

### Components

| Component | Source | Purpose |
|:----------|:-------|:--------|
| [![generator](https://img.shields.io/badge/SQL_Generator-161b22?style=flat-square&logo=python&logoColor=3776AB)](src/sql_engine/generator.py) | `src/sql_engine/generator.py` | Prompt construction, LLM SQL generation, retry logic |
| [![validator](https://img.shields.io/badge/SQL_Validator-161b22?style=flat-square&logo=python&logoColor=3776AB)](src/sql_engine/validator.py) | `src/sql_engine/validator.py` | DDL/DML blocking, schema enforcement, WHERE clause checks |
| [![rbac](https://img.shields.io/badge/RBAC-161b22?style=flat-square&logo=python&logoColor=3776AB)](src/auth/rbac.py) | `src/auth/rbac.py` | Role-to-schema mapping, authorized object filtering |
| [![glossary](https://img.shields.io/badge/KPI_Glossary-161b22?style=flat-square&logo=python&logoColor=3776AB)](src/knowledge/kpi_glossary.py) | `src/knowledge/kpi_glossary.py` | Business term to SQL expression mapping |
| [![eval](https://img.shields.io/badge/Eval_Suite-161b22?style=flat-square&logo=python&logoColor=3776AB)](src/evaluation/eval_runner.py) | `src/evaluation/eval_runner.py` | Correctness, safety, and latency scoring |
| [![audit](https://img.shields.io/badge/Audit_Logger-161b22?style=flat-square&logo=python&logoColor=3776AB)](src/app/middleware.py) | `src/app/middleware.py` | Request logging, CORS, rate limiting |

---

### SQL Safety Rules

> Every generated query is validated before execution. Failed validations are logged and returned to the user with an explanation.

| Rule | Enforcement |
|:-----|:------------|
| ![DDL](https://img.shields.io/badge/Block_DDL-f85149?style=flat-square) | Rejects CREATE, ALTER, DROP statements |
| ![DML](https://img.shields.io/badge/Block_DML-f85149?style=flat-square) | Rejects INSERT, UPDATE, DELETE statements |
| ![Schema](https://img.shields.io/badge/Schema_Auth-d29922?style=flat-square) | Rejects queries referencing tables outside user's authorized schema |
| ![WHERE](https://img.shields.io/badge/WHERE_Required-58a6ff?style=flat-square) | Requires WHERE clause on fact tables exceeding row threshold |
| ![SELECT*](https://img.shields.io/badge/Block_SELECT_*-7c3aed?style=flat-square) | Flags SELECT * on wide tables |

---

### Configuration

Role-to-schema access (`config/roles.yaml`):

```yaml
roles:
  fpa_analyst:
    schemas: [finance_reporting]
    views: [v_revenue, v_opex, v_margin_by_division]
  controller:
    schemas: [finance_reporting, finance_detail]
    views: [v_revenue, v_opex, v_margin_by_division, v_journal_entries, v_trial_balance]
```

KPI glossary (`config/kpi_definitions.yaml`):

```yaml
kpis:
  gross_margin:
    display_name: Gross Margin
    sql: "(SUM(revenue) - SUM(cogs)) / NULLIF(SUM(revenue), 0)"
    grain: division, month
    source_view: v_revenue
  opex_variance:
    display_name: OPEX Variance
    sql: "SUM(actual_opex) - SUM(budget_opex)"
    grain: cost_center, month
    source_view: v_opex
```

---

### Quick Start

```bash
git clone https://github.com/nicholasjh-work/llm-text-to-sql-finance.git
cd llm-text-to-sql-finance

python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env   # fill in Snowflake and LLM API credentials

# Run the app
python -m src.app.main

# Run tests
pytest tests/ -v

# Run evaluation suite
python scripts/run_eval.py
```

---

### Tech Stack

| Component | Technology |
|:----------|:-----------|
| ![API](https://img.shields.io/badge/API-000000?style=flat-square) | Flask (Python 3.11) |
| ![DB](https://img.shields.io/badge/Database-29B5E8?style=flat-square) | Snowflake (snowflake-connector-python) |
| ![LLM](https://img.shields.io/badge/LLM-1C3C3C?style=flat-square) | Model-agnostic, configurable in settings |
| ![Config](https://img.shields.io/badge/Config-CB171E?style=flat-square) | YAML (roles, safety rules, KPI glossary) |
| ![Test](https://img.shields.io/badge/Tests-0A9EDC?style=flat-square) | pytest |
| ![Auth](https://img.shields.io/badge/Auth-7c3aed?style=flat-square) | RBAC with session validation |

---

### Disclaimer

The application code and architecture in this repository reflect a governed analytics product delivered for an enterprise finance organization. The actual data, credentials, and proprietary business logic from that engagement remain confidential. Sample schemas and KPI definitions included here are illustrative and do not represent real financial data.

---

<p align="center">
  <a href="https://linkedin.com/in/nicholashidalgo"><img src="https://img.shields.io/badge/LinkedIn-0A66C2?style=for-the-badge&logo=linkedin&logoColor=white" alt="LinkedIn"></a>&nbsp;
  <a href="https://nicholashidalgo.com"><img src="https://img.shields.io/badge/Website-000000?style=for-the-badge&logo=About.me&logoColor=white" alt="Website"></a>&nbsp;
  <a href="mailto:analytics@nicholashidalgo.com"><img src="https://img.shields.io/badge/Email-D14836?style=for-the-badge&logo=gmail&logoColor=white" alt="Email"></a>
</p>
