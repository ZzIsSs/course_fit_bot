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
    Đảm bảo an toàn cho Serverless với connect_timeout=5.

    Usage:
        with get_db(database_url) as conn:
            result = fetch_one(conn, "SELECT 1")
    """
    if not database_url:
        raise ValueError("DATABASE_URL chưa được cấu hình hoặc rỗng.")

    conn = None
    try:
        conn = psycopg2.connect(
            database_url,
            cursor_factory=RealDictCursor,
            connect_timeout=5
        )
        yield conn
        conn.commit()
    except Exception as e:
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
        logging.error(f"Database error: {e}")
        raise
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


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
