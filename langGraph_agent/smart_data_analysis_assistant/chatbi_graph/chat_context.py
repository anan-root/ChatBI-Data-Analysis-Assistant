import json

from pydantic import BaseModel

try:
    from langchain_core.messages import SystemMessage
except ModuleNotFoundError:
    class SystemMessage:
        def __init__(self, content: str):
            self.content = content

try:
    from .services.workspace_sql_scope import build_workspace_sql_policy_text
except ImportError:
    from services.workspace_sql_scope import build_workspace_sql_policy_text


class UserInput(BaseModel):
    user_id: str
    message: str
    history: list[dict]
    workspace_id: str | None = None


def build_workspace_system_message(workspace_context: dict) -> SystemMessage:
    context_text = json.dumps(workspace_context, ensure_ascii=False)
    sql_policy = build_workspace_sql_policy_text(workspace_context)
    return SystemMessage(
        content=(
            "你正在回答企业 ChatBI 的当前业务空间问题。"
            "必须优先基于下方 workspace_context 中的业务空间、字段角色、指标目录、报告摘要和数据质量信息回答。"
            "不要跨业务空间混用数据，不要声称已经读取明细行数据；如果问题需要明细查询但该空间尚未入库，请说明需要先确认入库。"
            "回答中请简要说明使用的数据资产名称、业务类型和关键字段依据。\n"
            f"{sql_policy}\n"
            f"workspace_context={context_text}"
        )
    )
