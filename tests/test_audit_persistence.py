from langGraph_agent.smart_data_analysis_assistant.chatbi_graph.config import postgres_audit_enabled
from langGraph_agent.smart_data_analysis_assistant.chatbi_graph.services import audit_persistence


def test_postgres_audit_disabled_by_default(monkeypatch):
    monkeypatch.delenv("CHATBI_USE_POSTGRES_AUDIT", raising=False)

    assert postgres_audit_enabled() is False


def test_persist_audit_event_skips_when_disabled(monkeypatch):
    monkeypatch.delenv("CHATBI_USE_POSTGRES_AUDIT", raising=False)

    result = audit_persistence.persist_audit_event({"eventType": "sql_decision"})

    assert result == {"enabled": False, "synced": False}


def test_persist_audit_event_calls_repository_when_enabled(monkeypatch):
    captured = {}

    class FakeRepository:
        @staticmethod
        def insert_audit_event(event):
            captured["event"] = event
            return {"ok": True, "auditId": 7}

    monkeypatch.setenv("CHATBI_USE_POSTGRES_AUDIT", "true")
    monkeypatch.setattr(audit_persistence, "_audit_repository", lambda: FakeRepository)

    result = audit_persistence.persist_audit_event({"eventType": "sql_decision", "source": "test"})

    assert result["synced"] is True
    assert result["auditId"] == 7
    assert captured["event"]["source"] == "test"


def test_list_persisted_audit_events_delegates_to_repository(monkeypatch):
    captured = {}

    class FakeRepository:
        @staticmethod
        def list_audit_events(**kwargs):
            captured.update(kwargs)
            return [{"eventType": "sql_decision"}]

    monkeypatch.setattr(audit_persistence, "_audit_repository", lambda: FakeRepository)

    events = audit_persistence.list_persisted_audit_events(limit=10, allowed=False)

    assert events[0]["eventType"] == "sql_decision"
    assert captured["limit"] == 10
    assert captured["allowed"] is False
