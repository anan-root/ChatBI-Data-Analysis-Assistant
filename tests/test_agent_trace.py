from langGraph_agent.smart_data_analysis_assistant.chatbi_graph.services.agent_trace import (
    build_evidence,
    infer_intent_from_route,
    step_from_ai_message,
    step_from_tool_message,
)


class FakeAIMessage:
    def __init__(self, content="", tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls or []


class FakeToolMessage:
    def __init__(self, content, name="db_sql_tool"):
        self.content = content
        self.name = name


def get_message_text(message):
    return message.content


def test_extracts_tool_plan_from_ai_message():
    message = FakeAIMessage(
        tool_calls=[
            {
                "name": "db_sql_tool",
                "args": {"query": 'select "销售额" from "import_sales"'},
                "id": "call_1",
            }
        ]
    )

    steps = step_from_ai_message(message)

    assert steps[0]["stage"] == "tool_plan"
    assert steps[0]["toolName"] == "db_sql_tool"
    assert steps[0]["sql"] == 'select "销售额" from "import_sales"'


def test_tool_result_marks_blocked_scope_failure():
    message = FakeToolMessage("错误: 工作空间 SQL 范围检查未通过。检测到越权表引用")

    step = step_from_tool_message(message, get_message_text)

    assert step["status"] == "blocked"
    assert "越权表引用" in step["reason"]


def test_build_evidence_collects_workspace_fields_and_sql():
    workspace_context = {
        "workspaceId": "job_001",
        "workspaceName": "销售空间",
        "schema": {"columns": ["日期", "销售额"]},
    }
    steps = [
        {
            "sql": 'select "销售额" from "import_sales"',
            "status": "ok",
            "summary": "查询销售额",
        }
    ]

    evidence = build_evidence(workspace_context, steps, knowledge=[{"title": "销售额"}])

    assert evidence["workspaceName"] == "销售空间"
    assert evidence["fields"] == ["日期", "销售额"]
    assert evidence["sql"][0]["allowed"] is True
    assert evidence["knowledge"][0]["title"] == "销售额"


def test_infer_intent_from_route_result():
    assert infer_intent_from_route("业务数据查询分析") == "data_query"
    assert infer_intent_from_route("纯python编码") == "python"
