from statistics import mean

import pandas as pd

try:
    from .import_cleaning import json_safe
except ImportError:
    from services.import_cleaning import json_safe


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

