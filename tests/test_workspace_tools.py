from langGraph_agent.smart_data_analysis_assistant.chatbi_graph.services import workspace_tools


def test_compact_workspace_list_uses_import_jobs(monkeypatch):
    monkeypatch.setattr(
        workspace_tools,
        "list_import_jobs",
        lambda limit=20: {
            "metadataStore": "file",
            "jobs": [
                {
                    "jobId": "job_001",
                    "workspaceName": "销售演示",
                    "businessType": "销售经营",
                    "originalFilename": "sales.xlsx",
                    "imported": True,
                    "dbTable": "import_sales",
                    "schemaProfile": {"rowCount": 10, "columnCount": 3, "roleCounts": {"metric": 1}},
                }
            ],
        },
    )

    result = workspace_tools.compact_workspace_list(limit=5)

    assert result["metadataStore"] == "file"
    assert result["workspaces"][0]["workspaceId"] == "job_001"
    assert result["workspaces"][0]["rows"] == 10


def test_workspace_schema_profile_compacts_fields(monkeypatch):
    monkeypatch.setattr(
        workspace_tools,
        "get_import_job",
        lambda workspace_id: {
            "jobId": workspace_id,
            "workspaceName": "用户演示",
            "businessType": "用户运营",
            "originalFilename": "users.xlsx",
            "schemaProfile": {
                "rowCount": 20,
                "columnCount": 2,
                "columns": ["用户ID", "活跃天数"],
                "fields": [{"name": "用户ID", "role": "identifier"}],
                "roleCounts": {"identifier": 1},
            },
        },
    )

    result = workspace_tools.workspace_schema_profile("job_002")

    assert result["workspaceId"] == "job_002"
    assert result["schemaProfile"]["columns"] == ["用户ID", "活跃天数"]


def test_workspace_analysis_context_uses_report_builder():
    def fake_report_builder(workspace_id):
        return {
            "jobId": workspace_id,
            "workspaceName": "库存演示",
            "businessType": "库存管理",
            "sourceFile": "inventory.xlsx",
            "imported": True,
            "dbTable": "import_inventory",
            "schemaProfile": {"columns": ["SKU", "库存量"], "fields": [], "roleCounts": {}},
            "dataProfile": {"profileSummary": "20 行"},
            "qualityScore": {"score": 90, "grade": "A"},
            "analysisPlan": {"name": "库存分析"},
            "metricCatalog": [{"name": "库存量"}],
            "recommendedPaths": [{"name": "缺货风险"}],
            "priorityActions": [{"priority": "P0"}],
            "diagnosticStory": [{"stage": "现象"}],
            "sections": [],
        }

    result = workspace_tools.workspace_analysis_context("job_003", fake_report_builder)

    assert result["workspaceId"] == "job_003"
    assert result["qualityScore"]["score"] == 90
    assert result["recommendedPaths"][0]["name"] == "缺货风险"


def test_workspace_report_summary_compacts_charts_and_sql():
    def fake_report_builder(workspace_id):
        return {
            "jobId": workspace_id,
            "workspaceName": "运营演示",
            "businessType": "运营分析",
            "qualityScore": {"score": 88},
            "executiveSummary": {"highlights": []},
            "diagnosticStory": [{"stage": "现象"}],
            "priorityActions": [{"priority": "P1"}],
            "recommendedPaths": [{"name": "渠道对比"}],
            "charts": [{"title": "渠道转化", "type": "bar", "businessQuestion": "哪个渠道好", "whyThisChart": "适合对比"}],
            "sqlTemplates": [{"name": "渠道排行"}],
        }

    result = workspace_tools.workspace_report_summary("job_004", fake_report_builder)

    assert result["charts"][0]["title"] == "渠道转化"
    assert result["sqlTemplates"][0]["name"] == "渠道排行"
