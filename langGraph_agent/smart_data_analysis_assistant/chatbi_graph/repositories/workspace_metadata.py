import json

from psycopg2.extras import Json

try:
    from .database import get_connection
except ImportError:
    from repositories.database import get_connection


SCHEMA_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS chatbi_workspace (
        workspace_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        business_type TEXT NOT NULL DEFAULT '通用业务',
        source_file TEXT NOT NULL,
        created_at TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        imported BOOLEAN NOT NULL DEFAULT FALSE,
        db_table TEXT,
        metadata JSONB NOT NULL DEFAULT '{}'::jsonb
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS chatbi_data_asset (
        asset_id TEXT PRIMARY KEY,
        workspace_id TEXT NOT NULL REFERENCES chatbi_workspace(workspace_id) ON DELETE CASCADE,
        original_filename TEXT NOT NULL,
        cleaned_file TEXT NOT NULL,
        rows_before INTEGER,
        rows_after INTEGER,
        columns_before INTEGER,
        columns_after INTEGER,
        schema_profile JSONB NOT NULL DEFAULT '{}'::jsonb,
        cleaning_report JSONB NOT NULL DEFAULT '{}'::jsonb,
        created_at TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS chatbi_import_job (
        job_id TEXT PRIMARY KEY,
        workspace_id TEXT NOT NULL REFERENCES chatbi_workspace(workspace_id) ON DELETE CASCADE,
        status TEXT NOT NULL DEFAULT 'cleaned',
        suggested_table_name TEXT,
        imported BOOLEAN NOT NULL DEFAULT FALSE,
        db_table TEXT,
        imported_at TIMESTAMP,
        metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
        created_at TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS chatbi_analysis_report (
        report_id TEXT PRIMARY KEY,
        workspace_id TEXT NOT NULL REFERENCES chatbi_workspace(workspace_id) ON DELETE CASCADE,
        report_type TEXT NOT NULL DEFAULT 'workspace',
        report_summary JSONB NOT NULL DEFAULT '{}'::jsonb,
        quality_score JSONB NOT NULL DEFAULT '{}'::jsonb,
        analysis_plan JSONB NOT NULL DEFAULT '{}'::jsonb,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS chatbi_metric_definition (
        metric_id TEXT PRIMARY KEY,
        workspace_id TEXT REFERENCES chatbi_workspace(workspace_id) ON DELETE CASCADE,
        name TEXT NOT NULL,
        formula TEXT,
        source TEXT,
        scene TEXT,
        metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
]


def init_metadata_schema():
    with get_connection() as conn:
        with conn.cursor() as cursor:
            for statement in SCHEMA_STATEMENTS:
                cursor.execute(statement)
        conn.commit()
    return {
        "ok": True,
        "tables": [
            "chatbi_workspace",
            "chatbi_data_asset",
            "chatbi_import_job",
            "chatbi_analysis_report",
            "chatbi_metric_definition",
        ],
    }


def upsert_import_metadata(metadata):
    init_metadata_schema()
    job_id = metadata["jobId"]
    workspace_name = metadata.get("workspaceName") or metadata.get("originalFilename", job_id)
    business_type = metadata.get("businessType") or "通用业务"
    created_at = metadata.get("createdAt")
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO chatbi_workspace (
                    workspace_id, name, business_type, source_file, created_at,
                    imported, db_table, metadata, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (workspace_id) DO UPDATE SET
                    name = EXCLUDED.name,
                    business_type = EXCLUDED.business_type,
                    source_file = EXCLUDED.source_file,
                    imported = EXCLUDED.imported,
                    db_table = EXCLUDED.db_table,
                    metadata = EXCLUDED.metadata,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    job_id,
                    workspace_name,
                    business_type,
                    metadata.get("originalFilename"),
                    created_at,
                    metadata.get("imported", False),
                    metadata.get("dbTable"),
                    Json(metadata),
                ),
            )
            cursor.execute(
                """
                INSERT INTO chatbi_data_asset (
                    asset_id, workspace_id, original_filename, cleaned_file,
                    rows_before, rows_after, columns_before, columns_after,
                    schema_profile, cleaning_report, created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (asset_id) DO UPDATE SET
                    original_filename = EXCLUDED.original_filename,
                    cleaned_file = EXCLUDED.cleaned_file,
                    rows_before = EXCLUDED.rows_before,
                    rows_after = EXCLUDED.rows_after,
                    columns_before = EXCLUDED.columns_before,
                    columns_after = EXCLUDED.columns_after,
                    schema_profile = EXCLUDED.schema_profile,
                    cleaning_report = EXCLUDED.cleaning_report,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    job_id,
                    job_id,
                    metadata.get("originalFilename"),
                    metadata.get("cleanedFile", ""),
                    metadata.get("rowsBefore"),
                    metadata.get("rowsAfter"),
                    metadata.get("columnsBefore"),
                    metadata.get("columnsAfter"),
                    Json(metadata.get("schemaProfile", {})),
                    Json(
                        {
                            "removedEmptyRows": metadata.get("removedEmptyRows", 0),
                            "removedEmptyColumns": metadata.get("removedEmptyColumns", 0),
                            "removedDuplicateRows": metadata.get("removedDuplicateRows", 0),
                            "fillActions": metadata.get("fillActions", []),
                            "typeChanges": metadata.get("typeChanges", []),
                        }
                    ),
                    created_at,
                ),
            )
            cursor.execute(
                """
                INSERT INTO chatbi_import_job (
                    job_id, workspace_id, status, suggested_table_name,
                    imported, db_table, imported_at, metadata, created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (job_id) DO UPDATE SET
                    status = EXCLUDED.status,
                    suggested_table_name = EXCLUDED.suggested_table_name,
                    imported = EXCLUDED.imported,
                    db_table = EXCLUDED.db_table,
                    imported_at = EXCLUDED.imported_at,
                    metadata = EXCLUDED.metadata,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    job_id,
                    job_id,
                    "imported" if metadata.get("imported") else "cleaned",
                    metadata.get("suggestedTableName"),
                    metadata.get("imported", False),
                    metadata.get("dbTable"),
                    metadata.get("importedAt"),
                    Json(metadata),
                    created_at,
                ),
            )
        conn.commit()
    return {"ok": True, "jobId": job_id}


def load_import_metadata(job_id):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT metadata FROM chatbi_import_job WHERE job_id = %s", (job_id,))
            row = cursor.fetchone()
    if not row:
        return None
    metadata = row[0]
    return json.loads(metadata) if isinstance(metadata, str) else metadata


def list_import_metadata(limit=20):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT metadata
                FROM chatbi_import_job
                ORDER BY COALESCE(created_at, updated_at) DESC
                LIMIT %s
                """,
                (limit,),
            )
            rows = cursor.fetchall()
    return [json.loads(metadata) if isinstance(metadata, str) else metadata for (metadata,) in rows]


def upsert_analysis_report(report):
    init_metadata_schema()
    workspace_id = report["jobId"]
    report_id = f"{workspace_id}:workspace"
    report_summary = {
        "workspaceName": report.get("workspaceName"),
        "businessType": report.get("businessType"),
        "sourceFile": report.get("sourceFile"),
        "executiveSummary": report.get("executiveSummary", {}),
        "diagnosticStory": report.get("diagnosticStory", []),
        "priorityActions": report.get("priorityActions", []),
        "recommendedPaths": report.get("recommendedPaths", []),
        "sections": report.get("sections", []),
    }
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO chatbi_analysis_report (
                    report_id, workspace_id, report_type, report_summary,
                    quality_score, analysis_plan, created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (report_id) DO UPDATE SET
                    report_summary = EXCLUDED.report_summary,
                    quality_score = EXCLUDED.quality_score,
                    analysis_plan = EXCLUDED.analysis_plan,
                    created_at = CURRENT_TIMESTAMP
                """,
                (
                    report_id,
                    workspace_id,
                    "workspace",
                    Json(report_summary),
                    Json(report.get("qualityScore", {})),
                    Json(report.get("analysisPlan", {})),
                ),
            )
        conn.commit()
    return {"ok": True, "reportId": report_id, "workspaceId": workspace_id}


def replace_metric_definitions(workspace_id, metrics):
    init_metadata_schema()
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "DELETE FROM chatbi_metric_definition WHERE workspace_id = %s",
                (workspace_id,),
            )
            for index, metric in enumerate(metrics or []):
                metric_name = metric.get("name") or f"metric_{index + 1}"
                metric_id = f"{workspace_id}:{index + 1}:{metric_name}"
                cursor.execute(
                    """
                    INSERT INTO chatbi_metric_definition (
                        metric_id, workspace_id, name, formula, source, scene, metadata, created_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT (metric_id) DO UPDATE SET
                        name = EXCLUDED.name,
                        formula = EXCLUDED.formula,
                        source = EXCLUDED.source,
                        scene = EXCLUDED.scene,
                        metadata = EXCLUDED.metadata,
                        created_at = CURRENT_TIMESTAMP
                    """,
                    (
                        metric_id,
                        workspace_id,
                        metric_name,
                        metric.get("formula"),
                        metric.get("source"),
                        metric.get("scene"),
                        Json(metric),
                    ),
                )
        conn.commit()
    return {"ok": True, "workspaceId": workspace_id, "metricCount": len(metrics or [])}
