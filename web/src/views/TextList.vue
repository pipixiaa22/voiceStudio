<template>
  <div class="text-list-page">
    <a-layout>
      <a-layout-sider width="260" class="sidebar">
        <FolderTree
          :selectedFolderId="selectedFolderId"
          @select="selectedFolderId = $event"
          @moveText="fetchTexts"
        />
      </a-layout-sider>
      <a-layout-content class="main-content">
        <!-- Header Section -->
        <div class="content-header">
          <div class="header-left">
            <h1 class="page-title">
              <span class="title-accent">文</span>本库
            </h1>
            <span class="text-count">{{ filteredTexts.length }} 篇文本</span>
          </div>
          <div class="header-actions">
            <a-input-search
              v-model:value="searchQuery"
              placeholder="搜索文本..."
              class="search-input"
              allowClear
            />
            <a-select v-model:value="sortBy" class="sort-select">
              <a-select-option value="created_at">创建时间</a-select-option>
              <a-select-option value="updated_at">更新时间</a-select-option>
            </a-select>
            <a-select v-model:value="sortOrder" class="sort-select">
              <a-select-option value="desc">降序</a-select-option>
              <a-select-option value="asc">升序</a-select-option>
            </a-select>
            <router-link to="/edit">
              <a-button type="primary" class="create-btn">
                <template #icon>
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <line x1="12" y1="5" x2="12" y2="19"/>
                    <line x1="5" y1="12" x2="19" y2="12"/>
                  </svg>
                </template>
                新建文本
              </a-button>
            </router-link>
          </div>
        </div>

        <div class="ink-divider"></div>

        <!-- Table Section -->
        <a-spin :spinning="loading" tip="载入中...">
          <a-table
            :dataSource="filteredTexts"
            :columns="columns"
            rowKey="id"
            :pagination="{ pageSize: 20, hideOnSinglePage: true }"
            class="text-table"
            :customRow="(record) => ({
              draggable: true,
              onDragstart: (e) => handleTextDragStart(record.id, e),
              onDragend: handleTextDragEnd,
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
                  <a-tooltip title="导出 SRT 字幕">
                    <a-button size="small" class="action-btn" @click="handleExport(record)">
                      <template #icon>
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                          <polyline points="7 10 12 15 17 10"/>
                          <line x1="12" y1="15" x2="12" y2="3"/>
                        </svg>
                      </template>
                    </a-button>
                  </a-tooltip>
                  <a-popconfirm
                    title="确定删除此文本？"
                    description="删除后不可恢复"
                    @confirm="handleDelete(record.id)"
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
      </a-layout-content>
    </a-layout>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { message } from 'ant-design-vue'
import { useTextsStore } from '../stores/texts'
import FolderTree from '../components/FolderTree.vue'

const textsStore = useTextsStore()
const selectedFolderId = ref(null)
const searchQuery = ref('')
const sortBy = ref('created_at')
const sortOrder = ref('desc')

const loading = computed(() => textsStore.loading)

const columns = [
  {
    title: '标题',
    key: 'title',
    dataIndex: 'title',
    width: '30%',
    ellipsis: true,
  },
  {
    title: '标签',
    key: 'tags',
    width: '20%',
  },
  {
    title: '创建时间',
    key: 'created_at',
    width: '18%',
  },
  {
    title: '更新时间',
    key: 'updated_at',
    width: '18%',
  },
  {
    title: '操作',
    key: 'action',
    width: '14%',
    align: 'center',
  },
]

const fetchTexts = () => {
  textsStore.fetchTexts({
    folder_id: selectedFolderId.value,
    sort_by: sortBy.value,
    order: sortOrder.value,
  })
}

onMounted(fetchTexts)
watch([selectedFolderId, sortBy, sortOrder], fetchTexts)

const filteredTexts = computed(() => {
  if (!searchQuery.value) return textsStore.texts
  const query = searchQuery.value.toLowerCase()
  return textsStore.texts.filter(t =>
    t.title.toLowerCase().includes(query) || t.content.toLowerCase().includes(query)
  )
})

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
  return date.toLocaleDateString('zh-CN', {
    month: 'short',
    day: 'numeric',
  })
}

const handleExport = async (record) => {
  await textsStore.exportSrt(record.id, { speed: 5, max_chars: 20 })
  message.success(`已导出：${record.title}.srt`)
}

const handleDelete = async (id) => {
  await textsStore.deleteText(id)
  message.success('已删除')
}

// Drag and drop handlers for text rows
const handleTextDragStart = (textId, event) => {
  event.dataTransfer.setData('textId', textId)
  event.dataTransfer.effectAllowed = 'move'
  // Add visual feedback
  event.target.closest('tr').classList.add('dragging')
}

const handleTextDragEnd = (event) => {
  // Remove visual feedback
  event.target.closest('tr')?.classList.remove('dragging')
}
</script>

<style scoped>
.text-list-page {
  max-width: 1400px;
  margin: 0 auto;
}

.sidebar {
  background: var(--surface-card) !important;
  border-radius: var(--radius-lg) 0 0 var(--radius-lg);
  border: 1px solid var(--surface-border);
  border-right: none;
  padding: var(--space-lg);
  overflow-y: auto;
  max-height: calc(100vh - 130px);
}

.main-content {
  background: var(--surface-card) !important;
  border-radius: 0 var(--radius-lg) var(--radius-lg) 0;
  border: 1px solid var(--surface-border);
  padding: var(--space-xl);
  min-height: calc(100vh - 130px);
}

.content-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-md);
}

.header-left {
  display: flex;
  align-items: baseline;
  gap: var(--space-md);
}

.page-title {
  font-family: var(--font-display);
  font-size: 28px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
  letter-spacing: 2px;
}

.title-accent {
  color: var(--gold);
  text-shadow: 0 0 20px var(--gold-glow);
}

.text-count {
  font-size: 13px;
  color: var(--text-muted);
}

.header-actions {
  display: flex;
  gap: var(--space-sm);
  align-items: center;
}

.search-input {
  width: 220px;
}

.sort-select {
  width: 110px;
}

.create-btn {
  padding: 0 20px !important;
  height: 36px;
  font-weight: 600 !important;
  letter-spacing: 1px;
}

.create-btn svg {
  width: 16px;
  height: 16px;
  margin-right: 6px;
}

/* Table Styling */
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
  color: var(--gold);
}

.custom-tag {
  background: rgba(212, 168, 83, 0.1) !important;
  border: 1px solid rgba(212, 168, 83, 0.2) !important;
  color: var(--gold) !important;
  border-radius: var(--radius-sm) !important;
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

/* Dragging State */
.text-table :deep(.ant-table-row) {
  cursor: grab;
  transition: all var(--transition-fast);
}

.text-table :deep(.ant-table-row:hover) {
  background: var(--surface-hover);
}

.text-table :deep(.ant-table-row.dragging) {
  opacity: 0.5;
  cursor: grabbing;
  background: var(--gold-glow);
}

/* Responsive */
@media (max-width: 1200px) {
  .content-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .header-actions {
    width: 100%;
    flex-wrap: wrap;
  }

  .search-input {
    flex: 1;
    min-width: 200px;
  }
}

@media (max-width: 768px) {
  .sidebar {
    display: none;
  }

  .main-content {
    border-radius: var(--radius-lg);
  }
}
</style>
