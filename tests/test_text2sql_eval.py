from langGraph_agent.smart_data_analysis_assistant.chatbi_graph.services.text2sql_eval import (
    evaluate_case,
    load_eval_cases,
    run_text2sql_eval,
)


def test_load_eval_cases_includes_safety_scenarios():
    cases = load_eval_cases()

    assert any(case["id"] == "delete_blocked" for case in cases)
    assert any(case["id"] == "not_imported_workspace" for case in cases)


def test_dangerous_sql_is_blocked():
    result = evaluate_case(
        {
            "id": "danger",
            "category": "readonly_sql",
            "sql": 'delete from "import_sales"',
            "workspace": "imported_sales",
            "expectAllowed": False,
        }
    )

    assert result["actualAllowed"] is False
    assert result["passed"] is True


def test_cross_workspace_table_is_blocked():
    result = evaluate_case(
        {
            "id": "cross",
            "category": "workspace_scope",
            "sql": 'select "销售额" from "用户表"',
            "workspace": "imported_sales",
            "expectAllowed": False,
        }
    )

    assert result["actualAllowed"] is False
    assert "越权表引用" in result["reason"]


def test_not_imported_workspace_blocks_detail_sql():
    result = evaluate_case(
        {
            "id": "draft",
            "category": "workspace_import",
            "sql": 'select "销售额" from "import_sales"',
            "workspace": "draft_sales",
            "expectAllowed": False,
        }
    )

    assert result["actualAllowed"] is False
    assert "尚未确认入库" in result["reason"]


def test_run_text2sql_eval_summarizes_results():
    result = run_text2sql_eval()

    assert result["total"] >= 8
    assert result["failed"] == 0
    assert "readonly_sql" in result["categoryStats"]
