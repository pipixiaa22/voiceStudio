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
