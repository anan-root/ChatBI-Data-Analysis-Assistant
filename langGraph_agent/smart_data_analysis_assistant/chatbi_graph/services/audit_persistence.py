try:
    from ..config import postgres_audit_enabled
except ImportError:
    from config import postgres_audit_enabled


def _audit_repository():
    try:
        from ..repositories import audit_events
    except ImportError:
        from repositories import audit_events
    return audit_events


def init_audit_storage():
    return _audit_repository().init_audit_schema()


def persist_audit_event(event):
    if not postgres_audit_enabled():
        return {"enabled": False, "synced": False}
    try:
        result = _audit_repository().insert_audit_event(event)
        return {"enabled": True, "synced": True, **result}
    except Exception as exc:
        return {"enabled": True, "synced": False, "error": str(exc)}


def list_persisted_audit_events(limit=200, event_type=None, workspace_id=None, allowed=None, source=None):
    return _audit_repository().list_audit_events(
        limit=limit,
        event_type=event_type,
        workspace_id=workspace_id,
        allowed=allowed,
        source=source,
    )
