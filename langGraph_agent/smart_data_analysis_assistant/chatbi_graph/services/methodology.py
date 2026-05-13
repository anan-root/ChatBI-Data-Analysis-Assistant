try:
    from .analysis_utils import has_column_keyword
    from .charts import build_chart_blueprints, build_chart_plan_from_blueprints
except ImportError:
    from services.analysis_utils import has_column_keyword
    from services.charts import build_chart_blueprints, build_chart_plan_from_blueprints


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

