import json

from langGraph_agent.smart_data_analysis_assistant.core.audit import (
    audit_admin_token,
    audit_sql_decision,
    get_audit_log_path,
    postgres_audit_enabled,
    read_audit_events,
    read_jsonl_audit_events,
    redact_query,
    write_audit_event,
)
from langGraph_agent.smart_data_analysis_assistant.chatbi_graph import bi_api
from langGraph_agent.smart_data_analysis_assistant.chatbi_graph.bi_api import build_audit_log_data
from langGraph_agent.smart_data_analysis_assistant.chatbi_graph.services import audit_persistence


def test_audit_sql_decision_writes_jsonl(monkeypatch, tmp_path):
    audit_file = tmp_path / "security_audit.jsonl"
    monkeypatch.setenv("CHATBI_AUDIT_LOG_PATH", str(audit_file))
    monkeypatch.setenv("CHATBI_AUDIT_ENABLED", "true")

    event = audit_sql_decision(
        source="test",
        allowed=False,
        query="select * from forbidden_table",
        reason="blocked",
        workspace_id="job_001",
        table_references=("forbidden_table",),
    )

    assert event["written"] is True
    assert get_audit_log_path() == audit_file
    line = audit_file.read_text(encoding="utf-8").strip()
    parsed = json.loads(line)
    assert parsed["eventType"] == "sql_decision"
    assert parsed["allowed"] is False
    assert parsed["workspaceId"] == "job_001"
    assert parsed["queryHash"]


def test_read_audit_events_returns_latest_first(monkeypatch, tmp_path):
    audit_file = tmp_path / "security_audit.jsonl"
    monkeypatch.setenv("CHATBI_AUDIT_LOG_PATH", str(audit_file))
    monkeypatch.setenv("CHATBI_AUDIT_ENABLED", "true")

    audit_sql_decision(source="test", allowed=True, query="select 1", reason="ok")
    audit_sql_decision(source="test", allowed=False, query="drop table x", reason="blocked")

    events = read_audit_events(limit=2)

    assert [event["allowed"] for event in events] == [False, True]


def test_read_jsonl_audit_events_ignores_postgres_mode(monkeypatch, tmp_path):
    audit_file = tmp_path / "security_audit.jsonl"
    monkeypatch.setenv("CHATBI_AUDIT_LOG_PATH", str(audit_file))
    monkeypatch.setenv("CHATBI_AUDIT_ENABLED", "true")
    monkeypatch.setenv("CHATBI_USE_POSTGRES_AUDIT", "true")

    audit_sql_decision(source="test", allowed=True, query="select 1", reason="ok")

    events = read_jsonl_audit_events()

    assert len(events) == 1
    assert events[0]["source"] == "test"


def test_build_audit_log_data_summarizes_counts(monkeypatch, tmp_path):
    audit_file = tmp_path / "security_audit.jsonl"
    monkeypatch.setenv("CHATBI_AUDIT_LOG_PATH", str(audit_file))
    monkeypatch.setenv("CHATBI_AUDIT_ENABLED", "true")

    audit_sql_decision(source="test", allowed=True, query="select 1", reason="ok")
    audit_sql_decision(source="test", allowed=False, query="update x set y = 1", reason="blocked")

    data = build_audit_log_data()

    assert data["total"] == 2
    assert data["allowedCount"] == 1
    assert data["blockedCount"] == 1
    assert data["store"] == "jsonl"


def test_read_audit_events_filters_by_workspace_and_allowed(monkeypatch, tmp_path):
    audit_file = tmp_path / "security_audit.jsonl"
    monkeypatch.setenv("CHATBI_AUDIT_LOG_PATH", str(audit_file))
    monkeypatch.setenv("CHATBI_AUDIT_ENABLED", "true")

    audit_sql_decision(source="workspace_sql_scope", allowed=True, query="select 1", reason="ok", workspace_id="job_a")
    audit_sql_decision(source="workspace_sql_scope", allowed=False, query="select *", reason="blocked", workspace_id="job_b")

    events = read_audit_events(workspace_id="job_b", allowed=False)

    assert len(events) == 1
    assert events[0]["workspaceId"] == "job_b"
    assert events[0]["allowed"] is False


def test_audit_admin_token_reads_optional_env(monkeypatch):
    monkeypatch.setenv("CHATBI_AUDIT_ADMIN_TOKEN", "secret-token")

    assert audit_admin_token() == "secret-token"


def test_postgres_audit_disabled_by_default(monkeypatch):
    monkeypatch.delenv("CHATBI_USE_POSTGRES_AUDIT", raising=False)

    assert postgres_audit_enabled() is False


def test_write_audit_event_syncs_to_postgres_when_enabled(monkeypatch, tmp_path):
    audit_file = tmp_path / "security_audit.jsonl"
    captured = {}

    def fake_sync(event):
        captured["event"] = event
        return {"enabled": True, "synced": True, "auditId": 1}

    monkeypatch.setenv("CHATBI_AUDIT_LOG_PATH", str(audit_file))
    monkeypatch.setenv("CHATBI_AUDIT_ENABLED", "true")
    monkeypatch.setenv("CHATBI_USE_POSTGRES_AUDIT", "true")
    monkeypatch.setattr(audit_persistence, "persist_audit_event", fake_sync)

    event = write_audit_event("sql_decision", source="test", allowed=True)

    assert event["postgresAudit"]["synced"] is True
    assert captured["event"]["source"] == "test"


def test_build_audit_log_data_reads_postgres_when_enabled(monkeypatch):
    monkeypatch.setenv("CHATBI_USE_POSTGRES_AUDIT", "true")
    monkeypatch.setattr(
        audit_persistence,
        "list_persisted_audit_events",
        lambda **kwargs: [{"eventType": "sql_decision", "allowed": False, "workspaceId": "job_1"}],
    )

    data = build_audit_log_data(allowed=False)

    assert data["store"] == "postgres"
    assert data["blockedCount"] == 1


def test_migrate_audit_logs_to_postgres_uses_jsonl_source(monkeypatch, tmp_path):
    audit_file = tmp_path / "security_audit.jsonl"
    monkeypatch.setenv("CHATBI_AUDIT_LOG_PATH", str(audit_file))
    monkeypatch.setenv("CHATBI_AUDIT_ENABLED", "true")
    monkeypatch.setenv("CHATBI_USE_POSTGRES_AUDIT", "true")
    monkeypatch.setattr(bi_api, "persist_audit_event", lambda event: {"enabled": True, "synced": True, "auditId": 1})
    audit_sql_decision(source="test", allowed=True, query="select 1", reason="ok")

    result = bi_api.migrate_audit_logs_to_postgres()

    assert result["migrated"] == 1
    assert result["failed"] == 0


def test_redact_query_limits_preview_length():
    preview = redact_query("select " + "x" * 800, max_length=40)

    assert len(preview) == 43
    assert preview.endswith("...")
