<template>
  <div class="system-config-panel">
    <a-spin :spinning="loading">
      <!-- Database -->
      <a-divider>数据库连接</a-divider>
      <a-form layout="vertical" size="small">
        <a-form-item label="当前状态">
          <a-tag :color="config.database?.effective_db === 'MySQL' ? 'green' : 'blue'">
            {{ config.database?.effective_db || 'SQLite' }}
          </a-tag>
        </a-form-item>
        <a-form-item label="DATABASE_URL">
          <a-input-password
            v-model:value="form.DATABASE_URL"
            placeholder="mysql+pymysql://user:pass@host:port/db?charset=utf8mb4"
          />
          <span class="hint">留空则使用本地 SQLite</span>
        </a-form-item>
        <a-button size="small" @click="handleTest('database')" :loading="testingDb">
          测试连接
        </a-button>
        <a-tag v-if="testResult.database" :color="testResult.database.ok ? 'green' : 'red'" style="margin-left: 8px">
          {{ testResult.database.message }}
        </a-tag>
      </a-form>

      <!-- Redis -->
      <a-divider>Redis 连接</a-divider>
      <a-form layout="vertical" size="small">
        <a-form-item label="当前状态">
          <a-tag :color="config.redis?.connected ? 'green' : 'orange'">
            {{ config.redis?.connected ? '已连接' : (config.redis?.REDIS_URL ? '连接失败' : '未配置') }}
          </a-tag>
        </a-form-item>
        <a-form-item label="REDIS_URL">
          <a-input-password
            v-model:value="form.REDIS_URL"
            placeholder="redis://:password@host:port/db"
          />
        </a-form-item>
        <a-form-item label="REDIS_KEY_PREFIX">
          <a-input v-model:value="form.REDIS_KEY_PREFIX" placeholder="video-script" />
        </a-form-item>
        <a-button size="small" @click="handleTest('redis')" :loading="testingRedis">
          测试连接
        </a-button>
        <a-tag v-if="testResult.redis" :color="testResult.redis.ok ? 'green' : 'red'" style="margin-left: 8px">
          {{ testResult.redis.message }}
        </a-tag>
      </a-form>

      <!-- RAG -->
      <a-divider>RAG 向量库</a-divider>
      <a-form layout="vertical" size="small">
        <a-form-item label="CHROMADB_PERSIST_DIR">
          <a-input
            v-model:value="form.CHROMADB_PERSIST_DIR"
            placeholder="留空则使用默认路径 data/chromadb"
          />
        </a-form-item>
        <a-form-item label="OPENAI_API_KEY (用于 Embedding)">
          <a-input-password
            v-model:value="form.OPENAI_API_KEY"
            placeholder="sk-..."
          />
        </a-form-item>
        <a-form-item label="DEEPSEEK_API_KEY (备选 Embedding)">
          <a-input-password
            v-model:value="form.DEEPSEEK_API_KEY"
            placeholder="sk-..."
          />
        </a-form-item>
      </a-form>

      <!-- Save -->
      <div class="save-section">
        <a-button type="primary" @click="handleSave" :loading="saving">
          保存配置
        </a-button>
        <span class="hint">保存后需要重启服务生效</span>
      </div>
    </a-spin>
  </div>
</template>

<script setup>
import { ref, reactive, watch } from 'vue'
import { message } from 'ant-design-vue'
import { systemApi } from '../../api'

const props = defineProps({ active: Boolean })

const loading = ref(false)
const saving = ref(false)
const testingDb = ref(false)
const testingRedis = ref(false)
const config = ref({})
const testResult = reactive({ database: null, redis: null })

const form = reactive({
  DATABASE_URL: '',
  REDIS_URL: '',
  REDIS_KEY_PREFIX: 'video-script',
  CHROMADB_PERSIST_DIR: '',
  OPENAI_API_KEY: '',
  DEEPSEEK_API_KEY: '',
})

const loadConfig = async () => {
  loading.value = true
  try {
    const { data } = await systemApi.getConfig()
    config.value = data
    // Populate form with masked values (user can overwrite)
    form.DATABASE_URL = ''
    form.REDIS_URL = ''
    form.REDIS_KEY_PREFIX = data.redis?.REDIS_KEY_PREFIX || 'video-script'
    form.CHROMADB_PERSIST_DIR = data.rag?.CHROMADB_PERSIST_DIR || ''
    form.OPENAI_API_KEY = ''
    form.DEEPSEEK_API_KEY = ''
  } finally {
    loading.value = false
  }
}

const handleSave = async () => {
  saving.value = true
  try {
    // Only send non-empty values
    const updates = {}
    for (const [key, val] of Object.entries(form)) {
      if (val !== '') updates[key] = val
    }
    if (Object.keys(updates).length === 0) {
      message.warning('没有需要保存的配置')
      return
    }
    const { data } = await systemApi.updateConfig(updates)
    message.success(data.message || '已保存')
  } catch (e) {
    message.error('保存失败: ' + (e.response?.data?.error || e.message))
  } finally {
    saving.value = false
  }
}

const handleTest = async (target) => {
  if (target === 'database') testingDb.value = true
  if (target === 'redis') testingRedis.value = true
  testResult[target] = null

  try {
    const payload = { target }
    if (target === 'database' && form.DATABASE_URL) {
      payload.DATABASE_URL = form.DATABASE_URL
    }
    if (target === 'redis' && form.REDIS_URL) {
      payload.REDIS_URL = form.REDIS_URL
    }
    const { data } = await systemApi.testConfig(payload)
    testResult[target] = data[target]
  } catch (e) {
    testResult[target] = { ok: false, message: '测试失败' }
  } finally {
    testingDb.value = false
    testingRedis.value = false
  }
}

watch(() => props.active, (val) => {
  if (val && !config.value.database) loadConfig()
})
</script>

<style scoped>
.system-config-panel { padding: 0 4px; }
.hint { display: block; font-size: 12px; color: var(--text-muted); margin-top: 4px; }
.save-section { margin-top: 16px; display: flex; align-items: center; gap: 12px; }
:deep(.ant-divider) { margin: 16px 0 12px; font-size: 13px; }
:deep(.ant-form-item) { margin-bottom: 12px; }
</style>
