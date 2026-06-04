# 剧情续写图谱 Obsidian 化改造方案

## 背景

当前剧情续写模块已经具备人物关系图和事件因果图，但视觉与交互更接近流程图编辑器：

- 前端 `NovelCharacterGraph.vue`、`NovelEventGraph.vue` 使用 `@vue-flow/core`。
- 节点以白底矩形卡片展示，连线由 Vue Flow edge 渲染。
- 自动布局是简单网格或依赖已保存坐标。
- 后端 `server/routes/novels/graph.py` 返回基础 `nodes` / `edges`，并通过 `/graph/layout` 保存 `node_x` / `node_y`。

这套实现适合“编辑流程”，但不适合长篇小说的关系探索。用户预期应更接近 Obsidian Graph View：暗色无边界画布、力导向布局、点状节点、关系网络自然聚集、缩放平移、搜索过滤、邻居高亮、点击后查看详情。

## 改造目标

将图谱工作区改造成 **小说知识网络探索器**，核心体验类似 Obsidian 图谱：

- 人物、势力、地点、物品、事件以节点形式出现在同一类网络画布中。
- 节点按关系强度、事件因果、章节距离自然聚集。
- 支持缩放、平移、拖拽、搜索、过滤、悬浮高亮、点击聚焦。
- 人物关系图和事件因果图保留独立入口，但交互语言统一。
- 保留图谱编辑能力，不把图谱降级成只读展示。
- 后端继续维护真实实体、关系、事件、因果关系，前端只负责图谱投影和交互状态。

## 非目标

本次不建议重写小说知识库核心模型：

- 不删除现有 `NovelEntity`、`NovelRelation`、`NovelEvent`、`NovelEventRelation`。
- 不改变 AI 提取图谱变更的主流程。
- 不把人物关系和事件因果合并成单表，除非后续做全局知识图谱引擎。
- 不为了视觉效果牺牲人工编辑、变更确认和后端一致性。

## 当前问题

### 1. 图谱视觉不符合知识网络预期

Vue Flow 默认样式强调流程节点和边，矩形卡片会让人物关系图看起来像低密度流程图，而不是知识网络。

问题表现：

- 节点过大，几十个节点后画布拥挤。
- 关系线标签占用空间，网络阅读被文字干扰。
- 白底卡片和编辑器节点视觉太强，不像 Obsidian 的轻量节点。
- 缺少整体网络感、聚类感和探索感。

### 2. 布局能力不足

当前 `handleAutoLayout` 是网格布局，无法表达：

- 关系强弱。
- 人物中心性。
- 势力或阵营聚类。
- 事件时间线和因果方向。
- 孤立节点、桥接节点、核心节点的差异。

### 3. 图谱数据缺少展示元信息

后端当前返回基础字段：

人物节点：

- `id`
- `type`
- `name`
- `importance`
- `x`
- `y`
- `summary`

人物边：

- `id`
- `source`
- `target`
- `type`
- `label`
- `strength`
- `status`

事件节点和边类似。前端要做 Obsidian 风格图谱，还需要：

- 节点权重。
- 节点度数。
- 最近出现章节。
- 阵营、地点、世界观分类。
- 是否孤立。
- 是否与当前章节相关。
- 是否有未确认 AI 变更。
- 图谱过滤统计。

这些可以前端临时计算一部分，但建议后端提供标准化 graph projection，避免多处重复推断。

### 4. 编辑与探索混在一起

当前图谱工具栏只有新增、保存、自动布局。Obsidian 风格图谱需要区分两类模式：

- 探索模式：浏览、搜索、过滤、聚焦、查看邻居。
- 编辑模式：新增节点、创建关系、调整关系、保存布局。

如果不区分，用户很容易在探索图谱时误触编辑操作。

## 推荐技术路线

### 前端渲染选型

建议新增一层图谱渲染组件，不继续用 Vue Flow 承担 Obsidian 风格图谱主画布。

推荐方案：

- 使用 `d3-force` 负责力导向布局。
- 使用原生 SVG 或 Canvas 渲染。
- 中小图谱先用 SVG，后续节点超过 500 再切 Canvas。

理由：

- `d3-force` 很适合关系网络布局。
- SVG 便于做 hover、click、label、tooltip、selection。
- 当前小说图谱大概率是几十到几百节点，SVG 性能足够。
- Vue Flow 更适合节点编辑器，不适合模拟 Obsidian Graph View 的轻节点网络。

可选依赖：

```bash
cd web
pnpm add d3-force d3-zoom d3-drag d3-selection
```

如果希望依赖更少，也可以直接安装 `d3`，但建议按模块安装。

### 前端组件拆分

新增组件：

- `web/src/components/novel/graph/ObsidianGraphCanvas.vue`
- `web/src/components/novel/graph/GraphToolbar.vue`
- `web/src/components/novel/graph/GraphFilters.vue`
- `web/src/components/novel/graph/GraphLegend.vue`
- `web/src/components/novel/graph/GraphInspector.vue`
- `web/src/components/novel/graph/useForceGraph.js`
- `web/src/components/novel/graph/graphProjection.js`

保留入口组件：

- `NovelCharacterGraph.vue`
- `NovelEventGraph.vue`

但它们不再直接渲染 Vue Flow，而是负责加载数据、传入模式和处理编辑动作。

推荐结构：

```text
NovelCharacterGraph.vue
  -> GraphToolbar.vue
  -> GraphFilters.vue
  -> ObsidianGraphCanvas.vue
  -> GraphInspector.vue

NovelEventGraph.vue
  -> GraphToolbar.vue
  -> GraphFilters.vue
  -> ObsidianGraphCanvas.vue
  -> GraphInspector.vue
```

## 目标交互

### 1. 画布

画布效果：

- 深色背景。
- 节点是圆点或小胶囊，不再是大卡片。
- 节点大小由权重决定。
- 连线默认细线，颜色和透明度由关系类型、强度、状态决定。
- 默认只显示关键节点标签，缩放或 hover 时显示更多标签。
- 当前选中节点及其一跳邻居高亮，其他节点淡化。

基础操作：

- 鼠标滚轮缩放。
- 拖动画布平移。
- 拖拽节点固定位置。
- 双击节点进入聚焦。
- 点击空白处取消选中。
- 点击节点打开右侧详情。
- 点击边打开关系详情。

### 2. 搜索

顶部搜索框：

- 支持按名称、别名、摘要搜索。
- 输入时匹配节点高亮。
- 回车聚焦第一个匹配节点。
- 搜索结果列表可快速跳转。

### 3. 过滤

人物图过滤：

- 人物 / 势力 / 地点 / 道具。
- 关系类型：师徒、同盟、敌对、亲属、恋人、背叛、其他。
- 关系状态：active、hidden、deprecated。
- 重要性范围。
- 是否只看当前章节相关。
- 是否只看未确认 AI 变更相关。

事件图过滤：

- 事件类型。
- 章节范围。
- 因果关系类型：causes、drives、blocks、reverses、reveals、escalates。
- 置信度范围。
- 是否只显示主线事件。

### 4. 模式切换

图谱顶部提供模式切换：

- `探索`
- `编辑`

探索模式：

- 默认模式。
- 不显示新增关系的交互锚点。
- 点击节点/边只查看详情。
- 可以固定节点位置，但保存布局需要明确点击。

编辑模式：

- 显示新增节点、新增关系、删除关系、保存布局。
- 支持从一个节点拖到另一个节点创建关系。
- 创建关系后弹窗选择关系类型、标签、描述、强度。

### 5. 右侧详情

点击人物节点：

- 名称、类型、重要性。
- 摘要、别名、属性。
- 关系列表，按入边/出边分组。
- 最近关联事件。
- 操作：编辑、删除、以此为中心聚焦、隐藏其他节点。

点击人物关系边：

- 源人物、目标人物。
- 关系类型、标签、强度、状态。
- 描述和证据。
- 操作：编辑、删除、反转方向、标记隐藏。

点击事件节点：

- 标题、类型、章节、时间线顺序。
- 摘要、参与者、地点、影响。
- 前因和后果。
- 操作：编辑、聚焦因果链。

点击事件关系边：

- 源事件、目标事件。
- 关系类型、置信度、描述。
- 操作：编辑、删除。

## 前端状态设计

在 `web/src/stores/novels.js` 中新增图谱 UI 状态，避免散落在组件内部：

```js
graphView: {
  mode: 'explore',
  query: '',
  focusedNodeId: null,
  selectedNodeId: null,
  selectedEdgeId: null,
  hoveredNodeId: null,
  hoveredEdgeId: null,
  filters: {
    nodeTypes: [],
    edgeTypes: [],
    chapterRange: null,
    minImportance: 0,
    minStrength: 0,
    currentChapterOnly: false,
  },
  layout: {
    running: true,
    pinnedNodeIds: [],
    zoom: 1,
  },
}
```

注意：

- `selectedEntityId`、`selectedRelationId`、`selectedEventId` 可以继续保留，兼容现有 inspector。
- 新图谱内部统一使用 `selectedNodeId` / `selectedEdgeId`，再由入口组件映射到实体或事件。
- 节点 id 必须统一字符串化，例如 `entity:12`、`event:34`，避免人物和事件 id 冲突。

## 前端数据投影

新增 `graphProjection.js`，将后端领域数据转换成统一图谱数据：

```js
{
  nodes: [
    {
      id: 'entity:12',
      rawId: 12,
      kind: 'entity',
      type: 'character',
      label: '沈青',
      summary: '...',
      weight: 8,
      degree: 5,
      x: 120,
      y: -40,
      pinned: false,
      raw: {}
    }
  ],
  edges: [
    {
      id: 'relation:9',
      rawId: 9,
      kind: 'relation',
      source: 'entity:12',
      target: 'entity:18',
      type: '师徒',
      label: '师徒',
      weight: 0.8,
      directed: false,
      raw: {}
    }
  ]
}
```

人物图投影：

- `NovelEntity` -> `kind: 'entity'`
- `NovelRelation` -> `kind: 'relation'`
- `importance` 映射节点大小。
- `strength` 映射边宽和力导向距离。

事件图投影：

- `NovelEvent` -> `kind: 'event'`
- `NovelEventRelation` -> `kind: 'event_relation'`
- `timeline_order` 可影响初始 x 轴位置。
- `confidence` 映射边透明度。
- 事件边默认 `directed: true`，用箭头或边尾渐变表达方向。

## 力导向布局规则

### 人物关系图

建议力参数：

- `forceManyBody`: -180 到 -420，节点越多斥力越大。
- `forceLink.distance`: 根据关系强度计算，强关系更近。
- `forceCenter`: 居中。
- `forceCollide`: 节点半径 + label 安全距离。

关系强度映射：

```text
strength 0.0 -> distance 220
strength 0.5 -> distance 150
strength 1.0 -> distance 80
```

节点大小：

```text
importance 1-3  -> 4px
importance 4-6  -> 6px
importance 7-8  -> 8px
importance 9-10 -> 11px
```

### 事件因果图

事件图既要自然聚集，也要保留时间/因果方向。

建议混合布局：

- `forceLink` 表达因果链。
- `forceManyBody` 避免拥挤。
- `forceX` 根据 `timeline_order` 或章节号给事件一个时间轴倾向。
- `forceY` 根据事件类型轻微分层。

这样事件图会接近“横向时间 + 局部因果网络”，比纯 Obsidian 随机团块更适合剧情审查。

## 后端改造方案

### 1. 保留现有接口

继续保留：

- `GET /api/novels/<project_id>/graph/characters`
- `GET /api/novels/<project_id>/graph/events`
- `PUT /api/novels/<project_id>/graph/layout`

这样前端可以渐进迁移，不破坏现有调用。

### 2. 扩展 graph response

现有接口可以增加字段，但不删除旧字段。

人物节点增加：

```json
{
  "degree": 5,
  "in_degree": 2,
  "out_degree": 3,
  "recent_chapter_id": 28,
  "recent_chapter_title": "夜雨入山",
  "has_pending_change": true,
  "tags": ["主角", "青云宗"],
  "last_seen_at": "2026-06-04T10:00:00Z"
}
```

人物边增加：

```json
{
  "source_name": "沈青",
  "target_name": "陆雪",
  "evidence_count": 3,
  "chapter_ids": [12, 18, 28],
  "has_pending_change": false
}
```

事件节点增加：

```json
{
  "chapter_title": "夜雨入山",
  "participant_names": ["沈青", "陆雪"],
  "location_name": "青云宗后山",
  "in_degree": 1,
  "out_degree": 2,
  "has_pending_change": false
}
```

事件边增加：

```json
{
  "source_title": "沈青入山",
  "target_title": "师姐护短",
  "chapter_span": [3, 4],
  "evidence_count": 1
}
```

### 3. 新增统一图谱投影接口

建议新增：

```http
GET /api/novels/<project_id>/graph/projection?type=characters
GET /api/novels/<project_id>/graph/projection?type=events
GET /api/novels/<project_id>/graph/projection?type=mixed
```

返回前端可直接渲染的统一结构：

```json
{
  "type": "characters",
  "nodes": [],
  "edges": [],
  "stats": {
    "node_count": 36,
    "edge_count": 58,
    "isolated_count": 4,
    "pending_change_count": 6,
    "max_degree": 12
  },
  "legend": {
    "node_types": ["character", "faction", "location", "item"],
    "edge_types": ["师徒", "同盟", "敌对"]
  }
}
```

好处：

- 前端图谱组件不必理解所有后端表结构。
- 后续做混合图谱时不用推翻前端。
- 后端可统一计算 degree、pending change、统计信息。

### 4. 新增邻居接口

用于点击节点后快速加载详情和邻居：

```http
GET /api/novels/<project_id>/graph/neighborhood?node_id=entity:12&depth=1
```

返回：

```json
{
  "center": {},
  "nodes": [],
  "edges": [],
  "stats": {}
}
```

用途：

- 大图谱性能优化。
- 聚焦一个角色的一跳/二跳关系。
- 后续可支持“只看与当前章节相关的局部图谱”。

### 5. 布局保存升级

现有 `/graph/layout` 只保存实体和事件坐标。建议扩展为统一 layout payload：

```json
{
  "graph_type": "characters",
  "positions": [
    {
      "id": "entity:12",
      "x": 120,
      "y": -40,
      "pinned": true
    }
  ]
}
```

兼容策略：

- 后端继续支持旧字段 `entity_positions`、`event_positions`。
- 新字段 `positions` 优先。
- `pinned` 如果暂时不入库，可先只保存在 localStorage，后续再加字段。

### 6. 是否需要新增数据库字段

第一阶段不必须新增字段。

可继续复用：

- `NovelEntity.node_x`
- `NovelEntity.node_y`
- `NovelEvent.node_x`
- `NovelEvent.node_y`

第二阶段建议增加：

- `node_pinned`：用户手动固定节点。
- `last_seen_chapter_id`：最近出现章节。
- `graph_tags_json`：图谱显示标签。

如果不想改表，可以先通过后端查询实时计算或从 `attributes_json` / `effects_json` 中读取。

## API 兼容策略

迁移期建议三步：

1. 旧接口保持不变，新前端先使用旧接口 + 本地投影。
2. 后端新增 `projection` 接口，前端切换到统一图谱数据。
3. 稳定后再考虑让旧 `characters/events` 接口只承担领域 CRUD，图谱渲染统一走 `projection`。

这能降低一次性改动风险。

## 实施步骤

### 阶段一：前端 Obsidian 视觉替换

目标：不改后端接口，先把视觉和交互做对。

任务：

- 新增 `ObsidianGraphCanvas.vue`。
- 新增 `graphProjection.js`，把现有 nodes/edges 转成统一 graph 数据。
- 在 `NovelCharacterGraph.vue` 中替换 Vue Flow 渲染。
- 在 `NovelEventGraph.vue` 中替换 Vue Flow 渲染。
- 实现缩放、平移、拖拽节点、点击选择、hover 邻居高亮。
- 实现基础 toolbar：搜索、重置视图、运行/暂停布局、保存布局。

验收：

- 人物图不再是矩形卡片流程图。
- 节点形成自然网络。
- 点击人物仍能驱动现有 `selectedEntityId`。
- 点击关系仍能驱动现有 `selectedRelationId`。
- 保存布局仍写入现有 `/graph/layout`。

### 阶段二：探索与过滤能力

目标：让图谱具备 Obsidian 式探索能力。

任务：

- 增加搜索框。
- 增加节点类型、边类型、重要性、章节范围过滤。
- 增加一跳邻居高亮。
- 增加“只看选中节点邻居”。
- 增加图例。
- 右侧 inspector 显示节点邻居和关系列表。

验收：

- 大量人物时可以快速找到目标角色。
- 选中角色后能看清直接关系。
- 事件图可以按章节范围查看局部因果。

### 阶段三：后端图谱投影接口

目标：后端提供更适合图谱渲染的数据。

任务：

- 新增 `GET /graph/projection`。
- 后端计算 degree、in_degree、out_degree。
- 后端补充关系双方名称、事件参与者名称、章节标题。
- 后端返回 stats 和 legend。
- 增加接口测试。

验收：

- 前端不再需要重复计算基础统计。
- graph toolbar 可以显示节点数、边数、孤立节点数。
- 图谱渲染数据结构对人物图和事件图一致。

### 阶段四：编辑模式补全

目标：保留图谱可编辑能力。

任务：

- 探索/编辑模式切换。
- 编辑模式新增节点。
- 编辑模式从节点拖拽创建关系。
- 关系创建弹窗接入现有 `createRelation` / `createEventRelation`。
- 节点和关系编辑复用现有 inspector 或新增表单。
- 删除关系前确认。

验收：

- 用户可以在新图谱上完成原 Vue Flow 中已有的新增人物、新增关系、保存布局。
- 新增关系后图谱即时刷新。
- AI 图谱变更确认后，新节点和新关系能自然进入图谱。

### 阶段五：混合知识图谱

目标：把人物、地点、势力、事件连接起来，形成真正的小说知识网络。

任务：

- `projection?type=mixed` 返回实体和事件。
- 事件参与者生成 `entity -> event` 或 `event -> entity` 辅助边。
- 地点实体与事件生成 location 边。
- 当前章节上下文高亮。
- 支持从章节编辑器打开“本章相关图谱”。

验收：

- 用户能看到某章涉及哪些人、在哪里、导致了什么事件。
- 续写前可以用图谱检查人物和事件一致性。

## 测试方案

### 前端验证

运行：

```bash
cd web
pnpm run build
```

建议补充组件级或轻量测试：

- `graphProjection.js` 可以单测。
- 输入空节点、孤立节点、多关系、重复关系、事件有向边都应稳定输出。
- 过滤逻辑可以单测。

如果项目暂未配置前端测试，不强行引入完整测试框架，先保证投影函数是纯函数，后续再接 Vitest。

### 后端验证

新增或扩展：

- `server/tests/test_novel_graph.py`

测试点：

- `GET /graph/characters` 保持兼容旧字段。
- `GET /graph/events` 保持兼容旧字段。
- `GET /graph/projection?type=characters` 返回统一 nodes/edges/stats。
- `GET /graph/projection?type=events` 返回统一 nodes/edges/stats。
- degree 统计正确。
- pending change 标记正确。
- `/graph/layout` 同时支持旧 payload 和新 payload。

运行：

```bash
uv run pytest server/tests/test_novel_graph.py -v
```

## 性能策略

### 第一阶段

适配规模：

- 0 到 200 节点：SVG + d3-force。
- 200 到 500 节点：降低 label 数量，默认只显示核心节点 label。

### 第二阶段

如果图谱超过 500 节点：

- 默认只加载当前章节相关子图。
- 支持 neighborhood 接口按需加载。
- Canvas 替代 SVG 主渲染。
- SVG 只渲染选中节点、tooltip 和 label。

## 视觉规范

建议主视觉：

- 背景：`#0f1117` 或与当前应用暗色变量对齐。
- 普通节点：低饱和蓝灰。
- 主角/高重要性人物：更亮、更大。
- 势力：偏紫或青色。
- 地点：偏绿色。
- 事件：偏橙色。
- 敌对关系：红色。
- 同盟关系：绿色。
- 因果推进：蓝色。
- 阻碍/反转：橙红色。

标签策略：

- 默认只显示重要性高或 degree 高的节点。
- hover 显示当前节点和一跳邻居标签。
- zoom 大于阈值后显示更多标签。
- 边标签默认隐藏，选中或 hover 时显示。

## 风险与处理

### 风险一：力导向布局每次打开都变化

处理：

- 初次布局使用 force simulation。
- 用户拖拽后标记 pinned。
- 保存布局后优先使用保存坐标。
- 未保存布局变动时提示。

### 风险二：事件图失去时间线阅读感

处理：

- 事件图不要使用纯自由网络。
- 加入 `forceX`，按 `timeline_order` 或章节号分布。
- 提供“因果网络 / 时间轴”视图切换。

### 风险三：图谱编辑误操作

处理：

- 默认探索模式。
- 编辑操作必须切到编辑模式。
- 删除节点、删除边必须确认。
- AI 提取变更仍走确认列表，不直接在图谱上静默落库。

### 风险四：前端计算过重

处理：

- 第一阶段前端计算 degree 可以接受。
- 后端 projection 接口上线后，把统计和聚合移到后端。
- 大图谱引入局部加载。

## 推荐最终状态

完成后，剧情续写图谱模块应形成三层能力：

1. 领域层：后端维护人物、关系、事件、因果、AI 变更。
2. 投影层：后端或前端把领域数据转换成统一 graph projection。
3. 体验层：前端用 Obsidian 风格画布完成探索、过滤、聚焦和编辑。

这样既能满足“像 Obsidian 一样看图谱”的直观期待，又不会破坏小说续写模块最重要的能力：长期一致性、人工确认、可编辑知识库和 AI 图谱提取闭环。

