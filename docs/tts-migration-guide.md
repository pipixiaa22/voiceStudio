# TTS 语音合成前端迁移指南

## 概述

后端已重构 TTS 服务层，新增智能分块合成 API (`sync-package-v2`)。本文档指导前端从旧 API 迁移到新 API，并同步优化前端交互。

## 新旧 API 对比

### 旧 API（保留，不推荐）

| 端点 | 用途 | 问题 |
|------|------|------|
| `POST /api/tts/synthesize` | 单段合成 | 无 |
| `POST /api/tts/batch-synthesize` | 批量 ZIP | 逐字幕段合成，音色割裂 |
| `POST /api/tts/sync-package` | 同步包 | 逐字幕段合成，音色割裂 |

### 新 API（推荐）

| 端点 | 用途 | 优势 |
|------|------|------|
| `POST /api/tts/sync-package-v2` | 智能分块同步包 | 自动合并字幕段为语音块，音色更连贯 |

## 新 API 请求格式

```javascript
// POST /api/tts/sync-package-v2
{
  "api_key": "tts-key",           // 必填
  "title": "作品标题",             // 可选，默认 "语音合成"
  "content": "完整文本内容",       // 必填
  "voice_description": "温柔女声", // 必填
  "subtitle_options": {
    "max_chars": 20,               // 字幕段最大字数，默认 20
    "gap": 0.3                     // 段间静音间隔，默认 0.3 秒
  },
  "synthesis_options": {
    "mode": "chunked",             // 合成模式：chunked | whole
    "chunk_max_chars": 200         // 语音块最大字数，默认 200
  }
}
```

## 新 API 响应

返回 ZIP 文件，包含：

```
{title}_完整音频.wav    ← 完整音频（可直接导入剪映）
{title}_同步字幕.srt    ← 同步字幕（时间轴精准对齐）
manifest.json           ← 元数据（语音块、字幕时间轴等）
chunks/001.wav          ← 语音块 1
chunks/002.wav          ← 语音块 2
...
```

## 前端 API 封装变更

### 旧代码 (`web/src/api/index.js`)

```javascript
export const ttsApi = {
  synthesize: (data) => api.post('/tts/synthesize', data),
  batchSynthesize: (data) => api.post('/tts/batch-synthesize', data, { responseType: 'blob' }),
  syncPackage: (data) => api.post('/tts/sync-package', data, { responseType: 'blob' }),
  polish: (data) => api.post('/tts/polish', data),
}
```

### 新代码

```javascript
export const ttsApi = {
  // 保留旧 API（向后兼容）
  synthesize: (data) => api.post('/tts/synthesize', data),
  batchSynthesize: (data) => api.post('/tts/batch-synthesize', data, { responseType: 'blob' }),
  syncPackage: (data) => api.post('/tts/sync-package', data, { responseType: 'blob' }),
  polish: (data) => api.post('/tts/polish', data),

  // 新增 v2 API
  syncPackageV2: (data) => api.post('/tts/sync-package-v2', data, { responseType: 'blob' }),
}
```

## 前端交互优化建议

### 1. 简化 VoiceSynthModal

当前 `VoiceSynthModal.vue` 存在的问题：

- 每个字幕段都有独立的音色描述输入框（过于复杂）
- 用户需要逐段管理音色（不符合"统一音色"的设计理念）
- 没有"智能分块"选项

**建议改为四步流程：**

```
Step 1: 选择文本 → 选择已有文本或手动粘贴
Step 2: 音色设置 → 统一音色描述 + 润色
Step 3: 合成选项 → 整篇 / 智能分块 / 逐字幕段
Step 4: 生成 → 下载同步包
```

### 2. 新增合成模式选择

在"生成同步包"按钮旁新增模式选择：

```vue
<a-radio-group v-model:value="synthesisMode">
  <a-radio-button value="chunked">智能分块（推荐）</a-radio-button>
  <a-radio-button value="whole">整篇合成</a-radio-button>
  <a-radio-button value="segmented">逐字幕段</a-radio-button>
</a-radio-group>
```

### 3. 简化音色输入

移除逐段音色输入，改为统一音色描述：

```vue
<!-- 旧：每段都有音色输入 -->
<div v-for="segment in segments">
  <a-input v-model:value="segment.voiceDescription" />
</div>

<!-- 新：统一音色描述 -->
<a-textarea v-model:value="defaultVoice" placeholder="描述音色..." />
<a-button @click="handlePolish">润色</a-button>
```

### 4. 生成按钮逻辑

```javascript
const handleGenerate = async () => {
  const payload = {
    api_key: ttsKey.value,
    title: sourceTitle.value,
    content: fullContent.value,  // 完整文本，不是分段后的
    voice_description: defaultVoice.value,
    subtitle_options: {
      max_chars: 20,
      gap: 0.3,
    },
    synthesis_options: {
      mode: synthesisMode.value,  // chunked | whole | segmented
      chunk_max_chars: 200,
    },
  }

  const response = await ttsApi.syncPackageV2(payload)
  // 下载 ZIP...
}
```

### 5. manifest.json 展示

生成完成后，可以解析 manifest.json 展示结果：

```javascript
const handleGenerate = async () => {
  // ... 生成逻辑 ...

  // 解压 ZIP 并展示
  const zip = await JSZip.loadAsync(response.data)
  const manifest = JSON.parse(await zip.file('manifest.json').async('string'))

  // 展示语音块信息
  chunks.value = manifest.chunks
  subtitles.value = manifest.subtitles
  totalDuration.value = manifest.total_duration
}
```

## 样式优化建议

### 1. 对话框宽度

当前 800px，建议改为 900px 以容纳更多内容。

### 2. 步骤指示器

新增步骤条，引导用户完成四步流程：

```vue
<a-steps :current="currentStep" size="small">
  <a-step title="选择文本" />
  <a-step title="音色设置" />
  <a-step title="合成选项" />
  <a-step title="生成" />
</a-steps>
```

### 3. 音色预设卡片

将音色描述改为卡片式预设：

```vue
<div class="voice-presets">
  <div
    v-for="preset in voicePresets"
    :key="preset.id"
    class="preset-card"
    :class="{ active: selectedPreset === preset.id }"
    @click="selectPreset(preset)"
  >
    <span class="preset-name">{{ preset.name }}</span>
    <span class="preset-desc">{{ preset.description }}</span>
  </div>
</div>
```

预设示例：

| 名称 | 描述 |
|------|------|
| 温柔叙述 | 年轻女性，温柔甜美，语速中慢 |
| 专业解说 | 成熟男性，沉稳有力，语速适中 |
| 活泼朗读 | 年轻女性，活泼明快，语速较快 |
| 治愈故事 | 温暖中性，柔和治愈，语速缓慢 |

### 4. 生成进度

显示语音块合成进度：

```vue
<a-modal v-model:open="generating" title="正在生成..." :footer="null" :closable="false">
  <a-progress :percent="progress" :status="progressStatus" />
  <p>{{ progressText }}</p>
</a-modal>
```

## 迁移检查清单

- [ ] 添加 `syncPackageV2` 到 `ttsApi`
- [ ] 简化 VoiceSynthModal 为四步流程
- [ ] 移除逐段音色输入
- [ ] 新增合成模式选择（chunked/whole/segmented）
- [ ] 使用完整文本而非分段文本调用新 API
- [ ] 解析 manifest.json 展示结果
- [ ] 新增步骤指示器
- [ ] 新增音色预设卡片
- [ ] 新增生成进度条
- [ ] 测试：智能分块模式
- [ ] 测试：整篇合成模式
- [ ] 测试：逐字幕段模式（向后兼容）
- [ ] 测试：失败重试
