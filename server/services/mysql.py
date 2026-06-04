import os
import pymysql
from contextlib import contextmanager
from dotenv import load_dotenv

# Load the project .env explicitly so this helper works from any cwd.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
load_dotenv(os.path.join(PROJECT_ROOT, '.env'), override=True)

# 数据库配置，优先从环境变量读取
DB_CONFIG = {
    'host': os.environ.get('VOICE_DB_HOST', '115.190.210.249'),
    'port': int(os.environ.get('VOICE_DB_PORT', '3306')),
    'database': os.environ.get('VOICE_DB_NAME', 'video_script'),
    'user': os.environ.get('VOICE_DB_USER', 'root'),
    'password': os.environ.get('VOICE_DB_PASSWORD', ''),
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor,
}


@contextmanager
def get_connection():
    """获取数据库连接的上下文管理器。"""
    conn = pymysql.connect(**DB_CONFIG)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


@contextmanager
def get_cursor():
    """获取游标的上下文管理器。"""
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            yield cursor
        finally:
            cursor.close()
