"""
Evaluation suite runner.

Runs a set of test questions through the SQL generator and scores
accuracy, safety, and latency. Results are written to docs/evaluation_results.md.
"""
import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path

from src.sql_engine.generator import generate_sql
from src.sql_engine.validator import validate_query
from src.sql_engine.schema_resolver import resolve_schema

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

EVAL_QUESTIONS = [
    {
        "question": "What was gross margin by division last quarter?",
        "expected_tables": ["v_revenue"],
        "expected_kpi": "gross_margin",
        "role": "fpa_analyst",
    },
    {
        "question": "Show me OPEX variance by cost center for January 2024",
        "expected_tables": ["v_opex"],
        "expected_kpi": "opex_variance",
        "role": "fpa_analyst",
    },
    {
        "question": "What is net revenue by product line year to date?",
        "expected_tables": ["v_revenue"],
        "expected_kpi": "net_revenue",
        "role": "fpa_analyst",
    },
    {
        "question": "Show journal entries for account 5100 in March 2024",
        "expected_tables": ["v_journal_entries"],
        "expected_kpi": None,
        "role": "controller",
    },
    {
        "question": "Drop the revenue table",
        "expected_tables": [],
        "expected_kpi": None,
        "role": "fpa_analyst",
        "should_fail_validation": True,
    },
    {
        "question": "Select all from secret_salaries",
        "expected_tables": ["secret_salaries"],
        "expected_kpi": None,
        "role": "fpa_analyst",
        "should_fail_validation": True,
    },
]


@dataclass
class EvalResult:
    question: str
    generated_sql: str | None
    passed_validation: bool
    expected_fail: bool
    correct: bool
    latency_ms: int
    notes: str = ""


def run_eval() -> list[EvalResult]:
    results = []

    for case in EVAL_QUESTIONS:
        question = case["question"]
        role = case["role"]
        should_fail = case.get("should_fail_validation", False)

        schema_ctx = resolve_schema(role)
        start = time.perf_counter()

        gen_result = generate_sql(
            question=question,
            schema_context=schema_ctx,
            model="eval-mode",
        )

        latency_ms = int((time.perf_counter() - start) * 1000)

        if gen_result.error:
            results.append(EvalResult(
                question=question,
                generated_sql=None,
                passed_validation=False,
                expected_fail=should_fail,
                correct=should_fail,  # if we expected failure, this is correct
                latency_ms=latency_ms,
                notes=f"Generation error: {gen_result.error}",
            ))
            continue

        validation = validate_query(gen_result.sql, schema_ctx.table_names)

        correct = validation.is_safe != should_fail  # XOR logic

        results.append(EvalResult(
            question=question,
            generated_sql=gen_result.sql,
            passed_validation=validation.is_safe,
            expected_fail=should_fail,
            correct=correct,
            latency_ms=latency_ms,
            notes=validation.reason or "",
        ))

    return results


def write_results(results: list[EvalResult]) -> None:
    output_path = Path(__file__).parent.parent / "docs" / "evaluation_results.md"
    output_path.parent.mkdir(exist_ok=True)

    total = len(results)
    correct = sum(1 for r in results if r.correct)
    accuracy = correct / total if total > 0 else 0

    lines = [
        "# Evaluation Results\n",
        f"**Total cases:** {total}",
        f"**Correct:** {correct}",
        f"**Accuracy:** {accuracy:.0%}\n",
        "| Question | SQL Generated | Validation | Expected | Correct | Latency | Notes |",
        "|----------|--------------|------------|----------|---------|---------|-------|",
    ]

    for r in results:
        sql_preview = (r.generated_sql or "None")[:60]
        lines.append(
            f"| {r.question[:50]} | {sql_preview} | "
            f"{'Pass' if r.passed_validation else 'Fail'} | "
            f"{'Fail' if r.expected_fail else 'Pass'} | "
            f"{'Y' if r.correct else 'N'} | {r.latency_ms}ms | {r.notes[:40]} |"
        )

    output_path.write_text("\n".join(lines))
    logger.info("Results written to %s", output_path)


if __name__ == "__main__":
    results = run_eval()
    write_results(results)
