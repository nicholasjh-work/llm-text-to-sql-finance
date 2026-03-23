"""
SQL Generator: constructs prompts from user questions + schema context,
sends to the LLM API, and parses the SQL response.
"""
import logging
import re
from dataclasses import dataclass
from typing import Optional

from src.knowledge.kpi_glossary import lookup_kpi_terms
from src.knowledge.schema_registry import SchemaContext

logger = logging.getLogger(__name__)


@dataclass
class GenerationResult:
    sql: Optional[str]
    confidence: float
    error: Optional[str] = None
    raw_response: Optional[str] = None


SYSTEM_PROMPT = """You are a SQL generation assistant for a finance team.

Rules:
1. Generate ONLY a single SELECT statement. No DDL, no DML, no multi-statement queries.
2. Use only the tables and columns provided in the schema context below.
3. When a KPI term is referenced, use the exact SQL definition provided.
4. Always qualify column names with table aliases.
5. Include a WHERE clause on fact tables.
6. Return ONLY the SQL query, no explanation, no markdown fencing.

Schema context:
{schema_context}

KPI definitions:
{kpi_context}
"""


def _build_prompt(question: str, schema_context: SchemaContext) -> tuple[str, str]:
    """Build system and user prompts for the LLM."""
    schema_text = schema_context.to_prompt_text()
    kpi_terms = lookup_kpi_terms(question)
    kpi_text = "\n".join(
        f"- {k.display_name}: {k.sql} (grain: {k.grain}, source: {k.source_view})"
        for k in kpi_terms
    ) or "No matching KPI definitions."

    system = SYSTEM_PROMPT.format(schema_context=schema_text, kpi_context=kpi_text)
    user = f"Question: {question}"
    return system, user


def _call_llm(system_prompt: str, user_prompt: str, model: str) -> str:
    """Call the LLM API. Returns raw text response.

    Production: calls the configured LLM endpoint.
    This stub returns a placeholder for demonstration.
    Replace with actual API call (OpenAI, Anthropic, Azure, etc.)
    """
    # Example integration point:
    #
    # import httpx
    # response = httpx.post(
    #     settings.llm_endpoint,
    #     json={
    #         "model": model,
    #         "messages": [
    #             {"role": "system", "content": system_prompt},
    #             {"role": "user", "content": user_prompt},
    #         ],
    #         "max_tokens": 500,
    #         "temperature": 0.0,
    #     },
    #     headers={"Authorization": f"Bearer {settings.llm_api_key}"},
    #     timeout=30,
    # )
    # return response.json()["choices"][0]["message"]["content"]

    logger.info("LLM call: model=%s prompt_length=%d", model, len(system_prompt) + len(user_prompt))
    raise NotImplementedError(
        "Replace this stub with your LLM API call. "
        "See comments above for integration pattern."
    )


def _extract_sql(raw: str) -> Optional[str]:
    """Extract SQL from LLM response, stripping markdown fences if present."""
    cleaned = raw.strip()

    # Remove markdown SQL fences
    fence_pattern = re.compile(r"```(?:sql)?\s*\n?(.*?)\n?```", re.DOTALL | re.IGNORECASE)
    match = fence_pattern.search(cleaned)
    if match:
        cleaned = match.group(1).strip()

    # Basic validation: must start with SELECT
    if not cleaned.upper().startswith("SELECT"):
        return None

    return cleaned


def generate_sql(
    question: str,
    schema_context: SchemaContext,
    model: str,
    max_retries: int = 2,
) -> GenerationResult:
    """Generate SQL from a natural-language question.

    Constructs a schema-aware prompt, calls the LLM, extracts and returns SQL.
    Retries on malformed output up to max_retries times.
    """
    system_prompt, user_prompt = _build_prompt(question, schema_context)

    for attempt in range(1, max_retries + 1):
        try:
            raw = _call_llm(system_prompt, user_prompt, model)
        except NotImplementedError as e:
            return GenerationResult(sql=None, confidence=0.0, error=str(e))
        except Exception as e:
            logger.error("LLM call failed (attempt %d): %s", attempt, e)
            if attempt == max_retries:
                return GenerationResult(sql=None, confidence=0.0, error=f"LLM call failed: {e}")
            continue

        sql = _extract_sql(raw)
        if sql:
            confidence = _estimate_confidence(question, sql, schema_context)
            return GenerationResult(sql=sql, confidence=confidence, raw_response=raw)

        logger.warning("Malformed SQL on attempt %d, retrying", attempt)

    return GenerationResult(
        sql=None,
        confidence=0.0,
        error="Failed to generate valid SQL after retries",
    )


def _estimate_confidence(question: str, sql: str, schema_context: SchemaContext) -> float:
    """Estimate confidence in the generated SQL.

    Heuristic scoring based on:
    - KPI term match (question references a governed KPI)
    - Table coverage (all referenced tables are in authorized schema)
    - Query complexity (simpler queries get higher confidence)
    """
    score = 0.7  # base confidence

    kpi_terms = lookup_kpi_terms(question)
    if kpi_terms:
        score += 0.15  # governed KPI match

    authorized = {t.lower() for t in schema_context.table_names}
    sql_upper = sql.upper()

    # Check all referenced tables are authorized
    from_tables = re.findall(r"FROM\s+(\w+)|JOIN\s+(\w+)", sql_upper)
    flat = [t.lower() for pair in from_tables for t in pair if t]
    if flat and all(t in authorized for t in flat):
        score += 0.1

    # Penalize very long queries (higher chance of error)
    if len(sql) > 1000:
        score -= 0.1

    return round(min(max(score, 0.0), 1.0), 2)
