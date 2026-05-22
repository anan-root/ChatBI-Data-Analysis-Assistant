import os
import json
import math
from pathlib import Path
from statistics import mean
from datetime import date, datetime

import pandas as pd
try:
    from ..core.audit import get_audit_log_path, read_audit_events, read_jsonl_audit_events
except ImportError:
    from core.audit import get_audit_log_path, read_audit_events, read_jsonl_audit_events

try:
    from .config import EXPORT_DIR, MONTH_COLUMNS
    from .repositories.database import fetch_all, get_connection
    from .services.import_cleaning import (
        build_schema_profile,
        deduplicate_columns,
        get_import_job,
        get_import_job_file,
        infer_business_type_from_schema,
        json_ready,
        json_safe,
        list_import_jobs,
        load_import_job,
        migrate_file_metadata_to_postgres,
        normalize_table_name,
        process_import_file,
        save_import_job,
    )
except ImportError:
    from config import EXPORT_DIR, MONTH_COLUMNS
    from repositories.database import fetch_all, get_connection
    from services.import_cleaning import (
        build_schema_profile,
        deduplicate_columns,
        get_import_job,
        get_import_job_file,
        infer_business_type_from_schema,
        json_ready,
        json_safe,
        list_import_jobs,
        load_import_job,
        migrate_file_metadata_to_postgres,
        normalize_table_name,
        process_import_file,
        save_import_job,
    )
try:
    from .services.charts import (
        build_chart_blueprints,
        build_chart_plan_from_blueprints,
        build_interactive_chart_config,
        build_workspace_charts,
    )
except ImportError:
    from services.charts import (
        build_chart_blueprints,
        build_chart_plan_from_blueprints,
        build_interactive_chart_config,
        build_workspace_charts,
    )

try:
    from .services.exporters import (
        write_dashboard_csv_file as export_dashboard_csv_file,
        write_metrics_csv_file as export_metrics_csv_file,
        write_report_markdown_file as export_report_markdown_file,
        write_workspace_report_markdown_file as export_workspace_report_markdown_file,
    )
except ImportError:
    from services.exporters import (
        write_dashboard_csv_file as export_dashboard_csv_file,
        write_metrics_csv_file as export_metrics_csv_file,
        write_report_markdown_file as export_report_markdown_file,
        write_workspace_report_markdown_file as export_workspace_report_markdown_file,
    )
try:
    from .services.workspace_context import build_workspace_chat_context_from_report
except ImportError:
    from services.workspace_context import build_workspace_chat_context_from_report

try:
    from .services.knowledge_base import build_rag_catalog
except ImportError:
    from services.knowledge_base import build_rag_catalog

try:
    from .services.text2sql_eval import run_text2sql_eval
except ImportError:
    from services.text2sql_eval import run_text2sql_eval

try:
    from .services.reporting_persistence import sync_workspace_report_to_postgres
except ImportError:
    from services.reporting_persistence import sync_workspace_report_to_postgres

try:
    from .config import postgres_audit_enabled
    from .services.audit_persistence import init_audit_storage, persist_audit_event
except ImportError:
    from config import postgres_audit_enabled
    from services.audit_persistence import init_audit_storage, persist_audit_event

try:
    from .services.analysis_utils import (
        build_metric_catalog,
        build_monitor_items,
        build_sql_templates_for_workspace,
        categorical_columns,
        choose_dimension,
        choose_primary_metric,
        datetime_like_columns,
        numeric_columns,
        summarize_top_categories,
    )
    from .services.diagnostics import (
        build_anomaly_diagnosis,
        build_benchmark_summary,
        build_diagnostic_story,
        build_driver_analysis,
        build_methodology_sections,
        build_priority_actions,
        build_significance_tests,
        build_workspace_modules,
    )
    from .services.methodology import (
        build_analysis_plan,
        build_business_methodology,
        build_executive_summary,
        build_growth_suggestions,
        build_monetization_suggestions,
    )
    from .services.profiling import (
        build_data_profile,
        build_quality_score,
        build_recommended_paths,
    )
except ImportError:
    from services.analysis_utils import (
        build_metric_catalog,
        build_monitor_items,
        build_sql_templates_for_workspace,
        categorical_columns,
        choose_dimension,
        choose_primary_metric,
        datetime_like_columns,
        numeric_columns,
        summarize_top_categories,
    )
    from services.diagnostics import (
        build_anomaly_diagnosis,
        build_benchmark_summary,
        build_diagnostic_story,
        build_driver_analysis,
        build_methodology_sections,
        build_priority_actions,
        build_significance_tests,
        build_workspace_modules,
    )
    from services.methodology import (
        build_analysis_plan,
        build_business_methodology,
        build_executive_summary,
        build_growth_suggestions,
        build_monetization_suggestions,
    )
    from services.profiling import (
        build_data_profile,
        build_quality_score,
        build_recommended_paths,
    )



def infer_business_type(df_or_columns):
    columns = df_or_columns.columns if hasattr(df_or_columns, "columns") else df_or_columns
    columns_text = " ".join(str(column).lower() for column in columns)
    score_map = {
        "销售经营": ["成交", "销售", "销售额", "订单", "客单价", "客户", "区域", "省份", "产品"],
        "用户运营": ["用户", "活跃", "留存", "注册", "访问", "登录", "复购", "生命周期"],
        "财务经营": ["成本", "利润", "收入", "费用", "预算", "毛利", "净利", "应收", "应付"],
        "库存管理": ["库存", "入库", "出库", "仓", "sku", "库龄", "补货", "周转"],
        "运营分析": ["活动", "渠道", "转化", "投放", "运营", "留资", "线索", "曝光", "点击"],
    }
    scores = {business: sum(1 for keyword in keywords if keyword.lower() in columns_text) for business, keywords in score_map.items()}
    best_type, best_score = max(scores.items(), key=lambda item: item[1])
    return best_type if best_score > 0 else "通用业务"


def build_audit_log_data(limit=200, event_type=None, workspace_id=None, allowed=None, source=None):
    events = read_audit_events(
        limit=limit,
        event_type=event_type,
        workspace_id=workspace_id,
        allowed=allowed,
        source=source,
    )
    allowed_count = sum(1 for event in events if event.get("allowed") is True)
    blocked_count = sum(1 for event in events if event.get("allowed") is False)
    workspace_events = [event for event in events if event.get("workspaceId")]
    return {
        "enabled": os.getenv("CHATBI_AUDIT_ENABLED", "true").strip().lower() not in {"0", "false", "no", "off"},
        "store": "postgres" if postgres_audit_enabled() else "jsonl",
        "total": len(events),
        "allowedCount": allowed_count,
        "blockedCount": blocked_count,
        "workspaceEventCount": len(workspace_events),
        "filters": {
            "eventType": event_type,
            "workspaceId": workspace_id,
            "allowed": allowed,
            "source": source,
        },
        "events": events,
    }


def init_audit_log_storage():
    return init_audit_storage()


def migrate_audit_logs_to_postgres(limit=None):
    migrated = []
    failed = []
    events = read_jsonl_audit_events(limit=limit or 1000)
    for event in reversed(events):
        result = persist_audit_event(event)
        if result.get("synced"):
            migrated.append({"queryHash": event.get("queryHash"), **result})
        else:
            failed.append({"queryHash": event.get("queryHash"), "error": result.get("error") or "未启用 PostgreSQL 审计"})
    return {
        "source": str(get_audit_log_path()),
        "migrated": len(migrated),
        "failed": len(failed),
        "items": migrated[:20],
        "failedItems": failed[:20],
    }


def build_schema_profile_from_metadata(metadata, df=None):
    if metadata.get("schemaProfile"):
        return metadata["schemaProfile"]
    if df is not None:
        return build_schema_profile(df, metadata["originalFilename"])
    return {
        "fileName": metadata["originalFilename"],
        "rowCount": metadata.get("rowsAfter", 0),
        "columnCount": metadata.get("columnsAfter", 0),
        "columns": [column["name"] for column in metadata.get("columns", [])],
        "fields": metadata.get("columns", []),
        "roleCounts": {},
    }


def build_workspace_report(job_id):
    metadata, cleaned_file = get_import_job_file(job_id)
    df = pd.read_csv(cleaned_file, encoding="utf-8-sig")
    schema_profile = build_schema_profile_from_metadata(metadata, df)
    rows = len(df)
    columns = list(df.columns)
    numeric = numeric_columns(df)
    categorical = categorical_columns(df)
    date_columns = datetime_like_columns(df)

    numeric_profile = []
    for column in numeric:
        series = pd.to_numeric(df[column], errors="coerce")
        numeric_profile.append(
            {
                "column": column,
                "sum": round(float(series.sum()), 4),
                "mean": round(float(series.mean()), 4) if series.notna().any() else 0,
                "max": round(float(series.max()), 4) if series.notna().any() else 0,
                "min": round(float(series.min()), 4) if series.notna().any() else 0,
            }
        )

    primary_metric = choose_primary_metric(numeric_profile)
    primary_dimension = choose_dimension(categorical, ["产品", "区域", "省份", "业务组", "小组", "客户", "用户"])
    business_type = metadata.get("businessType") or infer_business_type_from_schema(schema_profile)
    top_categories = summarize_top_categories(df, primary_dimension, primary_metric) if primary_dimension else []
    analysis_plan = build_analysis_plan(business_type, schema_profile, numeric, categorical, date_columns, primary_metric, primary_dimension)
    charts = build_workspace_charts(df, primary_metric, primary_dimension, date_columns, numeric, analysis_plan.get("chartBlueprints"))
    data_profile = build_data_profile(df, schema_profile, numeric, categorical, date_columns, metadata)
    quality_score = build_quality_score(data_profile, metadata, primary_metric, primary_dimension, date_columns)
    recommended_paths = build_recommended_paths(business_type, analysis_plan["framework"], data_profile, quality_score, primary_metric, primary_dimension, date_columns)
    interactiveCharts = build_interactive_chart_config(df, numeric, categorical, date_columns)

    trend = []
    if date_columns and primary_metric:
        date_column = date_columns[0]
        tmp = df[[date_column, primary_metric]].copy()
        tmp[date_column] = pd.to_datetime(tmp[date_column], errors="coerce")
        tmp[primary_metric] = pd.to_numeric(tmp[primary_metric], errors="coerce")
        tmp = tmp.dropna(subset=[date_column])
        if not tmp.empty:
            grouped = tmp.groupby(tmp[date_column].dt.to_period("M"))[primary_metric].sum().sort_index()
            trend = [{"period": str(index), "value": round(float(value), 4)} for index, value in grouped.items()]

    insights = []
    if primary_metric:
        total_value = next((item["sum"] for item in numeric_profile if item["column"] == primary_metric), 0)
        insights.append(f"核心指标 `{primary_metric}` 合计为 {total_value}，可作为该业务空间的主分析口径。")
    if primary_dimension and top_categories:
        leader = top_categories[0]
        insights.append(f"`{primary_dimension}` 中贡献最高的是 `{leader['name']}`，对应值为 {leader['value']}。")
    if trend:
        best_period = max(trend, key=lambda item: item["value"])
        insights.append(f"按 `{date_columns[0]}` 汇总后，峰值周期为 {best_period['period']}，值为 {best_period['value']}。")
    if not insights:
        insights.append("当前数据更适合先做字段理解、分布观察和业务口径确认，再沉淀专项分析模板。")

    monitor_items = build_monitor_items(trend, primary_metric)
    high_monitor_items = [item for item in monitor_items if item["severity"] in ["high", "medium"]]
    metric_catalog = build_metric_catalog(numeric_profile, primary_metric)
    sql_templates = build_sql_templates_for_workspace(metadata.get("dbTable"), primary_metric, primary_dimension, date_columns[0] if date_columns else None)
    growth_suggestions = build_growth_suggestions(columns, categorical)
    monetization_suggestions = build_monetization_suggestions(primary_metric, numeric_profile)
    benchmark_summary = build_benchmark_summary(top_categories, trend, primary_metric, primary_dimension)
    driver_analysis = build_driver_analysis(df, primary_metric, categorical, date_columns)
    anomaly_diagnosis = build_anomaly_diagnosis(monitor_items, primary_metric, primary_dimension, top_categories)
    significance_tests = build_significance_tests(df, primary_metric, categorical, numeric)
    priority_actions = build_priority_actions(business_type, primary_metric, primary_dimension, benchmark_summary, driver_analysis, anomaly_diagnosis, columns)
    executive_summary = build_executive_summary(business_type, primary_metric, primary_dimension, top_categories, trend, numeric_profile, analysis_plan)
    diagnostic_story = build_diagnostic_story(insights, benchmark_summary, anomaly_diagnosis, driver_analysis, priority_actions, primary_metric)
    workspace_modules = build_workspace_modules(business_type, data_profile, primary_metric, primary_dimension, date_columns)
    methodology_sections = build_methodology_sections(
        analysis_plan.get("methodology", []),
        benchmark_summary,
        driver_analysis,
        anomaly_diagnosis,
        significance_tests,
        priority_actions,
    )

    sections = [
        {
            "title": "业务空间概览",
            "content": f"该空间来自 `{metadata['originalFilename']}`，识别为 `{metadata.get('businessType') or infer_business_type(df)}`，清洗后包含 {rows} 行、{len(columns)} 个字段。数据质量评分 {quality_score['score']} 分（{quality_score['grade']}），{quality_score['summary']}",
        },
        {
            "title": "数据画像",
            "content": f"{data_profile['profileSummary']} 高缺失字段 {len(data_profile['highMissingFields'])} 个，高基数维度 {len(data_profile['highCardinalityDimensions'])} 个。主要字段包括：{', '.join(columns[:10])}。",
        },
        {
            "title": "AI 分析方案预判",
            "content": f"系统选择 `{analysis_plan['framework']['title']}`，置信度 `{analysis_plan['confidence']}`。{analysis_plan['focus']} 推荐路径：{' → '.join(item['name'] for item in recommended_paths[:6])}。{analysis_plan['inputSummary']}",
        },
        {
            "title": "问题诊断链路",
            "content": " ".join(f"{item['stage']}：{item['content']}" for item in diagnostic_story),
        },
        *methodology_sections,
        {
            "title": "指标体系",
            "content": f"建议将 `{primary_metric or '主指标'}` 设为一级经营指标，并用 {', '.join(item['name'] for item in metric_catalog[:4])} 作为辅助指标。"
        },
        {
            "title": "业务监控与异常",
            "content": f"基于时间趋势共识别 {len(high_monitor_items)} 个重点波动周期；建议对主指标配置月度环比和偏离均值监控。"
            if trend
            else "当前未识别稳定时间字段，建议补充日期/月份字段后开启趋势监控。"
        },
        {
            "title": "增长分析",
            "content": " ".join(item["content"] for item in growth_suggestions),
        },
        {
            "title": "变现与成本",
            "content": " ".join(item["content"] for item in monetization_suggestions) if monetization_suggestions else "当前未识别收入/金额类字段，建议补充金额、成本或费用字段后做变现分析。",
        },
        {
            "title": "SQL 分析模板",
            "content": f"已生成 {len(sql_templates)} 个该业务空间专属 SQL 模板，可用于总量、排行和趋势查询。",
        },
        {
            "title": "数据清洗质量",
            "content": f"导入时删除重复行 {metadata.get('removedDuplicateRows', 0)} 行，空行 {metadata.get('removedEmptyRows', 0)} 行；缺失值处理 {len(metadata.get('fillActions', []))} 个字段，类型转换 {len(metadata.get('typeChanges', []))} 个字段。",
        },
        {
            "title": "后续建议",
            "content": "建议先确认主指标、时间字段和核心维度，再在该业务空间内配置专属看板、异常监控和分析模板，避免与默认样例业务混用。",
        },
    ]

    report = json_ready(
        {
            "jobId": job_id,
            "workspaceName": metadata.get("workspaceName") or Path(metadata["originalFilename"]).stem,
            "businessType": business_type,
            "sourceFile": metadata["originalFilename"],
            "createdAt": metadata["createdAt"],
            "imported": metadata.get("imported", False),
            "dbTable": metadata.get("dbTable"),
            "workspaceModules": workspace_modules,
            "summaryCards": [
                {"label": "数据行数", "value": rows, "unit": "行", "note": "清洗后的可分析记录"},
                {"label": "字段数量", "value": len(columns), "unit": "个", "note": "自动标准化后的字段"},
                {"label": "数值字段", "value": len(numeric), "unit": "个", "note": "可用于聚合指标"},
                {"label": "维度字段", "value": len(categorical), "unit": "个", "note": "可用于分组分析"},
            ],
            "numericProfile": numeric_profile[:8],
            "schemaProfile": schema_profile,
            "executiveSummary": executive_summary,
            "analysisPlan": analysis_plan,
            "charts": charts,
            "interactiveCharts": interactiveCharts,
            "dataProfile": data_profile,
            "qualityScore": quality_score,
            "recommendedPaths": recommended_paths,
            "diagnosticStory": diagnostic_story,
            "methodology": analysis_plan.get("methodology", []),
            "benchmarkSummary": benchmark_summary,
            "driverAnalysis": driver_analysis,
            "anomalyDiagnosis": anomaly_diagnosis,
            "significanceTests": significance_tests,
            "priorityActions": priority_actions,
            "metricCatalog": metric_catalog,
            "topCategories": top_categories,
            "trend": trend[-12:],
            "monitorItems": monitor_items,
            "growthSuggestions": growth_suggestions,
            "monetizationSuggestions": monetization_suggestions,
            "sqlTemplates": sql_templates,
            "cleaningQuality": {
                "removedDuplicateRows": metadata.get("removedDuplicateRows", 0),
                "removedEmptyRows": metadata.get("removedEmptyRows", 0),
                "removedEmptyColumns": metadata.get("removedEmptyColumns", 0),
                "fillActions": metadata.get("fillActions", []),
                "typeChanges": metadata.get("typeChanges", []),
            },
            "sections": sections,
        }
    )
    sync_result = sync_workspace_report_to_postgres(report)
    if sync_result.get("enabled"):
        report["postgresMetadata"] = sync_result
    return report


def build_workspace_chat_context(job_id):
    report = build_workspace_report(job_id)
    return build_workspace_chat_context_from_report(report)


def list_business_workspaces(limit=200):
    workspaces = []
    for job in list_import_jobs(limit)["jobs"]:
        schema_profile = job.get("schemaProfile") or {}
        role_counts = schema_profile.get("roleCounts", {})
        business_type = job.get("businessType", "通用业务")
        preview_modules = build_workspace_modules(
            business_type,
            None,
            "主指标" if role_counts.get("metric", 0) else None,
            "核心维度" if role_counts.get("dimension", 0) else None,
            ["时间"] if role_counts.get("time", 0) else [],
        )
        workspaces.append(
            {
                "workspaceId": job["jobId"],
                "name": job.get("workspaceName") or Path(job["originalFilename"]).stem,
                "businessType": business_type,
                "sourceFile": job["originalFilename"],
                "createdAt": job["createdAt"],
                "rows": job.get("rowsAfter", 0),
                "columns": job.get("columnsAfter", 0),
                "imported": job.get("imported", False),
                "dbTable": job.get("dbTable"),
                "roleCounts": role_counts,
                "moduleCount": len(preview_modules),
                "modules": preview_modules,
            }
        )
    groups = []
    for business_type in ["销售经营", "用户运营", "财务经营", "库存管理", "运营分析", "通用业务"]:
        items = [workspace for workspace in workspaces if workspace["businessType"] == business_type]
        if items:
            groups.append({"businessType": business_type, "count": len(items), "workspaces": items})
    return {"workspaces": workspaces, "groups": groups}


def postgres_type_for_series(series):
    if pd.api.types.is_integer_dtype(series):
        return "BIGINT"
    if pd.api.types.is_float_dtype(series):
        return "DOUBLE PRECISION"
    if pd.api.types.is_bool_dtype(series):
        return "BOOLEAN"
    if pd.api.types.is_datetime64_any_dtype(series):
        return "TIMESTAMP"
    return "TEXT"


def table_exists(cursor, table_name):
    cursor.execute(
        """
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = %s
        )
        """,
        (table_name,),
    )
    return cursor.fetchone()[0]


def unique_table_name(cursor, preferred_name):
    table_name = preferred_name
    suffix = 1
    while table_exists(cursor, table_name):
        suffix += 1
        table_name = f"{preferred_name[:50]}_{suffix}"
    return table_name


def commit_import_job(job_id, table_name=None):
    try:
        from psycopg2 import sql
        from psycopg2.extras import execute_values
    except ImportError as exc:
        raise RuntimeError("缺少 psycopg2，无法将清洗数据写入 PostgreSQL。请先安装 requirements.txt。") from exc

    metadata, cleaned_file = get_import_job_file(job_id)
    df = pd.read_csv(cleaned_file, encoding="utf-8-sig")
    if df.empty:
        raise ValueError("清洗后的文件没有可入库的数据。")

    preferred_table_name = normalize_table_name(table_name or metadata.get("suggestedTableName"), metadata.get("originalFilename"))
    columns = deduplicate_columns(df.columns)
    df.columns = columns

    with get_connection() as conn:
        with conn.cursor() as cursor:
            target_table_name = unique_table_name(cursor, preferred_table_name)
            column_definitions = [
                sql.SQL("{} {}").format(sql.Identifier(column), sql.SQL(postgres_type_for_series(df[column])))
                for column in columns
            ]
            create_statement = sql.SQL("CREATE TABLE {} ({})").format(
                sql.Identifier(target_table_name),
                sql.SQL(", ").join(column_definitions),
            )
            cursor.execute(create_statement)
            insert_statement = sql.SQL("INSERT INTO {} ({}) VALUES %s").format(
                sql.Identifier(target_table_name),
                sql.SQL(", ").join(sql.Identifier(column) for column in columns),
            )
            values = [
                tuple(None if pd.isna(value) else json_safe(value) for value in row)
                for row in df.itertuples(index=False, name=None)
            ]
            execute_values(cursor, insert_statement.as_string(cursor), values)
        conn.commit()

    metadata["imported"] = True
    metadata["dbTable"] = target_table_name
    metadata["importedAt"] = datetime.now().isoformat(timespec="seconds")
    save_import_job(metadata)
    return {
        "jobId": job_id,
        "imported": True,
        "dbTable": target_table_name,
        "rows": len(df),
        "columns": columns,
    }


def commit_import_jobs(job_ids):
    results = []
    for job_id in job_ids:
        try:
            metadata = load_import_job(job_id)
            if metadata.get("imported"):
                results.append(
                    {
                        "jobId": job_id,
                        "ok": True,
                        "skipped": True,
                        "dbTable": metadata.get("dbTable"),
                        "message": "已入库，跳过重复入库。",
                    }
                )
                continue
            committed = commit_import_job(job_id)
            results.append({"ok": True, "skipped": False, **committed})
        except Exception as exc:
            results.append({"jobId": job_id, "ok": False, "message": str(exc)})
    return {
        "total": len(job_ids),
        "success": sum(1 for item in results if item.get("ok")),
        "failed": sum(1 for item in results if not item.get("ok")),
        "results": results,
    }


def init_metadata_storage():
    try:
        from .repositories.workspace_metadata import init_metadata_schema
    except ImportError:
        from repositories.workspace_metadata import init_metadata_schema
    return init_metadata_schema()


def migrate_metadata_storage(limit=None):
    return migrate_file_metadata_to_postgres(limit)


def write_workspace_report_markdown_file(job_id):
    return export_workspace_report_markdown_file(job_id, build_workspace_report)


def write_report_markdown_file():
    return export_report_markdown_file(build_report_data)


def write_metrics_csv_file():
    return export_metrics_csv_file(build_metric_definitions)


def write_dashboard_csv_file():
    return export_dashboard_csv_file(build_dashboard_data)


def safe_number(value):
    if value is None:
        return 0
    return float(value)


def load_sales_rows():
    columns = ", ".join([f'"{column}"' for column in ["product_name", *MONTH_COLUMNS]])
    return fetch_all(f'SELECT {columns} FROM "销量表"')


def build_dashboard_data():
    products = fetch_all('SELECT product_name, product_price FROM "商品表"')
    sales_rows = load_sales_rows()
    users = fetch_all('SELECT userid, username, occupation FROM "用户表"')
    active_rows = fetch_all('SELECT "用户id", "活跃时长_分钟" FROM "用户活跃表"')

    monthly_totals = []
    for month, column in enumerate(MONTH_COLUMNS, start=1):
        monthly_totals.append(
            {
                "month": f"{month}月",
                "sales": int(sum(safe_number(row.get(column)) for row in sales_rows)),
            }
        )

    product_sales = []
    for row in sales_rows:
        product_sales.append(
            {
                "product": row["product_name"],
                "totalSales": int(sum(safe_number(row.get(column)) for column in MONTH_COLUMNS)),
            }
        )
    product_sales.sort(key=lambda item: item["totalSales"], reverse=True)

    prices = [safe_number(item["product_price"]) for item in products]
    active_minutes = [safe_number(item["活跃时长_分钟"]) for item in active_rows]
    total_sales = sum(item["sales"] for item in monthly_totals)
    previous_month = monthly_totals[-2]["sales"] if len(monthly_totals) >= 2 else 0
    current_month = monthly_totals[-1]["sales"] if monthly_totals else 0
    month_over_month = (
        round((current_month - previous_month) / previous_month * 100, 2)
        if previous_month
        else 0
    )

    return {
        "summaryCards": [
            {
                "label": "商品数量",
                "value": len(products),
                "unit": "个",
                "note": "商品表覆盖的可分析 SKU",
            },
            {
                "label": "年度销量",
                "value": int(total_sales),
                "unit": "件",
                "note": f"12月环比 {month_over_month}%",
            },
            {
                "label": "平均价格",
                "value": round(mean(prices), 2) if prices else 0,
                "unit": "元",
                "note": "商品价格均值",
            },
            {
                "label": "平均活跃时长",
                "value": round(mean(active_minutes), 2) if active_minutes else 0,
                "unit": "分钟",
                "note": f"覆盖 {len(users)} 位用户",
            },
        ],
        "monthlySales": monthly_totals,
        "topProducts": product_sales[:10],
    }


def build_metric_definitions():
    return [
        {
            "name": "年度销量",
            "owner": "业务分析",
            "formula": "SUM(1月销量 ... 12月销量)",
            "source": "销量表",
            "scene": "整体经营规模、商品销售表现",
        },
        {
            "name": "月度销量",
            "owner": "运营分析",
            "formula": "SUM(月份销量字段)",
            "source": "销量表",
            "scene": "趋势分析、旺季识别、补货决策",
        },
        {
            "name": "商品均价",
            "owner": "商品分析",
            "formula": "AVG(product_price)",
            "source": "商品表",
            "scene": "价格带分析、品类定价对比",
        },
        {
            "name": "用户活跃时长",
            "owner": "用户分析",
            "formula": "AVG(活跃时长_分钟)",
            "source": "用户活跃表",
            "scene": "用户参与度、功能粘性评估",
        },
        {
            "name": "Top 商品销量",
            "owner": "经营分析",
            "formula": "按商品聚合 12 个月销量后排序",
            "source": "销量表",
            "scene": "爆品识别、重点商品跟踪",
        },
    ]


def build_sql_analysis_data():
    return {
        "capabilities": [
            {
                "title": "自然语言查数",
                "description": "将业务问题转换为 PostgreSQL 查询，覆盖商品、销量、用户和活跃数据。",
                "example": "查询奇多的价格是多少",
            },
            {
                "title": "聚合统计",
                "description": "支持总量、均值、TopN、月度趋势等常用分析口径。",
                "example": "查询销量最高的10个商品",
            },
            {
                "title": "对比分析",
                "description": "支持商品、品类、月份之间的销量与价格对比。",
                "example": "抽纸近12个月总销量和洗手液哪个更高",
            },
            {
                "title": "同比环比模板",
                "description": "围绕月度销量字段计算环比变化，用于监控业务波动。",
                "example": "分析12月销量相比11月的变化",
            },
        ],
        "sqlTemplates": [
            {
                "name": "商品价格查询",
                "sql": 'SELECT product_name, product_price FROM "商品表" WHERE product_name LIKE \'%奇多%\';',
            },
            {
                "name": "商品年度销量排行",
                "sql": 'SELECT product_name, ("1月销量"+"2月销量"+...+"12月销量") AS total_sales FROM "销量表" ORDER BY total_sales DESC LIMIT 10;',
            },
            {
                "name": "月度总销量趋势",
                "sql": 'SELECT SUM("1月销量") AS jan_sales, SUM("2月销量") AS feb_sales, ... FROM "销量表";',
            },
        ],
    }


def build_import_clean_data():
    return {
        "status": "planned",
        "workflow": [
            "上传 Excel / CSV 文件或选择数据库表",
            "自动识别字段名、数据类型和空值比例",
            "清理重复行、空白字符、异常类型和缺失值",
            "生成清洗预览与字段映射",
            "确认后导入数据库并进入分析流程",
            "按需导出清洗后数据或分析结果",
        ],
        "cleaningRules": [
            {"rule": "去重", "description": "基于整行或业务主键删除重复记录"},
            {"rule": "缺失值处理", "description": "数值字段用均值/0填充，文本字段标记为未知"},
            {"rule": "类型校正", "description": "自动识别日期、数值、文本字段并转换"},
            {"rule": "字段标准化", "description": "统一字段命名、去除前后空格和特殊字符"},
        ],
        "exportOptions": [
            {
                "label": "导出指标口径",
                "description": "下载指标名称、公式、来源和应用场景 CSV",
                "url": "/api/bi/export/metrics",
            },
            {
                "label": "导出分析报告",
                "description": "下载结构化业务分析报告 Markdown",
                "url": "/api/bi/export/report",
            },
            {
                "label": "导出看板数据",
                "description": "下载指标卡、月度趋势和 Top 商品 CSV",
                "url": "/api/bi/export/dashboard",
            },
        ],
    }


def build_user_growth_data():
    active_rows = fetch_all('SELECT "用户id", "活跃时长_分钟" FROM "用户活跃表"')
    users = fetch_all('SELECT userid, username, occupation FROM "用户表"')
    active_minutes = [safe_number(row["活跃时长_分钟"]) for row in active_rows]
    high_active_count = sum(1 for value in active_minutes if value >= 30)
    active_user_ids = {row["用户id"] for row in active_rows}

    return {
        "summary": [
            {"label": "用户数", "value": len(users), "unit": "人"},
            {"label": "活跃用户", "value": len(active_user_ids), "unit": "人"},
            {"label": "高活跃用户", "value": high_active_count, "unit": "人"},
            {
                "label": "平均活跃时长",
                "value": round(mean(active_minutes), 2) if active_minutes else 0,
                "unit": "分钟",
            },
        ],
        "segments": [
            {"name": "高活跃", "condition": "活跃时长 ≥ 30 分钟", "action": "重点运营与复购转化"},
            {"name": "中活跃", "condition": "10-30 分钟", "action": "推送核心功能与优惠活动"},
            {"name": "低活跃", "condition": "< 10 分钟", "action": "召回与新手引导"},
        ],
    }


def build_monetization_data():
    dashboard = build_dashboard_data()
    products = fetch_all('SELECT product_name, product_price FROM "商品表"')
    price_map = {row["product_name"]: safe_number(row["product_price"]) for row in products}
    sales_rows = load_sales_rows()
    revenue_rows = []
    for row in sales_rows:
        total_sales = sum(safe_number(row.get(column)) for column in MONTH_COLUMNS)
        revenue_rows.append(
            {
                "product": row["product_name"],
                "totalSales": int(total_sales),
                "estimatedRevenue": round(total_sales * price_map.get(row["product_name"], 0), 2),
            }
        )
    revenue_rows.sort(key=lambda item: item["estimatedRevenue"], reverse=True)
    total_revenue = sum(item["estimatedRevenue"] for item in revenue_rows)

    return {
        "summary": [
            {"label": "估算收入", "value": round(total_revenue, 2), "unit": "元"},
            {"label": "销量规模", "value": dashboard["summaryCards"][1]["value"], "unit": "件"},
            {"label": "收入 Top 商品", "value": revenue_rows[0]["product"] if revenue_rows else "-", "unit": ""},
        ],
        "topRevenueProducts": revenue_rows[:8],
        "costNote": "当前样例库暂无成本字段，成本分析模块已预留 ROI、毛利率、补贴效率等指标口径。",
    }


def build_rag_data():
    catalog = build_rag_catalog()
    return {
        "enabled": True,
        "positioning": "企业知识库增强模块已接入本地指标口径字典，当前采用轻量关键词检索，为 Agent 提供业务语义参考。",
        "mode": catalog["mode"],
        "catalogCount": catalog["count"],
        "catalog": catalog["items"],
        "scenarios": [
            "指标口径问答：解释 GMV、留存、活跃等企业内部定义",
            "数据字典检索：查询字段含义、来源表和使用限制",
            "历史报告召回：复用过往分析结论辅助当前判断",
            "权限隔离：按部门、项目、角色控制可检索文档",
        ],
        "suggestedStack": [
            "文档解析：Markdown / PDF / Word / Excel",
            "向量化：Embedding 模型",
            "向量库：FAISS / Milvus / pgvector",
            "检索策略：TopK + rerank + 引用来源",
            "接入方式：作为可选工具，不默认影响 SQL 分析",
        ],
    }


def build_ai_eval_data():
    return run_text2sql_eval()


def build_anomaly_data():
    monthly_sales = build_dashboard_data()["monthlySales"]
    values = [item["sales"] for item in monthly_sales]
    if not values:
        return {"items": [], "baseline": 0}

    baseline = mean(values)
    items = []
    for index, item in enumerate(monthly_sales):
        previous_value = values[index - 1] if index > 0 else None
        mom = (
            round((item["sales"] - previous_value) / previous_value * 100, 2)
            if previous_value
            else 0
        )
        deviation = round((item["sales"] - baseline) / baseline * 100, 2) if baseline else 0
        severity = "normal"
        if abs(deviation) >= 25 or abs(mom) >= 35:
            severity = "high"
        elif abs(deviation) >= 15 or abs(mom) >= 20:
            severity = "medium"
        items.append(
            {
                "month": item["month"],
                "sales": item["sales"],
                "mom": mom,
                "deviation": deviation,
                "severity": severity,
                "insight": build_anomaly_insight(mom, deviation),
            }
        )
    return {"baseline": round(baseline, 2), "items": items}


def build_anomaly_insight(mom, deviation):
    if mom >= 35:
        return "环比大幅增长，建议排查促销、季节或爆品贡献。"
    if mom <= -35:
        return "环比大幅下降，建议检查供给、活动结束或需求回落。"
    if deviation >= 25:
        return "明显高于均值，适合沉淀为旺季或活动样本。"
    if deviation <= -25:
        return "明显低于均值，需要关注商品动销和用户需求。"
    return "波动处于可接受区间，持续观察即可。"


def build_report_data():
    dashboard = build_dashboard_data()
    anomaly = build_anomaly_data()
    top_products = dashboard["topProducts"][:3]
    high_anomalies = [item for item in anomaly["items"] if item["severity"] == "high"]
    best_month = max(dashboard["monthlySales"], key=lambda item: item["sales"], default=None)
    worst_month = min(dashboard["monthlySales"], key=lambda item: item["sales"], default=None)

    report = [
        {
            "title": "现象",
            "content": (
                f"全年销量合计 {dashboard['summaryCards'][1]['value']} 件，"
                f"最高月份为 {best_month['month']}（{best_month['sales']} 件），"
                f"最低月份为 {worst_month['month']}（{worst_month['sales']} 件）。"
                if best_month and worst_month
                else "暂无足够销量数据。"
            ),
        },
        {
            "title": "原因拆解",
            "content": (
                f"Top 商品集中在 {', '.join(item['product'] for item in top_products)}，"
                "说明头部商品对销量贡献明显；月度波动可结合活动、季节和库存继续验证。"
                if top_products
                else "暂无商品销量排行数据。"
            ),
        },
        {
            "title": "异常关注",
            "content": (
                f"发现 {len(high_anomalies)} 个高等级异常月份："
                + "、".join(item["month"] for item in high_anomalies[:5])
                if high_anomalies
                else "当前未发现高等级异常月份，建议维持常规监控。"
            ),
        },
        {
            "title": "建议",
            "content": "优先跟踪 Top 商品库存和活动节奏；对环比大幅波动月份补充活动、价格、渠道等维度做归因。",
        },
    ]

    return {"sections": report}
