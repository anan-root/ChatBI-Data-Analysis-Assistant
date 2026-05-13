import pandas as pd

try:
    from .import_cleaning import json_safe
except ImportError:
    from services.import_cleaning import json_safe


def has_column_keyword(columns, keywords):
    text = " ".join(str(column) for column in columns)
    return any(keyword in text for keyword in keywords)


def summarize_top_categories(df, category_column, metric_column=None, limit=5):
    if metric_column:
        grouped = df.groupby(category_column, dropna=False)[metric_column].sum().sort_values(ascending=False)
        return [
            {"name": json_safe(index), "value": round(float(value), 4)}
            for index, value in grouped.head(limit).items()
        ]
    counts = df[category_column].value_counts(dropna=False).head(limit)
    return [{"name": json_safe(index), "value": int(value)} for index, value in counts.items()]


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

