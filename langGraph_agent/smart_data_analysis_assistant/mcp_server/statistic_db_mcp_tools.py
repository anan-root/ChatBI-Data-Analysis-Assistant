"""
TEXT2SQL 数据库查询MCP:
list_tables_tool:获取数据表结构信息工具
db_sql_tool:写SQL并执行SQL查询并返回数据库运算结果
pip install langchain_community
pip install mcp
pip install dotenv
"""

import sys
import os
# 添加当前项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from langchain_community.utilities import SQLDatabase
from mcp.server import FastMCP
from dotenv import load_dotenv
import os

load_dotenv()
QWEN_API_KEY = os.getenv("QWEN_API_KEY")
db_host = os.getenv("db_host", "127.0.0.1")
db_port = os.getenv("db_port", 5432)
user = os.getenv("user", "postgres")
password = os.getenv("password", "123456")
dbname = os.getenv("dbname", "sales_chat")


# %%
mcp = FastMCP(
    name="search_db_mcp", instructions="数据库查询MCP", host="0.0.0.0", port=9004
)
db = SQLDatabase.from_uri(
    f"postgresql://{user}:{password}@{db_host}:{db_port}/{dbname}"
)

# %%
def get_table_comments(db):
    """获取所有表及其字段的注释信息"""
    # 查询表注释和列注释
    query = """
    SELECT 
        t.table_name, 
        obj_description(('"' || t.table_schema || '"."' || t.table_name || '"')::regclass, 'pg_class') as table_comment,
        c.column_name, 
        c.data_type,
        pg_catalog.col_description(('"' || t.table_schema || '"."' || t.table_name || '"')::regclass::oid, c.ordinal_position) as column_comment
    FROM 
        information_schema.tables t
    JOIN 
        information_schema.columns c ON t.table_name = c.table_name AND t.table_schema = c.table_schema
    WHERE 
        t.table_schema NOT IN ('pg_catalog', 'information_schema')
        AND t.table_type = 'BASE TABLE'
    ORDER BY 
        t.table_name, c.ordinal_position
    """
    # 执行查询
    result = db._execute(query)
    # 组织结果
    tables = {}
    for row in result:
        print("row:", row)
        table_name = row.get("table_name", "")
        table_comment = row.get("table_comment", "") or "无表注释"
        column_name = row.get("column_name", "")
        data_type = row.get("data_type")
        column_comment = row.get("column_comment", "") or "无列注释"

        if table_name not in tables:
            tables[table_name] = {"comment": table_comment, "columns": []}
        tables[table_name]["columns"].append(
            {"name": column_name, "type": data_type, "comment": column_comment}
        )
    return tables


# tables=get_table_comments(db)
# print(tables) #RAG
# %%
@mcp.tool()
async def list_tables_tool() -> str:
    """
    输入是个空字符串, 返回数据库中的所有表及其结构信息，包括表和字段的注释
    :return: 数据库中的所有表及其结构信息的格式化字符串
    """
    tables = get_table_comments(db)
    result = []

    for table_name, table_info in tables.items():
        # 表信息
        table_str = f"表名: {table_name}"
        if table_info["comment"]:
            table_str += f" [注释: {table_info['comment']}]"

        # 列信息
        columns_str = []
        for column in table_info["columns"]:
            col_str = f"  - {column['name']} ({column['type']})"
            if column["comment"]:
                col_str += f" [注释: {column['comment']}]"
            columns_str.append(col_str)

        result.append(table_str + "\n" + "\n".join(columns_str))

    return "\n\n".join(result)


# async def main():
#     result=await list_tables_tool()
#     print(result)
# import asyncio
# asyncio.run(main())
# %%
@mcp.tool()
def db_sql_tool(query: str) -> str:
    """
    执行SQL查询并返回结果。如果查询不正确，将返回错误信息;如果返回错误，请重写查询语句，检查后重试。
    :param query: 非空的要执行的SQL查询语句
    :return:str: 查询结果或错误信息
    """
    # 利用的是关系型数据库查询SQL的内置方法
    result = db.run_no_throw(query)  # 执行查询（不抛出异常）
    if not result:
        return "错误: 查询失败。请修改查询语句后重试。"
    return result


if __name__ == "__main__":
    # 以标准 sse方式运行 MCP 服务器
    mcp.run(transport="sse")

# nohup python statistic_db_mcp_tools.py &
# nohup uv run statistic_db_mcp_tools.py &  -->官方更推荐这个方法
