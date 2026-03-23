"""
Flask application entry point for the Text-to-SQL service.
"""
import logging

from flask import Flask, jsonify, request

from src.auth.rbac import require_role, get_user_context
from src.sql_engine.generator import generate_sql
from src.sql_engine.validator import validate_query
from src.sql_engine.executor import execute_query
from src.sql_engine.schema_resolver import resolve_schema
from src.app.middleware import setup_middleware, log_audit_event
from config.settings import Settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

settings = Settings()
app = Flask(__name__)
setup_middleware(app)


@app.route("/api/query", methods=["POST"])
@require_role(["fpa_analyst", "controller", "cfo"])
def query():
    """Convert a natural-language question to SQL, validate, execute, and return results."""
    body = request.get_json(force=True)
    question = body.get("question", "").strip()

    if not question:
        return jsonify({"error": "question is required"}), 400

    user_ctx = get_user_context(request)
    authorized_schema = resolve_schema(user_ctx.role)

    # Generate SQL from the question
    generation_result = generate_sql(
        question=question,
        schema_context=authorized_schema,
        model=settings.llm_model,
    )

    if generation_result.error:
        log_audit_event(user_ctx, question, None, "generation_failed")
        return jsonify({"error": generation_result.error}), 422

    # Validate the generated SQL against safety rules
    validation = validate_query(
        sql=generation_result.sql,
        authorized_tables=authorized_schema.table_names,
    )

    if not validation.is_safe:
        log_audit_event(user_ctx, question, generation_result.sql, "validation_failed", validation.reason)
        return jsonify({
            "error": "Query failed safety validation",
            "reason": validation.reason,
            "generated_sql": generation_result.sql,
        }), 403

    # Execute the validated query
    exec_result = execute_query(generation_result.sql)

    log_audit_event(
        user_ctx, question, generation_result.sql,
        "success" if exec_result.success else "execution_failed",
        row_count=exec_result.row_count,
    )

    if not exec_result.success:
        return jsonify({
            "error": "Query execution failed",
            "detail": exec_result.error,
            "generated_sql": generation_result.sql,
        }), 500

    return jsonify({
        "question": question,
        "generated_sql": generation_result.sql,
        "confidence": generation_result.confidence,
        "results": exec_result.rows,
        "columns": exec_result.columns,
        "row_count": exec_result.row_count,
    })


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=settings.port, debug=settings.debug)
