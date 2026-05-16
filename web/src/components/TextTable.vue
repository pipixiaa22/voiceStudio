<template>
  <a-spin :spinning="loading" tip="载入中...">
    <a-table
      :dataSource="texts"
      :columns="columns"
      rowKey="id"
      :pagination="{ pageSize: 20, hideOnSinglePage: true }"
      class="text-table"
      :customRow="(record) => ({
        draggable: true,
        onDragstart: (e) => handleDragStart(record.id, e),
        onDragend: handleDragEnd,
      })"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'title'">
          <router-link :to="`/edit/${record.id}`" class="text-link">
            <span class="text-title">{{ record.title }}</span>
          </router-link>
        </template>
        <template v-else-if="column.key === 'tags'">
          <a-tag v-for="tag in record.tags" :key="tag.id" class="custom-tag">
            {{ tag.name }}
          </a-tag>
        </template>
        <template v-else-if="column.key === 'created_at'">
          <span class="date-text">{{ formatDate(record.created_at) }}</span>
        </template>
        <template v-else-if="column.key === 'updated_at'">
          <span class="date-text">{{ formatDate(record.updated_at) }}</span>
        </template>
        <template v-else-if="column.key === 'action'">
          <a-space :size="8">
            <a-tooltip title="预览 SRT 字幕">
              <a-button size="small" class="action-btn" @click="$emit('preview', record)">
                <template #icon>
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                    <circle cx="12" cy="12" r="3"/>
                  </svg>
                </template>
              </a-button>
            </a-tooltip>
            <a-dropdown :trigger="['click']">
              <a-button size="small" class="action-btn">
                <template #icon>
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                    <polyline points="7 10 12 15 17 10"/>
                    <line x1="12" y1="15" x2="12" y2="3"/>
                  </svg>
                </template>
              </a-button>
              <template #overlay>
                <a-menu @click="({ key }) => $emit('export', record, key)">
                  <a-menu-item key="zh">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14" style="margin-right: 8px; vertical-align: -2px">
                      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                      <polyline points="14 2 14 8 20 8"/>
                    </svg>
                    中文字幕
                  </a-menu-item>
                  <a-menu-item key="bilingual">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14" style="margin-right: 8px; vertical-align: -2px">
                      <circle cx="12" cy="12" r="10"/>
                      <line x1="2" y1="12" x2="22" y2="12"/>
                      <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>
                    </svg>
                    中英双语
                  </a-menu-item>
                </a-menu>
              </template>
            </a-dropdown>
            <a-popconfirm
              title="确定删除此文本？"
              description="删除后不可恢复"
              @confirm="$emit('delete', record.id)"
              okText="删除"
              cancelText="取消"
              okButtonProps="{ danger: true }"
            >
              <a-tooltip title="删除文本">
                <a-button size="small" danger class="action-btn">
                  <template #icon>
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <polyline points="3 6 5 6 21 6"/>
                      <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                    </svg>
                  </template>
                </a-button>
              </a-tooltip>
            </a-popconfirm>
          </a-space>
        </template>
      </template>
    </a-table>
  </a-spin>
</template>

<script setup>
import { message } from 'ant-design-vue'

defineProps({
  texts: { type: Array, default: () => [] },
  loading: Boolean,
})

defineEmits(['preview', 'export', 'delete'])

const columns = [
  { title: '标题', key: 'title', dataIndex: 'title', width: '34%', ellipsis: true },
  { title: '标签', key: 'tags', width: '18%', responsive: ['md'] },
  { title: '创建时间', key: 'created_at', width: '16%', responsive: ['lg'] },
  { title: '更新时间', key: 'updated_at', width: '18%', responsive: ['sm'] },
  { title: '操作', key: 'action', width: 132, align: 'center' },
]

const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  const now = new Date()
  const diff = now - date
  const days = Math.floor(diff / (1000 * 60 * 60 * 24))

  if (days === 0) {
    const hours = Math.floor(diff / (1000 * 60 * 60))
    if (hours === 0) {
      const minutes = Math.floor(diff / (1000 * 60))
      return minutes <= 1 ? '刚刚' : `${minutes} 分钟前`
    }
    return `${hours} 小时前`
  } else if (days === 1) {
    return '昨天'
  } else if (days < 7) {
    return `${days} 天前`
  }
  return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}

const handleDragStart = (textId, event) => {
  event.dataTransfer.setData('textId', textId)
  event.dataTransfer.effectAllowed = 'move'
  event.target.closest('tr').classList.add('dragging')
}

const handleDragEnd = (event) => {
  event.target.closest('tr')?.classList.remove('dragging')
}
</script>

<style scoped>
.text-table {
  margin-top: var(--space-md);
}

.text-link {
  text-decoration: none;
}

.text-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
  transition: color var(--transition-fast);
}

.text-link:hover .text-title {
  color: var(--text-secondary);
}

.custom-tag {
  background: var(--surface-muted) !important;
  border: 1px solid var(--surface-border) !important;
  color: var(--text-secondary) !important;
  border-radius: 999px !important;
  font-size: 12px !important;
  padding: 2px 10px !important;
}

.date-text {
  font-size: 13px;
  color: var(--text-muted);
}

.action-btn {
  width: 32px !important;
  height: 32px !important;
  padding: 0 !important;
  display: inline-flex !important;
  align-items: center;
  justify-content: center;
}

.action-btn svg {
  width: 15px;
  height: 15px;
}

:deep(.ant-table-row) {
  cursor: grab;
  transition: all var(--transition-fast);
}

:deep(.ant-table-row:hover) {
  background: var(--surface-hover);
}

:deep(.ant-table-row.dragging) {
  opacity: 0.5;
  cursor: grabbing;
  background: var(--surface-active);
}
</style>
