"""Database repository helpers for ChatBI."""

import os


def get_connection():
    try:
        import psycopg2
    except ImportError as exc:
        raise RuntimeError("缺少 psycopg2，无法连接 PostgreSQL。请先安装 requirements.txt。") from exc

    db_password = os.getenv("password")
    if not db_password:
        raise RuntimeError("数据库密码未配置，请在 .env 中设置 password，禁止使用默认弱密码。")
    return psycopg2.connect(
        host=os.getenv("db_host", "127.0.0.1"),
        port=os.getenv("db_port", "5432"),
        user=os.getenv("user", "postgres"),
        password=db_password,
        dbname=os.getenv("dbname", "sales_chat"),
    )


def fetch_all(sql, params=None):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql, params or ())
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
