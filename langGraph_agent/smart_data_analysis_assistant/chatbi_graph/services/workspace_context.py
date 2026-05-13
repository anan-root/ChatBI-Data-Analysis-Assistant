try:
    from .import_cleaning import json_ready
except ImportError:
    from services.import_cleaning import json_ready


def build_workspace_chat_context_from_report(report):
    schema_profile = report.get("schemaProfile", {})
    data_profile = report.get("dataProfile", {})
    quality_score = report.get("qualityScore", {})
    analysis_plan = report.get("analysisPlan", {})
    metric_catalog = report.get("metricCatalog", [])
    context = {
        "workspaceId": report.get("jobId"),
        "workspaceName": report.get("workspaceName"),
        "businessType": report.get("businessType"),
        "sourceFile": report.get("sourceFile"),
        "dbTable": report.get("dbTable"),
        "imported": report.get("imported"),
        "schema": {
            "rowCount": schema_profile.get("rowCount"),
            "columnCount": schema_profile.get("columnCount"),
            "columns": schema_profile.get("columns", [])[:80],
            "roleCounts": schema_profile.get("roleCounts", {}),
            "fields": schema_profile.get("fields", [])[:80],
        },
        "dataProfile": {
            "summary": data_profile.get("profileSummary"),
            "missingRate": data_profile.get("missingRate"),
            "duplicateRate": data_profile.get("duplicateRate"),
            "highMissingFields": data_profile.get("highMissingFields", [])[:10],
            "highCardinalityDimensions": data_profile.get("highCardinalityDimensions", [])[:10],
        },
        "qualityScore": {
            "score": quality_score.get("score"),
            "grade": quality_score.get("grade"),
            "summary": quality_score.get("summary"),
            "penalties": quality_score.get("penalties", [])[:8],
        },
        "analysisPlan": {
            "name": analysis_plan.get("name"),
            "confidence": analysis_plan.get("confidence"),
            "focus": analysis_plan.get("focus"),
            "framework": analysis_plan.get("framework", {}),
        },
        "metricCatalog": metric_catalog[:12],
        "reportSummary": {
            "executiveHighlights": report.get("executiveSummary", {}).get("highlights", [])[:6],
            "diagnosticStory": report.get("diagnosticStory", [])[:5],
            "priorityActions": report.get("priorityActions", [])[:8],
            "recommendedPaths": report.get("recommendedPaths", [])[:8],
            "sections": [
                {"title": section.get("title"), "content": section.get("content")}
                for section in report.get("sections", [])[:8]
            ],
        },
    }
    return json_ready(context)
