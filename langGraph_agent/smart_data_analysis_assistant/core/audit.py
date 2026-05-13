"""Lightweight audit logging for security-sensitive ChatBI operations."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


DEFAULT_AUDIT_MAX_EVENTS = 200
AUDIT_ENABLED_ENV = "CHATBI_AUDIT_ENABLED"
AUDIT_LOG_PATH_ENV = "CHATBI_AUDIT_LOG_PATH"
AUDIT_ADMIN_TOKEN_ENV = "CHATBI_AUDIT_ADMIN_TOKEN"


def is_audit_enabled() -> bool:
    return os.getenv(AUDIT_ENABLED_ENV, "true").strip().lower() in {"1", "true", "yes", "on"}


def audit_admin_token() -> str:
    return os.getenv(AUDIT_ADMIN_TOKEN_ENV, "").strip()


def default_audit_log_path() -> Path:
    try:
        from langGraph_agent.smart_data_analysis_assistant.chatbi_graph.config import AUDIT_DIR
    except ImportError:
        try:
            from chatbi_graph.config import AUDIT_DIR
        except ImportError:
            AUDIT_DIR = Path.cwd() / "audit_logs"
    return Path(AUDIT_DIR) / "security_audit.jsonl"


def get_audit_log_path() -> Path:
    configured_path = os.getenv(AUDIT_LOG_PATH_ENV)
    if configured_path:
        return Path(configured_path)
    return default_audit_log_path()


def redact_query(query: str | None, max_length: int = 500) -> str:
    if not query:
        return ""
    compact_query = " ".join(str(query).split())
    if len(compact_query) <= max_length:
        return compact_query
    return f"{compact_query[:max_length]}..."


def hash_query(query: str | None) -> str:
    return hashlib.sha256(str(query or "").encode("utf-8")).hexdigest()[:16]


def _audit_persistence_service():
    try:
        from langGraph_agent.smart_data_analysis_assistant.chatbi_graph.services import audit_persistence
    except ImportError:
        try:
            from chatbi_graph.services import audit_persistence
        except ImportError:
            return None
    return audit_persistence


def postgres_audit_enabled() -> bool:
    try:
        from langGraph_agent.smart_data_analysis_assistant.chatbi_graph.config import postgres_audit_enabled as enabled
    except ImportError:
        try:
            from chatbi_graph.config import postgres_audit_enabled as enabled
        except ImportError:
            return False
    return enabled()


def sync_audit_event_to_postgres(event: dict[str, Any]) -> dict[str, Any]:
    service = _audit_persistence_service()
    if service is None:
        return {"enabled": False, "synced": False}
    return service.persist_audit_event(event)


def write_audit_event(event_type: str, **payload: Any) -> dict[str, Any]:
    event = {
        "timestamp": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "eventType": event_type,
        **payload,
    }
    if not is_audit_enabled():
        return {**event, "written": False}

    log_path = get_audit_log_path()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as audit_file:
        audit_file.write(json.dumps(event, ensure_ascii=False, default=str) + "\n")
    postgres_result = sync_audit_event_to_postgres(event)
    return {**event, "written": True, "postgresAudit": postgres_result}


def audit_sql_decision(
    *,
    source: str,
    allowed: bool,
    query: str | None,
    reason: str = "",
    workspace_id: str | None = None,
    workspace_name: str | None = None,
    table_references: list[str] | tuple[str, ...] | None = None,
    row_limit: int | None = None,
    elapsed_ms: float | None = None,
    row_count: int | None = None,
) -> dict[str, Any]:
    return write_audit_event(
        "sql_decision",
        source=source,
        allowed=allowed,
        reason=reason,
        workspaceId=workspace_id,
        workspaceName=workspace_name,
        tableReferences=list(table_references or []),
        queryHash=hash_query(query),
        queryPreview=redact_query(query),
        rowLimit=row_limit,
        elapsedMs=round(elapsed_ms, 2) if elapsed_ms is not None else None,
        rowCount=row_count,
    )


def _matches_optional_filter(value: Any, expected: str | None) -> bool:
    if expected is None or expected == "":
        return True
    return str(value or "") == str(expected)


def _matches_allowed_filter(value: Any, expected: bool | None) -> bool:
    if expected is None:
        return True
    return bool(value) is expected


def _event_matches_filters(
    event: dict[str, Any],
    *,
    event_type: str | None = None,
    workspace_id: str | None = None,
    allowed: bool | None = None,
    source: str | None = None,
) -> bool:
    return (
        _matches_optional_filter(event.get("eventType"), event_type)
        and _matches_optional_filter(event.get("workspaceId"), workspace_id)
        and _matches_optional_filter(event.get("source"), source)
        and _matches_allowed_filter(event.get("allowed"), allowed)
    )


def read_audit_events(
    limit: int = DEFAULT_AUDIT_MAX_EVENTS,
    event_type: str | None = None,
    workspace_id: str | None = None,
    allowed: bool | None = None,
    source: str | None = None,
) -> list[dict[str, Any]]:
    max_events = max(1, min(int(limit or DEFAULT_AUDIT_MAX_EVENTS), 1000))
    if postgres_audit_enabled():
        service = _audit_persistence_service()
        if service is not None:
            try:
                return service.list_persisted_audit_events(
                    limit=max_events,
                    event_type=event_type,
                    workspace_id=workspace_id,
                    allowed=allowed,
                    source=source,
                )
            except Exception:
                pass

    return read_jsonl_audit_events(
        limit=max_events,
        event_type=event_type,
        workspace_id=workspace_id,
        allowed=allowed,
        source=source,
    )


def read_jsonl_audit_events(
    limit: int = DEFAULT_AUDIT_MAX_EVENTS,
    event_type: str | None = None,
    workspace_id: str | None = None,
    allowed: bool | None = None,
    source: str | None = None,
) -> list[dict[str, Any]]:
    max_events = max(1, min(int(limit or DEFAULT_AUDIT_MAX_EVENTS), 1000))
    log_path = get_audit_log_path()
    if not log_path.exists():
        return []

    events: list[dict[str, Any]] = []
    with log_path.open("r", encoding="utf-8") as audit_file:
        for line in audit_file:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not _event_matches_filters(
                event,
                event_type=event_type,
                workspace_id=workspace_id,
                allowed=allowed,
                source=source,
            ):
                continue
            events.append(event)
    return events[-max_events:][::-1]
