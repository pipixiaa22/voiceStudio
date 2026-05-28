<template>
  <div class="discovery-source-panel">
    <a-alert
      type="info"
      show-icon
      message="配置视频搜索平台"
      description="这里保存热点采集所需的平台 API Key。密钥只保存在本地后端数据库，列表中不会回显明文。"
    />

    <div class="source-section">
      <div class="source-header">
        <div>
          <div class="source-title">视频分析 LLM</div>
          <div class="source-meta">
            <span>用于结构分析和原创脚本生成</span>
            <span v-if="discoveryLlmKey">已配置</span>
            <span v-else>未配置（将复用音色描述优化的 API Key）</span>
          </div>
        </div>
      </div>
      <div class="field-row">
        <label>API Key</label>
        <a-input-password
          v-model:value="discoveryLlmKey"
          placeholder="留空则复用音色描述优化的 API Key"
        />
      </div>
      <div class="source-actions">
        <a-button size="small" type="primary" @click="saveDiscoveryLlmKey">
          保存
        </a-button>
      </div>
    </div>

    <a-spin :spinning="loading">
      <div class="source-list">
        <div v-for="source in configurableSources" :key="source.platform_key" class="source-section">
          <div class="source-header">
            <div>
              <div class="source-title">{{ source.display_name }}</div>
              <div class="source-meta">
                <span>{{ source.supports_search ? '支持关键词搜索' : '暂未接入关键词搜索' }}</span>
                <span v-if="source.is_configured">已配置</span>
                <span v-else>待配置</span>
              </div>
            </div>
            <a-switch
              v-if="source.supports_search"
              :checked="drafts[source.platform_key]?.is_enabled"
              size="small"
              @change="(value) => updateEnabled(source.platform_key, value)"
            />
          </div>

          <div v-for="field in source.config_fields" :key="field.key" class="field-row">
            <label>{{ field.label }}</label>
            <a-input-password
              :value="drafts[source.platform_key]?.config?.[field.key]"
              :placeholder="source.is_configured ? '已配置，留空则保持不变' : '输入 API Key'"
              @change="(event) => updateField(source.platform_key, field.key, event.target.value)"
            />
          </div>

          <div v-if="!source.supports_search" class="source-note">
            可先保存开放平台 Key，等后续接入搜索 Connector 后直接启用。
          </div>

          <div class="source-actions">
            <a-button
              size="small"
              type="primary"
              :loading="saving === source.platform_key"
              @click="saveSource(source)"
            >
              保存配置
            </a-button>
          </div>
        </div>
      </div>
    </a-spin>
  </div>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { message } from 'ant-design-vue'
import { discoveryApi } from '../../api'

const props = defineProps({
  active: { type: Boolean, default: true },
})

const sources = ref([])
const drafts = reactive({})
const loading = ref(false)
const saving = ref('')
const loaded = ref(false)
const discoveryLlmKey = ref(localStorage.getItem('mimo_discovery_llm_key') || '')

const configurableSources = computed(() => (
  sources.value.filter(source => source.config_fields?.length)
))

const syncDrafts = () => {
  for (const source of configurableSources.value) {
    drafts[source.platform_key] = {
      is_enabled: source.is_enabled,
      config: Object.fromEntries(source.config_fields.map(field => [field.key, ''])),
    }
  }
}

const loadSources = async () => {
  if (loaded.value) return
  loading.value = true
  try {
    const { data } = await discoveryApi.getSources()
    sources.value = data || []
    syncDrafts()
    loaded.value = true
  } catch (error) {
    message.error(error.response?.data?.error || '加载视频搜索配置失败')
  } finally {
    loading.value = false
  }
}

const updateEnabled = (platformKey, value) => {
  drafts[platformKey].is_enabled = value
}

const updateField = (platformKey, fieldKey, value) => {
  drafts[platformKey].config[fieldKey] = value
}

const saveSource = async (source) => {
  saving.value = source.platform_key
  try {
    const draft = drafts[source.platform_key]
    const config = Object.fromEntries(
      Object.entries(draft.config).filter(([, value]) => value?.trim())
    )
    const { data } = await discoveryApi.updateSourceConfig(source.platform_key, {
      is_enabled: draft.is_enabled,
      config,
    })
    sources.value = sources.value.map(item => (
      item.platform_key === source.platform_key ? data : item
    ))
    syncDrafts()
    window.dispatchEvent(new CustomEvent('discovery-sources-updated'))
    message.success(`${source.display_name} 配置已保存`)
  } catch (error) {
    message.error(error.response?.data?.error || '保存视频搜索配置失败')
  } finally {
    saving.value = ''
  }
}

watch(() => props.active, (active) => {
  if (active) {
    loadSources()
    discoveryLlmKey.value = localStorage.getItem('mimo_discovery_llm_key') || ''
  }
})

const saveDiscoveryLlmKey = () => {
  localStorage.setItem('mimo_discovery_llm_key', discoveryLlmKey.value.trim())
  message.success('视频分析 LLM API Key 已保存')
}
</script>

<style scoped>
.discovery-source-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.source-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
  margin-top: 16px;
}

.source-section {
  border: 1px solid var(--surface-border);
  border-radius: var(--radius-md);
  padding: 14px;
}

.source-header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.source-title {
  color: var(--text-primary);
  font-size: 14px;
  font-weight: 600;
}

.source-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 3px;
  color: var(--text-muted);
  font-size: 12px;
}

.field-row {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field-row label {
  color: var(--text-secondary);
  font-size: 12px;
}

.source-note {
  margin-top: 8px;
  color: var(--text-muted);
  font-size: 12px;
}

.source-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
}
</style>
