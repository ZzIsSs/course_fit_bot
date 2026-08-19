"""PostgreSQL database connection manager (Supabase).

Quản lý kết nối đến Supabase PostgreSQL.
Cung cấp context manager và các hàm tiện ích cho truy vấn.
"""
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager


@contextmanager
def get_db(database_url):
    """Context manager cho một phiên làm việc với database.

    Tự động commit khi thành công, rollback khi có lỗi.

    Usage:
        with get_db(database_url) as conn:
            result = fetch_one(conn, "SELECT 1")
    """
    conn = None
    try:
        conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
        yield conn
        conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        logging.error(f"Database error: {e}")
        raise
    finally:
        if conn:
            conn.close()


def execute(conn, sql, params=None):
    """Thực thi câu SQL (INSERT, UPDATE, DELETE).

    Returns:
        Số dòng bị ảnh hưởng.
    """
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.rowcount


def fetch_one(conn, sql, params=None):
    """Thực thi câu SQL và trả về 1 dòng kết quả (dict).

    Returns:
        Dict chứa kết quả, hoặc None nếu không có.
    """
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchone()


def fetch_all(conn, sql, params=None):
    """Thực thi câu SQL và trả về tất cả dòng kết quả.

    Returns:
        List[dict] kết quả, hoặc list rỗng.
    """
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()
