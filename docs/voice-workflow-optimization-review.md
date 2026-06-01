# 配音工作台工作流优化审查

审查日期：2026-05-29

## 结论

当前配音工作台已经具备第一版主链路：新建工程、导入文本、自动切句、画布展示、节点参数编辑、单句试听、整条试听、导出 ZIP。后端相关测试通过，前端也能完成生产构建。

但从“可稳定交付给剪映/CapCut 视频编辑使用”的角度看，还需要优先补齐五类问题：画布拖拽持久化、线性路径语义一致性、试听与导出缓存复用、音色与表演参数入口、长任务与错误反馈。下面按优先级整理。

## 已验证情况

- 后端配音工作台相关测试通过：`uv run pytest server/tests/test_voice_workflow_service.py server/tests/test_voice_workflows_routes.py server/tests/test_emotion_planner.py server/tests/test_audio_postprocess.py -q`，结果 `19 passed`。
- 前端构建通过：`pnpm run build`。
- 构建有体积警告：主 JS chunk 约 `1.86 MB`，gzip 后约 `576 KB`，后续建议做路由级拆包。

## 当前工作流

1. 用户进入 `/voice-workflows/new` 时，前端会立即创建一个空工程并跳转到真实 ID 页面。
2. 用户粘贴文本或选择已有文本后，需要再点击“自动切句”生成语句节点。
3. 节点参数在右侧检查器修改，前端把文本、情绪、语速、音量、停顿等字段标记为影响音频。
4. 单句试听会在临时节点场景下先保存一次，再调用后端试听接口。
5. 导出前端会先保存完整 snapshot，再调用后端导出接口生成 ZIP。
6. 后端导出按 `order_index` 排序合成音频，并生成完整音频、SRT、manifest 和分段 WAV。

## P0：建议优先修正

### 1. 画布节点拖拽位置可能不会持久化

代码里已经定义了 `handleNodesChange()` 并向父组件发出 `move` 事件，但 `<VueFlow>` 只绑定了 `@edges-change`，没有绑定节点变化事件。参考：`web/src/components/voice-workflow/VoiceFlowCanvas.vue:23-33`、`web/src/components/voice-workflow/VoiceFlowCanvas.vue:160-167`。

影响：用户拖动节点后，`node_x/node_y` 可能不会进入 store；保存刷新后画布位置回退，容易被认为“保存坏了”。

建议：
- 绑定 `@nodes-change="handleNodesChange"`。
- 加一个前端或浏览器测试：拖动节点、保存、刷新后坐标保持一致。

### 2. 线性路径语义还不够一致

后端 `validate_linear_edges()` 目前只检查引用、自环、入度和出度，没有检查“必须是一条完整链路”、环路、孤立节点，也没有返回基于边关系的真实顺序。参考：`server/services/voice_workflow_service.py:24-41`。

同时，试听整条路径和导出都直接使用 `ordered_segments()`，也就是按 `order_index` 排序，而不是按边遍历。参考：`server/routes/voice_workflows.py:145`、`server/routes/voice_workflows.py:189`、`server/services/voice_workflow_service.py:140-141`。

影响：用户手动连线后，画布看到的箭头顺序可能和导出音频顺序不一致；某些环路或断链数据也可能保存后在导出时表现异常。

建议：
- 后端新增 `resolve_linear_path(workflow)`：检查 exactly one head、无环、覆盖全部节点，并返回按边关系排列的 segments。
- 导出、整条试听、manifest 都使用这个解析结果。
- 前端 `addEdge()` 同步限制一个前驱/一个后继，失败时直接提示，不要等保存接口报错。参考：`web/src/stores/voiceWorkflows.js:142-158`。
- 如果第一版决定“线性只按顺序，不让用户自由连线”，那就把箭头改成展示性连接，避免用户误以为箭头可决定播放路径。

### 3. 保存策略会破坏音频缓存复用

当前保存 snapshot 会删除所有旧 segment，再重建新 segment。参考：`server/services/voice_workflow_service.py:94-108`。导出缓存路径又依赖新的 `segment.id`：`outputs/voice_workflow_cache/<workflow_id>/<segment.id>.wav`。参考：`server/routes/voice_workflows.py:196-201`。

影响：
- 只改标题或移动节点也可能导致 segment ID 变化，进而缓存路径变化。
- 单句试听返回的音频没有写入后端缓存，也没有持久更新 DB；前端只是本地把节点标成 `ready`。参考：`web/src/stores/voiceWorkflows.js:204-217`、`server/routes/voice_workflows.py:119-132`。
- 用户试听通过的一句，导出时仍可能重新合成，成本和等待时间都偏高。

建议：
- 保存时保留已有 segment ID，按 `id/client_id` 做 upsert，而不是全量删除重建。
- 或者把缓存文件名改为 fingerprint，不依赖 segment ID。
- 单句试听可选择写入缓存，并返回 `audio_url` / `cached: true`；导出可直接复用试听音频。
- `export_options.reuse_cache` 应真正控制是否复用缓存。

### 4. 音色和表演参数入口不完整

模型已经支持 `default_voice_profile_id`、`voice_profile_id`、`pitch`、`delivery_instruction`、`transition` 等字段，但右侧检查器只暴露了文本、4 个情绪、强度、语速、音量、段前/段后停顿。参考：`web/src/components/voice-workflow/SegmentInspector.vue:5-33`。

导入已有文本时也只复制了正文，没有设置 `source_text_id`。参考：`web/src/views/VoiceWorkflowView.vue:145-162`。

影响：用户很难完成“每句切换音色/角色、补充表演指令、调整音高”的真实配音工作流；已有文本和配音工程之间的来源关系也丢失。

建议：
- 复用现有 `VoiceProfileSelector`，提供工程默认音色和单句覆盖音色。
- 右侧检查器补齐 `pitch`、`transition`、`delivery_instruction`。
- 情绪选项与后端 `EMOTION_PRESETS` 对齐，至少补上 `sad`、`excited`、`whisper`。参考：`server/services/emotion_planner.py:7-16`。
- 从文本库导入时写入 `source_text_id`，列表页可显示来源文本标题。

### 5. 同步试听/导出缺少长任务体验和失败恢复

整条试听和导出会逐句同步调用 TTS。参考：`server/routes/voice_workflows.py:145-159`、`server/routes/voice_workflows.py:189-231`。一旦 TTS 报错、音频参数不一致或网络超时，当前路由没有统一错误包装，前端也没有分段进度、取消、重试。

影响：长文本导出容易卡住；失败后用户不知道失败在哪一句，也很难只重试失败段。

建议：
- 第一阶段至少返回结构化错误：`segment_id`、`order_index`、`message`。
- 第二阶段升级为 job：创建导出任务、轮询进度、逐段状态、失败重试。
- 前端底部时间线展示每句状态：缺失、生成中、已缓存、失败。

## P1：完善工作流体验

### 保存状态需要真实 dirty 状态

工具栏目前只根据 `saving` 显示“保存中/已保存”。参考：`web/src/components/voice-workflow/WorkflowToolbar.vue:3-11`。但 store 没有 `dirty` 状态，用户修改正文、节点、参数后仍可能看到“已保存”。

建议：
- store 增加 `dirty`、`lastSavedAt`、`saveError`。
- 所有影响 snapshot 的操作都标记 dirty。
- 页面离开前提示未保存；导出前如果自动保存失败，应停止导出并提示。

### 时间线还不能承担审片功能

底部时间线只显示句数、情绪和三个按钮。参考：`web/src/components/voice-workflow/TimelineAuditionBar.vue:1-20`。

建议：
- 显示每段预计/实际时长、停顿、音色、生成状态。
- 整条试听后复用返回的 timeline，显示 SRT 片段边界。
- 支持点击某段从对应时间播放，而不是只能整条从头播放。

### 整条试听的总时长不含停顿

`audition-path` 返回的 `total_duration` 是 `sum(durations)`，没有包含段前/段后停顿。参考：`server/routes/voice_workflows.py:168-172`。实际拼接音频由 `concat_emotional_wavs()` 写入了停顿。参考：`server/services/audio_postprocess.py:45-51`。

建议：以拼接 WAV 的帧数或 timeline 最后结束时间为准返回总时长。

### 导出选项和字幕选项需要真正生效

设计文档里有 `subtitle_options`、`export_options.reuse_cache`、`export_options.include_segment_wavs`，当前导出接口没有读取这些选项，而是始终按 workflow settings 和固定行为执行。参考：`server/routes/voice_workflows.py:176-243`。

建议：
- 支持请求级覆盖 `subtitle_options.max_chars`。
- `include_segment_wavs=false` 时不写入分段 WAV。
- `reuse_cache=false` 时强制重新合成并刷新缓存。

### 输入校验需要更靠前

`segments/plan` 直接 `int(data.get('max_chars', 80))`，非法输入会变成 500。参考：`server/routes/voice_workflows.py:91-97`。

建议：
- 复用 `_clamp_int()` 或增加 request parser。
- 对 settings、segment 参数、空工程导出、过长文本都返回 400 和明确错误。

### 前端构建体积偏大

当前构建通过，但 Vite 提示 chunk 大于 500 KB，主 JS 约 `1.86 MB`。

建议：
- 对 `/voice-workflows`、`/discovery`、视频生成等大页面做路由级 dynamic import。
- Vue Flow 相关组件只在配音工作台路由加载。

## P2：后续增强

- 列表页增加搜索、删除、复制工程、空状态、更新时间格式化。当前只显示标题和原始 `updated_at`。参考：`web/src/views/VoiceWorkflowList.vue:1-16`。
- 增加“重新生成缺失音频”和“只生成失败段”。
- 增加缓存清理策略：按工程删除、按 fingerprint 去重、按大小/时间清理。
- `build_segment_delivery_instruction()` 目前主要使用 emotion、rate、volume，建议把 `intensity` 和 `pitch` 也显式写入表演提示。参考：`server/services/emotion_planner.py:104-146`。
- 增加前端测试或浏览器回归：拖拽保存、导入文本、手动连线、试听按钮参数、导出按钮错误态。
- 增加后端测试：环路、断链、导出按边顺序、`reuse_cache=false`、`include_segment_wavs=false`、试听缓存复用、非法 `max_chars`。

## 建议实施顺序

### Phase 1：先修可信度

1. 修复画布拖拽持久化。
2. 明确线性路径唯一来源：按边解析，或禁止用户自由改播放边。
3. 增加真实 dirty/save/error 状态。
4. 导出前做完整校验，失败时不要开始 TTS。

### Phase 2：补齐真实配音能力

1. 接入工程默认音色和单句音色选择。
2. 补齐 pitch、transition、delivery instruction。
3. 打通单句试听缓存到导出复用。
4. 让导出选项、字幕选项真正生效。

### Phase 3：提升长文本生产体验

1. 导出改为 job。
2. 时间线展示逐段进度、失败和重试。
3. 路由级拆包，降低首屏 JS。
4. 增加浏览器级工作流回归测试。

## 验收清单

- 拖动一个节点，保存并刷新后位置不变。
- 手动连线后的播放顺序、时间线顺序、导出音频顺序、manifest 顺序一致。
- 存在环路、断链、孤立节点时，保存或导出给出明确错误。
- 单句试听后，不改参数直接导出不会重复合成该句。
- 修改文本、情绪、音色、语速、音量、停顿后，对应段落缓存失效。
- 工程默认音色和单句音色都能保存、刷新恢复、参与合成。
- 导出失败能定位到具体句子。
- `include_segment_wavs=false` 的 ZIP 不包含 `segments/*.wav`。
- `reuse_cache=false` 会强制重新生成。
- 长文本导出有可见进度，不让用户误以为页面卡死。
