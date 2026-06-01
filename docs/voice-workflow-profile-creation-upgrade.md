# 配音工作台内创建音色档案改造方案

审查日期：2026-05-29

## 背景

配音工作台现在已经可以为工程设置默认音色，也可以为单句设置独立音色。但当前入口只支持“选择已有音色档案”，不能在工作台上下文里直接创建新音色。

这会打断真实工作流：用户编辑某一句时发现需要一个新角色音色，必须离开当前上下文去其他入口创建，再回到工作台刷新选择。对于多角色旁白、短剧对话、修仙角色配音，这个断点很明显。

现有语音合成链路已经有成熟能力：

- `VoiceProfileSelector.vue`：音色选择、搜索、筛选、试听、新建入口。
- `VoiceProfileDrawer.vue`：创建音色档案，支持文本设计和音色复刻。
- `voiceProfilesApi.create()`：创建音色档案。
- `voiceProfilesApi.audition()`：音色试听。
- `server/routes/voice_profiles.py`：后端已有创建、校验、试听接口。

因此本次改造不应重复实现音色创建逻辑，而应把现有音色档案创建能力以“工作台上下文友好”的方式接入配音工作台。

## 目标

1. 在配音工作台默认音色选择处，可以直接新建音色档案。
2. 在单句音色选择处，可以直接新建音色档案。
3. 新建成功后自动选中新音色，并应用到当前上下文。
4. 保持和语音合成入口一致的创建逻辑、字段校验、试听行为和授权样音规则。
5. 不新增后端 API，不重复创建另一套音色表单。

## 非目标

- 不改音色档案数据库结构。
- 不新增工作流专用音色类型。
- 不在第一版里做 AI 自动为每句生成新音色。
- 不把音色创建嵌入到画布节点内部弹层，避免画布交互复杂化。

## 推荐方案

推荐采用“复用 `VoiceProfileDrawer` + 增强 `VoiceProfileIdField`”的方案。

当前 `VoiceProfileIdField.vue` 是轻量 ID 选择器，只负责把选择结果保存为 `voice_profile_id`。建议把它升级成工作台通用音色字段组件：

```text
VoiceProfileIdField
  - 显示当前选择
  - 支持搜索已有音色
  - 支持跟随工程默认音色
  - 支持新建音色
  - 新建成功后自动 emit 新音色 id
```

组件内部继续复用：

```text
VoiceProfileDrawer.vue
voiceProfilesApi.list()
voiceProfilesApi.create()
voiceProfilesApi.audition()
```

这样可以保持语音合成和配音工作台两处的音色档案行为一致。

## 交互设计

### 工程默认音色

位置：`WorkflowToolbar.vue` 顶部工具栏。

建议展示：

```text
默认音色 [ 选择默认音色 v ] [ + ]
```

行为：

- 点击下拉选择已有音色。
- 点击 `+` 打开“新建音色”抽屉。
- 新建成功后：
  - 刷新音色列表。
  - 自动把 `workflow.default_voice_profile_id` 设置为新音色 ID。
  - 对所有“跟随默认音色”的句子标记为 `audio_status = missing`。
  - 不覆盖已经手动设置过 `segment.voice_profile_id` 的句子。

### 单句音色

位置：`SegmentInspector.vue` 的“本句音色”表单项。

建议展示：

```text
本句音色 [ 跟随默认：温柔女旁白 v ] [ + ] [恢复默认]
```

行为：

- 默认值为 `null`，表示跟随工程默认音色。
- 选择已有音色后写入 `segment.voice_profile_id`。
- 点击 `+` 打开“新建音色”抽屉。
- 新建成功后：
  - 刷新音色列表。
  - 自动把当前句子的 `voice_profile_id` 设置为新音色 ID。
  - 当前句子 `audio_status` 标记为 `missing`。
  - 节点卡片立即显示新音色名称。

### 新建音色抽屉

复用 `VoiceProfileDrawer.vue`。

建议在工作台上下文传入可选初始值：

```js
{
  scene: 'short_video',
  audition_text: 当前句子文本 || 默认试听文案,
  raw_description: '',
  source_type: 'voice_design'
}
```

如果从单句音色入口打开，试听文案优先使用当前句子文本。这样用户创建角色音色时，能直接用真实台词试听，而不是固定模板文案。

## 技术设计

### 组件职责

#### `VoiceProfileIdField.vue`

当前职责：

- 接收 `modelValue`。
- 展示已有 `profiles`。
- emit `update:modelValue`。

建议增强后职责：

- 内部或外部支持 `profiles` 刷新。
- 提供“新建音色”按钮。
- 打开 `VoiceProfileDrawer`。
- 处理 `created` 事件。
- 新建成功后 emit：

```js
emit('created', profile)
emit('update:modelValue', profile.id)
emit('change', profile.id)
```

建议新增 props：

```js
{
  canCreate: Boolean,
  createButtonLabel: String,
  createInitialValues: Object,
  createApplyMode: 'select' | 'default'
}
```

第一版只需要 `canCreate` 和 `createInitialValues`，避免过度抽象。

#### `VoiceWorkflowView.vue`

当前由页面拉取 `voiceProfiles` 并传给工具栏、画布和检查器。

建议新增统一刷新函数：

```js
const refreshVoiceProfiles = async () => {
  const { data } = await voiceProfilesApi.list({ active: 1 })
  voiceProfiles.value = data
  return data
}
```

向子组件传入：

```text
:voice-profiles="voiceProfiles"
:create-profile="true"
@profile-created="handleProfileCreated"
```

但更推荐让 `VoiceProfileIdField` 自己打开 drawer，父层只提供刷新回调或接收 `created` 事件即可。

#### `WorkflowToolbar.vue`

用于工程默认音色。

新增事件：

```js
update:defaultVoiceProfileId
voice-profile-created
```

新建成功后直接调用已有：

```js
store.updateDefaultVoiceProfile(profile.id)
```

#### `SegmentInspector.vue`

用于单句音色。

新建成功后调用已有：

```js
store.updateSegment(segment.id, { voice_profile_id: profile.id })
```

这会触发现有音频失效逻辑，因为 `voice_profile_id` 已在 `AUDIO_FIELDS` 中。

### 数据流

#### 新建工程默认音色

```text
用户点击默认音色旁的 +
-> VoiceProfileIdField 打开 VoiceProfileDrawer
-> 用户填写并保存
-> POST /api/voice-profiles
-> created(profile)
-> 刷新 voiceProfiles
-> updateDefaultVoiceProfile(profile.id)
-> 保存工程时写入 workflow.default_voice_profile_id
```

#### 新建单句音色

```text
用户选中句子
-> 右侧本句音色点击 +
-> VoiceProfileDrawer 使用当前句子作为 audition_text
-> POST /api/voice-profiles
-> created(profile)
-> 刷新 voiceProfiles
-> updateSegment(segment.id, { voice_profile_id: profile.id })
-> 保存工程时写入 segment.voice_profile_id
```

## 与语音合成逻辑保持一致

### 应复用的能力

- 文本设计音色：`source_type = voice_design`
- 音色复刻：`source_type = voice_clone`
- 授权样音确认：`consent_confirmed`
- 样音格式限制：mp3/wav
- 试听文案：`audition_text`
- 负向约束：`negative_prompt`
- 音频标签：`style_tags`
- 场景：`scene`

### 不应复制的逻辑

不要在配音工作台里重新实现：

- 文件转 Base64。
- 复刻授权校验。
- 创建表单字段集合。
- 试听 API 调用。
- 音色创建成功后的表单重置。

这些都应继续由 `VoiceProfileDrawer.vue` 和后端 `voice_profiles` 接口负责。

## 最佳实践要求

### 1. 单一事实来源

音色档案创建只保留一套组件和一套后端 API。配音工作台只是使用者，不拥有新的音色创建模型。

### 2. 保存 ID，不保存完整档案

工作流中仍只保存：

```text
workflow.default_voice_profile_id
segment.voice_profile_id
```

不要把完整 profile snapshot 写进 workflow。导出时后端按 ID 查询最新音色档案。

### 3. 新建后自动应用

用户从哪个入口点击“新建”，新音色就应用到哪个上下文：

- 默认音色入口：应用到工程默认音色。
- 单句音色入口：应用到当前句子。

不要只创建不选中，否则用户会以为创建失败。

### 4. 创建失败不污染当前选择

如果 `POST /api/voice-profiles` 失败：

- 不改变当前 `modelValue`。
- 不关闭抽屉。
- 显示后端错误。

### 5. 试听文案贴近上下文

单句入口创建音色时，默认试听文案应使用当前句子文本。工程默认入口可以使用现有默认试听文案。

### 6. 音频缓存正确失效

新建并应用音色后：

- 工程默认音色变化：未设置单句音色的句子失效。
- 单句音色变化：只有当前句子失效。

这与当前 `voice_profile_id` 属于 `AUDIO_FIELDS` 的策略一致。

### 7. 可访问性和反馈

- `+` 按钮需要明确 tooltip，例如“新建音色档案”。
- 保存中按钮 loading。
- 创建成功 toast。
- 创建失败显示后端错误。

## 推荐实现步骤

### Step 1：增强 `VoiceProfileDrawer`

文件：`web/src/components/VoiceProfileDrawer.vue`

建议新增 props：

```js
initialValues: { type: Object, default: () => ({}) }
```

当 drawer 打开时，把初始值合并到表单：

```js
watch(() => props.open, open => {
  if (open) applyInitialValues()
})
```

用途：

- 单句创建时注入 `audition_text: segment.text`
- 默认音色创建时注入 `scene: 'short_video'`

### Step 2：增强 `VoiceProfileIdField`

文件：`web/src/components/voice-workflow/VoiceProfileIdField.vue`

新增：

- `canCreate`
- `createInitialValues`
- 内部引入 `VoiceProfileDrawer`
- 新增 `showCreateDrawer`
- 创建成功后 emit `created`

建议 UI：

```text
[ a-select ] [ + ]
```

其中 `+` 使用 Ant Design Vue 的小按钮即可。

### Step 3：默认音色入口接入创建

文件：`web/src/components/voice-workflow/WorkflowToolbar.vue`

传入：

```text
can-create
:create-initial-values="{ scene: 'short_video' }"
@created="$emit('voice-profile-created', $event)"
```

父层 `VoiceWorkflowView.vue` 处理：

```js
const handleDefaultProfileCreated = async profile => {
  await fetchVoiceProfiles()
  store.updateDefaultVoiceProfile(profile.id)
}
```

### Step 4：单句音色入口接入创建

文件：`web/src/components/voice-workflow/SegmentInspector.vue`

传入：

```text
can-create
:create-initial-values="{ audition_text: segment.text, scene: 'short_video' }"
@created="profile => patch({ voice_profile_id: profile.id })"
```

这样从当前句子创建的音色会自动应用到当前句。

### Step 5：刷新列表和标签

文件：`web/src/views/VoiceWorkflowView.vue`

创建成功后刷新 `voiceProfiles`，确保：

- 下拉列表出现新音色。
- 节点卡片能显示新音色名称。
- 默认音色选择器能显示新音色名称。

### Step 6：测试

新增或补充前端测试：

```text
web/src/utils/voiceWorkflowProfiles.test.js
```

覆盖：

- 新建音色后应使用 profile.id。
- 单句音色优先于默认音色。
- 默认音色变化不覆盖单句音色。

如果后续引入组件测试，再补：

- 点击新建按钮打开 drawer。
- 创建成功后 emit 新 profile id。
- 创建失败时不 emit `update:modelValue`。

后端不需要新增接口测试，但建议保留现有：

```bash
uv run pytest server/tests/test_voice_profiles.py server/tests/test_voice_workflow_service.py server/tests/test_voice_workflows_routes.py -q
```

## 验收标准

- 工程默认音色选择器旁边可以新建音色档案。
- 单句音色选择器旁边可以新建音色档案。
- 从工程默认音色入口创建后，新音色自动成为工程默认音色。
- 从单句音色入口创建后，新音色自动成为当前句音色。
- 新建单句音色时，试听文案默认填充当前句文本。
- 创建失败时，当前选择不变化。
- 新建成功后，下拉列表和节点卡片立即显示新音色名称。
- 保存并刷新工程后，默认音色和单句音色都能恢复。
- 导出时，单句音色覆盖工程默认音色。

## 风险与注意事项

1. `VoiceProfileDrawer` 当前创建按钮文案是“保存并试听”，但实际逻辑只创建档案，没有自动调用试听接口。建议后续统一文案或真正串联试听。
2. 工作台顶部空间有限，默认音色选择器加 `+` 按钮后需要检查小屏宽度。
3. 如果 `VoiceProfileIdField` 内部自己拉取 profiles，容易和父层 `voiceProfiles` 形成双状态。第一版建议仍由父层维护列表，子组件只负责创建并通知父层刷新。
4. 音色复刻会上传 Base64 样音，抽屉复用时要保留授权确认和大小限制，不要绕过 `VoiceProfileDrawer`。

## 推荐结论

建议按“复用现有音色抽屉 + 增强工作台音色字段”的方式改造。

这条路线改动小、行为一致、后端无需新增 API，也符合当前项目已有组件边界：音色档案由 `VoiceProfileDrawer` 管理，配音工作台只负责选择并应用音色 ID。
