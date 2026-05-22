# 音色档案后端与数据库文档

## 目标

新增音色档案后端能力，支持：

1. 系统预设音色。
2. 用户创建自定义音色。
3. 音色档案持久化。
4. 语音合成时通过 `voice_profile_id` 引用稳定音色。
5. 试听记录可追踪。

## 数据库选择

当前项目主数据仍使用 SQLite：

```text
data.db
```

新增云端 MySQL 用于音色档案：

```text
host: 115.190.210.249
port: 3306
database: video_script
```

第一阶段只把音色档案放到 MySQL，不迁移 texts、folders、tags。这样改动范围小，也避免影响现有文本库。

## 表设计

### voice_profiles

保存系统预设和用户自定义音色。

```sql
CREATE TABLE voice_profiles (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  profile_key VARCHAR(80) NOT NULL,
  name VARCHAR(120) NOT NULL,
  description VARCHAR(500) NULL,
  raw_description TEXT NOT NULL,
  canonical_prompt TEXT NOT NULL,
  negative_prompt TEXT NULL,
  provider VARCHAR(40) NOT NULL DEFAULT 'mimo',
  model VARCHAR(80) NOT NULL DEFAULT 'mimo-v2.5-tts-voicedesign',
  language VARCHAR(20) NOT NULL DEFAULT 'zh-CN',
  gender VARCHAR(40) NULL,
  age_group VARCHAR(40) NULL,
  accent VARCHAR(80) NULL,
  speed VARCHAR(40) NULL,
  emotion VARCHAR(80) NULL,
  scene VARCHAR(120) NULL,
  timbre VARCHAR(120) NULL,
  is_builtin TINYINT(1) NOT NULL DEFAULT 0,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  sort_order INT NOT NULL DEFAULT 100,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_voice_profiles_profile_key (profile_key),
  KEY idx_voice_profiles_builtin_active (is_builtin, is_active, sort_order),
  KEY idx_voice_profiles_scene (scene),
  KEY idx_voice_profiles_provider_model (provider, model)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

### voice_profile_auditions

保存试听记录。第一阶段可以只记录文本、状态和错误，不一定保存音频文件。

```sql
CREATE TABLE voice_profile_auditions (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  voice_profile_id BIGINT UNSIGNED NOT NULL,
  audition_text TEXT NOT NULL,
  audio_url VARCHAR(1000) NULL,
  status VARCHAR(30) NOT NULL DEFAULT 'created',
  error_message VARCHAR(1000) NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_voice_profile_auditions_profile_id (voice_profile_id),
  CONSTRAINT fk_voice_profile_auditions_profile
    FOREIGN KEY (voice_profile_id) REFERENCES voice_profiles(id)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

## 后端模型

建议新增：

```text
server/routes/voice_profiles.py
server/services/voice_profile_repository.py
server/services/voice_profile_normalizer.py
server/services/mysql.py
```

第一阶段可以不用 SQLAlchemy 管理 MySQL，直接用 repository 封装 PyMySQL。等后续决定整体迁移数据库，再统一接入 SQLAlchemy 多库配置。

## API 设计

### GET /api/voice-profiles

查询音色档案。

Query：

```text
active=1
builtin=1
scene=short_video_narration
q=女声
```

响应：

```json
[
  {
    "id": 1,
    "profile_key": "warm_female_narrator",
    "name": "温柔叙述女声",
    "description": "适合情感类、知识类短视频旁白",
    "canonical_prompt": "...",
    "is_builtin": true,
    "is_active": true
  }
]
```

### POST /api/voice-profiles

创建自定义音色。

请求：

```json
{
  "name": "我的课程旁白",
  "raw_description": "像一位耐心的中文课程老师，咬字清晰，语气自然",
  "negative_prompt": "不要太像播音腔，不要太快",
  "scene": "course",
  "gender": "female",
  "speed": "medium",
  "emotion": "clear_calm"
}
```

后端行为：

1. 校验 `name`、`raw_description`。
2. 生成 `profile_key`。
3. 若前端未传 `canonical_prompt`，调用 LLM 或本地模板生成。
4. 写入 `voice_profiles`。
5. 返回创建后的档案。

### PUT /api/voice-profiles/:id

更新自定义音色。

规则：

- 系统预设不能直接编辑。
- 系统预设可通过“复制为我的音色”创建自定义副本。
- 更新 raw description 后应重新生成 canonical prompt，或由用户显式保留旧 prompt。

### DELETE /api/voice-profiles/:id

删除自定义音色。

规则：

- 系统预设不能删除。
- 建议逻辑删除：`is_active=0`。

### POST /api/voice-profiles/:id/audition

生成试听。

请求：

```json
{
  "api_key": "tts-api-key",
  "text": "今天我们来聊一个很实用的方法..."
}
```

响应：

```json
{
  "audio_base64": "...",
  "audition_id": 1
}
```

## 与 TTS 同步包集成

`POST /api/tts/sync-package-v2` 支持新增字段：

```json
{
  "voice_profile_id": 1,
  "voice_profile_snapshot": {
    "canonical_prompt": "...",
    "negative_prompt": "..."
  },
  "voice_description": "..."
}
```

解析优先级：

1. 若有 `voice_profile_id`，后端从 MySQL 读取 `canonical_prompt`。
2. 若读取失败但有 `voice_profile_snapshot`，使用 snapshot。
3. 若没有档案，使用 `voice_description`。
4. 若三者都没有，返回 400。

manifest 中写入：

```json
{
  "voice_profile": {
    "id": 1,
    "profile_key": "warm_female_narrator",
    "name": "温柔叙述女声",
    "provider": "mimo",
    "model": "mimo-v2.5-tts-voicedesign"
  }
}
```

## 环境变量

不要把数据库密码写入代码。建议使用：

```text
VOICE_DB_HOST=115.190.210.249
VOICE_DB_PORT=3306
VOICE_DB_NAME=video_script
VOICE_DB_USER=root
VOICE_DB_PASSWORD=...
```

本地开发可放入 `.env`，生产环境由部署平台注入。

## 初始预设

建议插入 8 个系统预设：

1. 温柔叙述女声
2. 清晰课程女声
3. 沉稳纪录片男声
4. 干净新闻男声
5. 活力短视频女声
6. 治愈故事女声
7. 专业商务男声
8. 自然朋友感女声

系统预设使用 `is_builtin=1`，用户创建使用 `is_builtin=0`。

## 安全建议

1. 不建议长期用 MySQL root 账号连接应用。
2. 建议创建应用专用账号，例如 `video_script_app`。
3. 应用账号只授予 `video_script` 库的 SELECT/INSERT/UPDATE/DELETE 权限。
4. API Key 和数据库密码不要返回给前端。
5. 后端日志不要打印完整 canonical prompt 和用户 API Key。

## 测试策略

后端测试：

- 查询预设列表。
- 创建自定义音色。
- 系统预设不能删除。
- 自定义音色删除后不出现在 active 列表。
- audition 调用 TTS provider，可 mock。
- sync-package-v2 能通过 `voice_profile_id` 解析 prompt。

数据库测试：

- `profile_key` 唯一约束生效。
- `voice_profile_auditions` 外键级联删除生效。
- utf8mb4 能保存中文和 emoji。

## 分阶段落地

### Phase 1

- 创建 MySQL 数据库和表。
- 插入系统预设。
- 新增查询 API。
- 前端可选择预设。

### Phase 2

- 新增创建、编辑、停用自定义音色。
- 新增试听 API。
- 同步包支持 `voice_profile_id`。

### Phase 3

- 新增应用专用数据库账号。
- 新增音色版本管理。
- 新增最近使用和收藏。
