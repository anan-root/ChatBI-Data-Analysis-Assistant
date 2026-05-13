import ast
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_ALLOWED_ORIGINS = ("http://127.0.0.1:5173", "http://localhost:5173")
DANGEROUS_SQL_KEYWORDS = {
    "ALTER",
    "CALL",
    "COMMENT",
    "COPY",
    "CREATE",
    "DELETE",
    "DO",
    "DROP",
    "EXEC",
    "EXECUTE",
    "GRANT",
    "INSERT",
    "MERGE",
    "REINDEX",
    "REVOKE",
    "TRUNCATE",
    "UPDATE",
    "VACUUM",
}
READONLY_SQL_STARTERS = {"SELECT", "WITH", "EXPLAIN"}
DEFAULT_SQL_MAX_ROWS = 200
DEFAULT_SQL_TIMEOUT_MS = 5000
PYTHON_EXEC_ENV = "CHATBI_ENABLE_PYTHON_EXEC"
PYTHON_ALLOWED_MODULES = {
    "collections",
    "datetime",
    "decimal",
    "itertools",
    "json",
    "math",
    "matplotlib",
    "matplotlib.pyplot",
    "numpy",
    "pandas",
    "statistics",
}
PYTHON_BLOCKED_CALLS = {
    "__import__",
    "breakpoint",
    "compile",
    "eval",
    "exec",
    "globals",
    "input",
    "locals",
    "open",
    "vars",
}
PYTHON_BLOCKED_MODULE_ROOTS = {
    "builtins",
    "ctypes",
    "multiprocessing",
    "os",
    "pathlib",
    "pickle",
    "shutil",
    "socket",
    "subprocess",
    "sys",
}


@dataclass(frozen=True)
class SqlSafetyResult:
    allowed: bool
    query: str = ""
    reason: str = ""


@dataclass(frozen=True)
class PythonSandboxResult:
    ok: bool
    stdout: str = ""
    stderr: str = ""
    images: tuple[str, ...] = ()
    reason: str = ""


def parse_cors_origins(raw_value: str | None) -> list[str]:
    if not raw_value:
        return list(DEFAULT_ALLOWED_ORIGINS)
    origins = [origin.strip() for origin in raw_value.split(",") if origin.strip()]
    if not origins or "*" in origins:
        return list(DEFAULT_ALLOWED_ORIGINS)
    return origins


def get_int_env(name: str, default: int, minimum: int | None = None, maximum: int | None = None) -> int:
    raw_value = os.getenv(name)
    try:
        value = int(raw_value) if raw_value is not None else default
    except ValueError:
        value = default
    if minimum is not None:
        value = max(minimum, value)
    if maximum is not None:
        value = min(maximum, value)
    return value


def strip_sql_comments(query: str) -> str:
    without_block_comments = re.sub(r"/\*.*?\*/", " ", query, flags=re.DOTALL)
    return re.sub(r"--.*?(?=\n|$)", " ", without_block_comments)


def normalize_sql(query: str) -> str:
    return re.sub(r"\s+", " ", strip_sql_comments(query)).strip()


def _remove_trailing_semicolon(query: str) -> str:
    return query[:-1].strip() if query.endswith(";") else query


def _has_multiple_statements(query: str) -> bool:
    return ";" in _remove_trailing_semicolon(query)


def validate_readonly_sql(query: str) -> SqlSafetyResult:
    normalized = normalize_sql(query)
    if not normalized:
        return SqlSafetyResult(False, reason="SQL 不能为空")
    if _has_multiple_statements(normalized):
        return SqlSafetyResult(False, reason="只允许单条只读 SQL")

    first_token_match = re.match(r"^[A-Za-z]+", normalized)
    first_token = first_token_match.group(0).upper() if first_token_match else ""
    if first_token not in READONLY_SQL_STARTERS:
        return SqlSafetyResult(False, reason="只允许 SELECT / WITH / EXPLAIN 查询")

    tokens = {token.upper() for token in re.findall(r"\b[A-Za-z_]+\b", normalized)}
    dangerous = sorted(tokens & DANGEROUS_SQL_KEYWORDS)
    if dangerous:
        return SqlSafetyResult(False, reason=f"检测到危险 SQL 关键字: {', '.join(dangerous)}")

    return SqlSafetyResult(True, query=_remove_trailing_semicolon(normalized))


def enforce_select_limit(query: str, max_rows: int = DEFAULT_SQL_MAX_ROWS) -> str:
    normalized = _remove_trailing_semicolon(normalize_sql(query))
    if re.search(r"\blimit\s+\d+\b", normalized, flags=re.IGNORECASE):
        return normalized
    if re.match(r"^explain\b", normalized, flags=re.IGNORECASE):
        return normalized
    return f"{normalized} LIMIT {max_rows}"


def build_statement_timeout_sql(timeout_ms: int = DEFAULT_SQL_TIMEOUT_MS) -> str:
    timeout = max(100, int(timeout_ms))
    return f"SET LOCAL statement_timeout = {timeout}"


def is_python_execution_enabled() -> bool:
    return os.getenv(PYTHON_EXEC_ENV, "false").strip().lower() in {"1", "true", "yes", "on"}


def safe_parse_sequence(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return ast.literal_eval(value)


def _attribute_root(node: ast.AST) -> str | None:
    current = node
    while isinstance(current, ast.Attribute):
        current = current.value
    if isinstance(current, ast.Name):
        return current.id
    return None


def validate_python_script(script_content: str) -> tuple[bool, str]:
    if len(script_content) > 12000:
        return False, "Python 脚本过长，已拒绝执行"
    try:
        tree = ast.parse(script_content)
    except SyntaxError as exc:
        return False, f"Python 语法错误: {exc}"

    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [alias.name for alias in node.names]
            if isinstance(node, ast.ImportFrom) and node.module:
                names.append(node.module)
            for name in names:
                if name not in PYTHON_ALLOWED_MODULES and name.split(".")[0] not in PYTHON_ALLOWED_MODULES:
                    return False, f"模块 {name} 不在允许列表中"
        elif isinstance(node, ast.Call):
            function = node.func
            if isinstance(function, ast.Name) and function.id in PYTHON_BLOCKED_CALLS:
                return False, f"调用 {function.id} 存在安全风险"
            root = _attribute_root(function)
            if root in PYTHON_BLOCKED_MODULE_ROOTS:
                return False, f"调用 {root} 模块能力存在安全风险"
        elif isinstance(node, ast.Name):
            if node.id.startswith("__") and node.id.endswith("__"):
                return False, f"访问 {node.id} 存在安全风险"
        elif isinstance(node, ast.Attribute):
            if node.attr.startswith("__") and node.attr.endswith("__"):
                return False, f"访问 {node.attr} 存在安全风险"
    return True, ""


def python_script_uses_matplotlib(script_content: str) -> bool:
    try:
        tree = ast.parse(script_content)
    except SyntaxError:
        return False
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [alias.name for alias in node.names]
            if isinstance(node, ast.ImportFrom) and node.module:
                names.append(node.module)
            if any(name == "matplotlib" or name.startswith("matplotlib.") for name in names):
                return True
    return False


def run_python_script_in_sandbox(
    script_content: str,
    output_dir: Path,
    timeout_seconds: int = 5,
) -> PythonSandboxResult:
    valid, reason = validate_python_script(script_content)
    if not valid:
        return PythonSandboxResult(False, reason=reason)

    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="chatbi_py_") as temp_dir:
        temp_path = Path(temp_dir)
        script_path = temp_path / "script.py"
        image_capture_script = ""
        if python_script_uses_matplotlib(script_content):
            image_capture_script = f"""
try:
    import matplotlib.pyplot as plt
    output_dir = {str(output_dir.resolve())!r}
    import os
    os.makedirs(output_dir, exist_ok=True)
    for figure_number in plt.get_fignums():
        figure = plt.figure(figure_number)
        image_path = os.path.join(output_dir, f"sandbox_{{figure_number}}_{{os.getpid()}}.png")
        figure.savefig(image_path, format="png", bbox_inches="tight")
        print(f"CHATBI_IMAGE::{{image_path}}")
    plt.close("all")
except Exception as image_error:
    print(f"CHATBI_IMAGE_ERROR::{{image_error}}")
"""
        safe_script = f"{script_content}\n{image_capture_script}"
        script_path.write_text(safe_script, encoding="utf-8")
        env = {
            "HOME": os.getenv("HOME", str(Path.home())),
            "USERPROFILE": os.getenv("USERPROFILE", str(Path.home())),
            "TEMP": os.getenv("TEMP", str(temp_path)),
            "TMP": os.getenv("TMP", str(temp_path)),
            "MPLBACKEND": "Agg",
            "PYTHONIOENCODING": "utf-8",
            "PATH": os.getenv("PATH", ""),
            "SYSTEMROOT": os.getenv("SYSTEMROOT", ""),
            "WINDIR": os.getenv("WINDIR", ""),
        }
        python_path = os.getenv("PYTHONPATH")
        if python_path:
            env["PYTHONPATH"] = python_path
        try:
            completed = subprocess.run(
                [sys.executable, str(script_path)],
                cwd=str(temp_path),
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return PythonSandboxResult(False, reason=f"Python 沙箱执行超过 {timeout_seconds} 秒，已终止")

    images: list[str] = []
    stdout_lines: list[str] = []
    for line in completed.stdout.splitlines():
        if line.startswith("CHATBI_IMAGE::"):
            image_path = line.replace("CHATBI_IMAGE::", "", 1).strip()
            if image_path:
                images.append(image_path)
        else:
            stdout_lines.append(line)
    if completed.returncode != 0:
        return PythonSandboxResult(
            False,
            stdout="\n".join(stdout_lines),
            stderr=completed.stderr.strip(),
            images=tuple(images),
            reason="Python 沙箱执行失败",
        )
    return PythonSandboxResult(
        True,
        stdout="\n".join(stdout_lines).strip(),
        stderr=completed.stderr.strip(),
        images=tuple(images),
    )


def remove_directory_if_exists(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
