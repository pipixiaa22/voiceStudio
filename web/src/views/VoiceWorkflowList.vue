<template>
  <div class="voice-workflow-list">
    <div class="page-header">
      <div>
        <h1 class="page-title">配音工作台</h1>
        <p class="page-subtitle">{{ store.workflows.length }} 个配音工程</p>
      </div>
      <a-button type="primary" @click="$router.push('/voice-workflows/new')">新建配音工程</a-button>
    </div>

    <div class="list-tools">
      <a-input-search
        v-model:value="keyword"
        placeholder="搜索工程标题或源文本"
        allow-clear
      />
    </div>

    <a-empty v-if="!store.workflows.length" description="还没有配音工程">
      <a-button type="primary" @click="$router.push('/voice-workflows/new')">新建配音工程</a-button>
    </a-empty>

    <a-empty v-else-if="!filteredWorkflows.length" description="没有匹配的配音工程" />

    <div v-else class="workflow-grid">
      <article
        v-for="workflow in filteredWorkflows"
        :key="workflow.id"
        class="workflow-item"
      >
        <button class="workflow-main" @click="$router.push(`/voice-workflows/${workflow.id}`)">
          <strong>{{ workflow.title || '未命名配音工程' }}</strong>
          <span class="workflow-source">{{ sourcePreview(workflow) }}</span>
          <span class="workflow-meta">
            {{ workflow.segment_count || 0 }} 句 · {{ workflow.edge_count || 0 }} 条连线 · {{ formatDate(workflow.updated_at) }}
          </span>
        </button>
        <div class="workflow-actions">
          <a-button size="small" @click="$router.push(`/voice-workflows/${workflow.id}`)">打开</a-button>
          <a-button size="small" @click="handleDuplicate(workflow)">复制</a-button>
          <a-popconfirm
            title="删除这个配音工程？"
            ok-text="删除"
            cancel-text="取消"
            @confirm="handleDelete(workflow)"
          >
            <a-button size="small" danger>删除</a-button>
          </a-popconfirm>
        </div>
      </article>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { message } from 'ant-design-vue'
import { useVoiceWorkflowsStore } from '../stores/voiceWorkflows'

const store = useVoiceWorkflowsStore()
const keyword = ref('')

onMounted(() => store.fetchList())

const filteredWorkflows = computed(() => {
  const query = keyword.value.trim().toLowerCase()
  if (!query) return store.workflows
  return store.workflows.filter(workflow => {
    return [
      workflow.title,
      workflow.source_content,
      workflow.id ? `#${workflow.id}` : '',
    ].some(value => String(value || '').toLowerCase().includes(query))
  })
})

const sourcePreview = workflow => {
  const text = (workflow.source_content || '').replace(/\s+/g, ' ').trim()
  if (!text) return '空工程'
  return text.length > 54 ? `${text.slice(0, 54)}...` : text
}

const formatDate = value => {
  if (!value) return '未保存'
  return new Date(value).toLocaleString([], {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

const handleDuplicate = async workflow => {
  const title = `${workflow.title || '未命名配音工程'} 副本`
  const duplicate = await store.duplicate(workflow.id, title)
  message.success('已复制配音工程')
  return duplicate
}

const handleDelete = async workflow => {
  await store.remove(workflow.id)
  message.success('已删除配音工程')
}
</script>

<style scoped>
.voice-workflow-list { max-width: 1180px; margin: 0 auto; padding: var(--space-xl); }
.page-header { display: flex; align-items: center; justify-content: space-between; gap: var(--space-md); margin-bottom: var(--space-lg); }
.page-title { margin: 0; font-size: 28px; font-weight: 650; }
.page-subtitle { margin: 6px 0 0; color: var(--text-muted); }
.list-tools { max-width: 420px; margin-bottom: var(--space-lg); }
.workflow-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: var(--space-md); }
.workflow-item { border: 1px solid var(--surface-border); background: var(--surface); border-radius: var(--radius-md); padding: var(--space-md); display: flex; flex-direction: column; gap: var(--space-md); }
.workflow-main { text-align: left; border: 0; background: transparent; padding: 0; cursor: pointer; display: flex; flex-direction: column; gap: 8px; min-height: 112px; }
.workflow-main strong { font-size: 16px; color: var(--text-primary); }
.workflow-source { color: var(--text-secondary); line-height: 1.5; }
.workflow-meta { color: var(--text-muted); font-size: 12px; }
.workflow-actions { display: flex; gap: 8px; flex-wrap: wrap; }

@media (max-width: 720px) {
  .voice-workflow-list { padding: var(--space-md); }
  .page-header { align-items: flex-start; flex-direction: column; }
  .list-tools { max-width: none; }
}
</style>
