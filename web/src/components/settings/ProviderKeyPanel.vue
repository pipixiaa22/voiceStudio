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
        <a-tag v-if="preset._isCustom" color="blue" size="small">自定义</a-tag>
        <a-tag v-if="getConnectionStatus(preset.provider_key)" :color="getConnectionStatus(preset.provider_key).ok ? 'green' : 'red'" size="small">
          {{ getConnectionStatus(preset.provider_key).ok ? '可用' : '失败' }}
        </a-tag>
        <a-button
          v-if="preset._isCustom"
          type="text"
          danger
          size="small"
          class="delete-btn"
          @click="handleDeleteCustom(preset)"
        >
          删除
        </a-button>
      </div>

      <template v-if="isProviderEnabled(preset.provider_key)">
        <a-form-item label="API Key">
          <a-input-password
            :value="getProviderApiKey(preset.provider_key)"
            @change="(e) => updateApiKey(preset.provider_key, e.target.value)"
            placeholder="输入 API Key"
          />
        </a-form-item>

        <a-form-item label="Base URL">
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

    <!-- Add Custom Provider -->
    <div v-if="!showAddForm" class="add-section">
      <a-button type="dashed" block @click="showAddForm = true">
        + 添加自定义供应商
      </a-button>
    </div>

    <div v-else class="provider-section add-form">
      <div class="provider-header">
        <span class="provider-name">添加自定义供应商</span>
      </div>

      <a-form-item label="供应商名称">
        <a-input v-model:value="newProvider.display_name" placeholder="例如：我的 OpenAI 代理" />
      </a-form-item>

      <a-form-item label="Base URL">
        <a-input v-model:value="newProvider.base_url" placeholder="https://api.example.com/v1" />
      </a-form-item>

      <div class="models-header">
        <span>模型列表</span>
        <a-button type="link" size="small" @click="addModel">+ 添加模型</a-button>
      </div>

      <div v-for="(m, idx) in newProvider.models" :key="idx" class="model-entry">
        <div class="model-entry-row">
          <a-input
            v-model:value="m.model_key"
            placeholder="模型 ID (如 gpt-4o)"
            size="small"
            class="model-input"
          />
          <a-input
            v-model:value="m.display_name"
            placeholder="显示名称"
            size="small"
            class="model-input"
          />
          <a-button type="text" danger size="small" @click="removeModel(idx)" v-if="newProvider.models.length > 1">
            删除
          </a-button>
        </div>
        <a-checkbox-group
          v-model:value="m.capabilities"
          :options="capabilityOptions"
          class="model-caps"
        />
      </div>

      <div v-if="addError" class="test-result">
        <a-alert type="error" :message="addError" size="small" show-icon />
      </div>

      <div class="form-actions">
        <a-button size="small" @click="cancelAdd">取消</a-button>
        <a-button size="small" type="primary" :loading="adding" @click="handleAdd">添加</a-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, watch } from 'vue'
import { Modal } from 'ant-design-vue'
import { modelProvidersApi, customProvidersApi } from '../../api'
import { useModelSettings } from '../../stores/modelSettings'

const props = defineProps({
  active: { type: Boolean, default: true },
})

const { settings, getProvider, setProvider, removeProvider, getProviderApiKey } = useModelSettings()

const presets = ref([])
const testing = ref(null)
const testResults = ref({})

const showAddForm = ref(false)
const adding = ref(false)
const addError = ref('')
const newProvider = reactive({
  display_name: '',
  base_url: '',
  models: [{ model_key: '', display_name: '', capabilities: ['llm_text'] }],
})

const capabilityOptions = [
  { label: 'LLM', value: 'llm_text' },
  { label: '音色优化', value: 'llm_voice_prompt_polish' },
  { label: 'TTS', value: 'tts_plain' },
  { label: '分镜', value: 'scene_planning' },
  { label: '润色', value: 'script_polish' },
]

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
      provider_type: 'openai_compatible',
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

const loaded = ref(false)

const loadPresets = async () => {
  if (loaded.value) return
  try {
    const [presetRes, customRes] = await Promise.all([
      modelProvidersApi.getPresets(),
      customProvidersApi.list(),
    ])
    const builtin = presetRes.data.map(p => ({ ...p, _isCustom: false }))
    const custom = customRes.data.map(p => ({
      provider_key: p.provider_key,
      display_name: p.display_name,
      provider_type: 'openai_compatible',
      base_url: p.base_url,
      capabilities: [],
      models: p.models || [],
      _isCustom: true,
      _customId: p.id,
    }))
    presets.value = [...builtin, ...custom]
    loaded.value = true
  } catch (e) {
    console.error('加载供应商预设失败:', e)
  }
}

onMounted(loadPresets)

watch(() => props.active, (val) => {
  if (val) loadPresets()
})

const addModel = () => {
  newProvider.models.push({ model_key: '', display_name: '', capabilities: ['llm_text'] })
}

const removeModel = (idx) => {
  newProvider.models.splice(idx, 1)
}

const cancelAdd = () => {
  showAddForm.value = false
  addError.value = ''
  newProvider.display_name = ''
  newProvider.base_url = ''
  newProvider.models = [{ model_key: '', display_name: '', capabilities: ['llm_text'] }]
}

const handleAdd = async () => {
  addError.value = ''
  if (!newProvider.display_name.trim()) {
    addError.value = '请输入供应商名称'
    return
  }
  if (!newProvider.base_url.trim()) {
    addError.value = '请输入 Base URL'
    return
  }
  const validModels = newProvider.models.filter(m => m.model_key.trim())
  if (validModels.length === 0) {
    addError.value = '请至少添加一个模型并填写模型 ID'
    return
  }

  adding.value = true
  try {
    await customProvidersApi.create({
      display_name: newProvider.display_name.trim(),
      base_url: newProvider.base_url.trim(),
      models: validModels.map(m => ({
        model_key: m.model_key.trim(),
        display_name: m.display_name.trim() || m.model_key.trim(),
        capabilities: m.capabilities,
      })),
    })
    loaded.value = false
    await loadPresets()
    cancelAdd()
  } catch (e) {
    addError.value = e.response?.data?.error || '添加失败'
  } finally {
    adding.value = false
  }
}

const handleDeleteCustom = (preset) => {
  Modal.confirm({
    title: '删除供应商',
    content: `确定要删除「${preset.display_name}」吗？`,
    okText: '删除',
    okType: 'danger',
    cancelText: '取消',
    onOk: async () => {
      await customProvidersApi.delete(preset._customId)
      removeProvider(preset.provider_key)
      loaded.value = false
      await loadPresets()
    },
  })
}
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

.delete-btn {
  margin-left: auto;
}

.test-result {
  margin-top: 12px;
}

.add-section {
  margin-top: 4px;
}

.add-form {
  border-style: dashed;
}

.models-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
  font-size: 13px;
  font-weight: 500;
}

.model-entry {
  padding: 8px;
  margin-bottom: 8px;
  background: var(--paper, #fafafa);
  border-radius: 6px;
}

.model-entry-row {
  display: flex;
  gap: 8px;
  align-items: center;
}

.model-input {
  flex: 1;
}

.model-caps {
  margin-top: 6px;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 12px;
}
</style>
