# API Key 设置入口优化文档

## 背景

当前项目已经包含 `ApiSettingsModal.vue`，用于配置 MiMo TTS API Key、MiMo LLM API Key 和音色描述润色 prompt。随着语音合成、音色档案、音色复刻、视频生成等功能增加，API Key 不应散落在各个生成弹窗中。

API Key 是全局环境配置，不属于某一次生成任务。它应该放在稳定、可预期、随时可访问的位置。

## 目标

1. 将 API Key 配置入口统一到全局设置。
2. 减少语音合成、视频生成弹窗中的干扰项。
3. 在需要 API Key 的功能处提供轻量缺失提示。
4. 为后续模型选择、默认音色模式、连接测试预留扩展空间。

## 推荐位置

推荐放在应用顶部导航右侧：

```text
顶部导航右侧
齿轮图标 -> 设置 / API 与模型
```

理由：

- API Key 是账户级/环境级配置。
- 用户会自然地在“设置”中寻找密钥配置。
- 不会打断语音合成和视频生成的主流程。
- 后续新增其他供应商或模型时仍然有统一入口。

## 不推荐的位置

### 1. 不推荐放在语音合成弹窗内部

语音合成弹窗应该聚焦：

```text
选择文本 -> 音色档案 -> 试听确认 -> 生成同步包
```

如果在这里放 API Key 输入框，会让用户误以为每次生成都需要配置一次。

### 2. 不推荐放在视频生成弹窗内部

视频生成弹窗未来会包含模板、分镜、BGM、角色音色、预览等配置。API Key 放在这里会进一步增加认知负担。

### 3. 不推荐放在文本编辑页表单中

文本编辑页的核心是标题、正文、文件夹、标签和字幕预览。API Key 与文本内容无直接关系。

## 信息架构

建议将当前 `ApiSettingsModal.vue` 逐步升级为 `SettingsDrawer` 或 `SettingsModal`。

结构：

```text
设置
├── API 与模型
│   ├── MiMo TTS API Key
│   ├── MiMo LLM API Key
│   ├── 默认 TTS 模型
│   ├── 默认音色来源
│   └── 测试连接
├── 语音合成
│   ├── 默认音色档案
│   ├── 默认试听文案
│   ├── 默认分块长度
│   └── 是否生成前强制试听
└── 视频生成
    ├── 默认画幅
    ├── 默认视频模板
    ├── 默认 BGM 音量
    └── 默认导出包类型
```

第一阶段可以只实现 `API 与模型`。

## UI 设计

### 顶部入口

在 `App.vue` 顶部右侧添加设置按钮：

```text
[文本库]                                      [设置图标]
```

按钮形式：

- 齿轮图标。
- 无文字或 `设置` 文字均可。
- hover 显示 tooltip：`设置`。

### 设置弹窗

第一阶段沿用 modal：

```text
API 与模型设置

MiMo TTS API Key
[************************]
用于语音合成、音色试听、视频旁白生成

MiMo LLM API Key
[************************]
用于音色描述优化

音色描述优化 Prompt
[textarea]

[取消] [保存]
```

第二阶段升级为 drawer + tabs：

```text
设置
┌──────────────┬──────────────────────────┐
│ API 与模型   │ MiMo TTS API Key          │
│ 语音合成     │ MiMo LLM API Key          │
│ 视频生成     │ 默认 TTS 模型             │
└──────────────┴──────────────────────────┘
```

## 缺失 Key 提示

在业务弹窗中不直接放完整输入框，只提供轻量提示。

### 语音合成

如果缺少 TTS Key：

```text
需要配置 MiMo TTS API Key 才能生成语音。
[去设置]
```

如果缺少 LLM Key：

```text
未配置 MiMo LLM API Key，音色描述优化不可用。
[去设置]
```

### 音色试听

按钮禁用时提示：

```text
请先配置 TTS API Key
```

或显示：

```text
试听需要 TTS API Key
[去设置]
```

### 视频生成

如果视频生成需要 TTS：

```text
视频旁白生成需要 MiMo TTS API Key。
[去设置]
```

## 状态判断

当前 `useSettings()` 已经从 localStorage 读取：

```js
ttsKey
llmKey
systemPrompt
```

建议新增 computed：

```js
const hasTtsKey = computed(() => Boolean(ttsKey.value?.trim()))
const hasLlmKey = computed(() => Boolean(llmKey.value?.trim()))
```

各业务组件只判断状态，不直接关心 localStorage。

## API Key 存储

第一阶段继续使用 localStorage，保持现有逻辑。

注意：

- 不在日志中打印 API Key。
- 不在 manifest 中写入 API Key。
- 不把 API Key 存入云端数据库。
- 导出包中不包含 API Key。

后续如果加入用户系统，再迁移到服务端加密存储。

## 组件改造建议

### App.vue

新增：

```js
const settingsOpen = ref(false)
```

模板中增加：

```vue
<a-tooltip title="设置">
  <a-button type="text" @click="settingsOpen = true">
    <template #icon>
      <SettingsIcon />
    </template>
  </a-button>
</a-tooltip>

<ApiSettingsModal v-model:open="settingsOpen" />
```

如果当前项目没有 icon 库，可以先沿用现有 SVG 风格。

### ApiSettingsModal.vue

短期保留原组件，优化文案：

- 标题改为 `API 与模型设置`
- TTS Key 提示改为 `用于语音合成、音色试听、视频旁白生成`
- LLM Key 提示改为 `用于音色描述优化`

### VoiceSynthModal.vue

移除任何 API Key 输入框，只显示缺失提示。

```vue
<div v-if="!ttsKey" class="settings-alert">
  <span>需要配置 MiMo TTS API Key 才能生成语音。</span>
  <a-button size="small" @click="$emit('open-settings')">去设置</a-button>
</div>
```

如果不想跨组件 emit，也可以通过全局事件或 store 控制设置弹窗。

## 推荐实现阶段

### Phase 1：统一入口

- 在顶部导航右侧添加设置按钮。
- 点击打开现有 `ApiSettingsModal.vue`。
- 优化 `ApiSettingsModal` 文案。
- 各生成弹窗只显示缺失 Key 提示。

### Phase 2：设置分组

- 将 modal 升级为 drawer。
- 增加左侧分组：API 与模型、语音合成、视频生成。
- 加入默认模型、默认音色来源配置。

### Phase 3：连接测试

- 新增 `测试 TTS Key`。
- 新增 `测试 LLM Key`。
- 成功/失败给明确状态。

### Phase 4：多供应商准备

- 支持供应商选择：
  - MiMo
  - OpenAI
  - 其他 TTS
- 不同供应商显示不同 Key 和模型选项。

## 验收标准

1. 用户能在应用顶部稳定找到设置入口。
2. 语音合成和视频生成弹窗不再承担 API Key 配置职责。
3. 缺少 Key 时，业务弹窗给出明确提示和去设置入口。
4. 保存后，业务弹窗能立即读取新的 Key 状态。
5. API Key 不出现在日志、manifest、导出包中。
6. 现有 localStorage 配置兼容，不要求用户重新填写。

## 推荐结论

最小可行优化是：

```text
顶部右侧齿轮按钮
-> 打开 ApiSettingsModal
-> 业务弹窗只提示“去设置”
```

这是改动最小、收益最高的方案。它能让 API Key 从生成流程中抽离出来，让语音合成和视频生成界面更专注于创作配置。
