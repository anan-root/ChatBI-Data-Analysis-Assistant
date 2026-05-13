from datetime import datetime

import pandas as pd

try:
    from ..config import EXPORT_DIR
except ImportError:
    from config import EXPORT_DIR


def write_workspace_report_markdown_file(job_id, build_workspace_report):
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

def write_report_markdown_file(build_report_data):
    report = build_report_data()["sections"]
    lines = ["# ChatBI 业务分析报告", ""]
    for index, section in enumerate(report, start=1):
        lines.extend([f"## {index}. {section['title']}", "", section["content"], ""])
    output_file = EXPORT_DIR / f"chatbi_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    output_file.write_text("\n".join(lines), encoding="utf-8")
    return output_file

def write_metrics_csv_file(build_metric_definitions):
    output_file = EXPORT_DIR / f"chatbi_metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    pd.DataFrame(build_metric_definitions()).to_csv(output_file, index=False, encoding="utf-8-sig")
    return output_file

def write_dashboard_csv_file(build_dashboard_data):
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

