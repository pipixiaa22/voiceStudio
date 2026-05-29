# 线性配音工作台技术方案

## 背景

当前语音能力主要绑定在字幕同步包链路中：

```text
文本
-> split_text()
-> plan_speech_chunks()
-> TTSProvider.synthesize()
-> concat_wavs()
-> build_subtitle_timeline()
-> build_srt()
-> ZIP
```

已有方案 `2026-05-29-emotional-tts-segmentation-design.md` 解决的是“按字幕或语音块添加情绪参数”。本方案在它之上再抽出一层“配音工程”，让语音可以作为独立工作流被保存、编辑、试听和导出。

第一版只做线性旁白编排器。节点和箭头用于表达一句接一句的播放顺序，不做多分支、条件路径、并行对话或完整音频工作站。

## 目标

1. 新增独立“配音工作台”页面，支持可视化编辑线性旁白。
2. 每个语句节点可独立设置文本、情绪、强度、语速、音量、停顿和音色档案。
3. 支持从已有文本或粘贴文本生成初始语句节点。
4. 支持拖拽节点调整画布位置，用箭头显示前后关系。
5. 支持保存配音工程，后续可继续编辑。
6. 支持单句试听、整条路径试听、导出完整音频、SRT 和 manifest。
7. 复用现有 TTS、音色档案、字幕时间轴和 ZIP 打包能力。

## 非目标

1. 第一版不做分支工作流。
2. 第一版不做多轨音频编辑、逐字音高曲线、波形裁剪。
3. 第一版不强制做异步任务队列；长文本导出后续再升级为 job。
4. 第一版不替换 `VoiceSynthModal.vue`，而是保留快速生成入口。
5. 第一版不承诺所有 TTS provider 都能真实执行 pitch/rate；自然语言提示和音频后处理优先。

## 推荐方案

采用独立页面方案：

```text
/voice-workflows
/voice-workflows/new
/voice-workflows/:id
```

当前弹窗继续作为轻量入口。配音工作台负责高级编排、保存、试听和导出。后续视频生成、字幕生成可以读取同一个 voice workflow。

## 产品结构

### 页面布局

```text
顶部工具栏
  工程标题 / 保存状态 / 导入文本 / 自动切句 / 保存 / 导出

左侧 SourcePanel
  源文本
  节点库
  情绪预设
  批量操作

中间 VoiceFlowCanvas
  语句节点
  箭头连线
  节点拖拽
  选中态
  自动重排

右侧 SegmentInspector
  文本
  音色档案
  情绪
  强度
  语速
  音量
  段前/段后停顿
  转场/表演指令
  单句试听

底部 TimelineAuditionBar
  线性时间线
  试听选中句
  试听整条路径
  重新生成缺失音频
  导出同步包
```

### 交互规则

- 第一版校验每个节点最多一个前驱、一个后继。
- 拖拽画布节点只改变 `node_x/node_y`。
- 播放顺序由 `order_index` 和边关系共同保存；导出前以后端校验结果为准。
- 节点颜色由情绪决定，节点副标签显示音色档案。
- 修改文本、情绪、音色、语速、音量、停顿后，该节点音频缓存标记为失效。
- “自动重排”按 `order_index` 把节点排成可读的线性流程。

## 前端实现

### 路由

更新 `web/src/router/index.js`：

```js
{ path: '/voice-workflows', component: VoiceWorkflowList },
{ path: '/voice-workflows/new', component: VoiceWorkflowView },
{ path: '/voice-workflows/:id', component: VoiceWorkflowView },
```

第一版可以先不做完整列表页；导航进入 `/voice-workflows/new`，保存后跳转到 `/voice-workflows/:id`。

### 依赖

建议新增：

```bash
cd web && pnpm add @vue-flow/core
```

原因：

- 拖拽节点、连线、缩放、选中态是画布核心能力。
- 自研 SVG 连线和拖拽可行，但会把第一版时间消耗在基础交互细节上。
- 第一版仍限制为线性图，不使用复杂图算法。

### 组件拆分

```text
web/src/views/VoiceWorkflowView.vue
web/src/views/VoiceWorkflowList.vue
web/src/components/voice-workflow/WorkflowToolbar.vue
web/src/components/voice-workflow/SourcePanel.vue
web/src/components/voice-workflow/VoiceFlowCanvas.vue
web/src/components/voice-workflow/VoiceSegmentNode.vue
web/src/components/voice-workflow/SegmentInspector.vue
web/src/components/voice-workflow/TimelineAuditionBar.vue
web/src/stores/voiceWorkflows.js
```

### 状态模型

Pinia store 建议保存：

```js
{
  workflow: {
    id: null,
    title: '未命名配音工程',
    source_text_id: null,
    source_content: '',
    default_voice_profile_id: null,
    settings: {
      subtitle_max_chars: 20,
      chunk_max_chars: 200,
      provider: 'mimo'
    }
  },
  segments: [
    {
      id: 'tmp-1',
      order_index: 1,
      text: '我知道了。',
      node_x: 80,
      node_y: 120,
      emotion: 'calm',
      intensity: 0.3,
      rate: 0.95,
      pitch: -1,
      volume_db: 0,
      pause_before_ms: 0,
      pause_after_ms: 250,
      transition: 'normal',
      voice_profile_id: null,
      audio_status: 'missing',
      audio_url: null
    }
  ],
  edges: [
    { id: 'e1-2', source_segment_id: 1, target_segment_id: 2, order_index: 1 }
  ],
  selectedSegmentId: 1,
  dirty: false,
  saving: false,
  exporting: false
}
```

### API 客户端

在 `web/src/api/index.js` 新增：

```js
export const voiceWorkflowsApi = {
  list: () => api.get('/voice-workflows'),
  create: (data) => api.post('/voice-workflows', data),
  get: (id) => api.get(`/voice-workflows/${id}`),
  update: (id, data) => api.put(`/voice-workflows/${id}`, data),
  delete: (id) => api.delete(`/voice-workflows/${id}`),
  planSegments: (id, data) => api.post(`/voice-workflows/${id}/segments/plan`, data),
  auditionSegment: (id, segmentId, data) => api.post(`/voice-workflows/${id}/segments/${segmentId}/audition`, data),
  auditionPath: (id, data) => api.post(`/voice-workflows/${id}/audition-path`, data, { responseType: 'blob' }),
  exportPackage: (id, data) => api.post(`/voice-workflows/${id}/export`, data, { responseType: 'blob' }),
}
```

## 后端实现

### 数据模型

新增 `server/models/voice_workflow.py`。

#### VoiceWorkflow

```text
id
title
source_text_id nullable
source_content text
default_voice_profile_id nullable
settings_json text
created_at
updated_at
```

#### VoiceWorkflowSegment

```text
id
workflow_id
order_index
text
node_x
node_y
emotion
intensity
rate
pitch
volume_db
pause_before_ms
pause_after_ms
transition
delivery_instruction
voice_profile_id nullable
audio_status
audio_path nullable
audio_fingerprint nullable
created_at
updated_at
```

`audio_fingerprint` 根据文本、情绪参数、音色档案和 TTS 模型计算。参数变化后 fingerprint 不匹配，缓存失效。

#### VoiceWorkflowEdge

```text
id
workflow_id
source_segment_id
target_segment_id
order_index
```

第一版边表也可以被视为未来扩展点。即使当前是线性，也保留边关系，后续扩展分支时不用重做数据结构。

### API

新增 `server/routes/voice_workflows.py` 并在 `server/app.py` 注册蓝图。

```text
GET    /api/voice-workflows
POST   /api/voice-workflows
GET    /api/voice-workflows/<id>
PUT    /api/voice-workflows/<id>
DELETE /api/voice-workflows/<id>

POST   /api/voice-workflows/<id>/segments/plan
POST   /api/voice-workflows/<id>/segments/<segment_id>/audition
POST   /api/voice-workflows/<id>/audition-path
POST   /api/voice-workflows/<id>/export
```

### 请求响应要点

#### 创建工程

```json
{
  "title": "玄幻旁白配音",
  "source_text_id": 12,
  "source_content": "我知道了。可是你为什么现在才告诉我！",
  "default_voice_profile_id": 9
}
```

响应返回 workflow、segments、edges。若 `source_content` 不为空，可以直接按标点生成初始 segments。

#### 保存工程

`PUT /api/voice-workflows/<id>` 接收完整 workflow snapshot：

```json
{
  "workflow": { "title": "玄幻旁白配音", "settings": {} },
  "segments": [],
  "edges": []
}
```

后端采用 replace-by-snapshot：先校验，再在事务内更新工程、重建 segments/edges。第一版这样比逐个 patch 更简单可靠。

#### 单句试听

```json
{
  "api_key": "xxx",
  "segment": {
    "text": "可是你为什么现在才告诉我！",
    "emotion": "angry_burst",
    "intensity": 1.6,
    "rate": 1.15,
    "volume_db": 3,
    "pause_before_ms": 80,
    "pause_after_ms": 180,
    "voice_profile_id": 9
  }
}
```

响应：

```json
{
  "audio_base64": "UklGRiQAAABXQVZFZm10IBAAAAABAAEA",
  "duration": 2.2,
  "fingerprint": "sha256:segment-params-hash"
}
```

#### 导出

```json
{
  "api_key": "xxx",
  "subtitle_options": {
    "max_chars": 20
  },
  "export_options": {
    "reuse_cache": true,
    "include_segment_wavs": true
  }
}
```

响应仍为 ZIP。

### 服务层

新增：

```text
server/services/voice_workflow_service.py
server/services/emotion_planner.py
server/services/emotional_tts.py
server/services/audio_postprocess.py
```

#### voice_workflow_service.py

职责：

- workflow CRUD。
- snapshot 校验和保存。
- 线性路径校验。
- workflow segments 转 `EmotionSegment`。
- 导出 manifest。

关键函数：

```text
validate_linear_edges(segments, edges) -> list[int]
ordered_segments(workflow) -> list[VoiceWorkflowSegment]
save_workflow_snapshot(workflow_id, payload) -> dict
build_workflow_manifest(workflow, segments, timeline) -> dict
```

#### emotion_planner.py

复用情绪段落化方案中的 `EmotionSegment`、情绪枚举和规则识别。

额外提供：

```text
plan_workflow_segments(content: str, max_chars: int = 80) -> list[dict]
```

这里的 `max_chars` 是语句节点长度，不等于字幕 `max_chars`。节点可以比字幕长，导出时再按字幕规则拆分时间轴。

#### emotional_tts.py

职责：

- 构造段级表演指令。
- 组合 `build_voice_prompt()` 输出和 segment instruction。
- 调用 `TTSProvider.synthesize()`。
- 返回 wav bytes、duration、fingerprint。

第一版仍以 MiMo 自然语言 prompt 为主。

#### audio_postprocess.py

第一版支持：

- 每段 `pause_before_ms`
- 每段 `pause_after_ms`
- `volume_db` PCM 增益
- 防削波
- 拼接完整 WAV

第二阶段再做 fade、crossfade、LUFS、首尾静音裁剪。

## 导出流程

```text
POST /api/voice-workflows/<id>/export
  -> 读取 workflow
  -> 校验线性路径
  -> 生成 ordered segments
  -> 为每段解析 voice profile
  -> 构造 EmotionSegment
  -> 使用缓存或逐段 TTS
  -> audio_postprocess 拼接
  -> build_workflow_subtitle_timeline
  -> build_srt
  -> build_zip_package
  -> 返回 ZIP
```

字幕时间轴：

```text
current_time += pause_before_ms
segment_start = current_time
segment_end = segment_start + audio_duration
current_time = segment_end + pause_after_ms
```

如果一个语句节点拆成多个字幕段，按文本长度在该节点时长内分配。

## 与现有功能关系

### VoiceSynthModal

保留现状。后续可新增“打开高级编排”按钮：

```text
选择文本 -> 选择音色 -> 打开配音工作台
```

### sync-package-v2

保持兼容，不改变现有请求和响应。第一版工作台导出走新接口，内部复用公共服务。

### 视频生成

后续 `VideoGenerateModal.vue` 可以选择：

1. 使用当前输入文本直接生成旁白。
2. 选择已有 voice workflow，直接使用它导出的 voice audio 和 SRT timeline。

第一版只预留 manifest 和 API，不强行接入视频生成。

## Manifest

ZIP 中的 `manifest.json` 新增：

```json
{
  "title": "玄幻旁白配音",
  "source": "voice_workflow",
  "workflow_id": 1,
  "provider": "mimo",
  "segments": [
    {
      "id": 10,
      "order_index": 1,
      "text": "我知道了。",
      "emotion": "calm",
      "intensity": 0.3,
      "rate": 0.95,
      "volume_db": 0,
      "pause_before_ms": 0,
      "pause_after_ms": 250,
      "voice_profile_id": 9,
      "filename": "segments/001.wav"
    }
  ],
  "edges": [],
  "subtitles": [],
  "total_duration": 0
}
```

## 实施阶段

### Phase 1：数据模型与 API

- 新增 workflow/segment/edge 模型。
- 新增 CRUD API。
- 新增从文本生成初始 segments。
- 新增线性边校验。
- 测试覆盖模型序列化、创建、保存、读取、删除。

### Phase 2：前端工作台

- 新增路由和导航入口。
- 新增 Pinia store 和 API client。
- 新增工作台布局、画布节点、检查器、时间线。
- 支持导入文本、自动切句、保存工程。
- 第一版可先用 mock duration 展示时间线。

### Phase 3：试听与导出

- 新增单句试听。
- 新增整条路径试听。
- 新增导出 ZIP。
- 接入 `emotional_tts.py` 和 `audio_postprocess.py`。
- manifest 记录完整 workflow。

### Phase 4：增强与联动

- 音频缓存管理。
- 参数变更失效策略。
- 视频生成读取 workflow。
- 分支/多角色/多轨作为后续独立方案。

## 测试计划

### 后端单元测试

新增：

```text
server/tests/test_voice_workflow_service.py
server/tests/test_voice_workflows_routes.py
server/tests/test_emotion_planner.py
server/tests/test_audio_postprocess.py
```

覆盖：

- 创建工程时从文本生成 segments。
- 保存 snapshot 后 segments/edges 正确重建。
- 非线性边被拒绝。
- 节点参数 clamp 或校验。
- 修改参数后 audio fingerprint 变化。
- 导出 manifest 包含 workflow、segments、timeline。

### 前端验证

- 打开配音工作台。
- 导入文本并自动切句。
- 选择第二句，修改为爆发愤怒。
- 修改音色、语速、音量、停顿。
- 拖拽节点位置并保存。
- 刷新页面后工程恢复。
- 单句试听请求包含 segment 参数。
- 导出请求返回 ZIP。

## 风险

1. 引入 `@vue-flow/core` 会增加前端依赖，但可显著降低画布实现风险。
2. 同步导出长文本可能超时；如果超过当前 Flask 请求体验，需要升级为 job。
3. 自然语言 TTS 对情绪、语速、音高不一定稳定，必须保留用户手动试听和重生成。
4. 多段 TTS 可能声线漂移，需要在段级 prompt 中强调同一说话人。
5. 音频缓存如果只按文件路径判断，容易复用错误音频，必须使用 fingerprint。

## 结论

推荐第一版实现独立“配音工作台”，但严格限制为线性旁白编排器。

这条路线兼顾工程可控性和后续扩展性：当前字幕同步包链路不被破坏，新的 voice workflow 可以先服务配音导出，再逐步成为视频生成和剪映导出的统一语音来源。
