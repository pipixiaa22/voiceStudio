# SQLite 迁移到 MySQL 具体指南

## 背景

当前 Flask 后端默认使用项目根目录下的 SQLite：

```text
data.db
```

当前本地 SQLAlchemy 表包括：

```text
texts
folders
tags
text_tags
video_templates
video_jobs
video_assets
```

云端 MySQL 已存在：

```text
host: 115.190.210.249
port: 3306
database: video_script
```

该 MySQL 库中已经包含音色档案相关表，例如：

```text
voice_profiles
voice_profile_auditions
```

本指南只迁移当前 SQLite 中的 SQLAlchemy 业务表，不覆盖已有的 `voice_profiles` 等云端表。

## 迁移目标

1. 将 `data.db` 中的文本、文件夹、标签、视频模板、视频任务数据迁移到 MySQL。
2. 后端统一使用 MySQL 作为主数据库。
3. 保留现有主键 ID，避免前端路由和关联关系失效。
4. 保证迁移后接口测试通过。
5. 提供可回滚方案。

## 风险点

1. SQLite 与 MySQL 的布尔值、时间字段、外键行为不同。
2. `folders.parent_id` 是自关联外键，迁移时需要注意插入顺序或临时关闭外键检查。
3. `text_tags` 依赖 `texts` 和 `tags`，必须最后迁移。
4. 当前 SQLite 的 `video_jobs` 表可能缺少模型中新加的 `video_path` 字段，MySQL 应按最新 `models.py` 创建。
5. MySQL 中已有的音色表不能被 `DROP DATABASE` 或全库清空。
6. 不建议生产环境长期使用 MySQL root 账号。

## 推荐迁移策略

采用“同库新增/覆盖指定表”的方式：

```text
保留 video_script 数据库
保留 voice_profiles 等已有云端表
只创建/重建以下 SQLite 迁移表：
- folders
- texts
- tags
- text_tags
- video_templates
- video_jobs
- video_assets
```

## 迁移前准备

### 1. 停止后端服务

避免迁移过程中 SQLite 继续写入。

```bash
./start.sh stop
```

### 2. 备份 SQLite

```bash
mkdir -p backups
cp data.db "backups/data.$(date +%Y%m%d-%H%M%S).db"
```

### 3. 导出现有 SQLite 表计数

```bash
uv run python - <<'PY'
import sqlite3

tables = [
    'folders',
    'texts',
    'tags',
    'text_tags',
    'video_templates',
    'video_jobs',
    'video_assets',
]

conn = sqlite3.connect('data.db')
cur = conn.cursor()
for table in tables:
    try:
        cur.execute(f'SELECT COUNT(*) FROM {table}')
        print(table, cur.fetchone()[0])
    except Exception as e:
        print(table, 'missing', e)
conn.close()
PY
```

将输出保存下来，迁移后逐项对比。

## MySQL 连接配置

建议使用环境变量，不要把密码写死进代码：

```text
DATABASE_URL=mysql+pymysql://video_script_app:密码@115.190.210.249:3306/video_script?charset=utf8mb4
```

如果暂时仍使用 root，也应放到 `.env`：

```text
DATABASE_URL=mysql+pymysql://root:密码@115.190.210.249:3306/video_script?charset=utf8mb4
```

建议后续创建应用专用账号：

```sql
CREATE USER 'video_script_app'@'%' IDENTIFIED BY '强密码';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX
ON video_script.*
TO 'video_script_app'@'%';
FLUSH PRIVILEGES;
```

## 后端配置修改

当前 [server/app.py](/Users/ckrey/video/script/server/app.py) 固定使用 SQLite：

```python
db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
```

建议改为优先读取 `DATABASE_URL`：

```python
database_url = os.environ.get('DATABASE_URL')
if database_url:
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
else:
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
```

这样可以在本地继续用 SQLite，在生产环境切换到 MySQL。

## MySQL 表结构

以下 DDL 按当前 `server/models.py` 设计，使用 `utf8mb4`。

### folders

```sql
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

### tags

```sql
CREATE TABLE IF NOT EXISTS tags (
  id INT NOT NULL AUTO_INCREMENT,
  name VARCHAR(50) NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uk_tags_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

### texts

```sql
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

### text_tags

```sql
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

### video_templates

```sql
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

### video_jobs

```sql
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

### video_assets

```sql
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

## 迁移脚本

建议新增脚本：

```text
scripts/migrate_sqlite_to_mysql.py
```

示例脚本：

```python
import os
import sqlite3
from datetime import datetime

import pymysql
from dotenv import load_dotenv

load_dotenv()

SQLITE_PATH = os.environ.get('SQLITE_PATH', 'data.db')
MYSQL_CONFIG = {
    'host': os.environ.get('MYSQL_HOST', '115.190.210.249'),
    'port': int(os.environ.get('MYSQL_PORT', '3306')),
    'user': os.environ.get('MYSQL_USER', 'root'),
    'password': os.environ['MYSQL_PASSWORD'],
    'database': os.environ.get('MYSQL_DATABASE', 'video_script'),
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor,
}


TABLES = [
    'folders',
    'tags',
    'texts',
    'text_tags',
    'video_templates',
    'video_jobs',
    'video_assets',
]


def rows(sqlite_cur, table):
    sqlite_cur.execute(f'SELECT * FROM {table}')
    columns = [desc[0] for desc in sqlite_cur.description]
    for row in sqlite_cur.fetchall():
        yield dict(zip(columns, row))


def insert_rows(mysql_cur, table, items):
    items = list(items)
    if not items:
        return
    columns = list(items[0].keys())

    # SQLite 旧 video_jobs 表可能没有 video_path，MySQL 有该字段。
    if table == 'video_jobs' and 'video_path' not in columns:
        columns.append('video_path')
        for item in items:
            item['video_path'] = None

    placeholders = ', '.join(['%s'] * len(columns))
    column_sql = ', '.join(f'`{col}`' for col in columns)
    sql = f'INSERT INTO `{table}` ({column_sql}) VALUES ({placeholders})'
    values = [tuple(item.get(col) for col in columns) for item in items]
    mysql_cur.executemany(sql, values)


def reset_auto_increment(mysql_cur, table):
    mysql_cur.execute(f'SELECT COALESCE(MAX(id), 0) + 1 AS next_id FROM `{table}`')
    next_id = mysql_cur.fetchone()['next_id']
    mysql_cur.execute(f'ALTER TABLE `{table}` AUTO_INCREMENT = {next_id}')


def main():
    sqlite_conn = sqlite3.connect(SQLITE_PATH)
    sqlite_cur = sqlite_conn.cursor()

    mysql_conn = pymysql.connect(**MYSQL_CONFIG)
    try:
        with mysql_conn.cursor() as mysql_cur:
            mysql_cur.execute('SET FOREIGN_KEY_CHECKS=0')

            # 只清空从 SQLite 迁移的表，不动 voice_profiles 等云端表。
            for table in reversed(TABLES):
                mysql_cur.execute(f'TRUNCATE TABLE `{table}`')

            for table in TABLES:
                insert_rows(mysql_cur, table, rows(sqlite_cur, table))

            for table in ['folders', 'tags', 'texts', 'video_templates', 'video_jobs', 'video_assets']:
                reset_auto_increment(mysql_cur, table)

            mysql_cur.execute('SET FOREIGN_KEY_CHECKS=1')

        mysql_conn.commit()
    except Exception:
        mysql_conn.rollback()
        raise
    finally:
        mysql_conn.close()
        sqlite_conn.close()


if __name__ == '__main__':
    main()
```

运行：

```bash
MYSQL_HOST=115.190.210.249 \
MYSQL_PORT=3306 \
MYSQL_DATABASE=video_script \
MYSQL_USER=root \
MYSQL_PASSWORD='你的密码' \
uv run python scripts/migrate_sqlite_to_mysql.py
```

## 迁移后校验

### 1. 对比表计数

```bash
uv run python - <<'PY'
import os
import pymysql
from dotenv import load_dotenv

load_dotenv()

tables = [
    'folders',
    'texts',
    'tags',
    'text_tags',
    'video_templates',
    'video_jobs',
    'video_assets',
]

conn = pymysql.connect(
    host=os.environ.get('MYSQL_HOST', '115.190.210.249'),
    port=int(os.environ.get('MYSQL_PORT', '3306')),
    user=os.environ.get('MYSQL_USER', 'root'),
    password=os.environ['MYSQL_PASSWORD'],
    database=os.environ.get('MYSQL_DATABASE', 'video_script'),
    charset='utf8mb4',
)

with conn.cursor() as cur:
    for table in tables:
        cur.execute(f'SELECT COUNT(*) FROM {table}')
        print(table, cur.fetchone()[0])
conn.close()
PY
```

### 2. 检查关联完整性

```sql
SELECT COUNT(*) AS broken_text_folder
FROM texts t
LEFT JOIN folders f ON t.folder_id = f.id
WHERE t.folder_id IS NOT NULL AND f.id IS NULL;

SELECT COUNT(*) AS broken_text_tags_text
FROM text_tags tt
LEFT JOIN texts t ON tt.text_id = t.id
WHERE t.id IS NULL;

SELECT COUNT(*) AS broken_text_tags_tag
FROM text_tags tt
LEFT JOIN tags g ON tt.tag_id = g.id
WHERE g.id IS NULL;
```

三个结果都应为 `0`。

### 3. 启动后端并跑测试

```bash
DATABASE_URL='mysql+pymysql://root:密码@115.190.210.249:3306/video_script?charset=utf8mb4' \
uv run pytest -q
```

注意：当前测试夹具使用 `sqlite:///:memory:`，单元测试仍会走内存 SQLite，这是正常的。需要额外做一次手动 MySQL 启动验证：

```bash
DATABASE_URL='mysql+pymysql://root:密码@115.190.210.249:3306/video_script?charset=utf8mb4' \
uv run subtitle-web
```

然后访问：

```text
http://localhost:5002/api/texts
http://localhost:5002/api/folders
http://localhost:5002/api/video/templates
```

## 切换生产配置

确认迁移数据无误后，在启动环境中加入：

```text
DATABASE_URL=mysql+pymysql://video_script_app:密码@115.190.210.249:3306/video_script?charset=utf8mb4
```

然后重启服务：

```bash
./start.sh restart
```

如果 `start.sh` 不加载 `.env`，需要修改启动脚本或使用 shell export：

```bash
export DATABASE_URL='mysql+pymysql://...'
./start.sh restart
```

## 回滚方案

如果迁移后发现问题：

1. 停止服务。
2. 移除 `DATABASE_URL`。
3. 恢复 SQLite 备份。
4. 重启服务。

```bash
./start.sh stop
cp backups/data.YYYYMMDD-HHMMSS.db data.db
unset DATABASE_URL
./start.sh start
```

MySQL 中已迁移的数据可以保留，等修复后重新迁移。

## 建议的最终改造

### 1. 代码配置

[server/app.py](/Users/ckrey/video/script/server/app.py) 应支持：

```python
database_url = os.environ.get('DATABASE_URL')
if database_url:
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
```

### 2. 依赖

`pyproject.toml` 需要包含：

```toml
pymysql
python-dotenv
```

当前项目已经引入这些依赖时，可直接使用 `mysql+pymysql://`。

### 3. 后续迁移管理

当前项目使用 `db.create_all()`，适合早期开发，但不适合长期维护。建议后续引入：

```text
Flask-Migrate / Alembic
```

这样后续新增字段时，不需要手写 ALTER TABLE。

## 完整迁移顺序

推荐顺序：

```text
1. 停止后端
2. 备份 data.db
3. 记录 SQLite 表计数
4. 确认 MySQL video_script 数据库存在
5. 创建 MySQL 目标表
6. 运行迁移脚本
7. 对比 MySQL 表计数
8. 检查外键关联完整性
9. 修改 server/app.py 支持 DATABASE_URL
10. 使用 DATABASE_URL 启动后端
11. 手动验证文本库、文件夹、标签、视频模板接口
12. 前端走完整核心流程验证
13. 生产环境固定使用 MySQL
```

## 验收标准

1. MySQL 中 `texts/folders/tags/text_tags` 数量与 SQLite 一致。
2. MySQL 中 `video_templates/video_jobs/video_assets` 数量与 SQLite 一致，或符合预期。
3. 所有 `folder_id`、`parent_id`、`text_tags` 关联完整。
4. 后端使用 `DATABASE_URL` 后能正常启动。
5. `/api/texts`、`/api/folders`、`/api/tags` 正常返回。
6. 语音合成和音色档案功能不受影响。
7. 视频模板接口正常返回。
8. 移除 `DATABASE_URL` 后仍可回滚到 SQLite。
