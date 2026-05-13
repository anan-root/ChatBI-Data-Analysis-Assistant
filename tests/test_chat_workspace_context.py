from langGraph_agent.smart_data_analysis_assistant.chatbi_graph.chat_context import (
    UserInput,
    build_workspace_system_message,
)


def test_user_input_accepts_optional_workspace_id():
    payload = UserInput(
        user_id="demo",
        message="分析这个空间",
        history=[],
        workspace_id="job_001",
    )

    assert payload.workspace_id == "job_001"


def test_user_input_keeps_backward_compatibility_without_workspace_id():
    payload = UserInput(user_id="demo", message="查询价格", history=[])

    assert payload.workspace_id is None


def test_workspace_system_message_contains_asset_boundary():
    message = build_workspace_system_message(
        {
            "workspaceId": "job_001",
            "workspaceName": "销售月报",
            "businessType": "销售经营",
            "sourceFile": "sales.xlsx",
            "schema": {"columns": ["日期", "销售额"]},
        }
    )

    assert "不要跨业务空间混用数据" in message.content
    assert "workspace_context=" in message.content
    assert "销售月报" in message.content
