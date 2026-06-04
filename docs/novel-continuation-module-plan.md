# 剧情续写与小说知识图谱模块规划

## 需求结论

本模块定位为一个 **长篇小说 AI 创作工作台**，不是简单的段落续写工具。

已确认的核心需求：

- 支持所有小说类型：玄幻、仙侠、都市、悬疑、言情、科幻、历史、末世、轻小说等。
- 用户给出人物、世界观、大纲后，系统可以辅助从头到尾写完整本书。
- 生成方式以逐章生成为主，每章可由用户确认、修改、重生成后再进入下一章。
- 支持整书目标：总字数、章节数、每章字数、卷数、剧情节奏。
- 知识图谱必须包含人物关系图和事件因果图。
- 知识图谱是可编辑画布，不只是只读展示。
- 设定和图谱更新支持三种模式：手动维护、AI 提取后人工确认、AI 自动更新。
- 续写结果支持多版本，用户可选择一个版本作为正式稿。
- 正文编辑器采用 Markdown。

## 产品定位

一句话：

> 用人物、世界观、大纲作为长期记忆，让 AI 逐章生成整本小说，并通过可编辑知识图谱维护人物关系和事件因果。

核心价值：

- 帮用户把一个创意扩展成完整长篇小说。
- 保持长篇连载的一致性，降低人设漂移、剧情断裂、伏笔遗忘。
- 用图谱把复杂人物关系和事件因果显性化。
- 允许用户在 AI 生成和人工掌控之间切换。

## 总体工作流

### 1. 创建小说工程

用户创建一个小说工程，填写：

- 小说标题
- 类型
- 目标字数
- 目标章节数
- 每章目标字数
- 卷数或篇章结构
- 叙事视角
- 文风
- 平台风格
- 禁忌与雷区

示例：

```json
{
  "title": "长夜剑骨",
  "genre": "仙侠",
  "target_total_words": 800000,
  "target_chapters": 300,
  "words_per_chapter": 2600,
  "volume_count": 5,
  "pov": "third_person_limited",
  "tone": ["热血", "悬疑", "古风"],
  "platform_style": "起点长篇爽文",
  "taboos": ["不要让主角突然无脑", "不要提前揭露最终反派"]
}
```

### 2. 建立创作蓝图

用户可以手动填写，也可以让 AI 根据一句创意生成：

- 核心卖点
- 世界观
- 主角设定
- 主要人物
- 主要势力
- 主线目标
- 阶段性大纲
- 章节目录
- 主要冲突
- 关键事件
- 伏笔与回收计划

### 3. 生成全书大纲

系统根据目标字数和章节数拆分：

- 全书主线
- 卷大纲
- 篇章大纲
- 章节目录
- 每章剧情目标
- 每章冲突推进
- 每章需要出现的人物/事件/伏笔

大纲生成后必须可编辑。用户修改大纲后，后续章节生成以修改后的大纲为准。

### 4. 逐章生成

每章生成流程：

1. 选择章节。
2. 系统读取该章大纲、前文摘要、相关人物、相关事件、当前冲突和未回收伏笔。
3. 用户设置生成参数。
4. AI 生成多个版本。
5. 用户选择一个版本，或继续重生成。
6. 用户在 Markdown 编辑器中修改。
7. 用户确认保存为正式稿。
8. 系统更新章节摘要、人物状态、事件因果和知识图谱。

### 5. 图谱更新

每章保存后，知识库更新有三种模式：

- 手动模式：用户自己添加人物、事件、关系。
- AI 提取确认模式：AI 提取候选变更，用户逐条确认。
- 自动模式：AI 自动更新图谱，同时保留变更日志和回滚入口。

建议默认使用 **AI 提取确认模式**，最稳。

## 主要功能

### 小说工程管理

功能：

- 创建小说工程
- 编辑工程设定
- 设置总字数、章节数、每章字数
- 设置类型和文风
- 设置生成模型
- 设置知识库更新模式
- 归档或删除工程

列表字段：

- 标题
- 类型
- 当前章节进度
- 总字数进度
- 最近更新时间
- 当前状态

### 类型模板

因为要支持所有小说类型，需要做类型模板。

模板影响：

- 人物卡字段
- 世界观字段
- 冲突类型
- 节奏规则
- 续写 prompt
- 审稿规则

示例：

玄幻/仙侠模板：

- 修炼体系
- 宗门势力
- 法宝道具
- 境界差距
- 师徒/同门关系
- 秘境/传承/天劫

悬疑模板：

- 案件
- 线索
- 误导
- 真相层级
- 嫌疑人关系
- 时间线

都市模板：

- 职业身份
- 社会关系
- 商业/职场冲突
- 家庭关系
- 情感线

### 人物卡

人物卡字段：

- 姓名
- 别名
- 类型：主角、配角、反派、路人、隐藏人物
- 身份
- 所属势力
- 外貌
- 性格
- 目标
- 秘密
- 能力
- 弱点
- 与主线关系
- 人物弧光
- 当前状态
- 首次登场章节
- 最近登场章节

人物状态要支持随章节变化：

- 当前所在地
- 当前阵营
- 当前目标
- 当前情绪
- 是否知道某个秘密
- 与其他人物关系是否变化

### 世界观

世界观字段：

- 时代背景
- 地理结构
- 社会结构
- 核心规则
- 禁忌规则
- 权力结构
- 经济/资源体系
- 类型专属规则

世界观规则需要被续写和审稿引用，防止 AI 写出违反设定的内容。

### 大纲系统

大纲树层级：

- 全书
- 卷
- 篇章
- 章节
- 场景

每个大纲节点字段：

- 标题
- 摘要
- 目标字数
- 剧情目标
- 冲突目标
- 涉及人物
- 涉及事件
- 涉及伏笔
- 状态：规划中、待生成、已生成、已确认、需重写

### Markdown 章节编辑器

编辑器要求：

- Markdown 正文编辑
- 字数统计
- 章节标题
- 保存草稿
- 正式稿确认
- 版本切换
- AI 续写结果插入
- AI 续写结果替换
- 从当前位置继续写

第一版可以使用普通 Markdown 文本编辑器，不需要复杂富文本。

### 多版本生成

同一章或同一场景可以生成多个版本。

版本类型：

- 稳健推进版
- 强冲突版
- 爽点爆发版
- 悬疑反转版
- 感情拉扯版
- 文风精修版
- 用户自定义方向

每个版本记录：

- 生成类型
- 使用模型
- 使用上下文
- 用户指令
- 生成正文
- AI 自评
- 是否被采纳

用户可以：

- 预览版本
- 对比版本
- 采纳版本
- 删除版本
- 基于某个版本继续改写

### 逐章生成流水线

每章生成不是孤立调用，而是一个流水线：

1. 章节规划：确认本章目标。
2. 上下文组装：选择相关设定、人物、事件。
3. 多版本生成：一次生成 1-3 个版本。
4. 一致性检查：检查人物、世界观、事件因果。
5. 用户编辑：Markdown 修改。
6. 正式确认：写入章节正式稿。
7. 摘要生成：生成章节摘要。
8. 图谱更新：抽取人物关系和事件因果变化。
9. 进入下一章。

## 知识图谱

### 图谱要求

图谱必须是可编辑画布。

支持两种核心图谱：

- 人物关系图
- 事件因果图

后续可扩展：

- 势力关系图
- 伏笔回收图
- 地点事件图

### 人物关系图

节点：

- 人物
- 势力
- 组织
- 家族

边：

- 亲属
- 师徒
- 同门
- 同盟
- 敌对
- 暧昧
- 恋人
- 背叛
- 利用
- 欠债/恩情
- 知道秘密
- 隐藏关系

交互：

- 拖动画布节点
- 添加人物
- 添加关系
- 编辑关系类型
- 编辑关系描述
- 设置关系强度
- 设置关系状态：隐藏、活跃、破裂、反转
- 点击人物打开人物卡
- 点击关系打开证据和说明

### 事件因果图

节点：

- 事件
- 伏笔
- 冲突
- 决策
- 反转
- 揭示
- 结果

边：

- 导致
- 阻碍
- 推动
- 反转
- 揭露
- 回收
- 升级
- 解决

事件字段：

- 事件标题
- 事件摘要
- 发生章节
- 参与人物
- 发生地点
- 原因
- 结果
- 后续影响
- 关联伏笔

交互：

- 查看某个事件的前因后果
- 从事件跳转到章节正文
- 从章节正文定位事件
- 编辑因果边
- 让 AI 解释某条因果链是否合理

### 图谱视图过滤

过滤条件：

- 当前章节相关
- 当前卷相关
- 指定人物相关
- 指定剧情线相关
- 只看隐藏关系
- 只看未解决冲突
- 只看未回收伏笔
- 只看高重要度事件

## AI 生成能力

### 从零生成整本书蓝图

输入：

- 类型
- 一句话创意
- 目标字数
- 目标章节数
- 文风

输出：

- 小说简介
- 主角设定
- 核心人物
- 世界观
- 主线冲突
- 全书结构
- 卷大纲
- 章节规划
- 关键事件
- 人物关系初始图
- 事件因果初始图

### 逐章生成

输入：

- 当前章节大纲
- 前文摘要
- 当前正文尾部
- 相关人物卡
- 相关事件
- 当前冲突
- 未回收伏笔
- 用户指令
- 目标字数
- 版本方向

输出：

- 正文 Markdown
- 本章摘要
- 推进了哪些冲突
- 新增了哪些事件
- 改变了哪些人物关系
- 使用了哪些伏笔
- 可能的一致性风险

### 改写与精修

支持：

- 扩写
- 压缩
- 润色
- 加强冲突
- 加强爽点
- 加强悬疑
- 加强感情戏
- 改成指定文风
- 改成短视频解说稿

### 一致性审稿

检查：

- 人设是否崩坏
- 世界观规则是否冲突
- 时间线是否合理
- 人物是否出现在不可能出现的地点
- 事件因果是否断裂
- 伏笔是否遗忘
- 本章是否推进冲突
- 是否与前文重复
- 是否水文

## 知识库更新模式

### 手动模式

用户自己维护：

- 人物
- 关系
- 事件
- 因果
- 伏笔
- 冲突

适合对创作控制要求很高的用户。

### AI 提取确认模式

系统从章节正文中提取候选：

- 新人物
- 新关系
- 新事件
- 新因果
- 新伏笔
- 关系变化
- 人物状态变化

用户逐条确认、修改或拒绝。

这是推荐默认模式。

### 自动模式

AI 自动写入知识库。

要求：

- 保留变更日志
- 支持撤销
- 支持回滚到某章保存前
- 自动模式下必须标记 AI 置信度

## 后端设计

### 新增模型文件

建议新增：

- `server/models/novel.py`

### 数据表

核心表：

- `NovelProject`
- `NovelOutlineNode`
- `NovelChapter`
- `NovelChapterVersion`
- `NovelEntity`
- `NovelRelation`
- `NovelEvent`
- `NovelEventRelation`
- `NovelGeneration`
- `NovelGraphChange`

### NovelProject

字段：

- `id`
- `title`
- `genre`
- `premise`
- `target_total_words`
- `target_chapters`
- `words_per_chapter`
- `volume_count`
- `style_guide_json`
- `settings_json`
- `knowledge_update_mode`
- `status`
- `created_at`
- `updated_at`

### NovelChapter

字段：

- `id`
- `project_id`
- `outline_node_id`
- `title`
- `content_markdown`
- `summary`
- `order_index`
- `target_words`
- `word_count`
- `status`
- `created_at`
- `updated_at`

### NovelChapterVersion

字段：

- `id`
- `chapter_id`
- `version_type`
- `title`
- `content_markdown`
- `prompt_json`
- `context_snapshot_json`
- `model`
- `accepted`
- `created_at`

### NovelEntity

统一存人物、势力、地点、物品、规则。

字段：

- `id`
- `project_id`
- `entity_type`
- `name`
- `aliases_json`
- `summary`
- `attributes_json`
- `importance`
- `node_x`
- `node_y`
- `created_at`
- `updated_at`

`node_x/node_y` 用于可编辑画布保存位置。

### NovelRelation

人物关系和实体关系。

字段：

- `id`
- `project_id`
- `source_entity_id`
- `target_entity_id`
- `relation_type`
- `label`
- `description`
- `strength`
- `status`
- `evidence_json`
- `created_at`
- `updated_at`

### NovelEvent

字段：

- `id`
- `project_id`
- `chapter_id`
- `title`
- `summary`
- `event_type`
- `timeline_order`
- `participants_json`
- `location_entity_id`
- `effects_json`
- `node_x`
- `node_y`
- `created_at`
- `updated_at`

### NovelEventRelation

事件因果边。

字段：

- `id`
- `project_id`
- `source_event_id`
- `target_event_id`
- `relation_type`
- `label`
- `description`
- `confidence`
- `created_at`
- `updated_at`

### NovelGraphChange

图谱变更记录，用于 AI 自动模式回滚。

字段：

- `id`
- `project_id`
- `chapter_id`
- `change_type`
- `target_type`
- `target_id`
- `before_json`
- `after_json`
- `source`
- `confidence`
- `accepted`
- `created_at`

## API 设计

建议新增：

- `server/routes/novels.py`

### 工程

- `GET /api/novels`
- `POST /api/novels`
- `GET /api/novels/<project_id>`
- `PUT /api/novels/<project_id>`
- `DELETE /api/novels/<project_id>`

### 蓝图与大纲

- `POST /api/novels/<project_id>/blueprint/generate`
- `GET /api/novels/<project_id>/outline`
- `POST /api/novels/<project_id>/outline`
- `PUT /api/novels/<project_id>/outline/<node_id>`
- `DELETE /api/novels/<project_id>/outline/<node_id>`

### 章节

- `GET /api/novels/<project_id>/chapters`
- `POST /api/novels/<project_id>/chapters`
- `GET /api/novels/<project_id>/chapters/<chapter_id>`
- `PUT /api/novels/<project_id>/chapters/<chapter_id>`
- `POST /api/novels/<project_id>/chapters/<chapter_id>/confirm`
- `POST /api/novels/<project_id>/chapters/<chapter_id>/create-text`

### 多版本生成

- `POST /api/novels/<project_id>/chapters/<chapter_id>/generate-versions`
- `GET /api/novels/<project_id>/chapters/<chapter_id>/versions`
- `POST /api/novels/<project_id>/chapters/<chapter_id>/versions/<version_id>/accept`
- `DELETE /api/novels/<project_id>/chapters/<chapter_id>/versions/<version_id>`

### 知识图谱

- `GET /api/novels/<project_id>/graph/characters`
- `GET /api/novels/<project_id>/graph/events`
- `PUT /api/novels/<project_id>/graph/layout`

### 实体与关系

- `GET /api/novels/<project_id>/entities`
- `POST /api/novels/<project_id>/entities`
- `PUT /api/novels/<project_id>/entities/<entity_id>`
- `DELETE /api/novels/<project_id>/entities/<entity_id>`
- `GET /api/novels/<project_id>/relations`
- `POST /api/novels/<project_id>/relations`
- `PUT /api/novels/<project_id>/relations/<relation_id>`
- `DELETE /api/novels/<project_id>/relations/<relation_id>`

### 事件因果

- `GET /api/novels/<project_id>/events`
- `POST /api/novels/<project_id>/events`
- `PUT /api/novels/<project_id>/events/<event_id>`
- `DELETE /api/novels/<project_id>/events/<event_id>`
- `POST /api/novels/<project_id>/event-relations`
- `PUT /api/novels/<project_id>/event-relations/<relation_id>`
- `DELETE /api/novels/<project_id>/event-relations/<relation_id>`

### AI 提取与审稿

- `POST /api/novels/<project_id>/chapters/<chapter_id>/extract-graph`
- `POST /api/novels/<project_id>/graph-changes/<change_id>/accept`
- `POST /api/novels/<project_id>/graph-changes/<change_id>/reject`
- `POST /api/novels/<project_id>/chapters/<chapter_id>/review`

## 前端设计

### 路由

新增：

- `/novels`
- `/novels/:id`

### 页面

新增：

- `NovelProjectList.vue`
- `NovelWorkspace.vue`

### 组件

新增目录：

- `web/src/components/novel/`

组件：

- `NovelOutlinePanel.vue`
- `NovelChapterEditor.vue`
- `NovelGenerationPanel.vue`
- `NovelVersionList.vue`
- `NovelCharacterGraph.vue`
- `NovelEventGraph.vue`
- `NovelEntityInspector.vue`
- `NovelRelationInspector.vue`
- `NovelEventInspector.vue`
- `NovelBlueprintWizard.vue`
- `NovelExtractionReviewModal.vue`

### 工作台布局

推荐布局：

- 左侧：工程大纲树、章节列表
- 中间：Markdown 章节编辑器
- 右侧：生成参数、人物卡、事件卡、版本列表
- 下方或独立 Tab：可编辑知识图谱画布

### 图谱画布

建议使用 `@vue-flow/core`，因为项目已有语音工作流画布基础。

图谱画布能力：

- 节点拖拽
- 边编辑
- 节点类型样式
- 边类型样式
- 右键新增节点
- 右键新增关系
- 保存节点位置
- 按类型过滤
- 点击节点打开编辑面板

## AI 服务层

新增目录：

- `server/services/novel/`

文件：

- `blueprint_generator.py`
- `context_builder.py`
- `chapter_generator.py`
- `version_generator.py`
- `graph_extractor.py`
- `consistency_reviewer.py`
- `graph_builder.py`
- `summarizer.py`
- `prompt_templates.py`

### 上下文构建

逐章生成时，系统自动组装：

- 工程设定
- 类型模板
- 文风约束
- 当前章节大纲
- 前几章摘要
- 当前正文尾部
- 相关人物卡
- 相关人物关系
- 相关事件因果
- 当前未解决冲突
- 当前未回收伏笔
- 用户本次指令

### 上下文预算

建议：

- 工程设定：500-1000 字
- 世界观：800-1500 字
- 人物卡：每人 200-500 字
- 前文摘要：1000-2500 字
- 当前正文尾部：2000-4000 字
- 事件因果：800-1500 字
- 用户指令：不压缩

## Redis 使用建议

Redis 只做辅助，不存主数据。

适合用途：

- 生成任务状态
- 多版本生成缓存
- 图谱抽取锁
- AI 审稿缓存
- 限流

Key 示例：

- `novel:generation:{generation_id}`
- `novel:versions:{chapter_id}:{context_hash}`
- `novel:extract:{chapter_id}:lock`
- `novel:review:{chapter_id}:{content_hash}`
- `ratelimit:novel-generate:{ip}`

## 与现有模块联动

### 文本库

章节可一键创建为 `Text`：

- 标题：小说名 + 章节名
- 内容：章节 Markdown 去除标记或保留纯文本
- 标签：小说、章节、类型、人物

### TTS 和视频

后续可以支持：

- 小说章节转有声书
- 按人物自动拆分对话
- 按人物匹配音色
- 章节转短视频解说脚本
- 人物关系图转剧情讲解视频

## 第一版范围

为了快速上线，第一版建议包含：

- 小说工程 CRUD
- 设置目标字数、章节数、每章字数
- 类型模板基础字段
- 人物卡 CRUD
- 大纲树
- Markdown 章节编辑
- 逐章生成
- 多版本生成与采纳
- 人物关系可编辑画布
- 简版事件因果可编辑画布
- 章节摘要
- AI 提取确认模式
- 章节转文本库

第一版暂缓：

- 自动连续生成到第 N 章
- 复杂富文本编辑器
- 完整伏笔看板
- 多人协作
- 向量数据库
- 全自动图谱更新
- 复杂审稿评分体系

## 实施阶段

### Phase 1：工程、大纲、章节与逐章生成

目标：

- 用户能创建小说工程。
- 用户能设定总字数和章节数。
- 用户能维护大纲。
- 用户能用 Markdown 写章节。
- AI 能逐章生成多个版本。

后端：

- `NovelProject`
- `NovelOutlineNode`
- `NovelChapter`
- `NovelChapterVersion`
- `server/routes/novels.py`
- `server/services/novel/chapter_generator.py`
- `server/services/novel/context_builder.py`

前端：

- `/novels`
- `/novels/:id`
- 工程列表
- 工作台
- 大纲面板
- Markdown 编辑器
- 多版本列表

### Phase 2：人物关系图

目标：

- 用户能维护人物卡。
- 用户能在可编辑画布上维护人物关系。
- 续写时能引用人物关系。

后端：

- `NovelEntity`
- `NovelRelation`
- 人物图谱 API

前端：

- `NovelCharacterGraph.vue`
- `NovelEntityInspector.vue`
- `NovelRelationInspector.vue`

### Phase 3：事件因果图

目标：

- 用户能维护事件。
- 用户能维护事件之间的因果关系。
- 续写时能引用事件链。

后端：

- `NovelEvent`
- `NovelEventRelation`
- 事件图谱 API

前端：

- `NovelEventGraph.vue`
- `NovelEventInspector.vue`

### Phase 4：AI 抽取确认

目标：

- 章节保存后，AI 提取人物、关系、事件、因果候选。
- 用户确认后写入图谱。

后端：

- `NovelGraphChange`
- `graph_extractor.py`

前端：

- `NovelExtractionReviewModal.vue`

### Phase 5：一致性审稿

目标：

- 检查人设、世界观、事件因果、时间线问题。

后端：

- `consistency_reviewer.py`

前端：

- 审稿结果面板

## 验收标准

第一版完成时，需要满足：

- 可以创建一个小说工程。
- 可以设置目标 30 万字、100 章、每章 3000 字。
- 可以创建人物卡并在画布上连线。
- 可以创建事件并在画布上建立因果边。
- 可以创建大纲树。
- 可以选择某一章逐章生成至少 2 个版本。
- 可以采纳某个版本作为章节正文。
- 可以在 Markdown 编辑器中修改正文。
- 保存章节后可以生成摘要。
- 保存章节后可以让 AI 提取图谱候选。
- 章节可以转入现有文本库。

## 关键风险

- 整本书上下文过大：必须依赖章节摘要、相关实体筛选和上下文预算。
- 图谱维护复杂：第一版必须让 AI 提取候选，降低手动维护成本。
- 自动更新可能污染知识库：默认应使用 AI 提取确认模式。
- 多类型小说 prompt 容易泛化不足：需要类型模板逐步完善。
- 可编辑画布开发量较大：复用 `@vue-flow/core`，先做基础编辑能力。
- 多版本生成成本高：需要限流和 Redis 缓存，避免重复消耗模型额度。

## 后续可扩展能力

- 自动连续生成到指定章节，但每章仍保留审稿记录。
- 伏笔看板。
- 人物状态时间线。
- 章节爽点/钩子评分。
- 小说改短视频脚本。
- 小说改有声书工作流。
- 角色对手戏生成器。
- 事件因果合理性推演。
- 全书完结后自动生成简介、章节梗概和人物百科。

