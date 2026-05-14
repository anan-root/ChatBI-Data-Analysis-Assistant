"""
Workspace MCP:
把业务空间、字段画像、质量评分、分析方案和报告摘要暴露给 Agent。
"""

import os
import sys

from dotenv import load_dotenv
from mcp.server import FastMCP

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHATBI_GRAPH_DIR = os.path.join(BASE_DIR, "chatbi_graph")
sys.path.append(BASE_DIR)
sys.path.append(CHATBI_GRAPH_DIR)

from chatbi_graph.bi_api import build_workspace_report
from chatbi_graph.services.workspace_tools import (
    compact_workspace_list,
    json_dumps,
    workspace_analysis_context,
    workspace_report_summary,
    workspace_schema_profile,
)

load_dotenv()

mcp = FastMCP(
    name="workspace_mcp",
    instructions="业务空间、字段画像、质量评分、分析方案和报告摘要 MCP",
    host="0.0.0.0",
    port=9006,
)


@mcp.tool()
async def list_workspaces_tool(limit: int = 20) -> str:
    """
    返回最近的业务空间列表，包括空间 ID、业务类型、来源文件、行列规模和入库状态。
    :param limit: 最多返回空间数量，默认 20
    """
    return json_dumps(compact_workspace_list(limit=limit))


@mcp.tool()
async def get_workspace_schema_tool(workspace_id: str) -> str:
    """
    返回指定业务空间的字段画像、字段角色、行列规模和入库状态。
    :param workspace_id: 业务空间 ID / 导入任务 ID
    """
    return json_dumps(workspace_schema_profile(workspace_id))


@mcp.tool()
async def get_workspace_analysis_context_tool(workspace_id: str) -> str:
    """
    返回指定业务空间的 Agent 分析上下文，包括 schema、质量评分、分析方案、指标目录、推荐路径和优先行动。
    :param workspace_id: 业务空间 ID / 导入任务 ID
    """
    return json_dumps(workspace_analysis_context(workspace_id, build_workspace_report))


@mcp.tool()
async def get_workspace_report_summary_tool(workspace_id: str) -> str:
    """
    返回指定业务空间的报告摘要，包括诊断链路、行动建议、图表解释和 SQL 模板。
    :param workspace_id: 业务空间 ID / 导入任务 ID
    """
    return json_dumps(workspace_report_summary(workspace_id, build_workspace_report))


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
