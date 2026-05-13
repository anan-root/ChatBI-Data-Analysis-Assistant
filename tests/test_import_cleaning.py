import pandas as pd

from langGraph_agent.smart_data_analysis_assistant.chatbi_graph.services.import_cleaning import (
    build_schema_profile,
    clean_dataframe,
    infer_business_type_from_schema,
    json_ready,
    normalize_table_name,
)


def test_clean_dataframe_serializes_timestamp_and_profiles_fields():
    raw = pd.DataFrame(
        {
            " 日期 ": [pd.Timestamp("2026-01-01"), pd.Timestamp("2026-01-02")],
            "销售额": [100.0, None],
            "区域": [" 华东 ", ""],
        }
    )

    cleaned, report = clean_dataframe(raw)
    profile = build_schema_profile(cleaned, "销售数据.xlsx")
    payload = json_ready({"preview": cleaned.to_dict(orient="records"), "profile": profile})

    assert cleaned["日期"].iloc[0] == "2026-01-01 00:00:00"
    assert cleaned["销售额"].iloc[1] == 0
    assert cleaned["区域"].iloc[1] == "未知"
    assert report["columnsAfter"] == 3
    assert profile["roleCounts"]["metric"] >= 1
    assert infer_business_type_from_schema(profile) == "销售经营"
    assert payload["preview"][0]["日期"] == "2026-01-01 00:00:00"


def test_normalize_table_name_adds_import_prefix_and_sanitizes():
    assert normalize_table_name("销售 数据 2026", None).startswith("import_")
    assert " " not in normalize_table_name("销售 数据 2026", None)
