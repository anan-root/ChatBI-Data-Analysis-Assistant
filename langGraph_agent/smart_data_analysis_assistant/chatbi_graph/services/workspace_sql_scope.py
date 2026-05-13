import re
from dataclasses import dataclass

try:
    from ...core.security import validate_readonly_sql
    from ...core.audit import audit_sql_decision
except ImportError:
    from core.security import validate_readonly_sql
    from core.audit import audit_sql_decision


IDENTIFIER_PATTERN = r'"[^"]+"|[\w\u4e00-\u9fff]+'
TABLE_REFERENCE_RE = re.compile(
    rf"\b(?:from|join)\s+((?:{IDENTIFIER_PATTERN}\s*\.\s*)?{IDENTIFIER_PATTERN})",
    flags=re.IGNORECASE,
)
TABLE_ALIAS_RE = re.compile(
    rf"\b(?:from|join)\s+((?:{IDENTIFIER_PATTERN}\s*\.\s*)?{IDENTIFIER_PATTERN})(?:\s+(?:as\s+)?({IDENTIFIER_PATTERN}))?",
    flags=re.IGNORECASE,
)
CTE_NAME_RE = re.compile(
    rf"(?:\bwith|,)\s*({IDENTIFIER_PATTERN})\s+as\s*\(",
    flags=re.IGNORECASE,
)
QUALIFIED_IDENTIFIER_RE = re.compile(
    rf"({IDENTIFIER_PATTERN})\s*\.\s*({IDENTIFIER_PATTERN}|\*)",
    flags=re.IGNORECASE,
)
QUOTED_IDENTIFIER_RE = re.compile(r'"([^"]+)"')
SELECT_STAR_RE = re.compile(r"\bselect\s+\*", flags=re.IGNORECASE)
SELECT_ALIAS_RE = re.compile(rf"\bas\s+({IDENTIFIER_PATTERN})", flags=re.IGNORECASE)
RESERVED_AFTER_TABLE = {
    "cross",
    "full",
    "group",
    "having",
    "inner",
    "join",
    "left",
    "limit",
    "offset",
    "on",
    "order",
    "right",
    "union",
    "where",
}


@dataclass(frozen=True)
class WorkspaceSqlValidationResult:
    allowed: bool
    query: str = ""
    reason: str = ""
    table_references: tuple[str, ...] = ()
    column_references: tuple[str, ...] = ()


def normalize_table_identifier(identifier):
    names = re.findall(IDENTIFIER_PATTERN, str(identifier or ""))
    if not names:
        return ""
    return names[-1].strip('"').strip().lower()


def extract_table_references(query):
    references = []
    for match in TABLE_REFERENCE_RE.finditer(query or ""):
        table_name = normalize_table_identifier(match.group(1))
        if table_name:
            references.append(table_name)
    return tuple(dict.fromkeys(references))


def extract_cte_names(query):
    cte_names = []
    for match in CTE_NAME_RE.finditer(query or ""):
        cte_name = normalize_table_identifier(match.group(1))
        if cte_name:
            cte_names.append(cte_name)
    return set(cte_names)


def extract_table_aliases(query):
    aliases = {}
    for match in TABLE_ALIAS_RE.finditer(query or ""):
        table_name = normalize_table_identifier(match.group(1))
        alias_name = normalize_table_identifier(match.group(2))
        if table_name and alias_name and alias_name not in RESERVED_AFTER_TABLE:
            aliases[alias_name] = table_name
    return aliases


def allowed_column_names(scope):
    columns = list(scope.get("columns") or [])
    for field in scope.get("fields") or []:
        field_name = field.get("name")
        if field_name:
            columns.append(field_name)
    return {
        normalize_table_identifier(column_name)
        for column_name in columns
        if normalize_table_identifier(column_name)
    }


def extract_select_aliases(query):
    aliases = []
    for match in SELECT_ALIAS_RE.finditer(query or ""):
        alias_name = normalize_table_identifier(match.group(1))
        if alias_name:
            aliases.append(alias_name)
    return set(aliases)


def extract_column_references(query, scope):
    allowed_tables = {
        normalize_table_identifier(table_name)
        for table_name in scope.get("allowedTables", [])
        if table_name
    }
    table_aliases = extract_table_aliases(query)
    relation_names = set(allowed_tables)
    relation_names.update(alias for alias, table in table_aliases.items() if table in allowed_tables)
    cte_names = extract_cte_names(query)
    query_aliases = extract_select_aliases(query) | set(table_aliases)
    allowed_columns = allowed_column_names(scope)

    references = []
    forbidden = []

    if not allowed_columns:
        return tuple(), tuple()

    if SELECT_STAR_RE.search(query or ""):
        forbidden.append("*")

    for match in QUALIFIED_IDENTIFIER_RE.finditer(query or ""):
        qualifier = normalize_table_identifier(match.group(1))
        column_name = "*" if match.group(2).strip() == "*" else normalize_table_identifier(match.group(2))
        if qualifier not in relation_names or qualifier in cte_names:
            continue
        if column_name == "*":
            forbidden.append("*")
            continue
        references.append(column_name)
        if column_name not in allowed_columns:
            forbidden.append(column_name)

    allowed_identifiers = allowed_columns | allowed_tables | relation_names | cte_names | query_aliases
    for match in QUOTED_IDENTIFIER_RE.finditer(query or ""):
        identifier = normalize_table_identifier(match.group(1))
        if not identifier or identifier in allowed_identifiers:
            if identifier in allowed_columns:
                references.append(identifier)
            continue
        references.append(identifier)
        forbidden.append(identifier)

    return tuple(dict.fromkeys(references)), tuple(dict.fromkeys(forbidden))


def build_workspace_sql_scope(workspace_context):
    if not workspace_context:
        return {"enabled": False, "allowedTables": []}
    schema = workspace_context.get("schema", {}) or {}
    db_table = workspace_context.get("dbTable")
    allowed_tables = [db_table] if db_table else []
    return {
        "enabled": True,
        "workspaceId": workspace_context.get("workspaceId"),
        "workspaceName": workspace_context.get("workspaceName"),
        "businessType": workspace_context.get("businessType"),
        "sourceFile": workspace_context.get("sourceFile"),
        "imported": bool(workspace_context.get("imported")),
        "dbTable": db_table,
        "allowedTables": allowed_tables,
        "allowedColumns": sorted(allowed_column_names({"columns": schema.get("columns", []) or [], "fields": schema.get("fields", []) or []})),
        "fields": schema.get("fields", []) or [],
        "columns": schema.get("columns", []) or [],
        "rowCount": schema.get("rowCount"),
        "columnCount": schema.get("columnCount"),
    }


def format_workspace_table_schema(scope):
    if not scope.get("enabled"):
        return ""
    fields = scope.get("fields") or []
    columns = scope.get("columns") or []
    field_lines = []
    for field in fields[:80]:
        name = field.get("name")
        dtype = field.get("dtype", "unknown")
        role = field.get("role", "unknown")
        missing_rate = field.get("missingRate")
        suffix = f", missingRate={missing_rate}" if missing_rate is not None else ""
        field_lines.append(f"  - {name} ({dtype}, role={role}{suffix})")
    if not field_lines:
        field_lines = [f"  - {column}" for column in columns[:80]]

    header = [
        "当前为企业 ChatBI 业务空间隔离模式。",
        f"业务空间: {scope.get('workspaceName') or scope.get('workspaceId')}",
        f"业务类型: {scope.get('businessType') or '未知'}",
        f"来源文件: {scope.get('sourceFile') or '未知'}",
        f"行列规模: {scope.get('rowCount') or 0} 行 / {scope.get('columnCount') or len(columns)} 列",
    ]
    if not scope.get("imported") or not scope.get("dbTable"):
        header.append("当前业务空间尚未确认入库，禁止调用 db_sql_tool 查询明细；只能基于 schema/profile/report 摘要回答。")
    else:
        header.append(f"允许查询表: \"{scope.get('dbTable')}\"")
        header.append("禁止查询其它业务空间、样例业务表、系统表或元数据表；禁止使用 SELECT *，只能查询字段画像中列出的字段。")
    return "\n".join([*header, "字段画像:", *field_lines])


def build_workspace_sql_policy_text(workspace_context):
    scope = build_workspace_sql_scope(workspace_context)
    if not scope.get("enabled"):
        return ""
    if not scope.get("imported") or not scope.get("dbTable"):
        return (
            "SQL_POLICY: 当前业务空间尚未确认入库，禁止调用 db_sql_tool；"
            "如需明细查询，请先提示用户在导入清洗模块确认入库。"
        )
    table_name = scope.get("dbTable")
    return (
        f'SQL_POLICY: 当前请求只能查询业务空间表 "{table_name}"。'
        "生成 SQL 时必须显式 FROM/JOIN 该表，禁止访问其它业务空间、样例表、系统表和元数据表；"
        "禁止 SELECT *，只能使用当前业务空间字段画像里列出的字段。"
    )


def validate_workspace_sql_scope(query, scope):
    safety = validate_readonly_sql(query)
    if not safety.allowed:
        audit_sql_decision(
            source="workspace_sql_scope",
            allowed=False,
            query=query,
            reason=safety.reason,
            workspace_id=scope.get("workspaceId") if scope else None,
            workspace_name=scope.get("workspaceName") if scope else None,
        )
        return WorkspaceSqlValidationResult(False, reason=safety.reason)
    if not scope.get("enabled"):
        audit_sql_decision(
            source="workspace_sql_scope",
            allowed=True,
            query=safety.query,
            reason="workspace scope disabled",
        )
        return WorkspaceSqlValidationResult(True, query=safety.query)
    if not scope.get("imported") or not scope.get("dbTable"):
        audit_sql_decision(
            source="workspace_sql_scope",
            allowed=False,
            query=safety.query,
            reason="当前业务空间尚未确认入库，不能执行数据库明细查询。",
            workspace_id=scope.get("workspaceId"),
            workspace_name=scope.get("workspaceName"),
        )
        return WorkspaceSqlValidationResult(
            False,
            reason="当前业务空间尚未确认入库，不能执行数据库明细查询。",
        )

    allowed_tables = {
        normalize_table_identifier(table_name)
        for table_name in scope.get("allowedTables", [])
        if table_name
    }
    table_references = extract_table_references(safety.query)
    cte_names = extract_cte_names(safety.query)
    external_references = tuple(
        table_name for table_name in table_references if table_name not in cte_names
    )
    if not external_references:
        audit_sql_decision(
            source="workspace_sql_scope",
            allowed=False,
            query=safety.query,
            reason="SQL 必须显式查询当前业务空间的数据表。",
            workspace_id=scope.get("workspaceId"),
            workspace_name=scope.get("workspaceName"),
            table_references=table_references,
        )
        return WorkspaceSqlValidationResult(
            False,
            reason="SQL 必须显式查询当前业务空间的数据表。",
            table_references=table_references,
        )
    forbidden_tables = [table_name for table_name in external_references if table_name not in allowed_tables]
    if forbidden_tables:
        audit_sql_decision(
            source="workspace_sql_scope",
            allowed=False,
            query=safety.query,
            reason=f"检测到越权表引用: {', '.join(forbidden_tables)}；仅允许查询当前业务空间表。",
            workspace_id=scope.get("workspaceId"),
            workspace_name=scope.get("workspaceName"),
            table_references=table_references,
        )
        return WorkspaceSqlValidationResult(
            False,
            reason=f"检测到越权表引用: {', '.join(forbidden_tables)}；仅允许查询当前业务空间表。",
            table_references=table_references,
        )
    column_references, forbidden_columns = extract_column_references(safety.query, scope)
    if forbidden_columns:
        reason = f"检测到越权字段引用: {', '.join(forbidden_columns)}；仅允许查询当前业务空间字段画像中的字段。"
        audit_sql_decision(
            source="workspace_sql_scope",
            allowed=False,
            query=safety.query,
            reason=reason,
            workspace_id=scope.get("workspaceId"),
            workspace_name=scope.get("workspaceName"),
            table_references=table_references,
        )
        return WorkspaceSqlValidationResult(
            False,
            reason=reason,
            table_references=table_references,
            column_references=column_references,
        )
    audit_sql_decision(
        source="workspace_sql_scope",
        allowed=True,
        query=safety.query,
        reason="workspace table and column scope allowed",
        workspace_id=scope.get("workspaceId"),
        workspace_name=scope.get("workspaceName"),
        table_references=table_references,
    )
    return WorkspaceSqlValidationResult(
        True,
        query=safety.query,
        table_references=table_references,
        column_references=column_references,
    )
