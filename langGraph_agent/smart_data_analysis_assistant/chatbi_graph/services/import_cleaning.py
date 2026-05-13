import json
import re
import uuid
from datetime import date, datetime
from pathlib import Path

import pandas as pd

try:
    from ..config import CLEANED_DATA_DIR, METADATA_DIR, postgres_metadata_enabled
except ImportError:
    from config import CLEANED_DATA_DIR, METADATA_DIR, postgres_metadata_enabled


def _metadata_repository():
    try:
        from ..repositories import workspace_metadata
    except ImportError:
        from repositories import workspace_metadata
    return workspace_metadata


def upsert_import_metadata(metadata):
    return _metadata_repository().upsert_import_metadata(metadata)


def load_import_metadata(job_id):
    return _metadata_repository().load_import_metadata(job_id)


def list_import_metadata(limit=20):
    return _metadata_repository().list_import_metadata(limit)


def sync_metadata_to_postgres(metadata):
    if not postgres_metadata_enabled():
        return {"enabled": False, "synced": False}
    try:
        result = upsert_import_metadata(metadata)
        return {"enabled": True, "synced": True, **result}
    except Exception as exc:
        return {"enabled": True, "synced": False, "error": str(exc)}


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
    sync_result = sync_metadata_to_postgres(metadata)
    if sync_result.get("enabled"):
        metadata["postgresMetadata"] = sync_result
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
        if postgres_metadata_enabled():
            metadata = load_import_metadata(job_id)
            if metadata:
                return metadata
        raise FileNotFoundError("导入任务不存在。")
    return json.loads(metadata_file.read_text(encoding="utf-8"))


def save_import_job(metadata):
    metadata_file = METADATA_DIR / f"{metadata['jobId']}.json"
    metadata = json_ready(metadata)
    metadata_file.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    sync_result = sync_metadata_to_postgres(metadata)
    if sync_result.get("enabled"):
        metadata["postgresMetadata"] = sync_result
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
    if postgres_metadata_enabled():
        try:
            jobs = [public_import_job(metadata) for metadata in list_import_metadata(limit)]
            return {"jobs": jobs, "metadataStore": "postgres"}
        except Exception:
            pass
    jobs = []
    for metadata_file in sorted(METADATA_DIR.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
        jobs.append(public_import_job(json.loads(metadata_file.read_text(encoding="utf-8"))))
        if len(jobs) >= limit:
            break
    return {"jobs": jobs, "metadataStore": "file"}


def migrate_file_metadata_to_postgres(limit=None):
    migrated = []
    failed = []
    for index, metadata_file in enumerate(sorted(METADATA_DIR.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True)):
        if limit is not None and index >= limit:
            break
        try:
            metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
            result = upsert_import_metadata(metadata)
            migrated.append({"jobId": metadata.get("jobId"), **result})
        except Exception as exc:
            failed.append({"file": str(metadata_file), "error": str(exc)})
    return {
        "total": len(migrated) + len(failed),
        "migrated": len(migrated),
        "failed": len(failed),
        "results": migrated,
        "errors": failed,
    }
