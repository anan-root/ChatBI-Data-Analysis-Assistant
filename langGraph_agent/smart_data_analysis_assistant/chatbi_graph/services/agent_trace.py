import json
import re
import uuid


BLOCKED_PATTERNS = ("未通过", "拒绝", "禁止", "越权", "危险", "尚未确认入库", "错误")


def new_trace_id(prefix="chat"):
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def workspace_summary(workspace_context):
    if not workspace_context:
        return None
    return {
        "workspaceId": workspace_context.get("workspaceId") or workspace_context.get("jobId"),
        "workspaceName": workspace_context.get("workspaceName") or workspace_context.get("name"),
        "businessType": workspace_context.get("businessType"),
    }


def infer_intent_from_route(route_result):
    if route_result == "业务数据查询分析":
        return "data_query"
    if route_result == "纯python编码":
        return "python"
    if route_result:
        return "chat"
    return "unknown"


def compact_text(value, limit=240):
    if value is None:
        return ""
    if isinstance(value, (dict, list, tuple)):
        text = json.dumps(value, ensure_ascii=False, default=str)
    else:
        text = str(value)
    text = re.sub(r"\s+", " ", text).strip()
    return f"{text[:limit]}..." if len(text) > limit else text


def extract_tool_calls(message):
    calls = getattr(message, "tool_calls", None) or []
    extracted = []
    for index, call in enumerate(calls):
        args = call.get("args") if isinstance(call, dict) else getattr(call, "args", {})
        name = call.get("name") if isinstance(call, dict) else getattr(call, "name", "")
        extracted.append(
            {
                "name": name or "unknown_tool",
                "args": args or {},
                "id": call.get("id", f"tool_{index}") if isinstance(call, dict) else getattr(call, "id", f"tool_{index}"),
            }
        )
    return extracted


def sql_from_args(args):
    if not isinstance(args, dict):
        return ""
    for key in ("query", "sql", "statement"):
        value = args.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def status_from_text(text):
    return "blocked" if any(pattern in text for pattern in BLOCKED_PATTERNS) else "ok"


def step_from_ai_message(message, node="LangGraph"):
    tool_calls = extract_tool_calls(message)
    if tool_calls:
        steps = []
        for call in tool_calls:
            sql = sql_from_args(call["args"])
            steps.append(
                {
                    "stage": "tool_plan",
                    "node": node,
                    "toolName": call["name"],
                    "status": "ok",
                    "summary": f"计划调用工具 {call['name']}",
                    "sql": sql,
                    "reason": "",
                }
            )
        return steps
    content = compact_text(getattr(message, "content", ""))
    if not content:
        return []
    return [
        {
            "stage": "answer",
            "node": node,
            "toolName": "",
            "status": "ok",
            "summary": content,
            "sql": "",
            "reason": "",
        }
    ]


def step_from_tool_message(message, get_message_text, node="LangGraph"):
    text = compact_text(get_message_text(message))
    tool_name = getattr(message, "name", "") or "tool_result"
    status = status_from_text(text)
    return {
        "stage": "tool_result",
        "node": node,
        "toolName": tool_name,
        "status": status,
        "summary": text,
        "sql": extract_sql_from_text(text),
        "reason": text if status == "blocked" else "",
    }


def extract_sql_from_text(text):
    if not text:
        return ""
    match = re.search(r"\b(?:select|with|explain)\b.+", text, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return ""
    return compact_text(match.group(0), limit=500)


def build_trace(trace_id, intent, workspace_context, steps):
    return {
        "traceId": trace_id,
        "intent": intent or "unknown",
        "workspace": workspace_summary(workspace_context),
        "steps": steps,
    }


def fields_from_workspace(workspace_context, limit=12):
    schema = (workspace_context or {}).get("schema") or {}
    fields = []
    for field in schema.get("fields") or []:
        name = field.get("name")
        if name:
            fields.append(name)
    if not fields:
        fields.extend(schema.get("columns") or [])
    return fields[:limit]


def sql_evidence_from_steps(steps):
    results = []
    seen = set()
    for step in steps:
        query = step.get("sql")
        if not query or query in seen:
            continue
        seen.add(query)
        results.append(
            {
                "query": query,
                "allowed": step.get("status") != "blocked",
                "reason": step.get("reason") or step.get("summary") or "",
            }
        )
    return results


def build_evidence(workspace_context, steps, knowledge=None):
    summary = workspace_summary(workspace_context) or {}
    return {
        "workspaceId": summary.get("workspaceId"),
        "workspaceName": summary.get("workspaceName"),
        "fields": fields_from_workspace(workspace_context),
        "sql": sql_evidence_from_steps(steps),
        "knowledge": list(knowledge or []),
    }
