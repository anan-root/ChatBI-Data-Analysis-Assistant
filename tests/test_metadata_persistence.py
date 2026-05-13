import json
import sys

from langGraph_agent.smart_data_analysis_assistant.chatbi_graph.config import postgres_metadata_enabled
from langGraph_agent.smart_data_analysis_assistant.chatbi_graph.services import (
    import_cleaning,
    reporting_persistence,
)


def test_workspace_metadata_repository_is_lazy_loaded():
    repository_module = "langGraph_agent.smart_data_analysis_assistant.chatbi_graph.repositories.workspace_metadata"

    assert repository_module not in sys.modules


def test_postgres_metadata_disabled_by_default(monkeypatch):
    monkeypatch.delenv("CHATBI_USE_POSTGRES_METADATA", raising=False)

    assert postgres_metadata_enabled() is False


def test_sync_metadata_skips_when_disabled(monkeypatch):
    monkeypatch.delenv("CHATBI_USE_POSTGRES_METADATA", raising=False)

    result = import_cleaning.sync_metadata_to_postgres({"jobId": "job_001"})

    assert result == {"enabled": False, "synced": False}


def test_sync_metadata_calls_repository_when_enabled(monkeypatch):
    called = {}

    def fake_upsert(metadata):
        called["metadata"] = metadata
        return {"ok": True, "jobId": metadata["jobId"]}

    monkeypatch.setenv("CHATBI_USE_POSTGRES_METADATA", "true")
    monkeypatch.setattr(import_cleaning, "upsert_import_metadata", fake_upsert)

    result = import_cleaning.sync_metadata_to_postgres({"jobId": "job_001"})

    assert result["synced"] is True
    assert called["metadata"]["jobId"] == "job_001"


def test_load_import_job_falls_back_to_postgres_when_file_missing(monkeypatch, tmp_path):
    monkeypatch.setenv("CHATBI_USE_POSTGRES_METADATA", "true")
    monkeypatch.setattr(import_cleaning, "METADATA_DIR", tmp_path)
    monkeypatch.setattr(import_cleaning, "load_import_metadata", lambda job_id: {"jobId": job_id, "originalFilename": "demo.csv"})

    metadata = import_cleaning.load_import_job("job_001")

    assert metadata["jobId"] == "job_001"


def test_migrate_file_metadata_to_postgres(monkeypatch, tmp_path):
    metadata = {"jobId": "job_001", "originalFilename": "demo.csv"}
    (tmp_path / "job_001.json").write_text(json.dumps(metadata), encoding="utf-8")
    monkeypatch.setattr(import_cleaning, "METADATA_DIR", tmp_path)
    monkeypatch.setattr(import_cleaning, "upsert_import_metadata", lambda item: {"ok": True, "jobId": item["jobId"]})

    result = import_cleaning.migrate_file_metadata_to_postgres()

    assert result["migrated"] == 1
    assert result["failed"] == 0


def test_sync_workspace_report_skips_when_disabled(monkeypatch):
    monkeypatch.delenv("CHATBI_USE_POSTGRES_METADATA", raising=False)

    result = reporting_persistence.sync_workspace_report_to_postgres({"jobId": "job_001"})

    assert result == {"enabled": False, "synced": False}


def test_sync_workspace_report_persists_report_and_metrics(monkeypatch):
    calls = {}

    def fake_upsert_report(report):
        calls["report"] = report
        return {"ok": True, "reportId": f"{report['jobId']}:workspace"}

    def fake_replace_metrics(workspace_id, metrics):
        calls["metrics"] = metrics
        calls["workspace_id"] = workspace_id
        return {"ok": True, "workspaceId": workspace_id, "metricCount": len(metrics)}

    monkeypatch.setenv("CHATBI_USE_POSTGRES_METADATA", "true")
    monkeypatch.setattr(reporting_persistence, "upsert_analysis_report", fake_upsert_report)
    monkeypatch.setattr(reporting_persistence, "replace_metric_definitions", fake_replace_metrics)

    result = reporting_persistence.sync_workspace_report_to_postgres(
        {
            "jobId": "job_001",
            "metricCatalog": [{"name": "销售额", "formula": "SUM(销售额)"}],
        }
    )

    assert result["synced"] is True
    assert calls["workspace_id"] == "job_001"
    assert calls["metrics"][0]["name"] == "销售额"
