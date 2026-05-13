
import pandas as pd


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

