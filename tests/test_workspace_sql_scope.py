from langGraph_agent.smart_data_analysis_assistant.chatbi_graph.services.workspace_sql_scope import (
    build_workspace_sql_policy_text,
    build_workspace_sql_scope,
    extract_column_references,
    extract_table_references,
    format_workspace_table_schema,
    validate_workspace_sql_scope,
)


def workspace_context(imported=True):
    return {
        "workspaceId": "job_001",
        "workspaceName": "销售月报",
        "businessType": "销售经营",
        "sourceFile": "sales.xlsx",
        "imported": imported,
        "dbTable": "import_sales" if imported else None,
        "schema": {
            "rowCount": 100,
            "columnCount": 2,
            "columns": ["日期", "销售额"],
            "fields": [
                {"name": "日期", "dtype": "object", "role": "time", "missingRate": 0},
                {"name": "销售额", "dtype": "float64", "role": "metric", "missingRate": 0},
            ],
        },
    }


def test_extract_table_references_supports_quoted_and_schema_tables():
    references = extract_table_references('select * from public."import_sales" join dim_product on true')

    assert references == ("import_sales", "dim_product")


def test_workspace_sql_scope_allows_current_workspace_table():
    scope = build_workspace_sql_scope(workspace_context())

    result = validate_workspace_sql_scope('select "销售额" from "import_sales"', scope)

    assert result.allowed is True
    assert result.table_references == ("import_sales",)
    assert result.column_references == ("销售额",)


def test_workspace_sql_scope_allows_qualified_columns_and_aliases():
    scope = build_workspace_sql_scope(workspace_context())

    result = validate_workspace_sql_scope('select s."销售额" as "总销售额" from "import_sales" s', scope)

    assert result.allowed is True
    assert result.column_references == ("销售额",)


def test_workspace_sql_scope_rejects_select_star():
    scope = build_workspace_sql_scope(workspace_context())

    result = validate_workspace_sql_scope('select * from "import_sales"', scope)

    assert result.allowed is False
    assert "越权字段引用" in result.reason


def test_workspace_sql_scope_rejects_unknown_quoted_column():
    scope = build_workspace_sql_scope(workspace_context())

    result = validate_workspace_sql_scope('select "利润" from "import_sales"', scope)

    assert result.allowed is False
    assert "利润" in result.reason


def test_extract_column_references_detects_qualified_star():
    scope = build_workspace_sql_scope(workspace_context())

    references, forbidden = extract_column_references('select s.* from "import_sales" s', scope)

    assert references == ()
    assert forbidden == ("*",)


def test_workspace_sql_scope_writes_audit_event(monkeypatch, tmp_path):
    from langGraph_agent.smart_data_analysis_assistant.core.audit import read_audit_events

    monkeypatch.setenv("CHATBI_AUDIT_LOG_PATH", str(tmp_path / "audit.jsonl"))
    monkeypatch.setenv("CHATBI_AUDIT_ENABLED", "true")
    scope = build_workspace_sql_scope(workspace_context())

    validate_workspace_sql_scope('select * from "用户表"', scope)

    events = read_audit_events(limit=1)
    assert events[0]["eventType"] == "sql_decision"
    assert events[0]["allowed"] is False
    assert events[0]["workspaceId"] == "job_001"


def test_workspace_sql_scope_rejects_cross_workspace_table():
    scope = build_workspace_sql_scope(workspace_context())

    result = validate_workspace_sql_scope('select * from "用户表"', scope)

    assert result.allowed is False
    assert "越权表引用" in result.reason


def test_workspace_sql_scope_rejects_sql_before_import():
    scope = build_workspace_sql_scope(workspace_context(imported=False))

    result = validate_workspace_sql_scope("select * from import_sales", scope)

    assert result.allowed is False
    assert "尚未确认入库" in result.reason


def test_workspace_table_schema_explains_allowed_table():
    scope = build_workspace_sql_scope(workspace_context())
    schema_text = format_workspace_table_schema(scope)

    assert '允许查询表: "import_sales"' in schema_text
    assert "销售额" in schema_text


def test_workspace_sql_policy_mentions_no_db_query_before_import():
    policy = build_workspace_sql_policy_text(workspace_context(imported=False))

    assert "禁止调用 db_sql_tool" in policy
