import json
import os
from collections import defaultdict
from contextlib import contextmanager
from pathlib import Path

try:
    from ..services.workspace_sql_scope import build_workspace_sql_scope, validate_workspace_sql_scope
except ImportError:
    from services.workspace_sql_scope import build_workspace_sql_scope, validate_workspace_sql_scope


DEFAULT_CASES_FILE = Path(__file__).resolve().parents[4] / "tests" / "fixtures" / "text2sql_cases.json"


def sample_workspace_context(imported=True):
    return {
        "workspaceId": "eval_sales_imported" if imported else "eval_sales_draft",
        "workspaceName": "销售评测空间" if imported else "未入库销售空间",
        "businessType": "销售经营",
        "sourceFile": "sales_eval.xlsx",
        "imported": imported,
        "dbTable": "import_sales" if imported else None,
        "schema": {
            "rowCount": 100,
            "columnCount": 3,
            "columns": ["日期", "销售额", "地区"],
            "fields": [
                {"name": "日期", "dtype": "object", "role": "time", "missingRate": 0},
                {"name": "销售额", "dtype": "float64", "role": "metric", "missingRate": 0},
                {"name": "地区", "dtype": "object", "role": "dimension", "missingRate": 0},
            ],
        },
    }


WORKSPACE_FIXTURES = {
    "imported_sales": sample_workspace_context(imported=True),
    "draft_sales": sample_workspace_context(imported=False),
}


@contextmanager
def suppress_eval_audit():
    previous = os.environ.get("CHATBI_AUDIT_ENABLED")
    os.environ["CHATBI_AUDIT_ENABLED"] = "false"
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop("CHATBI_AUDIT_ENABLED", None)
        else:
            os.environ["CHATBI_AUDIT_ENABLED"] = previous


def load_eval_cases(cases_file=None):
    path = Path(cases_file) if cases_file else DEFAULT_CASES_FILE
    return json.loads(path.read_text(encoding="utf-8"))


def evaluate_case(case):
    workspace = WORKSPACE_FIXTURES.get(case.get("workspace"), WORKSPACE_FIXTURES["imported_sales"])
    scope = build_workspace_sql_scope(workspace)
    with suppress_eval_audit():
        validation = validate_workspace_sql_scope(case.get("sql", ""), scope)
    actual_allowed = bool(validation.allowed)
    expect_allowed = bool(case.get("expectAllowed"))
    passed = actual_allowed is expect_allowed
    return {
        "id": case.get("id"),
        "category": case.get("category", "uncategorized"),
        "question": case.get("question"),
        "sql": case.get("sql"),
        "workspace": case.get("workspace"),
        "expectAllowed": expect_allowed,
        "actualAllowed": actual_allowed,
        "passed": passed,
        "reason": validation.reason or ("allowed" if actual_allowed else "blocked"),
        "tableReferences": list(validation.table_references),
        "columnReferences": list(validation.column_references),
    }


def run_text2sql_eval(cases_file=None):
    cases = load_eval_cases(cases_file)
    results = [evaluate_case(case) for case in cases]
    by_category = defaultdict(lambda: {"total": 0, "passed": 0, "failed": 0})
    for result in results:
        bucket = by_category[result["category"]]
        bucket["total"] += 1
        if result["passed"]:
            bucket["passed"] += 1
        else:
            bucket["failed"] += 1
    total = len(results)
    passed = sum(1 for result in results if result["passed"])
    return {
        "positioning": "规则层 Text-to-SQL 评测：验证只读 SQL、workspace 表范围、字段白名单和未入库拦截，不代表真实模型准确率。",
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "passRate": round(passed / total, 4) if total else 0,
        "categoryStats": dict(by_category),
        "cases": results,
    }
