import os
from pathlib import Path

from langGraph_agent.smart_data_analysis_assistant.core.security import (
    DEFAULT_ALLOWED_ORIGINS,
    enforce_select_limit,
    is_python_execution_enabled,
    parse_cors_origins,
    run_python_script_in_sandbox,
    safe_parse_sequence,
    validate_python_script,
    validate_readonly_sql,
)


def test_validate_readonly_sql_allows_select_with_limit():
    result = validate_readonly_sql("select id, name from products limit 10;")

    assert result.allowed is True
    assert result.query == "select id, name from products limit 10"


def test_validate_readonly_sql_rejects_dangerous_keywords():
    result = validate_readonly_sql("select * from products; drop table products;")

    assert result.allowed is False
    assert "只允许单条只读 SQL" in result.reason


def test_validate_readonly_sql_rejects_update_statement():
    result = validate_readonly_sql("update products set price = 1")

    assert result.allowed is False
    assert "SELECT / WITH / EXPLAIN" in result.reason


def test_enforce_select_limit_adds_default_limit():
    query = enforce_select_limit("select * from products", max_rows=50)

    assert query == "select * from products LIMIT 50"


def test_enforce_select_limit_keeps_existing_limit():
    query = enforce_select_limit("select * from products limit 5", max_rows=50)

    assert query == "select * from products limit 5"


def test_parse_cors_origins_never_returns_wildcard():
    assert parse_cors_origins("*") == list(DEFAULT_ALLOWED_ORIGINS)
    assert parse_cors_origins(None) == list(DEFAULT_ALLOWED_ORIGINS)
    assert parse_cors_origins("http://localhost:5173,https://example.com") == [
        "http://localhost:5173",
        "https://example.com",
    ]


def test_python_execution_disabled_by_default(monkeypatch):
    monkeypatch.delenv("CHATBI_ENABLE_PYTHON_EXEC", raising=False)

    assert is_python_execution_enabled() is False


def test_validate_python_script_rejects_os_import():
    valid, reason = validate_python_script("import os\nos.remove('x')")

    assert valid is False
    assert "不在允许列表" in reason


def test_validate_python_script_rejects_eval():
    valid, reason = validate_python_script("eval('1 + 1')")

    assert valid is False
    assert "安全风险" in reason


def test_run_python_script_in_sandbox_allows_basic_print(tmp_path):
    result = run_python_script_in_sandbox("print(1 + 1)", Path(tmp_path), timeout_seconds=3)

    assert result.ok is True
    assert result.stdout == "2"


def test_safe_parse_sequence_uses_safe_parsers():
    assert safe_parse_sequence('["a", "b"]') == ["a", "b"]
    assert safe_parse_sequence("['a', 'b']") == ["a", "b"]
