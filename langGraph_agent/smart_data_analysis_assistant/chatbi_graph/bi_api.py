import os
import json
import math
import re
import uuid
from pathlib import Path
from statistics import mean
from datetime import date, datetime

import pandas as pd
import psycopg2
from psycopg2 import sql
from psycopg2.extras import execute_values
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env")


MONTH_COLUMNS = [f"{month}月销量" for month in range(1, 13)]
IMPORT_JOBS_DIR = BASE_DIR / "import_jobs"
CLEANED_DATA_DIR = IMPORT_JOBS_DIR / "cleaned"
METADATA_DIR = IMPORT_JOBS_DIR / "metadata"
EXPORT_DIR = BASE_DIR / "exports"

for directory in [CLEANED_DATA_DIR, METADATA_DIR, EXPORT_DIR]:
    directory.mkdir(parents=True, exist_ok=True)


def get_connection():
    return psycopg2.connect(
        host=os.getenv("db_host", "127.0.0.1"),
        port=os.getenv("db_port", "5432"),
        user=os.getenv("user", "postgres"),
        password=os.getenv("password", "123456"),
        dbname=os.getenv("dbname", "sales_chat"),
    )


def fetch_all(sql, params=None):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql, params or ())
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]


def normalize_identifier(value, fallback):
    text = str(value or "").strip().replace("\ufeff", "")
    text = re.sub(r"\s+", "_", text)
    text = re.sub(r"[^\w\u4e00-\u9fff]+", "_", text, flags=re.UNICODE).strip("_")
    if not text or text.lower().startswith("unnamed"):
        text = fallback
    if text[0].isdigit():
        text = f"field_{text}"
    return text[:60]


def deduplicate_columns(columns):
    seen = {}
    result = []
    for index, column in enumerate(columns):
        base_name = normalize_identifier(column, f"column_{index + 1}")
        count = seen.get(base_name, 0)
        seen[base_name] = count + 1
        result.append(base_name if count == 0 else f"{base_name}_{count + 1}")
    return result


def normalize_table_name(table_name, original_filename=None):
    fallback = Path(original_filename or "uploaded_data").stem
    normalized = normalize_identifier(table_name or fallback, "uploaded_data")
    if not normalized.startswith("import_"):
        normalized = f"import_{normalized}"
    return normalized[:58]


def read_dataset(file_path):
    file_path = Path(file_path)
    suffix = file_path.suffix.lower()
    if suffix == ".csv":
        try:
            return pd.read_csv(file_path, encoding="utf-8-sig")
        except UnicodeDecodeError:
            return pd.read_csv(file_path, encoding="gbk")
    if suffix in [".xlsx", ".xls"]:
        return pd.read_excel(file_path)
    raise ValueError("仅支持 CSV、XLSX、XLS 文件。")


def json_safe(value):
    if value is None:
        return None
    if isinstance(value, pd.Timestamp):
        return None if pd.isna(value) else value.isoformat()
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return json_safe(value.item())
    return value


def json_ready(value):
    if isinstance(value, dict):
        return {key: json_ready(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_ready(item) for item in value]
    if isinstance(value, tuple):
        return [json_ready(item) for item in value]
    return json_safe(value)


def dataframe_preview(df, limit=20):
    preview = []
    for row in df.head(limit).to_dict(orient="records"):
        preview.append({key: json_safe(value) for key, value in row.items()})
    return preview


def classify_field_role(column_name, dtype):
    name = str(column_name).lower()
    if any(keyword in name for keyword in ["date", "time", "日期", "时间", "月份", "年份"]):
        return "time"
    if any(keyword in name for keyword in ["金额", "收入", "销售额", "成交", "利润", "成本", "费用", "客单价", "销量", "数量", "客户数"]):
        return "metric"
    if pd.api.types.is_numeric_dtype(dtype):
        return "metric"
    if any(keyword in name for keyword in ["id", "工号", "编号", "编码"]):
        return "identifier"
    return "dimension"


def build_schema_profile(df, original_filename):
    fields = []
    for column in df.columns:
        series = df[column]
        non_null = int(series.notna().sum())
        fields.append(
            {
                "name": column,
                "dtype": str(series.dtype),
                "role": classify_field_role(column, series.dtype),
                "nonNull": non_null,
                "missingRate": round(float(series.isna().mean()), 4) if len(series) else 0,
                "uniqueCount": int(series.nunique(dropna=True)),
            }
        )
    return {
        "fileName": original_filename,
        "rowCount": int(len(df)),
        "columnCount": int(len(df.columns)),
        "columns": [field["name"] for field in fields],
        "fields": fields,
        "roleCounts": {
            "metric": sum(1 for field in fields if field["role"] == "metric"),
            "dimension": sum(1 for field in fields if field["role"] == "dimension"),
            "time": sum(1 for field in fields if field["role"] == "time"),
            "identifier": sum(1 for field in fields if field["role"] == "identifier"),
        },
    }


def infer_business_type_from_schema(schema_profile):
    columns_text = " ".join([schema_profile.get("fileName", ""), *schema_profile.get("columns", [])]).lower()
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


def clean_dataframe(raw_df):
    original_rows = len(raw_df)
    original_columns = len(raw_df.columns)
    df = raw_df.copy()

    df = df.dropna(axis=0, how="all")
    empty_rows_removed = original_rows - len(df)
    df = df.dropna(axis=1, how="all")
    empty_columns_removed = original_columns - len(df.columns)
    df.columns = deduplicate_columns(df.columns)

    for column in df.select_dtypes(include=["object"]).columns:
        df[column] = df[column].map(lambda value: value.strip() if isinstance(value, str) else value)
        df[column] = df[column].replace("", pd.NA)

    before_deduplicate = len(df)
    df = df.drop_duplicates()
    duplicate_rows_removed = before_deduplicate - len(df)

    missing_before = df.isna().sum().to_dict()
    type_changes = []
    fill_actions = []

    for column in df.select_dtypes(include=["datetime", "datetimetz"]).columns:
        df[column] = df[column].dt.strftime("%Y-%m-%d %H:%M:%S")
        type_changes.append({"column": column, "targetType": "datetime"})

    for column in df.columns:
        series = df[column]
        if series.dtype == "object":
            non_null_count = series.notna().sum()
            if non_null_count == 0:
                continue
            if any(keyword in column.lower() for keyword in ["date", "time", "日期", "时间"]):
                converted = pd.to_datetime(series, errors="coerce")
                if converted.notna().sum() / non_null_count >= 0.7:
                    df[column] = converted.dt.strftime("%Y-%m-%d %H:%M:%S")
                    type_changes.append({"column": column, "targetType": "datetime"})
                    continue
            converted_number = pd.to_numeric(series, errors="coerce")
            if converted_number.notna().sum() / non_null_count >= 0.85:
                df[column] = converted_number
                type_changes.append({"column": column, "targetType": "number"})

    for column in df.columns:
        missing_count = int(df[column].isna().sum())
        if missing_count == 0:
            continue
        if pd.api.types.is_numeric_dtype(df[column]):
            df[column] = df[column].fillna(0)
            fill_actions.append({"column": column, "missing": missing_count, "strategy": "填充 0"})
        else:
            df[column] = df[column].fillna("未知")
            fill_actions.append({"column": column, "missing": missing_count, "strategy": "填充 未知"})

    columns = []
    for column in df.columns:
        columns.append(
            {
                "name": column,
                "dtype": str(df[column].dtype),
                "missingBefore": int(missing_before.get(column, 0)),
                "missingAfter": int(df[column].isna().sum()),
            }
        )

    report = {
        "rowsBefore": original_rows,
        "rowsAfter": len(df),
        "columnsBefore": original_columns,
        "columnsAfter": len(df.columns),
        "removedEmptyRows": empty_rows_removed,
        "removedEmptyColumns": empty_columns_removed,
        "removedDuplicateRows": duplicate_rows_removed,
        "typeChanges": type_changes,
        "fillActions": fill_actions,
        "columns": columns,
    }
    return df, report


def process_import_file(file_path, original_filename):
    raw_df = read_dataset(file_path)
    cleaned_df, report = clean_dataframe(raw_df)
    job_id = uuid.uuid4().hex
    suggested_table_name = normalize_table_name(None, original_filename)
    workspace_name = Path(original_filename).stem or "上传数据业务"
    cleaned_file = CLEANED_DATA_DIR / f"{job_id}.csv"
    metadata_file = METADATA_DIR / f"{job_id}.json"
    schema_profile = build_schema_profile(cleaned_df, original_filename)
    business_type = infer_business_type_from_schema(schema_profile)

    cleaned_df.to_csv(cleaned_file, index=False, encoding="utf-8-sig")
    metadata = {
        "jobId": job_id,
        "originalFilename": original_filename,
        "workspaceName": workspace_name,
        "businessType": business_type,
        "schemaProfile": schema_profile,
        "suggestedTableName": suggested_table_name,
        "cleanedFile": str(cleaned_file),
        "createdAt": datetime.now().isoformat(timespec="seconds"),
        "imported": False,
        "dbTable": None,
        "preview": dataframe_preview(cleaned_df),
        **report,
    }
    metadata = json_ready(metadata)
    metadata_file.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    return public_import_job(metadata)


def public_import_job(metadata):
    result = dict(metadata)
    result.pop("cleanedFile", None)
    result["workspaceName"] = result.get("workspaceName") or Path(result["originalFilename"]).stem
    schema_profile = result.get("schemaProfile") or {
        "fileName": result["originalFilename"],
        "columns": [column["name"] for column in result.get("columns", [])],
        "fields": result.get("columns", []),
        "rowCount": result.get("rowsAfter", 0),
        "columnCount": result.get("columnsAfter", 0),
    }
    result["schemaProfile"] = schema_profile
    result["businessType"] = result.get("businessType") or infer_business_type_from_schema(schema_profile)
    result["downloadUrl"] = f"/api/bi/import-clean/jobs/{metadata['jobId']}/download"
    return result


def load_import_job(job_id):
    metadata_file = METADATA_DIR / f"{job_id}.json"
    if not metadata_file.exists():
        raise FileNotFoundError("导入任务不存在。")
    return json.loads(metadata_file.read_text(encoding="utf-8"))


def save_import_job(metadata):
    metadata_file = METADATA_DIR / f"{metadata['jobId']}.json"
    metadata = json_ready(metadata)
    metadata_file.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")


def get_import_job(job_id):
    return public_import_job(load_import_job(job_id))


def get_import_job_file(job_id):
    metadata = load_import_job(job_id)
    cleaned_file = Path(metadata["cleanedFile"])
    if not cleaned_file.exists():
        raise FileNotFoundError("清洗后的文件不存在。")
    return metadata, cleaned_file


def list_import_jobs(limit=20):
    jobs = []
    for metadata_file in sorted(METADATA_DIR.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
        jobs.append(public_import_job(json.loads(metadata_file.read_text(encoding="utf-8"))))
        if len(jobs) >= limit:
            break
    return {"jobs": jobs}


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


def numeric_columns(df):
    return [column for column in df.columns if pd.api.types.is_numeric_dtype(df[column])]


def categorical_columns(df):
    return [
        column
        for column in df.columns
        if not pd.api.types.is_numeric_dtype(df[column])
        and df[column].nunique(dropna=True) <= min(30, max(10, len(df) // 2))
    ]


def datetime_like_columns(df):
    result = []
    for column in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[column]):
            result.append(column)
            continue
        if any(keyword in str(column).lower() for keyword in ["date", "time", "日期", "时间", "月份", "年份"]):
            parsed = pd.to_datetime(df[column], errors="coerce")
            if parsed.notna().sum() >= max(1, len(df) * 0.5):
                result.append(column)
    return result


def summarize_top_categories(df, category_column, metric_column=None, limit=5):
    if metric_column:
        grouped = df.groupby(category_column, dropna=False)[metric_column].sum().sort_values(ascending=False)
        return [
            {"name": json_safe(index), "value": round(float(value), 4)}
            for index, value in grouped.head(limit).items()
        ]
    counts = df[category_column].value_counts(dropna=False).head(limit)
    return [{"name": json_safe(index), "value": int(value)} for index, value in counts.items()]


def choose_primary_metric(numeric_profile):
    for keyword in ["成交金额", "销售额", "收入", "金额", "利润", "销量", "成交客户数", "客户数"]:
        for candidate in numeric_profile:
            if keyword in candidate["column"]:
                return candidate["column"]
    return numeric_profile[0]["column"] if numeric_profile else None


def choose_dimension(categorical, preferred_keywords=None):
    preferred_keywords = preferred_keywords or []
    for keyword in preferred_keywords:
        for column in categorical:
            if keyword in column:
                return column
    return categorical[0] if categorical else None


def build_metric_catalog(numeric_profile, primary_metric):
    catalog = []
    for item in numeric_profile[:8]:
        aggregation = "SUM" if item["column"] == primary_metric or any(keyword in item["column"] for keyword in ["金额", "收入", "销售额", "销量", "客户数"]) else "AVG"
        catalog.append(
            {
                "name": item["column"],
                "formula": f"{aggregation}({item['column']})",
                "value": item["sum"] if aggregation == "SUM" else item["mean"],
                "scene": "核心经营规模" if item["column"] == primary_metric else "辅助拆解指标",
            }
        )
    return catalog


def build_monitor_items(trend, primary_metric):
    if not trend:
        return []
    values = [item["value"] for item in trend]
    baseline = mean(values) if values else 0
    items = []
    for index, item in enumerate(trend):
        previous = values[index - 1] if index > 0 else None
        mom = round((item["value"] - previous) / previous * 100, 2) if previous else 0
        deviation = round((item["value"] - baseline) / baseline * 100, 2) if baseline else 0
        severity = "normal"
        if abs(mom) >= 30 or abs(deviation) >= 25:
            severity = "high"
        elif abs(mom) >= 15 or abs(deviation) >= 15:
            severity = "medium"
        items.append(
            {
                "period": item["period"],
                "metric": primary_metric,
                "value": item["value"],
                "mom": mom,
                "deviation": deviation,
                "severity": severity,
                "suggestion": "重点复盘该周期活动、渠道、区域或产品结构变化。" if severity != "normal" else "波动可接受，持续观察。",
            }
        )
    return items


def build_sql_templates_for_workspace(table_name, primary_metric, dimension, date_column):
    table_ref = f'"{table_name}"' if table_name else "当前业务空间表"
    templates = [
        {
            "name": "总量概览",
            "sql": f"SELECT COUNT(*) AS row_count{f', SUM(\"{primary_metric}\") AS total_metric' if primary_metric else ''} FROM {table_ref};",
        }
    ]
    if dimension and primary_metric:
        templates.append(
            {
                "name": "维度贡献排行",
                "sql": f"SELECT \"{dimension}\", SUM(\"{primary_metric}\") AS total_metric FROM {table_ref} GROUP BY \"{dimension}\" ORDER BY total_metric DESC LIMIT 10;",
            }
        )
    if date_column and primary_metric:
        templates.append(
            {
                "name": "时间趋势",
                "sql": f"SELECT DATE_TRUNC('month', \"{date_column}\"::timestamp) AS month, SUM(\"{primary_metric}\") AS total_metric FROM {table_ref} GROUP BY month ORDER BY month;",
            }
        )
    return templates


def has_column_keyword(columns, keywords):
    text = " ".join(str(column) for column in columns)
    return any(keyword in text for keyword in keywords)


def find_column_by_keywords(columns, keywords):
    for keyword in keywords:
        for column in columns:
            if keyword in str(column):
                return column
    return None


def safe_ratio(numerator, denominator):
    return round(float(numerator) / float(denominator) * 100, 2) if denominator else 0


def pearson_correlation(df, x_column, y_column):
    series = df[[x_column, y_column]].copy()
    series[x_column] = pd.to_numeric(series[x_column], errors="coerce")
    series[y_column] = pd.to_numeric(series[y_column], errors="coerce")
    series = series.dropna()
    if len(series) < 3:
        return None
    correlation = series[x_column].corr(series[y_column])
    if pd.isna(correlation):
        return None
    return round(float(correlation), 4)


ANALYSIS_FRAMEWORK_LIBRARY = {
    "销售经营": {
        "title": "销售经营分析框架",
        "goal": "定位成交增长、收入结构、区域效率、客户质量和投入产出问题。",
        "framework": [
            "销售漏斗：线索/商机/报价/成交逐层看转化和流失。",
            "客户分层：按贡献、频次、最近成交识别高价值、潜力、沉默客户。",
            "区域效率：对比区域贡献、客单、转化和资源覆盖。",
            "产品结构：识别头部产品、长尾产品、组合销售和结构风险。",
            "复购分析：观察客户持续购买、复购周期和复购贡献。",
            "ROI 预留：结合成本、费用、投放字段判断投入产出。",
        ],
        "requiredSignals": ["成交金额/销售额", "客户/用户", "产品/品类", "区域/城市", "时间", "成本/费用"],
        "defaultPath": ["主指标确认", "成交趋势", "产品结构", "区域效率", "客户分层", "异常归因", "策略优先级"],
    },
    "用户运营": {
        "title": "用户运营分析框架",
        "goal": "定位用户增长、转化、留存、活跃质量和复购问题。",
        "framework": [
            "用户分层：按活跃、消费、价值、生命周期拆用户。",
            "转化漏斗：访问/注册/激活/付费逐步定位卡点。",
            "留存分析：按 cohort 看次日、7 日、30 日留存。",
            "复购分析：看重复购买、复购周期和复购金额。",
            "渠道质量：比较渠道获客质量、转化效率和留存表现。",
        ],
        "requiredSignals": ["用户ID", "注册/活跃时间", "渠道", "行为/事件", "付费/订单", "留存标签"],
        "defaultPath": ["用户规模", "转化漏斗", "留存分层", "复购贡献", "渠道质量", "策略优先级"],
    },
    "财务经营": {
        "title": "财务经营分析框架",
        "goal": "定位收入、成本、利润、预算偏差和 ROI 健康度。",
        "framework": [
            "收入结构：按业务线/产品/区域拆收入贡献。",
            "成本结构：拆固定成本、变动成本、费用项和异常支出。",
            "利润质量：关注毛利率、净利率、利润贡献和低毛利单元。",
            "预算偏差：对比实际、预算和目标达成。",
            "ROI：计算投入产出和费用效率。",
        ],
        "requiredSignals": ["收入", "成本", "费用", "利润", "预算/目标", "期间"],
        "defaultPath": ["收入概览", "成本结构", "利润质量", "预算偏差", "ROI", "风险提示"],
    },
    "库存管理": {
        "title": "库存管理分析框架",
        "goal": "定位库存周转、缺货、滞销、SKU 结构和仓储效率问题。",
        "framework": [
            "库存结构：按 SKU/品类/仓库看库存占用。",
            "周转效率：用销量、库存和天数判断周转快慢。",
            "缺货风险：识别低库存高销量 SKU。",
            "滞销风险：识别高库存低销量 SKU。",
            "仓库效率：比较仓库库存占用、出入库和周转表现。",
        ],
        "requiredSignals": ["SKU/产品", "库存量", "销量/出库", "入库", "仓库", "日期"],
        "defaultPath": ["库存总览", "SKU 结构", "周转效率", "缺货风险", "滞销风险", "补货建议"],
    },
    "运营分析": {
        "title": "运营活动分析框架",
        "goal": "定位活动效果、渠道质量、转化效率、投放 ROI 和运营动作优先级。",
        "framework": [
            "活动效果：对比活动前后核心指标变化。",
            "渠道质量：比较渠道流量、线索、转化和成本。",
            "转化路径：识别曝光/点击/留资/成交卡点。",
            "人群分层：按来源、行为、价值分层运营。",
            "投放 ROI：结合费用和收入衡量投入产出。",
        ],
        "requiredSignals": ["活动/渠道", "曝光/点击", "线索/转化", "成本/投放", "收入/成交", "日期"],
        "defaultPath": ["活动概览", "渠道对比", "转化漏斗", "人群分层", "ROI", "动作优先级"],
    },
    "通用业务": {
        "title": "通用指标诊断框架",
        "goal": "在业务语义不足时，先完成指标、维度、趋势和异常的基础诊断。",
        "framework": [
            "数据画像：确认字段角色、缺失和唯一值。",
            "指标树：选择主指标和辅助指标。",
            "维度贡献：按核心维度拆结构。",
            "趋势异常：识别时间波动和异常周期。",
            "归因假设：用维度差异形成下一步检查路径。",
        ],
        "requiredSignals": ["核心数值指标", "业务维度", "时间字段", "唯一标识"],
        "defaultPath": ["数据画像", "主指标确认", "维度贡献", "趋势异常", "归因假设"],
    },
}


def analysis_framework_for(business_type):
    return ANALYSIS_FRAMEWORK_LIBRARY.get(business_type, ANALYSIS_FRAMEWORK_LIBRARY["通用业务"])


def build_business_methodology(business_type, columns, numeric, categorical, primary_metric, primary_dimension, date_columns):
    framework = analysis_framework_for(business_type)
    methods = []
    if business_type == "销售经营":
        methods.extend(
            [
                {"name": "销售漏斗", "fit": "中" if has_column_keyword(columns, ["线索", "商机", "报价", "成交", "转化"]) else "低", "question": "从机会到成交哪一步掉量最大？", "requiredFields": ["线索/客户", "阶段/状态", primary_metric or "成交金额"], "output": "转化短板、阶段流失、下一步补漏动作"},
                {"name": "客户分层", "fit": "高" if has_column_keyword(columns, ["客户", "用户"]) and primary_metric else "中", "question": "哪些客户贡献高、潜力大或需要唤醒？", "requiredFields": ["客户/用户", primary_metric or "金额指标", date_columns[0] if date_columns else "时间字段"], "output": "高价值客户、潜力客户、沉默客户"},
                {"name": "区域效率", "fit": "高" if has_column_keyword(columns, ["区域", "省份", "城市"]) else "低", "question": "哪些区域高贡献，哪些区域低效率？", "requiredFields": ["区域/省份/城市", primary_metric or "成交指标"], "output": "区域标杆、低效区域、资源倾斜建议"},
                {"name": "产品结构", "fit": "高" if has_column_keyword(columns, ["产品", "品类", "商品"]) else "低", "question": "收入由哪些产品驱动，是否过度集中？", "requiredFields": ["产品/品类", primary_metric or "销售额"], "output": "头部产品、长尾产品、组合优化"},
                {"name": "ROI", "fit": "高" if has_column_keyword(columns, ["成本", "费用", "投放", "预算"]) and primary_metric else "待补字段", "question": "投入是否带来足够产出？", "requiredFields": [primary_metric or "收入", "成本/费用/投放"], "output": "投入产出比、费用效率、预算优先级"},
                {"name": "复购", "fit": "中" if has_column_keyword(columns, ["客户", "用户", "订单", "成交"]) and date_columns else "低", "question": "客户是否持续购买，复购贡献如何？", "requiredFields": ["客户/用户", "订单/成交", "时间字段"], "output": "复购率、复购金额、复购人群特征"},
            ]
        )
    elif business_type == "用户运营":
        methods.extend(
            [
                {"name": "留存", "fit": "高" if date_columns and has_column_keyword(columns, ["用户", "注册", "活跃"]) else "中", "question": "新用户在后续周期是否持续活跃？", "requiredFields": ["用户", "注册/首访时间", "活跃时间"], "output": "周期留存、流失拐点、召回窗口"},
                {"name": "用户分层", "fit": "高" if has_column_keyword(columns, ["用户", "客户"]) else "中", "question": "哪些用户最值得运营？", "requiredFields": ["用户", primary_metric or "活跃/消费指标"], "output": "高价值、成长、沉默、流失风险用户"},
                {"name": "转化漏斗", "fit": "中" if has_column_keyword(columns, ["转化", "点击", "访问", "支付", "注册"]) else "低", "question": "从访问到转化卡在哪一步？", "requiredFields": ["用户", "事件/阶段", "时间"], "output": "漏斗流失、关键步骤优化"},
                {"name": "复购", "fit": "中" if has_column_keyword(columns, ["订单", "购买", "消费", "客户"]) else "低", "question": "用户是否重复购买或持续消费？", "requiredFields": ["用户", "订单/消费", "时间"], "output": "复购率、复购周期、复购驱动因素"},
            ]
        )
    elif business_type == "财务经营":
        methods.extend(
            [
                {"name": "ROI", "fit": "高" if has_column_keyword(columns, ["收入", "成本", "费用", "利润"]) else "中", "question": "收入、成本与利润之间是否健康？", "requiredFields": ["收入", "成本/费用", "利润"], "output": "投入产出、利润率、费用结构"},
                {"name": "预算偏差", "fit": "高" if has_column_keyword(columns, ["预算", "目标", "计划"]) else "待补字段", "question": "实际结果与预算差距在哪里？", "requiredFields": ["实际", "预算/目标", "期间"], "output": "偏差金额、偏差率、责任维度"},
                {"name": "产品/区域利润结构", "fit": "中" if primary_dimension and primary_metric else "低", "question": "利润由哪些业务单元贡献？", "requiredFields": [primary_dimension or "业务维度", primary_metric or "利润/收入"], "output": "利润贡献、低毛利单元、提效方向"},
            ]
        )
    elif business_type == "库存管理":
        methods.extend(
            [
                {"name": "库存结构", "fit": "高" if has_column_keyword(columns, ["库存", "sku", "SKU", "产品", "品类"]) else "中", "question": "库存占用集中在哪些 SKU/品类/仓库？", "requiredFields": ["SKU/产品", "库存量", "仓库/品类"], "output": "库存占用结构、头部 SKU、仓库压力"},
                {"name": "周转效率", "fit": "高" if has_column_keyword(columns, ["库存", "销量", "出库"]) else "待补字段", "question": "哪些商品周转快，哪些商品占用库存？", "requiredFields": ["库存量", "销量/出库", "日期"], "output": "周转快慢、补货优先级、滞销风险"},
                {"name": "缺货风险", "fit": "中" if has_column_keyword(columns, ["库存", "销量", "安全库存"]) else "低", "question": "哪些高销量 SKU 可能缺货？", "requiredFields": ["库存量", "销量", "安全库存"], "output": "缺货预警、补货建议"},
                {"name": "滞销风险", "fit": "中" if has_column_keyword(columns, ["库存", "销量", "库龄"]) else "低", "question": "哪些 SKU 高库存低动销？", "requiredFields": ["库存量", "销量/出库", "库龄"], "output": "滞销清单、促销/清仓建议"},
            ]
        )
    elif business_type == "运营分析":
        methods.extend(
            [
                {"name": "活动效果", "fit": "高" if has_column_keyword(columns, ["活动", "运营", "转化"]) and date_columns else "中", "question": "运营活动是否带来核心指标提升？", "requiredFields": ["活动", primary_metric or "核心指标", "日期"], "output": "活动前后对比、增量效果、复盘建议"},
                {"name": "渠道质量", "fit": "高" if has_column_keyword(columns, ["渠道", "来源"]) else "低", "question": "哪些渠道带来高质量转化？", "requiredFields": ["渠道/来源", "线索/转化", "成本/收入"], "output": "渠道贡献、渠道效率、预算建议"},
                {"name": "转化路径", "fit": "中" if has_column_keyword(columns, ["曝光", "点击", "留资", "转化", "成交"]) else "低", "question": "从触达到成交卡在哪一步？", "requiredFields": ["曝光/点击/留资/成交", "时间", "渠道"], "output": "转化短板、漏斗优化动作"},
                {"name": "投放 ROI", "fit": "高" if has_column_keyword(columns, ["投放", "成本", "费用", "收入"]) else "待补字段", "question": "投入是否产生有效回报？", "requiredFields": ["投放/费用", "收入/成交", "渠道/活动"], "output": "ROI、CPA、预算增减建议"},
            ]
        )
    else:
        methods.extend(
            [
                {"name": "指标树拆解", "fit": "高" if primary_metric else "中", "question": "核心指标由哪些维度共同驱动？", "requiredFields": [primary_metric or "核心指标", primary_dimension or "业务维度"], "output": "指标口径、贡献维度、问题定位路径"},
                {"name": "结构贡献", "fit": "高" if primary_metric and primary_dimension else "中", "question": "业务结构是否集中或失衡？", "requiredFields": [primary_dimension or "维度", primary_metric or "指标"], "output": "头部集中度、长尾结构、结构优化建议"},
                {"name": "趋势异常", "fit": "高" if primary_metric and date_columns else "低", "question": "核心指标是否出现异常波动？", "requiredFields": [date_columns[0] if date_columns else "时间字段", primary_metric or "指标"], "output": "波动周期、异常等级、复盘方向"},
            ]
        )
    method_names = {method["name"] for method in methods}
    for item in framework["framework"]:
        name = item.split("：", 1)[0]
        if name not in method_names:
            methods.append({"name": name, "fit": "框架建议", "question": item, "requiredFields": framework["requiredSignals"][:3], "output": "专项诊断结论与行动路径"})
    return methods


def build_chart_blueprints(business_type, primary_metric, primary_dimension, date_columns, numeric, columns):
    blueprints = []
    if primary_metric and primary_dimension:
        blueprints.append(
            {
                "type": "bar",
                "title": f"{primary_dimension} {primary_metric}排行",
                "businessQuestion": f"哪个 `{primary_dimension}` 对 `{primary_metric}` 的绝对贡献最高？",
                "whyThisChart": "横向/纵向柱形图适合做离散维度对比，能快速暴露头部贡献和低效尾部。",
                "interpretationGuide": "优先看 Top 项与中位项的差距；若头部远高于其他项，应继续拆产品、区域或人员组合。",
            }
        )
        blueprints.append(
            {
                "type": "pie",
                "title": f"{primary_dimension} 贡献结构",
                "businessQuestion": f"`{primary_dimension}` 的贡献是否过度集中？",
                "whyThisChart": "环形图适合表达结构占比；当 Top3 占比过高时，说明业务对少数维度依赖较强。",
                "interpretationGuide": "看 Top3/Top5 占比和长尾项数量，判断增长是靠少数爆点还是结构均衡。",
            }
        )
    if primary_metric and date_columns:
        blueprints.append(
            {
                "type": "line",
                "title": f"{primary_metric} 时间趋势",
                "businessQuestion": f"`{primary_metric}` 在时间上是否稳定增长或出现异常？",
                "whyThisChart": "折线图适合观察时间序列、季节性、拐点和异常波动，是监控型看板的基础视图。",
                "interpretationGuide": "重点看峰值、低谷、连续上升/下降和环比突变，再回溯活动、渠道、区域或产品变化。",
            }
        )
    if len(numeric) >= 2:
        blueprints.append(
            {
                "type": "scatter",
                "title": f"{numeric[0]} 与 {numeric[1]} 关系",
                "businessQuestion": f"`{numeric[0]}` 和 `{numeric[1]}` 是否存在协同或冲突关系？",
                "whyThisChart": "散点图适合发现相关性、分群和离群点，比单纯排行更容易暴露异常组合。",
                "interpretationGuide": "看点云方向和孤立点；强相关说明可联动优化，离群点需要单独复盘口径或业务事件。",
            }
        )
    if business_type == "销售经营" and has_column_keyword(columns, ["区域", "省份", "城市"]) and primary_metric:
        blueprints.append(
            {
                "type": "bar",
                "title": "区域效率对比",
                "businessQuestion": "哪些区域贡献高，哪些区域可能投入不足或转化偏低？",
                "whyThisChart": "区域对比视图能把资源配置问题显性化，适合经营例会定位区域标杆。",
                "interpretationGuide": "高贡献区域沉淀打法，低贡献区域进一步检查线索、客群、产品供给和团队覆盖。",
            }
        )
    if business_type == "销售经营" and has_column_keyword(columns, ["产品", "品类", "商品"]) and primary_metric:
        blueprints.append(
            {
                "type": "treemap",
                "title": "产品结构矩阵",
                "businessQuestion": "产品贡献是否健康，增长是否依赖少数 SKU/品类？",
                "whyThisChart": "Tableau 常用结构视图先看面积贡献，再下钻颜色或分组解释结构质量。",
                "interpretationGuide": "头部产品看护盘，长尾产品看组合销售、淘汰或渠道适配。",
            }
        )
    return blueprints


def build_chart_plan_from_blueprints(blueprints):
    return [
        {
            "type": chart["type"],
            "title": chart["title"],
            "reason": chart["whyThisChart"],
            "businessQuestion": chart["businessQuestion"],
        }
        for chart in blueprints
    ]


def build_growth_suggestions(columns, categorical):
    text = " ".join(columns)
    suggestions = []
    if any(keyword in text for keyword in ["客户", "用户"]):
        suggestions.append({"title": "客户分层", "content": "按成交金额、成交次数或产品类型识别高价值客户、潜力客户和沉默客户。"})
    if any(keyword in text for keyword in ["区域", "省份", "城市"]):
        suggestions.append({"title": "区域增长", "content": "按区域/省份拆解贡献与增速，识别可复制的高转化区域。"})
    if any(keyword in text for keyword in ["产品", "品类"]):
        suggestions.append({"title": "产品增长", "content": "按产品类型拆解成交贡献，定位增长产品、拖累产品和交叉销售机会。"})
    if not suggestions:
        suggestions.append({"title": "业务分层", "content": f"可优先选择 `{categorical[0]}` 做分层分析，观察不同群组的规模和贡献。" if categorical else "建议先补充业务维度字段，再做增长拆解。"})
    return suggestions


def build_monetization_suggestions(primary_metric, numeric_profile):
    if not primary_metric:
        return []
    suggestions = [{"title": "收入贡献", "content": f"以 `{primary_metric}` 作为收入/规模主指标，按产品、区域、团队等维度拆解贡献。"}]
    if any("客单价" in item["column"] for item in numeric_profile):
        suggestions.append({"title": "客单价效率", "content": "结合客单价和成交客户数，识别高价值产品与高效率团队。"})
    suggestions.append({"title": "成本 ROI 预留", "content": "当前表若补充成本、投放费用或人力成本字段，可继续计算 ROI、毛利率和获客效率。"})
    return suggestions


def build_data_profile(df, schema_profile, numeric, categorical, date_columns, metadata):
    rows = len(df)
    columns = list(df.columns)
    missing_cells = int(df.isna().sum().sum())
    total_cells = rows * len(columns) if rows and columns else 0
    missing_rate = round(missing_cells / total_cells * 100, 2) if total_cells else 0
    duplicate_rate = round(metadata.get("removedDuplicateRows", 0) / max(metadata.get("rowsBefore", rows), 1) * 100, 2)
    high_missing_fields = [
        {"name": field["name"], "missingRate": round(field.get("missingRate", 0) * 100, 2), "role": field.get("role", "unknown")}
        for field in schema_profile.get("fields", [])
        if field.get("missingRate", 0) >= 0.2
    ][:6]
    high_cardinality_dimensions = [
        {"name": column, "uniqueCount": int(df[column].nunique(dropna=True))}
        for column in categorical
        if df[column].nunique(dropna=True) >= max(20, rows * 0.2)
    ][:6]
    metric_ranges = []
    for column in numeric[:8]:
        series = pd.to_numeric(df[column], errors="coerce")
        metric_ranges.append(
            {
                "name": column,
                "min": round(float(series.min()), 4) if series.notna().any() else 0,
                "max": round(float(series.max()), 4) if series.notna().any() else 0,
                "mean": round(float(series.mean()), 4) if series.notna().any() else 0,
                "zeroRate": round(float((series == 0).mean() * 100), 2) if len(series) else 0,
            }
        )
    return {
        "rowCount": rows,
        "columnCount": len(columns),
        "metricCount": len(numeric),
        "dimensionCount": len(categorical),
        "timeCount": len(date_columns),
        "missingRate": missing_rate,
        "duplicateRate": duplicate_rate,
        "highMissingFields": high_missing_fields,
        "highCardinalityDimensions": high_cardinality_dimensions,
        "metricRanges": metric_ranges,
        "roleCounts": schema_profile.get("roleCounts", {}),
        "profileSummary": f"该表包含 {rows} 行、{len(columns)} 个字段，其中数值指标 {len(numeric)} 个、维度 {len(categorical)} 个、时间字段 {len(date_columns)} 个，整体缺失率 {missing_rate}%。",
    }


def build_quality_score(data_profile, metadata, primary_metric, primary_dimension, date_columns):
    score = 100
    penalties = []
    if data_profile["missingRate"] > 0:
        penalty = min(25, data_profile["missingRate"] * 0.8)
        score -= penalty
        penalties.append({"item": "缺失值", "penalty": round(penalty, 1), "detail": f"整体缺失率 {data_profile['missingRate']}%。"})
    if data_profile["duplicateRate"] > 0:
        penalty = min(15, data_profile["duplicateRate"])
        score -= penalty
        penalties.append({"item": "重复行", "penalty": round(penalty, 1), "detail": f"导入清洗前重复/空行占比约 {data_profile['duplicateRate']}%。"})
    if not primary_metric:
        score -= 20
        penalties.append({"item": "主指标", "penalty": 20, "detail": "未识别明确主指标，诊断深度会下降。"})
    if not primary_dimension:
        score -= 12
        penalties.append({"item": "核心维度", "penalty": 12, "detail": "缺少适合分组分析的核心维度。"})
    if not date_columns:
        score -= 10
        penalties.append({"item": "时间字段", "penalty": 10, "detail": "缺少稳定时间字段，无法做趋势和留存类分析。"})
    if data_profile["rowCount"] < 30:
        score -= 10
        penalties.append({"item": "样本量", "penalty": 10, "detail": "数据行数较少，显著性和异常判断偏弱。"})
    score = max(0, round(score, 1))
    if score >= 85:
        grade = "A"
        summary = "数据质量较好，可直接进入诊断型分析。"
    elif score >= 70:
        grade = "B"
        summary = "数据质量可用，建议关注少量字段补齐和口径确认。"
    elif score >= 55:
        grade = "C"
        summary = "数据可做初步分析，但需要先补齐关键字段。"
    else:
        grade = "D"
        summary = "数据质量偏弱，建议先治理字段、样本和业务口径。"
    return {
        "score": score,
        "grade": grade,
        "summary": summary,
        "penalties": penalties,
        "cleaningSummary": f"清洗删除重复行 {metadata.get('removedDuplicateRows', 0)} 行、空行 {metadata.get('removedEmptyRows', 0)} 行，类型转换 {len(metadata.get('typeChanges', []))} 个字段。",
    }


def build_recommended_paths(business_type, framework, data_profile, quality_score, primary_metric, primary_dimension, date_columns):
    paths = []
    for index, step in enumerate(framework["defaultPath"], start=1):
        readiness = "可执行"
        reason = "字段已满足基础分析。"
        if step in ["成交趋势", "趋势异常", "留存分层", "活动概览"] and not date_columns:
            readiness = "需补字段"
            reason = "缺少时间字段。"
        if step in ["产品结构", "区域效率", "客户分层", "渠道对比", "SKU 结构"] and not primary_dimension:
            readiness = "需补字段"
            reason = "缺少核心维度。"
        if step in ["ROI", "预算偏差", "投放 ROI"] and quality_score["grade"] in ["C", "D"]:
            readiness = "建议后置"
            reason = "需要先确认成本/费用/预算等字段口径。"
        paths.append(
            {
                "order": index,
                "name": step,
                "readiness": readiness,
                "reason": reason,
                "output": f"围绕 `{primary_metric or '核心指标'}` 输出 {step} 诊断结论。",
            }
        )
    if data_profile["missingRate"] >= 10:
        paths.insert(0, {"order": 0, "name": "数据治理优先", "readiness": "优先处理", "reason": "缺失率较高。", "output": "先补齐关键字段，再进入业务诊断。"})
    return paths


def build_analysis_plan(business_type, schema_profile, numeric, categorical, date_columns, primary_metric, primary_dimension):
    columns = schema_profile.get("columns", [])
    framework = analysis_framework_for(business_type)
    modules = ["指标体系", "数据清洗质量", "SQL 分析模板"]
    if primary_metric and primary_dimension:
        modules.extend(["BI 看板", "维度贡献分析", "归因诊断"])
    if primary_metric and date_columns:
        modules.extend(["业务监控与异常", "对比基准"])
    if any(keyword in " ".join(columns) for keyword in ["客户", "用户", "区域", "省份", "产品"]):
        modules.append("增长分析")
    if primary_metric and any(keyword in primary_metric for keyword in ["金额", "收入", "销售额", "利润", "客单价"]):
        modules.append("变现与成本分析")
    modules.append("策略优先级")

    methodology = build_business_methodology(business_type, columns, numeric, categorical, primary_metric, primary_dimension, date_columns)
    chart_blueprints = build_chart_blueprints(business_type, primary_metric, primary_dimension, date_columns, numeric, columns)
    chart_plan = build_chart_plan_from_blueprints(chart_blueprints)

    if business_type == "销售经营":
        focus = "采用销售经营方法论：先看销售漏斗/成交结果，再看客户分层、区域效率、产品结构、复购和 ROI 预留。"
    elif business_type == "用户运营":
        focus = "采用用户运营方法论：先看用户分层与转化漏斗，再看留存、复购、活跃质量和增长动作。"
    elif business_type == "财务经营":
        focus = "采用财务经营方法论：围绕收入、成本、利润、预算偏差和 ROI 判断经营质量。"
    elif business_type == "供应链库存":
        focus = "优先围绕库存周转、出入库、SKU 结构和异常库存做分析。"
    else:
        focus = "采用通用指标树方法：先确认主指标，再按结构贡献、趋势异常和关键维度做诊断。"

    return {
        "name": f"{business_type}分析方案",
        "framework": framework,
        "focus": focus,
        "confidence": "高" if primary_metric and (primary_dimension or date_columns) else "中",
        "inputPolicy": "schema-only",
        "inputSummary": f"仅使用文件名、{schema_profile.get('rowCount', 0)} 行、{schema_profile.get('columnCount', len(columns))} 列、字段名与字段角色进行方案预判，未传输明细数据。",
        "selectedModules": modules,
        "methodology": methodology,
        "chartPlan": chart_plan,
        "chartBlueprints": chart_blueprints,
        "reasoning": [
            f"识别到 {len(numeric)} 个数值字段、{len(categorical)} 个维度字段、{len(date_columns)} 个时间字段。",
            f"主指标选择为 `{primary_metric}`。" if primary_metric else "未识别明确主指标，建议先选择一个核心数值字段。",
            f"核心维度选择为 `{primary_dimension}`。" if primary_dimension else "未识别明确核心维度，建议补充可分组字段。",
        ],
    }


def build_executive_summary(business_type, primary_metric, primary_dimension, top_categories, trend, numeric_profile, analysis_plan):
    highlights = []
    if primary_metric:
        total_value = next((item["sum"] for item in numeric_profile if item["column"] == primary_metric), 0)
        highlights.append({"label": "主指标", "title": primary_metric, "value": total_value, "tone": "blue", "detail": "作为本报告的一级经营指标。"})
    if primary_dimension and top_categories:
        leader = top_categories[0]
        highlights.append({"label": "最大贡献维度", "title": str(leader["name"]), "value": leader["value"], "tone": "green", "detail": f"按 `{primary_dimension}` 聚合后的最高贡献项。"})
    if trend:
        best_period = max(trend, key=lambda item: item["value"])
        highlights.append({"label": "峰值周期", "title": best_period["period"], "value": best_period["value"], "tone": "amber", "detail": "需要结合活动、渠道、区域或团队复盘。"})
    highlights.append({"label": "分析方案", "title": analysis_plan["name"], "value": analysis_plan["confidence"], "tone": "purple", "detail": analysis_plan["inputSummary"]})
    actions = []
    if primary_metric and primary_dimension:
        actions.append(f"围绕 `{primary_dimension}` 建立 `{primary_metric}` 贡献排行和结构占比看板。")
    if trend:
        actions.append(f"对 `{primary_metric}` 建立周期环比、偏离均值和峰值复盘机制。")
    if business_type == "销售经营":
        actions.append("拆解产品、区域、团队三类维度，优先定位高贡献组合和低效区域。")
    actions.append("补充成本/费用字段后，可进一步计算 ROI、毛利率和投入产出效率。")
    return {"highlights": highlights[:4], "actions": actions}


def build_scatter_points(df, x_column, y_column, limit=120):
    sample = df[[x_column, y_column]].copy()
    sample[x_column] = pd.to_numeric(sample[x_column], errors="coerce")
    sample[y_column] = pd.to_numeric(sample[y_column], errors="coerce")
    sample = sample.dropna().head(limit)
    return [[round(float(row[x_column]), 4), round(float(row[y_column]), 4)] for _, row in sample.iterrows()]


def build_workspace_charts(df, primary_metric, primary_dimension, date_columns, numeric, chart_blueprints=None):
    chart_blueprints = chart_blueprints or []

    def blueprint_for(chart_type, fallback_title):
        for blueprint in chart_blueprints:
            if blueprint["type"] == chart_type and (fallback_title in blueprint["title"] or blueprint["title"] in fallback_title):
                return blueprint
        for blueprint in chart_blueprints:
            if blueprint["type"] == chart_type:
                return blueprint
        return {
            "businessQuestion": "这张图用于回答当前业务维度下的核心问题。",
            "whyThisChart": "该图表类型适合当前字段结构和分析目标。",
            "interpretationGuide": "结合头部、尾部、趋势和异常点进行业务判断。",
        }

    charts = []
    if primary_metric and primary_dimension:
        top_items = summarize_top_categories(df, primary_dimension, primary_metric, limit=10)
        title = f"{primary_dimension} {primary_metric}排行"
        blueprint = blueprint_for("bar", title)
        charts.append(
            {
                "type": "bar",
                "title": title,
                "description": "用于比较不同维度对核心指标的贡献。",
                "businessQuestion": blueprint["businessQuestion"],
                "whyThisChart": blueprint["whyThisChart"],
                "interpretationGuide": blueprint["interpretationGuide"],
                "x": [item["name"] for item in top_items],
                "y": [item["value"] for item in top_items],
            }
        )
        title = f"{primary_dimension} 贡献占比"
        blueprint = blueprint_for("pie", title)
        charts.append(
            {
                "type": "pie",
                "title": title,
                "description": "用于观察业务结构集中度和头部贡献。",
                "businessQuestion": blueprint["businessQuestion"],
                "whyThisChart": blueprint["whyThisChart"],
                "interpretationGuide": blueprint["interpretationGuide"],
                "data": top_items[:8],
            }
        )
    if primary_metric and date_columns:
        date_column = date_columns[0]
        tmp = df[[date_column, primary_metric]].copy()
        tmp[date_column] = pd.to_datetime(tmp[date_column], errors="coerce")
        tmp[primary_metric] = pd.to_numeric(tmp[primary_metric], errors="coerce")
        tmp = tmp.dropna(subset=[date_column])
        if not tmp.empty:
            grouped = tmp.groupby(tmp[date_column].dt.to_period("M"))[primary_metric].sum().sort_index()
            title = f"{primary_metric} 月度趋势"
            blueprint = blueprint_for("line", title)
            charts.append(
                {
                    "type": "line",
                    "title": title,
                    "description": "用于观察时间趋势、峰值周期和波动风险。",
                    "businessQuestion": blueprint["businessQuestion"],
                    "whyThisChart": blueprint["whyThisChart"],
                    "interpretationGuide": blueprint["interpretationGuide"],
                    "x": [str(index) for index in grouped.index],
                    "y": [round(float(value), 4) for value in grouped.values],
                }
            )
    if len(numeric) >= 2:
        title = f"{numeric[0]} 与 {numeric[1]} 分布"
        blueprint = blueprint_for("scatter", title)
        charts.append(
            {
                "type": "scatter",
                "title": title,
                "description": "用于观察两个数值指标之间的关系和潜在离群点。",
                "businessQuestion": blueprint["businessQuestion"],
                "whyThisChart": blueprint["whyThisChart"],
                "interpretationGuide": blueprint["interpretationGuide"],
                "xName": numeric[0],
                "yName": numeric[1],
                "data": build_scatter_points(df, numeric[0], numeric[1]),
            }
        )
    return charts


def build_interactive_chart_config(df, numeric, categorical, date_columns):
    metrics = numeric[:12]
    dimensions = categorical[:12]
    time_grains = [{"key": "month", "label": "月"}, {"key": "quarter", "label": "季"}, {"key": "year", "label": "年"}]
    config = {
        "metrics": metrics,
        "dimensions": dimensions,
        "dateColumns": date_columns[:6],
        "timeGrains": time_grains,
        "defaultMetric": metrics[0] if metrics else None,
        "defaultDimension": dimensions[0] if dimensions else None,
        "defaultDateColumn": date_columns[0] if date_columns else None,
        "datasets": {"bars": {}, "pies": {}, "lines": {}, "scatters": {}},
    }
    for metric in metrics[:8]:
        for dimension in dimensions[:8]:
            top_items = summarize_top_categories(df, dimension, metric, limit=12)
            key = f"{metric}||{dimension}"
            config["datasets"]["bars"][key] = {"x": [item["name"] for item in top_items], "y": [item["value"] for item in top_items]}
            config["datasets"]["pies"][key] = {"data": top_items[:8]}
    for metric in metrics[:8]:
        for date_column in date_columns[:4]:
            tmp = pd.DataFrame(
                {
                    "__date": df[date_column],
                    "__metric": pd.to_numeric(df[metric], errors="coerce"),
                }
            )
            tmp["__date"] = pd.to_datetime(tmp["__date"], errors="coerce")
            tmp = tmp.dropna(subset=["__date"])
            if tmp.empty:
                continue
            for grain in ["month", "quarter", "year"]:
                if grain == "month":
                    grouped = tmp.groupby(tmp["__date"].dt.to_period("M"))["__metric"].sum().sort_index()
                elif grain == "quarter":
                    grouped = tmp.groupby(tmp["__date"].dt.to_period("Q"))["__metric"].sum().sort_index()
                else:
                    grouped = tmp.groupby(tmp["__date"].dt.to_period("Y"))["__metric"].sum().sort_index()
                key = f"{metric}||{date_column}||{grain}"
                config["datasets"]["lines"][key] = {"x": [str(index) for index in grouped.index], "y": [round(float(value), 4) for value in grouped.values]}
    for index, metric in enumerate(metrics[:5]):
        for other_metric in metrics[index + 1 : index + 4]:
            key = f"{metric}||{other_metric}"
            config["datasets"]["scatters"][key] = {"data": build_scatter_points(df, metric, other_metric), "xName": metric, "yName": other_metric}
    return config


def build_benchmark_summary(top_categories, trend, primary_metric, primary_dimension):
    benchmark = []
    if top_categories:
        values = [item["value"] for item in top_categories]
        total = sum(values)
        top_value = values[0] if values else 0
        median_value = sorted(values)[len(values) // 2] if values else 0
        top3_share = safe_ratio(sum(values[:3]), total)
        benchmark.append(
            {
                "name": "头部集中度",
                "value": f"{top3_share}%",
                "baseline": "经营常用观察线：Top3 超过 60% 代表结构较集中，低于 35% 代表结构较分散。",
                "diagnosis": f"`{primary_dimension}` Top1 是 `{top_categories[0]['name']}`，约为中位项 {round(top_value / median_value, 2) if median_value else 'NA'} 倍。",
            }
        )
    if trend:
        values = [item["value"] for item in trend]
        baseline = mean(values) if values else 0
        peak = max(trend, key=lambda item: item["value"])
        valley = min(trend, key=lambda item: item["value"])
        volatility = safe_ratio(max(values) - min(values), baseline)
        benchmark.append(
            {
                "name": "趋势波动率",
                "value": f"{volatility}%",
                "baseline": "经营监控常用观察线：波动率超过 50% 需要复盘供给、活动、渠道或统计口径。",
                "diagnosis": f"`{primary_metric}` 峰值在 {peak['period']}，低谷在 {valley['period']}，应做周期对比复盘。",
            }
        )
    return benchmark


def build_driver_analysis(df, primary_metric, categorical, date_columns):
    if not primary_metric:
        return []
    candidates = []
    metric_series = pd.to_numeric(df[primary_metric], errors="coerce")
    overall_mean = float(metric_series.mean()) if metric_series.notna().any() else 0
    overall_sum = float(metric_series.sum()) if metric_series.notna().any() else 0
    for dimension in categorical[:8]:
        unique_count = df[dimension].nunique(dropna=True)
        if unique_count < 2 or unique_count > 40:
            continue
        grouped = df.groupby(dimension, dropna=False)[primary_metric].agg(["sum", "mean", "count"]).sort_values("sum", ascending=False)
        if grouped.empty:
            continue
        top_name = json_safe(grouped.index[0])
        top_sum = float(grouped.iloc[0]["sum"])
        top_mean = float(grouped.iloc[0]["mean"])
        share = safe_ratio(top_sum, overall_sum)
        lift = safe_ratio(top_mean - overall_mean, overall_mean)
        candidates.append(
            {
                "dimension": dimension,
                "driver": str(top_name),
                "contributionShare": share,
                "meanLift": lift,
                "sampleSize": int(grouped.iloc[0]["count"]),
                "diagnosis": f"`{dimension}` 下 `{top_name}` 贡献占比 {share}%，均值较全局 {'高' if lift >= 0 else '低'} {abs(lift)}%。",
                "hypothesis": f"该维度可能是 `{primary_metric}` 的关键驱动；建议继续交叉拆解时间、产品、区域或客户层级。",
            }
        )
    candidates = sorted(candidates, key=lambda item: (abs(item["meanLift"]), item["contributionShare"]), reverse=True)
    if date_columns and len(candidates) > 0:
        candidates[0]["hypothesis"] += f" 同时按 `{date_columns[0]}` 做前后周期对比，判断这是持续优势还是单期事件。"
    return candidates[:5]


def build_anomaly_diagnosis(monitor_items, primary_metric, primary_dimension, top_categories):
    anomalies = [item for item in monitor_items if item["severity"] in ["high", "medium"]]
    diagnosis = []
    for item in anomalies[-5:]:
        direction = "上升" if item["mom"] > 0 else "下降"
        diagnosis.append(
            {
                "period": item["period"],
                "severity": item["severity"],
                "finding": f"`{primary_metric}` 在 {item['period']} 环比{direction} {abs(item['mom'])}%，较均值偏离 {item['deviation']}%。",
                "possibleCauses": [
                    f"`{primary_dimension}` 头部项贡献变化" if primary_dimension and top_categories else "核心业务维度结构变化",
                    "活动/渠道/价格/供给变化",
                    "数据口径、缺失值填充或重复记录影响",
                ],
                "nextCheck": f"优先对比该周期与前一周期的 `{primary_dimension or '核心维度'}` 贡献差异，并核对清洗日志。",
            }
        )
    if not diagnosis and monitor_items:
        diagnosis.append(
            {
                "period": "整体",
                "severity": "normal",
                "finding": f"`{primary_metric}` 未出现高等级异常，当前更适合做结构优化而不是救火式处理。",
                "possibleCauses": ["业务运行相对平稳", "周期样本不足导致异常识别偏保守"],
                "nextCheck": "补充更多周期后重新评估季节性和异常阈值。",
            }
        )
    return diagnosis


def build_significance_tests(df, primary_metric, categorical, numeric):
    tests = []
    if primary_metric and categorical:
        metric = pd.to_numeric(df[primary_metric], errors="coerce")
        for dimension in categorical[:6]:
            grouped = df.assign(__metric=metric).dropna(subset=["__metric"]).groupby(dimension, dropna=False)["__metric"]
            stats = grouped.agg(["mean", "count"]).sort_values("mean", ascending=False)
            stats = stats[stats["count"] >= 3]
            if len(stats) < 2:
                continue
            top = stats.iloc[0]
            bottom = stats.iloc[-1]
            pooled = float(metric.std()) if metric.notna().sum() >= 3 else 0
            effect_size = round(float((top["mean"] - bottom["mean"]) / pooled), 3) if pooled else 0
            tests.append(
                {
                    "name": f"{dimension} 均值差异",
                    "method": "启发式效应量（Cohen's d 近似）",
                    "result": f"最高组均值 {round(float(top['mean']), 4)}，最低组均值 {round(float(bottom['mean']), 4)}，效应量 {effect_size}。",
                    "confidence": "较强" if abs(effect_size) >= 0.8 else "中等" if abs(effect_size) >= 0.5 else "弱",
                    "note": "当前为自动报告的轻量显著性判断；正式决策前建议接入完整统计检验和样本分布校验。",
                }
            )
            break
    if len(numeric) >= 2:
        correlation = pearson_correlation(df, numeric[0], numeric[1])
        if correlation is not None:
            tests.append(
                {
                    "name": f"{numeric[0]} 与 {numeric[1]} 相关性",
                    "method": "Pearson 相关系数",
                    "result": f"相关系数 r={correlation}。",
                    "confidence": "较强" if abs(correlation) >= 0.7 else "中等" if abs(correlation) >= 0.4 else "弱",
                    "note": "相关不代表因果；若用于策略归因，需结合实验、活动记录或时间先后关系。",
                }
            )
    return tests


def build_priority_actions(business_type, primary_metric, primary_dimension, benchmark_summary, driver_analysis, anomaly_diagnosis, columns):
    actions = []
    if anomaly_diagnosis and any(item["severity"] in ["high", "medium"] for item in anomaly_diagnosis):
        actions.append(
            {
                "priority": "P0",
                "title": "先复盘异常周期",
                "impact": "高",
                "effort": "中",
                "rationale": anomaly_diagnosis[-1]["finding"],
                "nextStep": anomaly_diagnosis[-1]["nextCheck"],
            }
        )
    if driver_analysis:
        driver = driver_analysis[0]
        actions.append(
            {
                "priority": "P1",
                "title": f"放大 `{driver['dimension']}` 的高贡献打法",
                "impact": "高",
                "effort": "中",
                "rationale": driver["diagnosis"],
                "nextStep": f"围绕 `{driver['driver']}` 拆解产品、区域、客户或周期，沉淀可复制动作。",
            }
        )
    if benchmark_summary:
        actions.append(
            {
                "priority": "P1",
                "title": "建立经营基准线",
                "impact": "中",
                "effort": "低",
                "rationale": benchmark_summary[0]["diagnosis"],
                "nextStep": "把 Top3 占比、趋势波动率和环比阈值加入固定看板。",
            }
        )
    if business_type == "销售经营" and has_column_keyword(columns, ["客户", "用户"]):
        actions.append(
            {
                "priority": "P2",
                "title": "补齐客户分层运营",
                "impact": "中",
                "effort": "中",
                "rationale": "销售经营数据已具备客户维度，可进一步识别高价值、潜力和沉默客户。",
                "nextStep": f"以 `{primary_metric or '成交金额'}` 和最近成交时间构建 RFM/复购标签。",
            }
        )
    if not has_column_keyword(columns, ["成本", "费用", "投放", "预算"]):
        actions.append(
            {
                "priority": "P3",
                "title": "补充 ROI 必要字段",
                "impact": "中",
                "effort": "低",
                "rationale": "当前可看收入/成交，但无法判断投入产出效率。",
                "nextStep": "在导入模板中增加成本、投放费用、预算或人力投入字段。",
            }
        )
    return actions[:5]


def build_methodology_sections(methodology, benchmark_summary, driver_analysis, anomaly_diagnosis, significance_tests, priority_actions):
    def join_items(items, formatter, empty_text):
        return " ".join(formatter(item) for item in items) if items else empty_text

    return [
        {
            "title": "专属分析方法论",
            "content": join_items(
                methodology[:6],
                lambda item: f"【{item['name']}】适配度 {item['fit']}，回答“{item['question']}”，输出 {item['output']}。",
                "当前字段不足以匹配专项方法论，建议先确认主指标和核心维度。",
            ),
        },
        {
            "title": "归因诊断",
            "content": join_items(
                driver_analysis,
                lambda item: f"{item['diagnosis']} 假设：{item['hypothesis']}",
                "暂未发现足够稳定的维度差异，建议补充更明确的业务维度或更长周期数据。",
            ),
        },
        {
            "title": "对比基准",
            "content": join_items(
                benchmark_summary,
                lambda item: f"{item['name']} 为 {item['value']}；{item['baseline']} {item['diagnosis']}",
                "当前缺少可计算的结构或趋势基准，建议补充时间字段和可分组维度。",
            ),
        },
        {
            "title": "异常原因假设",
            "content": join_items(
                anomaly_diagnosis,
                lambda item: f"{item['finding']} 可能原因：{'、'.join(item['possibleCauses'])}。下一步：{item['nextCheck']}",
                "暂未识别异常周期，建议继续观察并设置固定阈值。",
            ),
        },
        {
            "title": "显著性与可信度",
            "content": join_items(
                significance_tests,
                lambda item: f"{item['name']} 使用 {item['method']}，{item['result']} 可信度：{item['confidence']}。{item['note']}",
                "当前样本或字段不足以做轻量显著性判断；建议补充分组字段、实验标签或更完整周期。",
            ),
        },
        {
            "title": "策略建议优先级",
            "content": join_items(
                priority_actions,
                lambda item: f"{item['priority']}【{item['title']}】影响 {item['impact']}、成本 {item['effort']}。依据：{item['rationale']} 下一步：{item['nextStep']}",
                "当前建议先完成主指标、核心维度和时间字段确认，再输出策略优先级。",
            ),
        },
    ]


def build_workspace_modules(business_type, data_profile=None, primary_metric=None, primary_dimension=None, date_columns=None):
    modules = [
        {"key": "overview", "label": "空间总览", "description": "数据画像、质量评分、推荐路径和方案库命中。"},
        {"key": "report", "label": "诊断报告", "description": "按现象、对比、异常、归因假设、行动建议组织报告。"},
        {"key": "dashboard", "label": "BI 看板", "description": "核心指标、图表推荐和交互式维度/指标切换。"},
        {"key": "metrics", "label": "指标体系", "description": "该业务空间专属指标口径、SQL 模板和字段映射。"},
    ]
    if primary_metric and date_columns:
        modules.append({"key": "anomaly", "label": "异常监控", "description": "环比、偏离均值和异常原因假设。"})
    if business_type in ["销售经营", "用户运营", "运营分析"]:
        modules.append({"key": "growth", "label": "增长分析", "description": "客户/用户/渠道分层、转化和复购分析。"})
    if business_type in ["销售经营", "财务经营", "运营分析"]:
        modules.append({"key": "finance", "label": "变现/ROI", "description": "收入、成本、预算、ROI 和投入产出分析。"})
    if business_type == "库存管理":
        modules.append({"key": "inventory", "label": "库存诊断", "description": "SKU 结构、周转效率、缺货风险和滞销风险。"})
    modules.append({"key": "export", "label": "导出与入库", "description": "报告下载、清洗质量和入库表信息。"})
    return modules


def build_diagnostic_story(insights, benchmark_summary, anomaly_diagnosis, driver_analysis, priority_actions, primary_metric):
    phenomenon = " ".join(insights) if insights else f"当前报告围绕 `{primary_metric or '核心指标'}` 建立诊断链路。"
    comparison = " ".join(f"{item['name']}：{item['value']}，{item['diagnosis']}" for item in benchmark_summary) if benchmark_summary else "暂缺稳定基准，建议补充时间字段或目标字段形成可对比口径。"
    anomaly = " ".join(item["finding"] for item in anomaly_diagnosis) if anomaly_diagnosis else "暂未发现高等级异常，当前重点应放在结构优化和口径确认。"
    attribution = " ".join(f"{item['diagnosis']} {item['hypothesis']}" for item in driver_analysis[:3]) if driver_analysis else "暂未形成稳定归因假设，建议增加业务维度或更长周期数据。"
    actions = " ".join(f"{item['priority']}：{item['title']}，{item['nextStep']}" for item in priority_actions[:4]) if priority_actions else "先确认主指标、核心维度和时间字段，再配置分析路径。"
    return [
        {"stage": "现象", "title": "先确认发生了什么", "content": phenomenon},
        {"stage": "对比", "title": "再看是否偏离基准", "content": comparison},
        {"stage": "异常", "title": "定位需要复盘的波动", "content": anomaly},
        {"stage": "归因假设", "title": "提出可验证原因", "content": attribution},
        {"stage": "行动建议", "title": "按优先级推进动作", "content": actions},
    ]


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

    return json_ready(
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


def write_workspace_report_markdown_file(job_id):
    report = build_workspace_report(job_id)
    lines = [f"# {report['workspaceName']} 分析报告", "", f"- 业务类型：{report['businessType']}", f"- 来源文件：{report['sourceFile']}", ""]
    if report.get("executiveSummary"):
        lines.extend(["## 重点结论", ""])
        for item in report["executiveSummary"]["highlights"]:
            lines.append(f"- {item['label']}：{item['title']}（{item['value']}）— {item['detail']}")
        lines.extend(["", "## 建议动作", ""])
        for action in report["executiveSummary"]["actions"]:
            lines.append(f"- {action}")
        lines.append("")
    for section in report["sections"]:
        lines.extend([f"## {section['title']}", "", section["content"], ""])
    if report.get("analysisPlan"):
        lines.extend(["## AI 分析方案", "", report["analysisPlan"]["focus"], ""])
        lines.append("### 启用模块")
        for module in report["analysisPlan"]["selectedModules"]:
            lines.append(f"- {module}")
        if report["analysisPlan"].get("methodology"):
            lines.extend(["", "### 专属方法论"])
            for item in report["analysisPlan"]["methodology"]:
                lines.append(f"- {item['name']}：适配度 {item['fit']}，回答“{item['question']}”，输出 {item['output']}")
        lines.extend(["", "### 推荐图表"])
        for chart in report["analysisPlan"]["chartPlan"]:
            lines.append(f"- {chart['title']}（{chart['type']}）：回答“{chart.get('businessQuestion', '业务问题')}”；{chart['reason']}")
        lines.append("")
    if report.get("driverAnalysis"):
        lines.extend(["## 归因诊断", ""])
        for item in report["driverAnalysis"]:
            lines.append(f"- {item['diagnosis']} 假设：{item['hypothesis']}")
        lines.append("")
    if report.get("benchmarkSummary"):
        lines.extend(["## 对比基准", ""])
        for item in report["benchmarkSummary"]:
            lines.append(f"- {item['name']}：{item['value']}。{item['baseline']} {item['diagnosis']}")
        lines.append("")
    if report.get("significanceTests"):
        lines.extend(["## 显著性与可信度", ""])
        for item in report["significanceTests"]:
            lines.append(f"- {item['name']}：{item['method']}，{item['result']} 可信度：{item['confidence']}。")
        lines.append("")
    if report.get("priorityActions"):
        lines.extend(["## 策略建议优先级", ""])
        for item in report["priorityActions"]:
            lines.append(f"- {item['priority']} {item['title']}：影响 {item['impact']}，成本 {item['effort']}。{item['nextStep']}")
        lines.append("")
    if report.get("metricCatalog"):
        lines.extend(["## 指标清单", ""])
        for item in report["metricCatalog"]:
            lines.append(f"- {item['name']}：`{item['formula']}`，当前值 {item['value']}，场景：{item['scene']}")
        lines.append("")
    if report.get("monitorItems"):
        lines.extend(["## 异常监控明细", ""])
        for item in report["monitorItems"]:
            lines.append(f"- {item['period']}：{item['metric']}={item['value']}，环比 {item['mom']}%，偏离 {item['deviation']}%，等级 {item['severity']}")
        lines.append("")
    if report.get("sqlTemplates"):
        lines.extend(["## SQL 模板", ""])
        for item in report["sqlTemplates"]:
            lines.extend([f"### {item['name']}", "", f"```sql\n{item['sql']}\n```", ""])
    output_file = EXPORT_DIR / f"workspace_report_{job_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    output_file.write_text("\n".join(lines), encoding="utf-8")
    return output_file


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


def write_report_markdown_file():
    report = build_report_data()["sections"]
    lines = ["# ChatBI 业务分析报告", ""]
    for index, section in enumerate(report, start=1):
        lines.extend([f"## {index}. {section['title']}", "", section["content"], ""])
    output_file = EXPORT_DIR / f"chatbi_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    output_file.write_text("\n".join(lines), encoding="utf-8")
    return output_file


def write_metrics_csv_file():
    output_file = EXPORT_DIR / f"chatbi_metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    pd.DataFrame(build_metric_definitions()).to_csv(output_file, index=False, encoding="utf-8-sig")
    return output_file


def write_dashboard_csv_file():
    dashboard = build_dashboard_data()
    rows = []
    for card in dashboard["summaryCards"]:
        rows.append({"section": "summary", **card})
    for item in dashboard["monthlySales"]:
        rows.append({"section": "monthly_sales", "label": item["month"], "value": item["sales"], "unit": "件", "note": ""})
    for item in dashboard["topProducts"]:
        rows.append({"section": "top_products", "label": item["product"], "value": item["totalSales"], "unit": "件", "note": ""})
    output_file = EXPORT_DIR / f"chatbi_dashboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    pd.DataFrame(rows).to_csv(output_file, index=False, encoding="utf-8-sig")
    return output_file


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
    return {
        "enabled": False,
        "positioning": "企业知识库增强模块，可用于接入指标口径、业务 SOP、数据字典和历史分析报告；当前默认不参与问答链路。",
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
