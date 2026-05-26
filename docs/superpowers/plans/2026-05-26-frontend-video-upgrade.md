# Frontend Video Generation Upgrade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor the video generation modal from a single-step form into a 6-step wizard with template selection, scene planning, speaker voice binding, audio mixing, preview, and async job progress.

**Architecture:** Replace `VideoGenerateModal.vue` with a step-based wizard using Ant Design's `a-steps` component. Extract each step into a focused child component under `web/src/components/video/`. Add new API functions for templates and jobs.

**Tech Stack:** Vue 3, Ant Design Vue 4, Pinia, axios

---

## File Structure

| File | Responsibility |
|------|----------------|
| `web/src/api/index.js` | Add videoApi.templates, videoApi.jobs endpoints |
| `web/src/components/video/VideoGenerateModal.vue` | Step wizard container (replaces old modal) |
| `web/src/components/video/VideoTemplateStep.vue` | Template selection cards |
| `web/src/components/video/ScenePlannerStep.vue` | Multi-image upload + scene binding |
| `web/src/components/video/SpeakerVoiceStep.vue` | Character voice binding |
| `web/src/components/video/AudioMixStep.vue` | BGM upload + ambient selection |
| `web/src/components/video/VideoPreviewStep.vue` | Preview summary before generation |
| `web/src/components/video/VideoJobProgress.vue` | Async job status polling |

---

## Task 1: Add Video API Endpoints

**Files:**
- Modify: `web/src/api/index.js`

- [ ] **Step 1: Add new API functions**

Add to `videoApi` object in `web/src/api/index.js`:

```javascript
export const videoApi = {
  // ... existing generate function stays unchanged ...

  getTemplates: () => api.get('/video/templates'),

  getTemplate: (key) => api.get(`/video/templates/${key}`),

  createJob: (data) => api.post('/video/jobs', data),

  getJob: (jobId) => api.get(`/video/jobs/${jobId}`),

  listJobs: () => api.get('/video/jobs'),
}
```

- [ ] **Step 2: Verify build passes**

Run: `cd web && pnpm run build`
Expected: Build succeeds

- [ ] **Step 3: Commit**

```bash
git add web/src/api/index.js
git commit -m "feat: add video template and job API endpoints"
```

---

## Task 2: Create VideoGenerateModal Step Wizard Shell

**Files:**
- Create: `web/src/components/video/VideoGenerateModal.vue`
- Modify: `web/src/components/VideoGenerateModal.vue` (rename or replace)

- [ ] **Step 1: Create the step wizard container**

Create `web/src/components/video/VideoGenerateModal.vue`:

```vue
<template>
  <a-modal
    :open="open"
    title="生成视频"
    @update:open="$emit('update:open', $event)"
    :footer="null"
    width="680px"
    :destroy-on-close="true"
  >
    <a-steps :current="currentStep" size="small" style="margin-bottom: 24px">
      <a-step title="模板" />
      <a-step title="画面" />
      <a-step title="音色" />
      <a-step title="音频" />
      <a-step title="预览" />
      <a-step title="生成" />
    </a-steps>

    <div class="step-content">
      <VideoTemplateStep
        v-if="currentStep === 0"
        v-model:selected-template="selectedTemplate"
        @next="currentStep = 1"
      />
      <ScenePlannerStep
        v-if="currentStep === 1"
        v-model:scenes="scenes"
        :subtitle-count="subtitleCount"
        @prev="currentStep = 0"
        @next="currentStep = 2"
      />
      <SpeakerVoiceStep
        v-if="currentStep === 2"
        v-model:speaker-profiles="speakerProfiles"
        :content="textContent"
        @prev="currentStep = 1"
        @next="currentStep = 3"
      />
      <AudioMixStep
        v-if="currentStep === 3"
        v-model:audio-options="audioOptions"
        @prev="currentStep = 2"
        @next="currentStep = 4"
      />
      <VideoPreviewStep
        v-if="currentStep === 4"
        :selected-template="selectedTemplate"
        :scenes="scenes"
        :speaker-profiles="speakerProfiles"
        :audio-options="audioOptions"
        @prev="currentStep = 3"
        @generate="handleGenerate"
      />
      <VideoJobProgress
        v-if="currentStep === 5"
        :job-id="currentJobId"
        @done="handleDone"
        @retry="currentStep = 4"
      />
    </div>
  </a-modal>
</template>

<script setup>
import { ref, watch } from 'vue'
import { message } from 'ant-design-vue'
import { videoApi } from '../../api'
import { useSettings } from '../../stores/settings'
import VideoTemplateStep from './VideoTemplateStep.vue'
import ScenePlannerStep from './ScenePlannerStep.vue'
import SpeakerVoiceStep from './SpeakerVoiceStep.vue'
import AudioMixStep from './AudioMixStep.vue'
import VideoPreviewStep from './VideoPreviewStep.vue'
import VideoJobProgress from './VideoJobProgress.vue'

const props = defineProps({
  open: Boolean,
  textId: { type: Number, required: true },
  textTitle: { type: String, default: '视频' },
  textContent: { type: String, default: '' },
  subtitleCount: { type: Number, default: 0 },
})

const emit = defineEmits(['update:open'])

const { llmKey } = useSettings()

const currentStep = ref(0)
const selectedTemplate = ref(null)
const scenes = ref([])
const speakerProfiles = ref({})
const audioOptions = ref({
  bgm_enabled: false,
  bgm_volume: 0.18,
  bgm_fade_in: 1.0,
  bgm_fade_out: 1.5,
  ambient_enabled: false,
  ambient_key: 'wind',
  ambient_volume: 0.12,
})
const currentJobId = ref(null)

watch(() => props.open, (val) => {
  if (val) {
    currentStep.value = 0
    currentJobId.value = null
  }
})

const handleGenerate = async () => {
  if (!llmKey.value) {
    message.error('请先配置 API Key')
    return
  }

  try {
    const response = await videoApi.createJob({
      text_id: props.textId,
      title: props.textTitle,
      template_key: selectedTemplate.value?.template_key || 'xianxia_narration',
      scenes: scenes.value,
      speaker_profiles: speakerProfiles.value,
      audio_options: audioOptions.value,
      api_key: llmKey.value,
    })

    currentJobId.value = response.data.job_id
    currentStep.value = 5
  } catch (error) {
    message.error(error.response?.data?.error || '创建任务失败')
  }
}

const handleDone = () => {
  message.success('视频生成完成')
  emit('update:open', false)
}
</script>

<style scoped>
.step-content {
  min-height: 300px;
}
</style>
```

- [ ] **Step 2: Verify build passes**

Run: `cd web && pnpm run build`
Expected: Build succeeds (old modal still referenced, new one not yet wired)

- [ ] **Step 3: Commit**

```bash
git add web/src/components/video/VideoGenerateModal.vue
git commit -m "feat: add video generate modal step wizard shell"
```

---

## Task 3: Create VideoTemplateStep Component

**Files:**
- Create: `web/src/components/video/VideoTemplateStep.vue`

- [ ] **Step 1: Create template selection component**

Create `web/src/components/video/VideoTemplateStep.vue`:

```vue
<template>
  <div class="template-step">
    <h4>选择视频模板</h4>
    <div class="template-grid">
      <div
        v-for="template in templates"
        :key="template.template_key"
        class="template-card"
        :class="{ selected: selected?.template_key === template.template_key }"
        @click="selectTemplate(template)"
      >
        <div class="template-icon">{{ getTemplateIcon(template.template_key) }}</div>
        <div class="template-name">{{ template.name }}</div>
        <div class="template-desc">{{ getTemplateDesc(template.template_key) }}</div>
      </div>
    </div>

    <div v-if="selected" class="template-info">
      <a-descriptions size="small" :column="2" bordered>
        <a-descriptions-item label="画面节奏">{{ selected.config?.visual_effects?.motion }}</a-descriptions-item>
        <a-descriptions-item label="帧率">{{ selected.config?.fps }}fps</a-descriptions-item>
        <a-descriptions-item label="BGM 音量">{{ Math.round((selected.config?.audio?.bgm_volume || 0) * 100) }}%</a-descriptions-item>
        <a-descriptions-item label="环境音">{{ Math.round((selected.config?.audio?.ambient_volume || 0) * 100) }}%</a-descriptions-item>
      </a-descriptions>
    </div>

    <div class="step-actions">
      <a-button type="primary" :disabled="!selected" @click="$emit('next')">下一步</a-button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { videoApi } from '../../api'

const props = defineProps({
  selectedTemplate: Object,
})

const emit = defineEmits(['update:selectedTemplate', 'next'])

const templates = ref([])
const selected = ref(props.selectedTemplate)

onMounted(async () => {
  try {
    const response = await videoApi.getTemplates()
    templates.value = response.data
    if (!selected.value && templates.value.length > 0) {
      selectTemplate(templates.value[0])
    }
  } catch (error) {
    console.error('加载模板失败:', error)
  }
})

const selectTemplate = (template) => {
  selected.value = template
  emit('update:selectedTemplate', template)
}

const TEMPLATE_ICONS = {
  xianxia_narration: '📖',
  character_monologue: '🎭',
  chapter_title: '📑',
  battle_transition: '⚔️',
  technique_explain: '🔮',
}

const TEMPLATE_DESCS = {
  xianxia_narration: '慢推近、云雾、低音量BGM',
  character_monologue: '单图慢推、音色优先',
  chapter_title: '标题卡、淡入淡出',
  battle_transition: '快速缩放、闪白、剑鸣',
  technique_explain: '稳定画面、清晰旁白',
}

const getTemplateIcon = (key) => TEMPLATE_ICONS[key] || '🎬'
const getTemplateDesc = (key) => TEMPLATE_DESCS[key] || ''
</script>

<style scoped>
.template-step h4 {
  margin-bottom: 16px;
}

.template-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}

.template-card {
  border: 2px solid var(--border-color, #e8e8e8);
  border-radius: 8px;
  padding: 16px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s;
}

.template-card:hover {
  border-color: var(--primary-color, #1890ff);
}

.template-card.selected {
  border-color: var(--primary-color, #1890ff);
  background: var(--primary-bg, #e6f7ff);
}

.template-icon {
  font-size: 32px;
  margin-bottom: 8px;
}

.template-name {
  font-weight: 500;
  margin-bottom: 4px;
}

.template-desc {
  font-size: 12px;
  color: var(--text-secondary, #999);
}

.template-info {
  margin-bottom: 16px;
}

.step-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
```

- [ ] **Step 2: Verify build passes**

Run: `cd web && pnpm run build`
Expected: Build succeeds

- [ ] **Step 3: Commit**

```bash
git add web/src/components/video/VideoTemplateStep.vue
git commit -m "feat: add video template selection step"
```

---

## Task 4: Create ScenePlannerStep Component

**Files:**
- Create: `web/src/components/video/ScenePlannerStep.vue`

- [ ] **Step 1: Create scene planner component**

Create `web/src/components/video/ScenePlannerStep.vue`:

```vue
<template>
  <div class="scene-step">
    <h4>分镜设置</h4>
    <p class="hint">上传多张图片按顺序分配到分镜，或只上传一张图片用于整条视频。</p>

    <div class="scene-list">
      <div v-for="(scene, index) in localScenes" :key="index" class="scene-item">
        <div class="scene-header">
          <span class="scene-label">Scene {{ String(index + 1).padStart(2, '0') }}</span>
          <a-button
            v-if="localScenes.length > 1"
            type="text"
            size="small"
            danger
            @click="removeScene(index)"
          >
            移除
          </a-button>
        </div>

        <div class="scene-content">
          <a-upload
            :before-upload="(file) => handleSceneImage(file, index)"
            :show-upload-list="false"
            accept="image/*"
          >
            <a-button size="small">
              {{ scene.imageFile ? '更换图片' : '上传图片' }}
            </a-button>
          </a-upload>
          <span v-if="scene.imageFile" class="file-name">{{ scene.imageFile.name }}</span>
        </div>

        <div class="scene-motion">
          <span class="motion-label">动效:</span>
          <a-select v-model:value="scene.motion" size="small" style="width: 140px">
            <a-select-option value="slow_zoom_in">慢推近</a-select-option>
            <a-select-option value="slow_zoom_out">慢拉远</a-select-option>
            <a-select-option value="pan_left_right">左右平移</a-select-option>
            <a-select-option value="breathing_zoom">呼吸缩放</a-select-option>
            <a-select-option value="shake">轻微震动</a-select-option>
          </a-select>
        </div>
      </div>
    </div>

    <a-button type="dashed" block @click="addScene" style="margin-top: 12px">
      + 添加分镜
    </a-button>

    <div class="step-actions">
      <a-button @click="$emit('prev')">上一步</a-button>
      <a-button type="primary" @click="handleNext">下一步</a-button>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  scenes: { type: Array, default: () => [] },
  subtitleCount: { type: Number, default: 0 },
})

const emit = defineEmits(['update:scenes', 'prev', 'next'])

const localScenes = ref(props.scenes.length > 0 ? [...props.scenes] : [createEmptyScene()])

function createEmptyScene() {
  return {
    imageFile: null,
    motion: 'slow_zoom_in',
  }
}

watch(() => props.scenes, (val) => {
  if (val.length > 0 && localScenes.value.length === 1 && !localScenes.value[0].imageFile) {
    localScenes.value = [...val]
  }
})

const addScene = () => {
  localScenes.value.push(createEmptyScene())
}

const removeScene = (index) => {
  localScenes.value.splice(index, 1)
}

const handleSceneImage = (file, index) => {
  localScenes.value[index].imageFile = file
  return false
}

const handleNext = () => {
  emit('update:scenes', localScenes.value)
  emit('next')
}
</script>

<style scoped>
.scene-step h4 {
  margin-bottom: 8px;
}

.hint {
  color: var(--text-secondary, #999);
  font-size: 13px;
  margin-bottom: 16px;
}

.scene-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.scene-item {
  border: 1px solid var(--border-color, #e8e8e8);
  border-radius: 8px;
  padding: 12px;
}

.scene-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.scene-label {
  font-weight: 500;
  font-size: 13px;
}

.scene-content {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.file-name {
  font-size: 12px;
  color: var(--text-secondary, #999);
}

.scene-motion {
  display: flex;
  align-items: center;
  gap: 8px;
}

.motion-label {
  font-size: 13px;
  color: var(--text-secondary, #999);
}

.step-actions {
  display: flex;
  justify-content: space-between;
  margin-top: 16px;
}
</style>
```

- [ ] **Step 2: Verify build passes**

Run: `cd web && pnpm run build`
Expected: Build succeeds

- [ ] **Step 3: Commit**

```bash
git add web/src/components/video/ScenePlannerStep.vue
git commit -m "feat: add scene planner step component"
```

---

## Task 5: Create SpeakerVoiceStep Component

**Files:**
- Create: `web/src/components/video/SpeakerVoiceStep.vue`

- [ ] **Step 1: Create speaker voice binding component**

Create `web/src/components/video/SpeakerVoiceStep.vue`:

```vue
<template>
  <div class="speaker-step">
    <h4>角色声线绑定</h4>
    <p class="hint">系统已从文本中识别出以下角色，请为每个角色选择音色档案。</p>

    <div v-if="speakers.length === 0" class="no-speakers">
      <a-empty description="未检测到角色标注">
        <template #description>
          <span>文本中未发现【角色】格式的标注，将使用默认音色。</span>
        </template>
      </a-empty>
    </div>

    <div v-else class="speaker-list">
      <div v-for="speaker in speakers" :key="speaker" class="speaker-item">
        <div class="speaker-name">
          <span class="speaker-tag">{{ speaker }}</span>
        </div>
        <div class="speaker-voice">
          <a-select
            :value="localProfiles[speaker]"
            @change="(val) => updateProfile(speaker, val)"
            placeholder="选择音色档案"
            style="width: 100%"
            allow-clear
          >
            <a-select-option v-for="profile in voiceProfiles" :key="profile.id" :value="profile.id">
              {{ profile.name }}
            </a-select-option>
          </a-select>
        </div>
      </div>
    </div>

    <div class="step-actions">
      <a-button @click="$emit('prev')">上一步</a-button>
      <a-button type="primary" @click="handleNext">下一步</a-button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { voiceProfilesApi } from '../../api'

const props = defineProps({
  speakerProfiles: { type: Object, default: () => ({}) },
  content: { type: String, default: '' },
})

const emit = defineEmits(['update:speakerProfiles', 'prev', 'next'])

const localProfiles = ref({ ...props.speakerProfiles })
const voiceProfiles = ref([])

const speakers = computed(() => {
  const regex = /【([^】]+)】/g
  const found = new Set()
  let match
  while ((match = regex.exec(props.content)) !== null) {
    found.add(match[1])
  }
  return Array.from(found)
})

watch(() => props.speakerProfiles, (val) => {
  localProfiles.value = { ...val }
})

onMounted(async () => {
  try {
    const response = await voiceProfilesApi.list()
    voiceProfiles.value = response.data
  } catch (error) {
    console.error('加载音色档案失败:', error)
  }
})

const updateProfile = (speaker, profileId) => {
  if (profileId) {
    localProfiles.value[speaker] = profileId
  } else {
    delete localProfiles.value[speaker]
  }
}

const handleNext = () => {
  emit('update:speakerProfiles', localProfiles.value)
  emit('next')
}
</script>

<style scoped>
.speaker-step h4 {
  margin-bottom: 8px;
}

.hint {
  color: var(--text-secondary, #999);
  font-size: 13px;
  margin-bottom: 16px;
}

.no-speakers {
  padding: 24px 0;
}

.speaker-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.speaker-item {
  display: flex;
  align-items: center;
  gap: 16px;
}

.speaker-name {
  min-width: 80px;
}

.speaker-tag {
  background: var(--primary-bg, #e6f7ff);
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 13px;
}

.speaker-voice {
  flex: 1;
}

.step-actions {
  display: flex;
  justify-content: space-between;
  margin-top: 16px;
}
</style>
```

- [ ] **Step 2: Verify build passes**

Run: `cd web && pnpm run build`
Expected: Build succeeds

- [ ] **Step 3: Commit**

```bash
git add web/src/components/video/SpeakerVoiceStep.vue
git commit -m "feat: add speaker voice binding step"
```

---

## Task 6: Create AudioMixStep Component

**Files:**
- Create: `web/src/components/video/AudioMixStep.vue`

- [ ] **Step 1: Create audio mixing options component**

Create `web/src/components/video/AudioMixStep.vue`:

```vue
<template>
  <div class="audio-step">
    <h4>音频设置</h4>

    <a-form layout="vertical">
      <a-divider orientation="left">背景音乐 (BGM)</a-divider>

      <a-form-item>
        <a-switch v-model:checked="localOptions.bgm_enabled" checked-children="开启" un-checked-children="关闭" />
      </a-form-item>

      <template v-if="localOptions.bgm_enabled">
        <a-form-item label="BGM 文件">
          <a-upload
            :before-upload="handleBgmUpload"
            :show-upload-list="false"
            accept="audio/*"
          >
            <a-button>
              {{ bgmFile ? '更换 BGM' : '上传 BGM' }}
            </a-button>
          </a-upload>
          <span v-if="bgmFile" class="file-name">{{ bgmFile.name }}</span>
        </a-form-item>

        <a-form-item label="BGM 音量">
          <a-slider
            v-model:value="localOptions.bgm_volume"
            :min="0"
            :max="1"
            :step="0.01"
            :tip-formatter="(v) => `${Math.round(v * 100)}%`"
          />
        </a-form-item>

        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="淡入">
              <a-input-number v-model:value="localOptions.bgm_fade_in" :min="0" :max="5" :step="0.1" style="width: 100%" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="淡出">
              <a-input-number v-model:value="localOptions.bgm_fade_out" :min="0" :max="5" :step="0.1" style="width: 100%" />
            </a-form-item>
          </a-col>
        </a-row>
      </template>

      <a-divider orientation="left">环境音</a-divider>

      <a-form-item>
        <a-switch v-model:checked="localOptions.ambient_enabled" checked-children="开启" un-checked-children="关闭" />
      </a-form-item>

      <template v-if="localOptions.ambient_enabled">
        <a-form-item label="环境音类型">
          <a-select v-model:value="localOptions.ambient_key" style="width: 100%">
            <a-select-option value="wind">风声</a-select-option>
            <a-select-option value="rain">雨声</a-select-option>
            <a-select-option value="thunder">雷声</a-select-option>
            <a-select-option value="sword">剑鸣</a-select-option>
            <a-select-option value="bell">钟声</a-select-option>
            <a-select-option value="fire">火焰声</a-select-option>
          </a-select>
        </a-form-item>

        <a-form-item label="环境音音量">
          <a-slider
            v-model:value="localOptions.ambient_volume"
            :min="0"
            :max="1"
            :step="0.01"
            :tip-formatter="(v) => `${Math.round(v * 100)}%`"
          />
        </a-form-item>
      </template>
    </a-form>

    <div class="step-actions">
      <a-button @click="$emit('prev')">上一步</a-button>
      <a-button type="primary" @click="handleNext">下一步</a-button>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  audioOptions: { type: Object, default: () => ({}) },
})

const emit = defineEmits(['update:audioOptions', 'prev', 'next'])

const localOptions = ref({ ...props.audioOptions })
const bgmFile = ref(null)

watch(() => props.audioOptions, (val) => {
  localOptions.value = { ...val }
})

const handleBgmUpload = (file) => {
  bgmFile.value = file
  return false
}

const handleNext = () => {
  emit('update:audioOptions', localOptions.value)
  emit('next')
}
</script>

<style scoped>
.audio-step h4 {
  margin-bottom: 16px;
}

.file-name {
  margin-left: 8px;
  font-size: 13px;
  color: var(--text-secondary, #999);
}

.step-actions {
  display: flex;
  justify-content: space-between;
  margin-top: 16px;
}
</style>
```

- [ ] **Step 2: Verify build passes**

Run: `cd web && pnpm run build`
Expected: Build succeeds

- [ ] **Step 3: Commit**

```bash
git add web/src/components/video/AudioMixStep.vue
git commit -m "feat: add audio mix step component"
```

---

## Task 7: Create VideoPreviewStep Component

**Files:**
- Create: `web/src/components/video/VideoPreviewStep.vue`

- [ ] **Step 1: Create preview step component**

Create `web/src/components/video/VideoPreviewStep.vue`:

```vue
<template>
  <div class="preview-step">
    <h4>生成预览</h4>

    <a-descriptions :column="1" bordered size="small">
      <a-descriptions-item label="模板">
        {{ selectedTemplate?.name || '未选择' }}
      </a-descriptions-item>
      <a-descriptions-item label="分镜数量">
        {{ scenes.length }} 个
      </a-descriptions-item>
      <a-descriptions-item label="角色绑定">
        <span v-if="Object.keys(speakerProfiles).length === 0">无（使用默认音色）</span>
        <span v-else>
          <a-tag v-for="(profileId, speaker) in speakerProfiles" :key="speaker">
            {{ speaker }}
          </a-tag>
        </span>
      </a-descriptions-item>
      <a-descriptions-item label="BGM">
        {{ audioOptions.bgm_enabled ? '开启' : '关闭' }}
        <span v-if="audioOptions.bgm_enabled"> ({{ Math.round(audioOptions.bgm_volume * 100) }}%)</span>
      </a-descriptions-item>
      <a-descriptions-item label="环境音">
        {{ audioOptions.ambient_enabled ? AMBIENT_NAMES[audioOptions.ambient_key] || '开启' : '关闭' }}
        <span v-if="audioOptions.ambient_enabled"> ({{ Math.round(audioOptions.ambient_volume * 100) }}%)</span>
      </a-descriptions-item>
    </a-descriptions>

    <a-alert
      v-if="scenes.some(s => !s.imageFile)"
      type="warning"
      message="部分分镜未上传图片，将使用默认背景"
      style="margin-top: 16px"
      show-icon
    />

    <div class="step-actions">
      <a-button @click="$emit('prev')">上一步</a-button>
      <a-button type="primary" @click="$emit('generate')">开始生成</a-button>
    </div>
  </div>
</template>

<script setup>
defineProps({
  selectedTemplate: Object,
  scenes: { type: Array, default: () => [] },
  speakerProfiles: { type: Object, default: () => ({}) },
  audioOptions: { type: Object, default: () => ({}) },
})

defineEmits(['prev', 'generate'])

const AMBIENT_NAMES = {
  wind: '风声',
  rain: '雨声',
  thunder: '雷声',
  sword: '剑鸣',
  bell: '钟声',
  fire: '火焰声',
}
</script>

<style scoped>
.preview-step h4 {
  margin-bottom: 16px;
}

.step-actions {
  display: flex;
  justify-content: space-between;
  margin-top: 16px;
}
</style>
```

- [ ] **Step 2: Verify build passes**

Run: `cd web && pnpm run build`
Expected: Build succeeds

- [ ] **Step 3: Commit**

```bash
git add web/src/components/video/VideoPreviewStep.vue
git commit -m "feat: add video preview step component"
```

---

## Task 8: Create VideoJobProgress Component

**Files:**
- Create: `web/src/components/video/VideoJobProgress.vue`

- [ ] **Step 1: Create job progress polling component**

Create `web/src/components/video/VideoJobProgress.vue`:

```vue
<template>
  <div class="progress-step">
    <h4>视频生成中</h4>

    <div v-if="job" class="progress-content">
      <a-progress :percent="Math.round(job.progress * 100)" :status="progressStatus" />

      <div class="progress-info">
        <a-tag :color="statusColor">{{ statusLabel }}</a-tag>
        <span v-if="job.message" class="progress-message">{{ job.message }}</span>
      </div>

      <div v-if="job.status === 'completed'" class="completed-actions">
        <a-button type="primary" @click="$emit('done')">完成</a-button>
      </div>

      <div v-if="job.status === 'failed'" class="failed-actions">
        <a-alert type="error" :message="job.error_message || '生成失败'" style="margin-bottom: 16px" />
        <a-button @click="$emit('retry')">重试</a-button>
      </div>
    </div>

    <div v-else class="loading">
      <a-spin tip="正在创建任务..." />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { videoApi } from '../../api'

const props = defineProps({
  jobId: String,
})

const emit = defineEmits(['done', 'retry'])

const job = ref(null)
let pollTimer = null

const STATUS_LABELS = {
  queued: '排队中',
  planning: '规划中',
  synthesizing_voice: '合成语音',
  mixing_audio: '混合音频',
  rendering_video: '渲染视频',
  packaging: '打包中',
  completed: '已完成',
  failed: '失败',
}

const STATUS_COLORS = {
  queued: 'default',
  planning: 'processing',
  synthesizing_voice: 'processing',
  mixing_audio: 'processing',
  rendering_video: 'processing',
  packaging: 'processing',
  completed: 'success',
  failed: 'error',
}

const statusLabel = computed(() => STATUS_LABELS[job.value?.status] || job.value?.status)
const statusColor = computed(() => STATUS_COLORS[job.value?.status] || 'default')

const progressStatus = computed(() => {
  if (job.value?.status === 'completed') return 'success'
  if (job.value?.status === 'failed') return 'exception'
  return 'active'
})

const pollJob = async () => {
  if (!props.jobId) return

  try {
    const response = await videoApi.getJob(props.jobId)
    job.value = response.data

    if (job.value.status === 'completed' || job.value.status === 'failed') {
      clearInterval(pollTimer)
    }
  } catch (error) {
    console.error('查询任务状态失败:', error)
  }
}

onMounted(() => {
  pollJob()
  pollTimer = setInterval(pollJob, 2000)
})

onUnmounted(() => {
  if (pollTimer) {
    clearInterval(pollTimer)
  }
})

watch(() => props.jobId, () => {
  if (pollTimer) clearInterval(pollTimer)
  pollJob()
  pollTimer = setInterval(pollJob, 2000)
})
</script>

<style scoped>
.progress-step h4 {
  margin-bottom: 16px;
}

.progress-content {
  padding: 16px 0;
}

.progress-info {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
}

.progress-message {
  color: var(--text-secondary, #999);
  font-size: 13px;
}

.completed-actions,
.failed-actions {
  margin-top: 16px;
  text-align: center;
}

.loading {
  display: flex;
  justify-content: center;
  padding: 48px 0;
}
</style>
```

- [ ] **Step 2: Verify build passes**

Run: `cd web && pnpm run build`
Expected: Build succeeds

- [ ] **Step 3: Commit**

```bash
git add web/src/components/video/VideoJobProgress.vue
git commit -m "feat: add video job progress component"
```

---

## Task 9: Wire Up New Modal in Parent Components

**Files:**
- Modify: `web/src/components/VideoGenerateModal.vue` (old file - replace or redirect)
- Modify: parent components that import VideoGenerateModal

- [ ] **Step 1: Find all imports of the old VideoGenerateModal**

Search for imports of the old modal to update them.

- [ ] **Step 2: Update imports to use new modal**

In any file that imports `VideoGenerateModal`, change the import path:

```javascript
// Before
import VideoGenerateModal from '../components/VideoGenerateModal.vue'

// After
import VideoGenerateModal from '../components/video/VideoGenerateModal.vue'
```

Also add `textContent` and `subtitleCount` props if available.

- [ ] **Step 3: Verify build passes**

Run: `cd web && pnpm run build`
Expected: Build succeeds

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "feat: wire up new video generate modal"
```

---

## Task 10: Final Build and Cleanup

- [ ] **Step 1: Run full build**

Run: `cd web && pnpm run build`
Expected: Build succeeds with no errors

- [ ] **Step 2: Verify old modal can be removed**

If the old `web/src/components/VideoGenerateModal.vue` is no longer imported anywhere, delete it.

- [ ] **Step 3: Final commit**

```bash
git add -A
git commit -m "feat: complete frontend video generation upgrade"
```
