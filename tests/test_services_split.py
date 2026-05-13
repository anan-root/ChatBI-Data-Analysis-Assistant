import pandas as pd

from langGraph_agent.smart_data_analysis_assistant.chatbi_graph.services.charts import (
    build_chart_blueprints,
    build_interactive_chart_config,
    build_workspace_charts,
)
from langGraph_agent.smart_data_analysis_assistant.chatbi_graph.services.workspace_context import (
    build_workspace_chat_context_from_report,
)


def test_chart_service_builds_business_explanations():
    df = pd.DataFrame(
        {
            "区域": ["华东", "华北", "华东"],
            "销售额": [100, 80, 120],
            "日期": ["2026-01-01", "2026-02-01", "2026-02-15"],
            "成本": [50, 40, 55],
        }
    )
    blueprints = build_chart_blueprints("销售经营", "销售额", "区域", ["日期"], ["销售额", "成本"], list(df.columns))
    charts = build_workspace_charts(df, "销售额", "区域", ["日期"], ["销售额", "成本"], blueprints)
    interactive = build_interactive_chart_config(df, ["销售额", "成本"], ["区域"], ["日期"])

    assert any(chart["type"] == "bar" and chart["businessQuestion"] for chart in charts)
    assert any(chart["type"] == "line" for chart in charts)
    assert interactive["defaultMetric"] == "销售额"
    assert interactive["datasets"]["bars"]["销售额||区域"]["x"][0] == "华东"


def test_workspace_context_service_limits_report_payload():
    report = {
        "jobId": "job_001",
        "workspaceName": "销售月报",
        "businessType": "销售经营",
        "sourceFile": "sales.xlsx",
        "dbTable": "import_sales",
        "imported": True,
        "schemaProfile": {
            "rowCount": 100,
            "columnCount": 2,
            "columns": ["日期", "销售额"],
            "roleCounts": {"metric": 1},
            "fields": [{"name": "销售额", "role": "metric"}],
        },
        "dataProfile": {"profileSummary": "100 行", "missingRate": 0, "duplicateRate": 0},
        "qualityScore": {"score": 95, "grade": "A", "summary": "可分析", "penalties": []},
        "analysisPlan": {"name": "销售经营分析方案", "confidence": "高", "focus": "销售诊断", "framework": {}},
        "metricCatalog": [{"name": "销售额"}],
        "executiveSummary": {"highlights": [{"label": "主指标"}]},
        "diagnosticStory": [{"stage": "现象"}],
        "priorityActions": [{"priority": "P0"}],
        "recommendedPaths": [{"name": "成交趋势"}],
        "sections": [{"title": "概览", "content": "重点结论"}],
    }

    context = build_workspace_chat_context_from_report(report)

    assert context["workspaceId"] == "job_001"
    assert context["schema"]["columns"] == ["日期", "销售额"]
    assert context["reportSummary"]["sections"][0]["title"] == "概览"
