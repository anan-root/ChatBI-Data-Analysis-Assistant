from langGraph_agent.smart_data_analysis_assistant.chatbi_graph.services.knowledge_base import (
    build_rag_catalog,
    search_knowledge,
)


def test_search_knowledge_matches_roi():
    results = search_knowledge("请分析这个活动的 ROI 和投产比")

    assert results
    assert results[0]["title"] == "ROI"


def test_search_knowledge_matches_sales_amount():
    results = search_knowledge("本月销售额趋势如何")

    assert any(item["title"] == "销售额" for item in results)


def test_search_knowledge_returns_empty_when_no_match():
    results = search_knowledge("这个字段完全没有业务词")

    assert results == []


def test_build_rag_catalog_exposes_metric_dictionary():
    catalog = build_rag_catalog()

    assert catalog["enabled"] is True
    assert catalog["count"] >= 3
    assert any(item["title"] == "ROI" for item in catalog["items"])
