import json

try:
    from .import_cleaning import get_import_job, list_import_jobs
    from .workspace_context import build_workspace_chat_context_from_report
except ImportError:
    from services.import_cleaning import get_import_job, list_import_jobs
    from services.workspace_context import build_workspace_chat_context_from_report


def compact_workspace_list(limit=20):
    data = list_import_jobs(limit=limit)
    workspaces = []
    for job in data.get("jobs", []):
        schema_profile = job.get("schemaProfile", {}) or {}
        workspaces.append(
            {
                "workspaceId": job.get("jobId"),
                "name": job.get("workspaceName"),
                "businessType": job.get("businessType"),
                "sourceFile": job.get("originalFilename"),
                "imported": job.get("imported", False),
                "dbTable": job.get("dbTable"),
                "rows": schema_profile.get("rowCount") or job.get("rowsAfter"),
                "columns": schema_profile.get("columnCount") or job.get("columnsAfter"),
                "roleCounts": schema_profile.get("roleCounts", {}),
            }
        )
    return {"metadataStore": data.get("metadataStore"), "workspaces": workspaces}


def workspace_schema_profile(workspace_id):
    job = get_import_job(workspace_id)
    schema_profile = job.get("schemaProfile", {}) or {}
    return {
        "workspaceId": job.get("jobId"),
        "workspaceName": job.get("workspaceName"),
        "businessType": job.get("businessType"),
        "sourceFile": job.get("originalFilename"),
        "imported": job.get("imported", False),
        "dbTable": job.get("dbTable"),
        "schemaProfile": {
            "rowCount": schema_profile.get("rowCount"),
            "columnCount": schema_profile.get("columnCount"),
            "columns": schema_profile.get("columns", [])[:120],
            "roleCounts": schema_profile.get("roleCounts", {}),
            "fields": schema_profile.get("fields", [])[:120],
        },
    }


def workspace_analysis_context(workspace_id, build_workspace_report):
    report = build_workspace_report(workspace_id)
    context = build_workspace_chat_context_from_report(report)
    return {
        "workspaceId": context.get("workspaceId"),
        "workspaceName": context.get("workspaceName"),
        "businessType": context.get("businessType"),
        "sourceFile": context.get("sourceFile"),
        "imported": context.get("imported"),
        "dbTable": context.get("dbTable"),
        "schema": context.get("schema", {}),
        "dataProfile": context.get("dataProfile", {}),
        "qualityScore": context.get("qualityScore", {}),
        "analysisPlan": context.get("analysisPlan", {}),
        "metricCatalog": context.get("metricCatalog", []),
        "recommendedPaths": context.get("reportSummary", {}).get("recommendedPaths", []),
        "priorityActions": context.get("reportSummary", {}).get("priorityActions", []),
        "diagnosticStory": context.get("reportSummary", {}).get("diagnosticStory", []),
    }


def workspace_report_summary(workspace_id, build_workspace_report):
    report = build_workspace_report(workspace_id)
    return {
        "workspaceId": report.get("jobId"),
        "workspaceName": report.get("workspaceName"),
        "businessType": report.get("businessType"),
        "qualityScore": report.get("qualityScore", {}),
        "executiveSummary": report.get("executiveSummary", {}),
        "diagnosticStory": report.get("diagnosticStory", [])[:8],
        "priorityActions": report.get("priorityActions", [])[:8],
        "recommendedPaths": report.get("recommendedPaths", [])[:8],
        "charts": [
            {
                "title": chart.get("title"),
                "type": chart.get("type"),
                "businessQuestion": chart.get("businessQuestion"),
                "whyThisChart": chart.get("whyThisChart"),
            }
            for chart in report.get("charts", [])[:8]
        ],
        "sqlTemplates": report.get("sqlTemplates", [])[:8],
    }


def json_dumps(data):
    return json.dumps(data, ensure_ascii=False, default=str)
