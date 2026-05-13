import json

from psycopg2.extras import Json

try:
    from .database import get_connection
except ImportError:
    from repositories.database import get_connection


AUDIT_SCHEMA_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS chatbi_audit_event (
        audit_id BIGSERIAL PRIMARY KEY,
        event_type TEXT NOT NULL,
        source TEXT,
        allowed BOOLEAN,
        reason TEXT,
        workspace_id TEXT,
        workspace_name TEXT,
        table_references JSONB NOT NULL DEFAULT '[]'::jsonb,
        query_hash TEXT,
        query_preview TEXT,
        row_limit INTEGER,
        row_count INTEGER,
        elapsed_ms DOUBLE PRECISION,
        event_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
        occurred_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_chatbi_audit_event_occurred_at ON chatbi_audit_event (occurred_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_chatbi_audit_event_workspace ON chatbi_audit_event (workspace_id)",
    "CREATE INDEX IF NOT EXISTS idx_chatbi_audit_event_allowed ON chatbi_audit_event (allowed)",
    "CREATE INDEX IF NOT EXISTS idx_chatbi_audit_event_source ON chatbi_audit_event (source)",
]


def init_audit_schema():
    with get_connection() as conn:
        with conn.cursor() as cursor:
            for statement in AUDIT_SCHEMA_STATEMENTS:
                cursor.execute(statement)
        conn.commit()
    return {"ok": True, "tables": ["chatbi_audit_event"]}


def _timestamp_without_z(timestamp):
    if not timestamp:
        return None
    return str(timestamp).replace("Z", "+00:00")


def insert_audit_event(event):
    init_audit_schema()
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO chatbi_audit_event (
                    event_type, source, allowed, reason, workspace_id, workspace_name,
                    table_references, query_hash, query_preview, row_limit, row_count,
                    elapsed_ms, event_payload, occurred_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, COALESCE(%s::timestamptz, CURRENT_TIMESTAMP))
                RETURNING audit_id
                """,
                (
                    event.get("eventType"),
                    event.get("source"),
                    event.get("allowed"),
                    event.get("reason"),
                    event.get("workspaceId"),
                    event.get("workspaceName"),
                    Json(event.get("tableReferences", [])),
                    event.get("queryHash"),
                    event.get("queryPreview"),
                    event.get("rowLimit"),
                    event.get("rowCount"),
                    event.get("elapsedMs"),
                    Json(event),
                    _timestamp_without_z(event.get("timestamp")),
                ),
            )
            audit_id = cursor.fetchone()[0]
        conn.commit()
    return {"ok": True, "auditId": audit_id}


def _row_to_event(row):
    payload = row.get("event_payload") or {}
    if isinstance(payload, str):
        payload = json.loads(payload)
    event = dict(payload)
    event.setdefault("eventType", row.get("event_type"))
    event.setdefault("source", row.get("source"))
    event.setdefault("allowed", row.get("allowed"))
    event.setdefault("reason", row.get("reason"))
    event.setdefault("workspaceId", row.get("workspace_id"))
    event.setdefault("workspaceName", row.get("workspace_name"))
    event.setdefault("queryHash", row.get("query_hash"))
    event.setdefault("queryPreview", row.get("query_preview"))
    event.setdefault("rowLimit", row.get("row_limit"))
    event.setdefault("rowCount", row.get("row_count"))
    event.setdefault("elapsedMs", row.get("elapsed_ms"))
    if "timestamp" not in event and row.get("occurred_at"):
        event["timestamp"] = row["occurred_at"].isoformat()
    event["auditId"] = row.get("audit_id")
    return event


def list_audit_events(limit=200, event_type=None, workspace_id=None, allowed=None, source=None):
    init_audit_schema()
    conditions = []
    params = []
    if event_type:
        conditions.append("event_type = %s")
        params.append(event_type)
    if workspace_id:
        conditions.append("workspace_id = %s")
        params.append(workspace_id)
    if allowed is not None:
        conditions.append("allowed = %s")
        params.append(allowed)
    if source:
        conditions.append("source = %s")
        params.append(source)
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    params.append(max(1, min(int(limit or 200), 1000)))

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT audit_id, event_type, source, allowed, reason, workspace_id,
                       workspace_name, table_references, query_hash, query_preview,
                       row_limit, row_count, elapsed_ms, event_payload, occurred_at
                FROM chatbi_audit_event
                {where_clause}
                ORDER BY occurred_at DESC, audit_id DESC
                LIMIT %s
                """,
                params,
            )
            columns = [desc[0] for desc in cursor.description]
            rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
    return [_row_to_event(row) for row in rows]
