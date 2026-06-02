<template>
  <div class="novel-version-list">
    <a-empty v-if="!store.versions.length" description="暂无版本" />
    <div v-else class="version-cards">
      <div
        v-for="v in store.versions"
        :key="v.id"
        class="version-card"
        :class="{ accepted: v.accepted }"
      >
        <div class="version-header">
          <a-tag :color="typeColor(v.version_type)">{{ typeName(v.version_type) }}</a-tag>
          <a-tag v-if="v.accepted" color="green">已采纳</a-tag>
        </div>
        <div class="version-meta">
          {{ v.content_markdown?.length || 0 }} 字 · {{ formatDate(v.created_at) }}
        </div>
        <div class="version-preview">
          {{ (v.content_markdown || '').slice(0, 120) }}...
        </div>
        <div class="version-actions">
          <a-button size="small" @click="handlePreview(v)">预览</a-button>
          <a-button size="small" type="primary" @click="handleAccept(v)" :disabled="v.accepted">采纳</a-button>
          <a-popconfirm title="删除此版本？" @confirm="handleDelete(v)">
            <a-button size="small" danger>删除</a-button>
          </a-popconfirm>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { message } from 'ant-design-vue'
import { useNovelsStore } from '../../stores/novels'

const store = useNovelsStore()

const typeNames = { steady: '稳健', conflict: '强冲突', climax: '爽点', suspense: '悬疑', romance: '感情', polish: '精修', custom: '自定义' }
const typeColors = { steady: 'blue', conflict: 'red', climax: 'orange', suspense: 'purple', romance: 'pink', polish: 'cyan', custom: 'default' }
const typeName = (t) => typeNames[t] || t
const typeColor = (t) => typeColors[t] || 'default'

const formatDate = (iso) => {
  if (!iso) return ''
  return new Date(iso).toLocaleString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

const handlePreview = (v) => {
  store.currentChapter.content_markdown = v.content_markdown
}

const handleAccept = async (v) => {
  try {
    await store.acceptVersion(store.currentProject.id, store.currentChapter.id, v.id)
    message.success('已采纳')
  } catch {
    message.error('采纳失败')
  }
}

const handleDelete = async (v) => {
  try {
    await store.deleteVersion(store.currentProject.id, store.currentChapter.id, v.id)
    message.success('已删除')
  } catch {
    message.error('删除失败')
  }
}
</script>

<style scoped>
.version-cards { display: flex; flex-direction: column; gap: 8px; padding: 8px; }
.version-card {
  border: 1px solid var(--surface-border);
  border-radius: 6px;
  padding: 12px;
}
.version-card.accepted { border-color: var(--success); }
.version-header { display: flex; gap: 4px; margin-bottom: 4px; }
.version-meta { font-size: 12px; color: var(--text-muted); margin-bottom: 4px; }
.version-preview { font-size: 13px; color: var(--text-secondary); margin-bottom: 8px; line-height: 1.5; }
.version-actions { display: flex; gap: 4px; }
</style>
