import pandas as pd

from langGraph_agent.smart_data_analysis_assistant.chatbi_graph.services.analysis_utils import (
    choose_primary_metric,
    datetime_like_columns,
    numeric_columns,
)
from langGraph_agent.smart_data_analysis_assistant.chatbi_graph.services.diagnostics import (
    build_benchmark_summary,
    build_diagnostic_story,
    build_driver_analysis,
    build_priority_actions,
)
from langGraph_agent.smart_data_analysis_assistant.chatbi_graph.services.methodology import (
    build_analysis_plan,
    build_business_methodology,
)
from langGraph_agent.smart_data_analysis_assistant.chatbi_graph.services.profiling import (
    build_data_profile,
    build_quality_score,
)


def test_methodology_service_selects_sales_framework():
    schema_profile = {
        "rowCount": 3,
        "columnCount": 4,
        "columns": ["日期", "区域", "销售额", "成本"],
    }

    plan = build_analysis_plan("销售经营", schema_profile, ["销售额", "成本"], ["区域"], ["日期"], "销售额", "区域")
    methodology = build_business_methodology("销售经营", schema_profile["columns"], ["销售额"], ["区域"], "销售额", "区域", ["日期"])

    assert plan["framework"]["title"] == "销售经营分析框架"
    assert plan["inputPolicy"] == "schema-only"
    assert any(item["name"] == "区域效率" for item in methodology)


def test_profiling_service_scores_quality():
    df = pd.DataFrame({"日期": ["2026-01-01", "2026-01-02"], "区域": ["华东", "华北"], "销售额": [100, 200]})
    schema_profile = {
        "fields": [
            {"name": "日期", "role": "time", "missingRate": 0},
            {"name": "区域", "role": "dimension", "missingRate": 0},
            {"name": "销售额", "role": "metric", "missingRate": 0},
        ],
        "roleCounts": {"time": 1, "dimension": 1, "metric": 1},
    }
    metadata = {"rowsBefore": 2, "removedDuplicateRows": 0, "typeChanges": []}

    profile = build_data_profile(df, schema_profile, ["销售额"], ["区域"], ["日期"], metadata)
    quality = build_quality_score(profile, metadata, "销售额", "区域", ["日期"])

    assert profile["metricCount"] == 1
    assert quality["grade"] in ["A", "B"]


def test_diagnostics_service_builds_problem_chain():
    df = pd.DataFrame({"区域": ["华东", "华东", "华北"], "销售额": [100, 120, 20], "成本": [50, 60, 10]})
    top_categories = [{"name": "华东", "value": 220}, {"name": "华北", "value": 20}]
    trend = [{"period": "2026-01", "value": 100}, {"period": "2026-02", "value": 260}]
    benchmark = build_benchmark_summary(top_categories, trend, "销售额", "区域")
    drivers = build_driver_analysis(df, "销售额", ["区域"], [])
    actions = build_priority_actions("销售经营", "销售额", "区域", benchmark, drivers, [], ["区域", "销售额"])
    story = build_diagnostic_story(["销售额增长"], benchmark, [], drivers, actions, "销售额")

    assert benchmark
    assert drivers[0]["dimension"] == "区域"
    assert story[0]["stage"] == "现象"
    assert actions


def test_analysis_utils_detects_columns():
    df = pd.DataFrame({"日期": ["2026-01-01"], "销售额": [100]})

    assert numeric_columns(df) == ["销售额"]
    assert datetime_like_columns(df) == ["日期"]
    assert choose_primary_metric([{"column": "销售额"}]) == "销售额"
