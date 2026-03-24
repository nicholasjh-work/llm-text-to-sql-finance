# Governed Text-to-SQL for Finance Teams

**[Live Demo](https://nicholasjh-work.github.io/llm-text-to-sql-finance/)**

A natural-language interface that converts finance questions into SQL queries with schema awareness, role-based access control, and audit logging. Built for FP&A teams who depended on analysts for ad-hoc queries, creating 3-5 day delays and inconsistent reporting.

Cut ad-hoc reporting turnaround from days to seconds, freed 20+ analyst hours weekly, and reduced manual query errors by 75%.

## Architecture

```
User Question
    |
    v
[Auth Layer] -- RBAC + session validation
    |
    v
[Schema Resolver] -- maps user role to approved views/tables
    |
    v
[SQL Generator] -- LLM converts question to SQL with schema context
    |
    v
[SQL Safety Validator] -- blocks DROP, DELETE, UPDATE, unapproved tables
    |
    v
[Query Executor] -- runs validated SQL against Snowflake
    |
    v
[Output Formatter] -- returns results + generated SQL + confidence score
    |
    v
[Audit Logger] -- logs query, user, timestamp, result status
```

## Key Design Decisions

**Schema-aware generation.** The LLM receives only the tables and columns the user is authorized to query. This prevents hallucinated table references and enforces data access policies at the prompt level, not just at execution.

**SQL safety rules.** Every generated query passes through a validator that rejects DDL statements, write operations, queries against unapproved tables, and queries without a WHERE clause on large fact tables. Failed validations are logged and returned to the user with an explanation.

**KPI glossary integration.** Finance terms like "gross margin," "net revenue," and "OPEX variance" are mapped to exact SQL definitions in a governed glossary. The LLM references these definitions during generation so that "show me gross margin by division" always produces the same calculation regardless of who asks.

**Audit trail.** Every query is logged with the user ID, role, input question, generated SQL, execution status, row count, and timestamp. Compliance teams can audit who queried what and when.

## Project Structure

```
llm-text-to-sql-finance/
  src/
    app/
      __init__.py
      main.py               Flask app, routes, error handling
      middleware.py          Request logging, CORS, rate limiting
    auth/
      __init__.py
      rbac.py                Role-based access control
      session.py             Session management and validation
    sql_engine/
      __init__.py
      generator.py           LLM prompt construction and SQL generation
      validator.py           SQL safety rules and validation
      executor.py            Snowflake query execution with parameterization
      schema_resolver.py     Maps user roles to approved schemas/views
    evaluation/
      __init__.py
      eval_runner.py         Runs eval suite against test questions
      metrics.py             Accuracy, safety, latency scoring
    knowledge/
      __init__.py
      kpi_glossary.py        Finance KPI definitions and SQL mappings
      schema_registry.py     Table/column metadata and descriptions
  config/
    settings.py              App config from env vars
    roles.yaml               Role-to-schema access mappings
    safety_rules.yaml        SQL validation rules
    kpi_definitions.yaml     Governed KPI glossary
  tests/
    test_generator.py        SQL generation accuracy tests
    test_validator.py        Safety rule enforcement tests
    test_rbac.py             Access control tests
    test_executor.py         Query execution tests
    conftest.py              Shared fixtures
  scripts/
    seed_glossary.py         Load KPI definitions from YAML
    run_eval.py              Run evaluation suite
  data/
    sample_schemas/
      finance_views.sql      Example approved view definitions
      kpi_mappings.csv       KPI name to SQL expression mapping
  docs/
    architecture.md          System design and data flow
    deployment.md            Deployment and configuration guide
    evaluation_results.md    Eval suite results and accuracy metrics
  .env.example
  .gitignore
  requirements.txt
  pyproject.toml
  README.md
```

## Components

### SQL Generator (`src/sql_engine/generator.py`)

Constructs a prompt with the user's question, authorized schema context, and KPI glossary entries. Sends to the LLM API and parses the SQL response. Includes retry logic for malformed outputs.

### SQL Validator (`src/sql_engine/validator.py`)

Enforces safety rules before any query executes:
- Blocks DDL (CREATE, ALTER, DROP) and DML (INSERT, UPDATE, DELETE)
- Rejects queries referencing tables outside the user's authorized schema
- Requires WHERE clauses on fact tables exceeding a configurable row threshold
- Flags queries with SELECT * on wide tables
- Logs all validation failures with the reason

### RBAC (`src/auth/rbac.py`)

Maps authenticated users to roles defined in `config/roles.yaml`. Each role specifies which Snowflake schemas, tables, and views the user can query. The schema resolver filters the LLM's context window to only include authorized objects.

### KPI Glossary (`src/knowledge/kpi_glossary.py`)

A governed dictionary mapping business terms to SQL expressions. When the generator detects a KPI term in the user's question, it injects the exact SQL definition into the prompt. This ensures "gross margin" always means `(revenue - cogs) / revenue`, not whatever the LLM guesses.

### Evaluation Suite (`src/evaluation/`)

A set of test questions with expected SQL output and expected results. The eval runner scores generated SQL on correctness (does it return the right answer), safety (does it pass validation), and latency. Results are logged to `docs/evaluation_results.md`.

## Tech Stack

- **Python 3.11** with Flask for the API layer
- **Snowflake** as the query target (snowflake-connector-python)
- **LLM API** for SQL generation (model-agnostic, configurable in settings)
- **YAML** for configuration (roles, safety rules, KPI glossary)
- **pytest** for testing

## Getting Started

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

## Configuration

All sensitive values come from environment variables. See `.env.example` for the full list.

`config/roles.yaml` defines which roles can access which schemas:

```yaml
roles:
  fpa_analyst:
    schemas: [finance_reporting]
    views: [v_revenue, v_opex, v_margin_by_division]
  controller:
    schemas: [finance_reporting, finance_detail]
    views: [v_revenue, v_opex, v_margin_by_division, v_journal_entries, v_trial_balance]
```

`config/kpi_definitions.yaml` maps business terms to SQL:

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

## Disclaimer

The application code and architecture in this repository reflect a governed analytics product delivered for an enterprise finance organization. The actual data, credentials, and proprietary business logic from that engagement remain confidential. Sample schemas and KPI definitions included here are illustrative and do not represent real financial data.
