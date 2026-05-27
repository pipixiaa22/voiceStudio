#!/usr/bin/env python3
"""SQLite to MySQL migration script.

Migrates business tables from data.db to MySQL while preserving existing voice_profiles tables.

Usage:
    MYSQL_PASSWORD='your_password' uv run python scripts/migrate_sqlite_to_mysql.py

Environment variables:
    SQLITE_PATH: Path to SQLite database (default: data.db)
    MYSQL_HOST: MySQL host (default: 115.190.210.249)
    MYSQL_PORT: MySQL port (default: 3306)
    MYSQL_USER: MySQL user (default: root)
    MYSQL_PASSWORD: MySQL password (required)
    MYSQL_DATABASE: MySQL database (default: video_script)
"""

import os
import sqlite3
import sys

import pymysql
from dotenv import load_dotenv

load_dotenv()

SQLITE_PATH = os.environ.get('SQLITE_PATH', 'data.db')
MYSQL_CONFIG = {
    'host': os.environ.get('MYSQL_HOST', '115.190.210.249'),
    'port': int(os.environ.get('MYSQL_PORT', '3306')),
    'user': os.environ.get('MYSQL_USER', 'root'),
    'password': os.environ.get('MYSQL_PASSWORD', ''),
    'database': os.environ.get('MYSQL_DATABASE', 'video_script'),
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor,
}

# Tables to migrate (in order for foreign key constraints)
TABLES = [
    'folders',
    'tags',
    'texts',
    'text_tags',
    'video_templates',
    'video_jobs',
    'video_assets',
]

# MySQL CREATE TABLE statements
CREATE_TABLES = {
    'folders': """
        CREATE TABLE IF NOT EXISTS folders (
            id INT NOT NULL AUTO_INCREMENT,
            name VARCHAR(100) NOT NULL,
            parent_id INT NULL,
            created_at DATETIME NULL,
            PRIMARY KEY (id),
            KEY idx_folders_parent_id (parent_id),
            CONSTRAINT fk_folders_parent
                FOREIGN KEY (parent_id) REFERENCES folders(id)
                ON DELETE SET NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    'tags': """
        CREATE TABLE IF NOT EXISTS tags (
            id INT NOT NULL AUTO_INCREMENT,
            name VARCHAR(50) NOT NULL,
            PRIMARY KEY (id),
            UNIQUE KEY uk_tags_name (name)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    'texts': """
        CREATE TABLE IF NOT EXISTS texts (
            id INT NOT NULL AUTO_INCREMENT,
            title VARCHAR(200) NOT NULL DEFAULT '未命名',
            content TEXT NOT NULL,
            folder_id INT NULL,
            created_at DATETIME NULL,
            updated_at DATETIME NULL,
            PRIMARY KEY (id),
            KEY idx_texts_folder_id (folder_id),
            KEY idx_texts_created_at (created_at),
            KEY idx_texts_updated_at (updated_at),
            CONSTRAINT fk_texts_folder
                FOREIGN KEY (folder_id) REFERENCES folders(id)
                ON DELETE SET NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    'text_tags': """
        CREATE TABLE IF NOT EXISTS text_tags (
            text_id INT NOT NULL,
            tag_id INT NOT NULL,
            PRIMARY KEY (text_id, tag_id),
            KEY idx_text_tags_tag_id (tag_id),
            CONSTRAINT fk_text_tags_text
                FOREIGN KEY (text_id) REFERENCES texts(id)
                ON DELETE CASCADE,
            CONSTRAINT fk_text_tags_tag
                FOREIGN KEY (tag_id) REFERENCES tags(id)
                ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    'video_templates': """
        CREATE TABLE IF NOT EXISTS video_templates (
            id INT NOT NULL AUTO_INCREMENT,
            template_key VARCHAR(50) NOT NULL,
            name VARCHAR(100) NOT NULL,
            config_json TEXT NOT NULL,
            is_builtin TINYINT(1) NOT NULL DEFAULT 0,
            is_active TINYINT(1) NOT NULL DEFAULT 1,
            sort_order INT NOT NULL DEFAULT 0,
            created_at DATETIME NULL,
            updated_at DATETIME NULL,
            PRIMARY KEY (id),
            UNIQUE KEY uk_video_templates_template_key (template_key),
            KEY idx_video_templates_active_order (is_active, sort_order)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    'video_jobs': """
        CREATE TABLE IF NOT EXISTS video_jobs (
            id INT NOT NULL AUTO_INCREMENT,
            job_id VARCHAR(36) NOT NULL,
            title VARCHAR(200) NOT NULL DEFAULT '未命名',
            status VARCHAR(20) NOT NULL DEFAULT 'queued',
            progress FLOAT DEFAULT 0,
            stage VARCHAR(50) NULL,
            message VARCHAR(500) NULL,
            request_json TEXT NOT NULL,
            manifest_json TEXT NULL,
            output_path VARCHAR(500) NULL,
            video_path VARCHAR(500) NULL,
            error_message TEXT NULL,
            created_at DATETIME NULL,
            updated_at DATETIME NULL,
            PRIMARY KEY (id),
            UNIQUE KEY uk_video_jobs_job_id (job_id),
            KEY idx_video_jobs_status (status),
            KEY idx_video_jobs_created_at (created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    'video_assets': """
        CREATE TABLE IF NOT EXISTS video_assets (
            id INT NOT NULL AUTO_INCREMENT,
            job_id VARCHAR(36) NOT NULL,
            asset_type VARCHAR(50) NOT NULL,
            filename VARCHAR(200) NOT NULL,
            path VARCHAR(500) NOT NULL,
            metadata_json TEXT NULL,
            created_at DATETIME NULL,
            PRIMARY KEY (id),
            KEY idx_video_assets_job_id (job_id),
            KEY idx_video_assets_type (asset_type)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
}


def get_sqlite_rows(sqlite_cur, table):
    """Fetch all rows from a SQLite table."""
    sqlite_cur.execute(f'SELECT * FROM {table}')
    columns = [desc[0] for desc in sqlite_cur.description]
    for row in sqlite_cur.fetchall():
        yield dict(zip(columns, row))


def insert_mysql_rows(mysql_cur, table, items):
    """Insert rows into MySQL table."""
    items = list(items)
    if not items:
        return 0

    columns = list(items[0].keys())

    # Handle missing video_path column in old SQLite databases
    if table == 'video_jobs' and 'video_path' not in columns:
        columns.append('video_path')
        for item in items:
            item['video_path'] = None

    placeholders = ', '.join(['%s'] * len(columns))
    column_sql = ', '.join(f'`{col}`' for col in columns)
    sql = f'INSERT INTO `{table}` ({column_sql}) VALUES ({placeholders})'
    values = [tuple(item.get(col) for col in columns) for item in items]
    mysql_cur.executemany(sql, values)
    return len(items)


def reset_auto_increment(mysql_cur, table):
    """Reset auto_increment to next available ID."""
    mysql_cur.execute(f'SELECT COALESCE(MAX(id), 0) + 1 AS next_id FROM `{table}`')
    next_id = mysql_cur.fetchone()['next_id']
    mysql_cur.execute(f'ALTER TABLE `{table}` AUTO_INCREMENT = {next_id}')


def create_tables(mysql_cur):
    """Create MySQL tables if they don't exist."""
    for table, ddl in CREATE_TABLES.items():
        print(f'  Creating table {table}...')
        mysql_cur.execute(ddl)


def main():
    if not MYSQL_CONFIG['password']:
        print('Error: MYSQL_PASSWORD environment variable is required')
        sys.exit(1)

    print(f'SQLite: {SQLITE_PATH}')
    print(f'MySQL: {MYSQL_CONFIG["host"]}:{MYSQL_CONFIG["port"]}/{MYSQL_CONFIG["database"]}')
    print()

    # Connect to SQLite
    if not os.path.exists(SQLITE_PATH):
        print(f'Error: SQLite database not found: {SQLITE_PATH}')
        sys.exit(1)

    sqlite_conn = sqlite3.connect(SQLITE_PATH)
    sqlite_cur = sqlite_conn.cursor()

    # Record SQLite counts
    print('SQLite table counts:')
    sqlite_counts = {}
    for table in TABLES:
        try:
            sqlite_cur.execute(f'SELECT COUNT(*) FROM {table}')
            count = sqlite_cur.fetchone()[0]
            sqlite_counts[table] = count
            print(f'  {table}: {count}')
        except Exception as e:
            print(f'  {table}: ERROR - {e}')
            sqlite_counts[table] = 0
    print()

    # Connect to MySQL
    try:
        mysql_conn = pymysql.connect(**MYSQL_CONFIG)
    except Exception as e:
        print(f'Error connecting to MySQL: {e}')
        sys.exit(1)

    try:
        with mysql_conn.cursor() as mysql_cur:
            # Create tables
            print('Creating MySQL tables...')
            create_tables(mysql_cur)
            print()

            # Disable foreign key checks for migration
            mysql_cur.execute('SET FOREIGN_KEY_CHECKS=0')

            # Truncate tables (in reverse order for foreign keys)
            print('Truncating existing tables...')
            for table in reversed(TABLES):
                mysql_cur.execute(f'TRUNCATE TABLE `{table}`')
            print()

            # Migrate data
            print('Migrating data...')
            total_rows = 0
            for table in TABLES:
                rows = get_sqlite_rows(sqlite_cur, table)
                count = insert_mysql_rows(mysql_cur, table, rows)
                total_rows += count
                print(f'  {table}: {count} rows')

            # Reset auto increments
            print()
            print('Resetting auto increments...')
            for table in ['folders', 'tags', 'texts', 'video_templates', 'video_jobs', 'video_assets']:
                reset_auto_increment(mysql_cur, table)

            # Re-enable foreign key checks
            mysql_cur.execute('SET FOREIGN_KEY_CHECKS=1')

        # Commit
        mysql_conn.commit()
        print()
        print(f'Migration committed. Total rows: {total_rows}')

        # Verify counts
        print()
        print('MySQL table counts:')
        with mysql_conn.cursor() as mysql_cur:
            for table in TABLES:
                mysql_cur.execute(f'SELECT COUNT(*) as cnt FROM `{table}`')
                count = mysql_cur.fetchone()['cnt']
                expected = sqlite_counts.get(table, 0)
                status = '✓' if count == expected else f'✗ (expected {expected})'
                print(f'  {table}: {count} {status}')

    except Exception as e:
        print(f'Error during migration: {e}')
        mysql_conn.rollback()
        raise
    finally:
        mysql_conn.close()
        sqlite_conn.close()

    print()
    print('Migration complete!')


if __name__ == '__main__':
    main()
