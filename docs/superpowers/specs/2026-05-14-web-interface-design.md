# Web 界面设计

## 概述

为 SRT 字幕生成器添加 Web 界面，支持文本管理、分组、标签和导出功能。

## 技术栈

- 前端：Vue 3 + Vite + Pinia + Vue Router
- 后端：Flask + SQLAlchemy + SQLite
- 无认证（本地工具）

## 架构

```
script/
├── web/                    # Vue 前端
│   ├── src/
│   │   ├── views/         # 页面组件
│   │   ├── components/    # 通用组件
│   │   ├── api/           # API 调用封装
│   │   └── stores/        # Pinia 状态管理
│   └── package.json
├── server/                 # Flask 后端
│   ├── __init__.py
│   ├── app.py             # Flask 应用
│   ├── models.py          # SQLAlchemy 模型
│   ├── routes/            # API 路由
│   └── static/            # Vue 构建产物
├── splitter.py            # 现有模块（不变）
├── srt.py                 # 现有模块（不变）
├── main.py                # 现有 CLI（不变）
└── data.db                # SQLite 数据库
```

## 数据模型

### Text 文本表
- id: Integer, 主键
- title: String, 标题
- content: Text, 文本内容
- folder_id: Integer, 外键关联 Folder
- created_at: DateTime, 创建时间
- updated_at: DateTime, 更新时间

### Folder 文件夹表
- id: Integer, 主键
- name: String, 文件夹名称
- parent_id: Integer, 自引用外键（支持嵌套）
- created_at: DateTime, 创建时间

### Tag 标签表
- id: Integer, 主键
- name: String, 标签名（唯一）

### TextTag 关联表
- text_id: Integer, 外键
- tag_id: Integer, 外键

## API 设计

### 文本相关
- GET /api/texts — 获取文本列表
  - 查询参数：folder_id, tag, sort_by (created_at/updated_at), order (asc/desc)
- POST /api/texts — 创建文本
- PUT /api/texts/:id — 更新文本
- DELETE /api/texts/:id — 删除文本
- POST /api/texts/import — 上传 TXT 导入
- GET /api/texts/:id/srt — 导出 SRT
  - 查询参数：speed, max_chars

### 文件夹相关
- GET /api/folders — 获取文件夹树
- POST /api/folders — 创建文件夹
- DELETE /api/folders/:id — 删除文件夹

### 标签相关
- GET /api/tags — 获取所有标签
- POST /api/tags — 创建标签

## 页面结构

### 文本列表页
- 左侧：文件夹树（可展开/折叠）
- 右侧：文本列表（表格形式，显示标题、创建时间、更新时间、标签）
- 支持搜索、按时间排序
- 支持批量选择、批量导出

### 文本编辑页
- 文本编辑器（textarea 或 contenteditable）
- 标签选择器（多选）
- 文件夹选择器
- 保存按钮
- 导出 SRT 按钮（带参数配置）

### 导入页
- 文件上传区域（拖拽或点击）
- 上传后预览文本内容
- 选择目标文件夹和标签
- 确认导入

## CLI 兼容性

现有 CLI 功能完全保留：
- `uv run main.py input.txt` — 从文件生成 SRT
- `uv run main.py` — 从 stdin 生成 SRT
- 所有参数（--speed, --max-chars, -o）不变

Web 界面使用相同的 splitter.py 和 srt.py 模块。

## 启动方式

```bash
# 开发模式
cd web && npm run dev    # Vue 开发服务器
cd .. && python -m server.app  # Flask API 服务器

# 生产模式
cd web && npm run build  # 构建 Vue
python -m server.app     # Flask 服务静态文件
```

## 依赖

### Python 依赖（新增）
- flask
- flask-sqlalchemy
- flask-cors

### Node.js 依赖
- vue
- vue-router
- pinia
- axios
- vite
