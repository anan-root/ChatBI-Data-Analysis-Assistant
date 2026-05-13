from statistics import mean

import pandas as pd

try:
    from .analysis_utils import has_column_keyword, json_safe, pearson_correlation, safe_ratio
except ImportError:
    from services.analysis_utils import has_column_keyword, json_safe, pearson_correlation, safe_ratio


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

