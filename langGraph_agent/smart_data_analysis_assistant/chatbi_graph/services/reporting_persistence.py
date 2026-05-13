try:
    from ..config import postgres_metadata_enabled
except ImportError:
    from config import postgres_metadata_enabled


def _metadata_repository():
    try:
        from ..repositories import workspace_metadata
    except ImportError:
        from repositories import workspace_metadata
    return workspace_metadata


def upsert_analysis_report(report):
    return _metadata_repository().upsert_analysis_report(report)


def replace_metric_definitions(workspace_id, metrics):
    return _metadata_repository().replace_metric_definitions(workspace_id, metrics)


def sync_workspace_report_to_postgres(report):
    if not postgres_metadata_enabled():
        return {"enabled": False, "synced": False}
    try:
        report_result = upsert_analysis_report(report)
        metrics_result = replace_metric_definitions(
            report.get("jobId"),
            report.get("metricCatalog", []),
        )
        return {
            "enabled": True,
            "synced": True,
            "report": report_result,
            "metrics": metrics_result,
        }
    except Exception as exc:
        return {"enabled": True, "synced": False, "error": str(exc)}
