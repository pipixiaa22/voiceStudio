# 音色档案前端技术文档

## 目标

在现有语音合成界面中新增“预设音色”和“音色档案持久化”能力，让用户可以：

1. 选择系统预设音色。
2. 创建自己的音色档案。
3. 编辑、启用、停用、删除自定义音色。
4. 在生成语音前试听并确认音色。
5. 在同步包生成时使用已持久化的 `voice_profile_id` 或当前音色档案快照。

## 当前前端现状

相关文件：

```text
web/src/components/VoiceSynthModal.vue
web/src/api/index.js
web/src/stores/settings.js
```

当前音色只存在于弹窗内部状态：

```js
const defaultVoice = ref('')
```

问题：

- 刷新页面后音色丢失。
- 没有系统预设。
- 不能复用历史音色。
- 不能区分“音色档案”和“单次语气备注”。
- 同步包只传 `voice_description`，缺少稳定的档案标识。

## 新增前端模块

建议新增目录：

```text
web/src/components/voice-profile/
web/src/stores/voiceProfiles.js
```

组件：

```text
VoiceProfileSelect.vue
VoiceProfileEditor.vue
VoiceProfileDrawer.vue
VoicePresetGallery.vue
VoiceProfileAudition.vue
VoiceProfileTag.vue
```

API：

```js
export const voiceProfilesApi = {
  list: (params) => api.get('/voice-profiles', { params }),
  get: (id) => api.get(`/voice-profiles/${id}`),
  create: (data) => api.post('/voice-profiles', data),
  update: (id, data) => api.put(`/voice-profiles/${id}`, data),
  delete: (id) => api.delete(`/voice-profiles/${id}`),
  audition: (id, data) => api.post(`/voice-profiles/${id}/audition`, data),
}
```

## Pinia Store 设计

新增 `web/src/stores/voiceProfiles.js`：

```js
import { defineStore } from 'pinia'
import { voiceProfilesApi } from '../api'

export const useVoiceProfilesStore = defineStore('voiceProfiles', {
  state: () => ({
    profiles: [],
    loading: false,
    currentProfileId: localStorage.getItem('voice_profile_id') || null,
  }),
  getters: {
    activeProfiles: (state) => state.profiles.filter(p => p.is_active),
    builtinProfiles: (state) => state.profiles.filter(p => p.is_builtin),
    customProfiles: (state) => state.profiles.filter(p => !p.is_builtin),
    currentProfile: (state) => state.profiles.find(p => String(p.id) === String(state.currentProfileId)) || null,
  },
  actions: {
    async fetchProfiles() {
      this.loading = true
      try {
        const { data } = await voiceProfilesApi.list({ active: 1 })
        this.profiles = data
      } finally {
        this.loading = false
      }
    },
    selectProfile(id) {
      this.currentProfileId = id
      localStorage.setItem('voice_profile_id', id)
    },
    async createProfile(payload) {
      const { data } = await voiceProfilesApi.create(payload)
      this.profiles.unshift(data)
      this.selectProfile(data.id)
      return data
    },
    async updateProfile(id, payload) {
      const { data } = await voiceProfilesApi.update(id, payload)
      const index = this.profiles.findIndex(p => p.id === id)
      if (index !== -1) this.profiles[index] = data
      return data
    },
  },
})
```

## VoiceProfile 数据结构

前端统一使用：

```js
{
  id: 1,
  profile_key: 'warm_female_narrator',
  name: '温柔叙述女声',
  description: '适合情感类、知识类短视频旁白',
  raw_description: '年轻女性，温柔清澈，语速中慢',
  canonical_prompt: '一位年轻女性中文叙述者，音色清澈柔和...',
  negative_prompt: '不要儿童音，不要明显播音腔',
  provider: 'mimo',
  model: 'mimo-v2.5-tts-voicedesign',
  language: 'zh-CN',
  gender: 'female',
  age_group: 'young_adult',
  accent: 'standard_mandarin',
  speed: 'medium_slow',
  emotion: 'warm_calm',
  scene: 'short_video_narration',
  timbre: 'soft_clear',
  is_builtin: true,
  is_active: true,
}
```

## 与 VoiceSynthModal 集成

`VoiceSynthModal.vue` 中替换：

```js
const defaultVoice = ref('')
```

为：

```js
const voiceProfilesStore = useVoiceProfilesStore()
const selectedVoiceProfile = computed(() => voiceProfilesStore.currentProfile)
const fallbackVoiceDescription = ref('')

const resolvedVoicePrompt = computed(() => {
  return selectedVoiceProfile.value?.canonical_prompt || fallbackVoiceDescription.value.trim()
})
```

同步包 payload 改为：

```js
{
  api_key: ttsKey.value,
  title: sourceTitle.value,
  content: sourceContent.value,
  voice_profile_id: selectedVoiceProfile.value?.id || null,
  voice_profile_snapshot: selectedVoiceProfile.value || null,
  voice_description: resolvedVoicePrompt.value,
  subtitle_options: {
    max_chars: 20,
    gap: 0.3,
  },
  synthesis_options: {
    mode: 'chunked',
    chunk_max_chars: 200,
  },
}
```

注意：`content` 必须来自原始全文 `sourceContent`，不要从字幕段拼回。

## 创建音色流程

用户点击 `新建音色` 后打开 `VoiceProfileDrawer`。

表单字段：

- 音色名称
- 场景
- 性别/年龄感
- 语速
- 情绪
- 音色质感
- 原始描述
- 负向约束

提交逻辑：

1. 前端校验 `name` 和 `raw_description`。
2. 调用 `POST /api/voice-profiles`。
3. 后端生成或保存 `canonical_prompt`。
4. 前端插入列表并自动选中。
5. 提示用户生成试听。

## 试听流程

试听由 `VoiceProfileAudition.vue` 负责。

默认试听文案：

```text
今天我们来聊一个很实用的方法。它听起来简单，但真正做好并不容易。你可能会问，第一步应该从哪里开始？
```

流程：

1. 用户选择或创建音色。
2. 点击 `生成试听`。
3. 调用 `POST /api/voice-profiles/:id/audition`。
4. 返回 `audio_base64` 或试听文件 URL。
5. 用户点击 `确认使用`。
6. 当前语音合成会话记录 `voiceProfileConfirmed = true`。

## 状态校验

生成同步包按钮启用条件：

```text
ttsKey 存在
sourceContent 存在
resolvedVoicePrompt 存在
未处于生成中
已确认音色，或用户选择跳过试听
```

若用户选择系统预设，可以允许跳过试听，但界面应仍推荐试听。

## 预设加载策略

页面打开时：

1. `voiceProfilesStore.fetchProfiles()`
2. 若 localStorage 中有 `voice_profile_id` 且仍存在，自动选中。
3. 若没有选中项，默认选择第一个 `is_builtin=true` 且 `profile_key='warm_female_narrator'` 的音色。

## 错误处理

| 场景 | 前端处理 |
|------|----------|
| 预设加载失败 | 显示空态，允许用户使用临时描述 |
| 创建音色失败 | 表单保留输入，显示错误消息 |
| 试听失败 | 保留音色档案，允许重试 |
| 选中的音色被停用 | 清空选择并提示重新选择 |
| canonical_prompt 为空 | 回退到 raw_description |

## 分阶段实现

### Phase 1

- 新增 `voiceProfilesApi`。
- 新增 Pinia store。
- 在语音合成弹窗中支持选择预设音色。
- 同步包传 `voice_profile_id` 和 `voice_description`。

### Phase 2

- 新增音色创建抽屉。
- 支持编辑自定义音色。
- 支持试听确认。

### Phase 3

- 支持收藏、最近使用、复制预设为自定义。
- 支持按场景筛选。
- 支持音色版本和试听历史。
