# Frontend Model Provider Settings Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create frontend components for multi-model provider settings: model settings store, API functions, settings drawer with tabs, provider key management, and usage model selection.

**Architecture:** New `modelSettings` store manages provider configurations and usage defaults in localStorage. Settings drawer replaces the modal with tabbed interface. Model selector component filters by capability.

**Tech Stack:** Vue 3, Ant Design Vue 4, Pinia, axios

---

## File Structure

| File | Responsibility |
|------|----------------|
| `web/src/api/index.js` | Add modelProvidersApi functions |
| `web/src/stores/modelSettings.js` | Provider configs, usage defaults, migration |
| `web/src/components/settings/SettingsDrawer.vue` | Tabbed settings container |
| `web/src/components/settings/ProviderKeyPanel.vue` | API key management per provider |
| `web/src/components/settings/UsageModelPanel.vue` | Default model per usage |
| `web/src/components/settings/ModelSelect.vue` | Model dropdown filtered by capability |
| `web/src/components/ApiSettingsModal.vue` | Update to open SettingsDrawer |

---

## Task 1: Add Model Provider API Functions

**Files:**
- Modify: `web/src/api/index.js`

- [ ] **Step 1: Add API functions**

Add to `web/src/api/index.js` before `export default api`:

```javascript
export const modelProvidersApi = {
  getPresets: () => api.get('/model-providers/presets'),
  getAllModels: () => api.get('/models'),
  testConnection: (data) => api.post('/model-providers/test', data),
  llmComplete: (data) => api.post('/models/llm/complete', data),
  ttsSynthesize: (data) => api.post('/models/tts/synthesize', data),
}
```

- [ ] **Step 2: Verify build passes**

Run: `cd /Users/ckrey/video/script/web && pnpm run build`
Expected: Build succeeds

- [ ] **Step 3: Commit**

```bash
git add web/src/api/index.js
git commit -m "feat: add model provider API functions"
```

---

## Task 2: Create Model Settings Store

**Files:**
- Create: `web/src/stores/modelSettings.js`

- [ ] **Step 1: Create the store**

Create `web/src/stores/modelSettings.js`:

```javascript
import { ref, computed, watch } from 'vue'

const STORAGE_KEY = 'model_settings'

const defaultSettings = {
  providers: [],
  defaults: {},
}

function loadFromStorage() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) {
      return JSON.parse(raw)
    }
  } catch {}
  return { ...defaultSettings }
}

function saveToStorage(settings) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(settings))
}

function migrateOldKeys(settings) {
  const oldTtsKey = localStorage.getItem('mimo_tts_key') || ''
  const oldLlmKey = localStorage.getItem('mimo_llm_key') || ''

  if (oldTtsKey || oldLlmKey) {
    const hasMimo = settings.providers.some(p => p.provider_key === 'mimo')
    if (!hasMimo) {
      settings.providers.push({
        provider_key: 'mimo',
        api_key: oldTtsKey || oldLlmKey,
        enabled: true,
      })
    }
  }
  return settings
}

const settings = ref(migrateOldKeys(loadFromStorage()))

watch(settings, (val) => {
  saveToStorage(val)
}, { deep: true })

export function useModelSettings() {
  const getProvider = (key) => {
    return settings.value.providers.find(p => p.provider_key === key)
  }

  const setProvider = (key, config) => {
    const idx = settings.value.providers.findIndex(p => p.provider_key === key)
    if (idx >= 0) {
      settings.value.providers[idx] = { ...settings.value.providers[idx], ...config }
    } else {
      settings.value.providers.push({ provider_key: key, ...config })
    }
  }

  const removeProvider = (key) => {
    settings.value.providers = settings.value.providers.filter(p => p.provider_key !== key)
  }

  const getProviderApiKey = (key) => {
    return getProvider(key)?.api_key || ''
  }

  const setUsageDefault = (usage, providerKey, modelKey) => {
    settings.value.defaults[usage] = { provider_key: providerKey, model_key: modelKey }
  }

  const getUsageDefault = (usage) => {
    return settings.value.defaults[usage] || null
  }

  const resolveUsage = (usage) => {
    const def = getUsageDefault(usage)
    if (!def) return null
    return {
      provider_key: def.provider_key,
      model_key: def.model_key,
      api_key: getProviderApiKey(def.provider_key),
    }
  }

  return {
    settings,
    getProvider,
    setProvider,
    removeProvider,
    getProviderApiKey,
    setUsageDefault,
    getUsageDefault,
    resolveUsage,
  }
}
```

- [ ] **Step 2: Verify build passes**

Run: `cd /Users/ckrey/video/script/web && pnpm run build`
Expected: Build succeeds

- [ ] **Step 3: Commit**

```bash
git add web/src/stores/modelSettings.js
git commit -m "feat: add model settings store with migration"
```

---

## Task 3: Create ModelSelect Component

**Files:**
- Create: `web/src/components/settings/ModelSelect.vue`

- [ ] **Step 1: Create the component**

Create `web/src/components/settings/ModelSelect.vue`:

```vue
<template>
  <a-select
    :value="value"
    @change="handleChange"
    :placeholder="placeholder"
    style="width: 100%"
    :allow-clear="allowClear"
    option-label-prop="label"
  >
    <a-select-option
      v-for="model in filteredModels"
      :key="model.model_key"
      :value="model.model_key"
      :label="`${model.provider_name} / ${model.model_name}`"
      :disabled="!isProviderEnabled(model.provider_key)"
    >
      <div class="model-option">
        <span class="model-name">{{ model.provider_name }} / {{ model.model_name }}</span>
        <div class="model-caps">
          <a-tag v-for="cap in model.capabilities.slice(0, 2)" :key="cap" size="small">
            {{ CAP_LABELS[cap] || cap }}
          </a-tag>
        </div>
      </div>
    </a-select-option>
  </a-select>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { modelProvidersApi } from '../../api'
import { useModelSettings } from '../../stores/modelSettings'

const props = defineProps({
  value: String,
  capability: String,
  placeholder: { type: String, default: '选择模型' },
  allowClear: { type: Boolean, default: false },
})

const emit = defineEmits(['update:value', 'change'])

const { settings } = useModelSettings()
const allModels = ref([])

const CAP_LABELS = {
  llm_text: 'LLM',
  llm_voice_prompt_polish: '音色优化',
  tts_voice_design: '音色设计',
  tts_voice_clone: '音色复刻',
  tts_builtin_voice: '预置音色',
  tts_plain: 'TTS',
  scene_planning: '分镜',
  script_polish: '润色',
}

const filteredModels = computed(() => {
  if (!props.capability) return allModels.value
  return allModels.value.filter(m => m.capabilities.includes(props.capability))
})

const isProviderEnabled = (providerKey) => {
  return settings.value.providers.some(p => p.provider_key === providerKey && p.enabled !== false)
}

onMounted(async () => {
  try {
    const { data } = await modelProvidersApi.getAllModels()
    allModels.value = data
  } catch {}
})

const handleChange = (val) => {
  emit('update:value', val)
  const model = allModels.value.find(m => m.model_key === val)
  emit('change', val, model)
}
</script>

<style scoped>
.model-option {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.model-name {
  font-size: 13px;
}

.model-caps {
  display: flex;
  gap: 4px;
}
</style>
```

- [ ] **Step 2: Verify build passes**

Run: `cd /Users/ckrey/video/script/web && pnpm run build`
Expected: Build succeeds

- [ ] **Step 3: Commit**

```bash
git add web/src/components/settings/ModelSelect.vue
git commit -m "feat: add model select component"
```

---

## Task 4: Create ProviderKeyPanel Component

**Files:**
- Create: `web/src/components/settings/ProviderKeyPanel.vue`

- [ ] **Step 1: Create the component**

Create `web/src/components/settings/ProviderKeyPanel.vue`:

```vue
<template>
  <div class="provider-key-panel">
    <div v-for="preset in presets" :key="preset.provider_key" class="provider-section">
      <div class="provider-header">
        <a-switch
          :checked="isProviderEnabled(preset.provider_key)"
          @change="(val) => toggleProvider(preset.provider_key, val)"
          size="small"
        />
        <span class="provider-name">{{ preset.display_name }}</span>
        <a-tag v-if="getConnectionStatus(preset.provider_key)" :color="getConnectionStatus(preset.provider_key).ok ? 'green' : 'red'" size="small">
          {{ getConnectionStatus(preset.provider_key).ok ? '可用' : '失败' }}
        </a-tag>
      </div>

      <template v-if="isProviderEnabled(preset.provider_key)">
        <a-form-item label="API Key">
          <a-input-password
            :value="getProviderApiKey(preset.provider_key)"
            @change="(e) => updateApiKey(preset.provider_key, e.target.value)"
            placeholder="输入 API Key"
          />
        </a-form-item>

        <a-form-item v-if="needsBaseUrl(preset)" label="Base URL">
          <a-input
            :value="getProviderBaseUrl(preset.provider_key)"
            @change="(e) => updateBaseUrl(preset.provider_key, e.target.value)"
            :placeholder="preset.base_url"
          />
        </a-form-item>

        <a-button
          size="small"
          :loading="testing === preset.provider_key"
          @click="handleTest(preset)"
        >
          测试连接
        </a-button>

        <div v-if="testResults[preset.provider_key]" class="test-result">
          <a-alert
            :type="testResults[preset.provider_key].ok ? 'success' : 'error'"
            :message="testResults[preset.provider_key].message"
            size="small"
            show-icon
          />
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { modelProvidersApi } from '../../api'
import { useModelSettings } from '../../stores/modelSettings'

const { settings, getProvider, setProvider, getProviderApiKey } = useModelSettings()

const presets = ref([])
const testing = ref(null)
const testResults = ref({})

const isProviderEnabled = (key) => {
  return settings.value.providers.some(p => p.provider_key === key && p.enabled !== false)
}

const toggleProvider = (key, enabled) => {
  const existing = getProvider(key)
  if (existing) {
    setProvider(key, { enabled })
  } else {
    const preset = presets.value.find(p => p.provider_key === key)
    setProvider(key, {
      api_key: '',
      base_url: preset?.base_url || '',
      enabled,
    })
  }
}

const getProviderBaseUrl = (key) => {
  return getProvider(key)?.base_url || ''
}

const needsBaseUrl = (preset) => {
  return preset.provider_type === 'openai_compatible' || preset.provider_type === 'openai'
}

const updateApiKey = (key, value) => {
  setProvider(key, { api_key: value })
}

const updateBaseUrl = (key, value) => {
  setProvider(key, { base_url: value })
}

const getConnectionStatus = (key) => {
  return testResults.value[key] || null
}

const handleTest = async (preset) => {
  testing.value = preset.provider_key
  try {
    const provider = getProvider(preset.provider_key)
    const { data } = await modelProvidersApi.testConnection({
      provider_key: preset.provider_key,
      api_key: provider?.api_key || '',
      base_url: provider?.base_url || preset.base_url,
    })
    testResults.value[preset.provider_key] = data
  } catch (e) {
    testResults.value[preset.provider_key] = { ok: false, message: e.response?.data?.error || '测试失败' }
  } finally {
    testing.value = null
  }
}

onMounted(async () => {
  try {
    const { data } = await modelProvidersApi.getPresets()
    presets.value = data
  } catch {}
})
</script>

<style scoped>
.provider-key-panel {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.provider-section {
  padding: 16px;
  border: 1px solid var(--border-color, #e8e8e8);
  border-radius: 8px;
}

.provider-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.provider-name {
  font-weight: 500;
  font-size: 14px;
}

.test-result {
  margin-top: 12px;
}
</style>
```

- [ ] **Step 2: Verify build passes**

Run: `cd /Users/ckrey/video/script/web && pnpm run build`
Expected: Build succeeds

- [ ] **Step 3: Commit**

```bash
git add web/src/components/settings/ProviderKeyPanel.vue
git commit -m "feat: add provider key panel component"
```

---

## Task 5: Create UsageModelPanel Component

**Files:**
- Create: `web/src/components/settings/UsageModelPanel.vue`

- [ ] **Step 1: Create the component**

Create `web/src/components/settings/UsageModelPanel.vue`:

```vue
<template>
  <div class="usage-model-panel">
    <a-divider orientation="left">语音合成</a-divider>

    <div v-for="usage in ttsUsages" :key="usage.key" class="usage-item">
      <span class="usage-label">{{ usage.label }}</span>
      <ModelSelect
        :value="getUsageModelKey(usage.key)"
        @change="(val) => handleUsageChange(usage.key, val)"
        capability="tts_voice_design"
        placeholder="选择 TTS 模型"
        allow-clear
      />
    </div>

    <a-divider orientation="left">文本与规划</a-divider>

    <div v-for="usage in llmUsages" :key="usage.key" class="usage-item">
      <span class="usage-label">{{ usage.label }}</span>
      <ModelSelect
        :value="getUsageModelKey(usage.key)"
        @change="(val) => handleUsageChange(usage.key, val)"
        capability="llm_text"
        placeholder="选择 LLM 模型"
        allow-clear
      />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useModelSettings } from '../../stores/modelSettings'
import ModelSelect from './ModelSelect.vue'

const { settings, setUsageDefault, getUsageDefault } = useModelSettings()

const ttsUsages = [
  { key: 'tts_audition', label: '音色试听' },
  { key: 'tts_sync_package', label: '同步包语音' },
  { key: 'tts_video_voiceover', label: '视频旁白' },
]

const llmUsages = [
  { key: 'voice_prompt_polish', label: '音色描述优化' },
  { key: 'script_polish', label: '文案润色' },
  { key: 'scene_planning', label: '分镜规划' },
]

const getUsageModelKey = (usage) => {
  return getUsageDefault(usage)?.model_key || undefined
}

const handleUsageChange = (usage, modelKey) => {
  if (!modelKey) {
    // Clear
    setUsageDefault(usage, '', '')
    return
  }
  // Find provider from allModels - we need to get it from the model select
  // For now, store just the model_key and resolve later
  const def = getUsageDefault(usage)
  if (def) {
    setUsageDefault(usage, def.provider_key, modelKey)
  }
}
</script>

<style scoped>
.usage-model-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.usage-item {
  display: flex;
  align-items: center;
  gap: 16px;
}

.usage-label {
  min-width: 120px;
  font-size: 13px;
  color: var(--text-secondary, #666);
}
</style>
```

- [ ] **Step 2: Verify build passes**

Run: `cd /Users/ckrey/video/script/web && pnpm run build`
Expected: Build succeeds

- [ ] **Step 3: Commit**

```bash
git add web/src/components/settings/UsageModelPanel.vue
git commit -m "feat: add usage model panel component"
```

---

## Task 6: Create SettingsDrawer Component

**Files:**
- Create: `web/src/components/settings/SettingsDrawer.vue`

- [ ] **Step 1: Create the component**

Create `web/src/components/settings/SettingsDrawer.vue`:

```vue
<template>
  <a-drawer
    :open="open"
    @update:open="$emit('update:open', $event)"
    title="设置"
    placement="right"
    :width="480"
    :bodyStyle="{ padding: '16px' }"
  >
    <a-tabs v-model:activeKey="activeTab">
      <a-tab-pane key="providers" tab="API Key">
        <ProviderKeyPanel />
      </a-tab-pane>

      <a-tab-pane key="defaults" tab="默认模型">
        <UsageModelPanel />
      </a-tab-pane>

      <a-tab-pane key="advanced" tab="高级">
        <a-form layout="vertical">
          <a-form-item label="润色系统提示词">
            <a-textarea
              v-model:value="systemPrompt"
              :autoSize="{ minRows: 4, maxRows: 8 }"
            />
            <span class="hint">指导 LLM 如何润色音色描述</span>
          </a-form-item>
        </a-form>
      </a-tab-pane>
    </a-tabs>

    <template #footer>
      <a-button @click="$emit('update:open', false)">关闭</a-button>
    </template>
  </a-drawer>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useSettings } from '../../stores/settings'
import ProviderKeyPanel from './ProviderKeyPanel.vue'
import UsageModelPanel from './UsageModelPanel.vue'

defineProps({ open: Boolean })
defineEmits(['update:open'])

const { systemPrompt, loadFromStorage } = useSettings()
const activeTab = ref('providers')

watch(() => props.open, (val) => {
  if (val) loadFromStorage()
})
</script>

<style scoped>
.hint {
  display: block;
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 4px;
}
</style>
```

- [ ] **Step 2: Verify build passes**

Run: `cd /Users/ckrey/video/script/web && pnpm run build`
Expected: Build succeeds

- [ ] **Step 3: Commit**

```bash
git add web/src/components/settings/SettingsDrawer.vue
git commit -m "feat: add settings drawer component"
```

---

## Task 7: Wire Up SettingsDrawer in App.vue

**Files:**
- Modify: `web/src/App.vue`

- [ ] **Step 1: Update App.vue**

Read `web/src/App.vue` and replace the `ApiSettingsModal` import and usage with `SettingsDrawer`.

Change import from:
```javascript
import ApiSettingsModal from './components/ApiSettingsModal.vue'
```
to:
```javascript
import SettingsDrawer from './components/settings/SettingsDrawer.vue'
```

Change template usage from:
```vue
<ApiSettingsModal v-model:open="settingsOpen" />
```
to:
```vue
<SettingsDrawer v-model:open="settingsOpen" />
```

- [ ] **Step 2: Verify build passes**

Run: `cd /Users/ckrey/video/script/web && pnpm run build`
Expected: Build succeeds

- [ ] **Step 3: Commit**

```bash
git add web/src/App.vue
git commit -m "feat: wire up settings drawer in app"
```

---

## Task 8: Final Build and Cleanup

- [ ] **Step 1: Run full build**

Run: `cd /Users/ckrey/video/script/web && pnpm run build`
Expected: Build succeeds with no errors

- [ ] **Step 2: Final commit**

```bash
git add -A
git commit -m "feat: complete frontend model provider settings"
```
