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
          <span v-if="config.database?.host" class="hint" style="display: inline; margin-left: 8px">
            {{ config.database.host }}:{{ config.database.port }}/{{ config.database.database }}
          </span>
        </a-form-item>
        <a-row :gutter="12">
          <a-col :span="12">
            <a-form-item label="主机">
              <a-input v-model:value="db.host" placeholder="127.0.0.1" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="端口">
              <a-input v-model:value="db.port" placeholder="3306" />
            </a-form-item>
          </a-col>
        </a-row>
        <a-row :gutter="12">
          <a-col :span="12">
            <a-form-item label="用户名">
              <a-input v-model:value="db.user" placeholder="root" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="密码">
              <a-input-password v-model:value="db.password" placeholder="留空则无密码" />
            </a-form-item>
          </a-col>
        </a-row>
        <a-form-item label="数据库名">
          <a-input v-model:value="db.database" placeholder="video_script" />
        </a-form-item>
        <a-form-item label="驱动">
          <a-select v-model:value="db.driver" size="small" style="width: 200px">
            <a-select-option value="mysql+pymysql">MySQL (pymysql)</a-select-option>
          </a-select>
        </a-form-item>
        <a-button size="small" @click="handleTest('database')" :loading="testingDb">
          测试连接
        </a-button>
        <a-tag v-if="testResult.database" :color="testResult.database.ok ? 'green' : 'red'" style="margin-left: 8px">
          {{ testResult.database.message }}
        </a-tag>
        <span class="hint">全部留空则使用本地 SQLite</span>

        <!-- Table status after successful test -->
        <div v-if="tableStatus" class="table-status">
          <a-alert
            v-if="tableStatus.all_exist"
            type="success"
            show-icon
            message="表结构完整"
            :description="`全部 ${tableStatus.total} 张表已存在`"
            style="margin-top: 12px"
          />
          <a-alert
            v-else
            type="warning"
            show-icon
            message="表结构不完整"
            :description="`${tableStatus.existing}/${tableStatus.total} 张表已存在，缺少 ${tableStatus.missing.length} 张`"
            style="margin-top: 12px"
          />
          <div v-if="!tableStatus.all_exist" class="table-actions">
            <a-button size="small" type="primary" @click="handleCreateTables" :loading="creatingTables">
              自动创建表结构
            </a-button>
            <a-button size="small" @click="handleShowDdl" :loading="loadingDdl">
              查看 SQL 语句
            </a-button>
          </div>
        </div>

        <!-- DDL modal -->
        <a-modal v-model:open="showDdlModal" title="建表 SQL" width="700px" :footer="null">
          <p class="hint">复制以下 SQL 在数据库中手动执行：</p>
          <a-textarea :value="ddlContent" :autoSize="{ minRows: 10, maxRows: 30 }" readonly style="font-family: monospace; font-size: 12px; margin-top: 8px;" />
          <a-button size="small" style="margin-top: 8px" @click="copyDdl">复制到剪贴板</a-button>
        </a-modal>
      </a-form>

      <!-- Redis -->
      <a-divider>Redis 连接</a-divider>
      <a-form layout="vertical" size="small">
        <a-form-item label="当前状态">
          <a-tag :color="config.redis?.connected ? 'green' : 'orange'">
            {{ config.redis?.connected ? '已连接' : (config.redis?.host ? '连接失败' : '未配置') }}
          </a-tag>
          <span v-if="config.redis?.host" class="hint" style="display: inline; margin-left: 8px">
            {{ config.redis.host }}:{{ config.redis.port }}
          </span>
        </a-form-item>
        <a-row :gutter="12">
          <a-col :span="12">
            <a-form-item label="主机">
              <a-input v-model:value="rd.host" placeholder="127.0.0.1" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="端口">
              <a-input v-model:value="rd.port" placeholder="6379" />
            </a-form-item>
          </a-col>
        </a-row>
        <a-row :gutter="12">
          <a-col :span="12">
            <a-form-item label="密码">
              <a-input-password v-model:value="rd.password" placeholder="留空则无密码" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="数据库编号">
              <a-input v-model:value="rd.db" placeholder="0" />
            </a-form-item>
          </a-col>
        </a-row>
        <a-form-item label="KEY_PREFIX">
          <a-input v-model:value="rd.REDIS_KEY_PREFIX" placeholder="video-script" />
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
        <a-form-item label="向量库存储路径">
          <a-input
            v-model:value="rag.CHROMADB_PERSIST_DIR"
            placeholder="留空则使用默认路径 data/chromadb"
          />
        </a-form-item>
        <a-form-item label="OPENAI_API_KEY (用于 Embedding)">
          <a-input-password
            v-model:value="rag.OPENAI_API_KEY"
            placeholder="sk-..."
          />
        </a-form-item>
        <a-form-item label="DEEPSEEK_API_KEY (备选 Embedding)">
          <a-input-password
            v-model:value="rag.DEEPSEEK_API_KEY"
            placeholder="sk-..."
          />
        </a-form-item>
      </a-form>

      <!-- Save -->
      <div class="save-section">
        <a-button type="primary" @click="handleSave" :loading="saving">
          保存配置
        </a-button>
        <a-button v-if="saved" type="primary" danger @click="handleRestart" :loading="restarting">
          立即重启服务
        </a-button>
        <span v-if="saved && !restarting" class="hint">配置已保存，重启后生效</span>
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
const creatingTables = ref(false)
const loadingDdl = ref(false)
const restarting = ref(false)
const saved = ref(false)
const config = ref({})
const testResult = reactive({ database: null, redis: null })
const tableStatus = ref(null)
const showDdlModal = ref(false)
const ddlContent = ref('')

const db = reactive({
  driver: 'mysql+pymysql',
  host: '',
  port: '3306',
  user: '',
  password: '',
  database: '',
})

const rd = reactive({
  host: '',
  port: '6379',
  password: '',
  db: '0',
  REDIS_KEY_PREFIX: 'video-script',
})

const rag = reactive({
  CHROMADB_PERSIST_DIR: '',
  OPENAI_API_KEY: '',
  DEEPSEEK_API_KEY: '',
})

const loadConfig = async () => {
  loading.value = true
  try {
    const { data } = await systemApi.getConfig()
    config.value = data

    // Populate database fields
    db.host = data.database?.host || ''
    db.port = data.database?.port || '3306'
    db.user = data.database?.user || ''
    db.password = ''
    db.database = data.database?.database || ''
    db.driver = data.database?.driver || 'mysql+pymysql'

    // Populate redis fields
    rd.host = data.redis?.host || ''
    rd.port = data.redis?.port || '6379'
    rd.password = ''
    rd.db = data.redis?.db || '0'
    rd.REDIS_KEY_PREFIX = data.redis?.REDIS_KEY_PREFIX || 'video-script'

    // Populate rag fields
    rag.CHROMADB_PERSIST_DIR = data.rag?.CHROMADB_PERSIST_DIR || ''
    rag.OPENAI_API_KEY = ''
    rag.DEEPSEEK_API_KEY = ''
  } finally {
    loading.value = false
  }
}

const handleSave = async () => {
  saving.value = true
  try {
    const payload = {}

    // Database: only send if user filled in host+database
    if (db.host && db.database) {
      payload.database = { ...db }
    } else if (!db.host && !db.database) {
      // Explicitly clear to switch to SQLite
      payload.database = { host: '', database: '' }
    }

    // Redis: only send if user filled in host
    if (rd.host) {
      payload.redis = { ...rd }
    }

    // RAG: send non-empty values
    const ragUpdates = {}
    for (const [key, val] of Object.entries(rag)) {
      if (val !== '') ragUpdates[key] = val
    }
    if (Object.keys(ragUpdates).length > 0) {
      payload.rag = ragUpdates
    }

    if (Object.keys(payload).length === 0) {
      message.warning('没有需要保存的配置')
      return
    }

    const { data } = await systemApi.updateConfig(payload)
    message.success(data.message || '已保存')
    saved.value = true
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
  if (target === 'database') tableStatus.value = null

  try {
    const payload = { target }
    if (target === 'database') {
      payload.database = { ...db }
    }
    if (target === 'redis') {
      payload.redis = { ...rd }
    }
    const { data } = await systemApi.testConfig(payload)
    testResult[target] = data[target]

    // After successful database test, check tables on the tested DB
    if (target === 'database' && data[target]?.ok) {
      try {
        const { data: tables } = await systemApi.checkTables(db)
        tableStatus.value = tables
      } catch {
        // Table check is best-effort
      }
    }
  } catch (e) {
    testResult[target] = { ok: false, message: '测试失败' }
  } finally {
    testingDb.value = false
    testingRedis.value = false
  }
}

const handleCreateTables = async () => {
  creatingTables.value = true
  try {
    const { data } = await systemApi.createTables(db)
    message.success(data.message || '表已创建')
    // Re-check tables on the target DB
    const { data: tables } = await systemApi.checkTables(db)
    tableStatus.value = tables
  } catch (e) {
    message.error('创建失败: ' + (e.response?.data?.error || e.message))
  } finally {
    creatingTables.value = false
  }
}

const handleShowDdl = async () => {
  loadingDdl.value = true
  try {
    const { data } = await systemApi.getDdl()
    ddlContent.value = data.ddl || '无法生成 DDL'
    showDdlModal.value = true
  } catch (e) {
    message.error('获取 DDL 失败: ' + (e.response?.data?.error || e.message))
  } finally {
    loadingDdl.value = false
  }
}

const copyDdl = async () => {
  try {
    await navigator.clipboard.writeText(ddlContent.value)
    message.success('已复制到剪贴板')
  } catch {
    message.error('复制失败，请手动选择复制')
  }
}

const handleRestart = async () => {
  restarting.value = true
  try {
    await systemApi.restart()
    message.success('服务正在重启，请稍候...')
    // Poll health endpoint until server is back
    setTimeout(() => {
      window.location.reload()
    }, 3000)
  } catch {
    // If request fails (server is restarting), just reload after delay
    setTimeout(() => {
      window.location.reload()
    }, 3000)
  }
}

watch(() => props.active, (val) => {
  if (val) loadConfig()
})
</script>

<style scoped>
.system-config-panel { padding: 0 4px; }
.hint { display: block; font-size: 12px; color: var(--text-muted); margin-top: 4px; }
.save-section { margin-top: 16px; display: flex; align-items: center; gap: 12px; }
:deep(.ant-divider) { margin: 16px 0 12px; font-size: 13px; }
:deep(.ant-form-item) { margin-bottom: 12px; }
.table-status { margin-top: 8px; }
.table-actions { display: flex; gap: 8px; margin-top: 8px; }
</style>
