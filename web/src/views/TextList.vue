<template>
  <a-layout>
    <a-layout-sider width="220" style="background: #fff; padding: 16px">
      <FolderTree
        :selectedFolderId="selectedFolderId"
        @select="selectedFolderId = $event"
      />
    </a-layout-sider>
    <a-layout-content style="padding: 0 24px">
      <div style="margin-bottom: 16px; display: flex; gap: 16px; align-items: center">
        <a-input-search
          v-model:value="searchQuery"
          placeholder="搜索文本..."
          style="flex: 1"
        />
        <a-select v-model:value="sortBy" style="width: 120px">
          <a-select-option value="created_at">创建时间</a-select-option>
          <a-select-option value="updated_at">更新时间</a-select-option>
        </a-select>
        <a-select v-model:value="sortOrder" style="width: 100px">
          <a-select-option value="desc">降序</a-select-option>
          <a-select-option value="asc">升序</a-select-option>
        </a-select>
        <router-link to="/edit">
          <a-button type="primary">
            <template #icon><PlusOutlined /></template>
            新建文本
          </a-button>
        </router-link>
      </div>

      <a-spin :spinning="loading">
        <a-table
          :dataSource="filteredTexts"
          :columns="columns"
          rowKey="id"
          :pagination="{ pageSize: 20 }"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'title'">
              <router-link :to="`/edit/${record.id}`">{{ record.title }}</router-link>
            </template>
            <template v-else-if="column.key === 'tags'">
              <a-tag v-for="tag in record.tags" :key="tag.id" color="success">
                {{ tag.name }}
              </a-tag>
            </template>
            <template v-else-if="column.key === 'created_at'">
              {{ formatDate(record.created_at) }}
            </template>
            <template v-else-if="column.key === 'updated_at'">
              {{ formatDate(record.updated_at) }}
            </template>
            <template v-else-if="column.key === 'action'">
              <a-space>
                <a-button size="small" @click="handleExport(record.id)">
                  <template #icon><DownloadOutlined /></template>
                  导出SRT
                </a-button>
                <a-popconfirm
                  title="确定删除此文本？"
                  @confirm="handleDelete(record.id)"
                >
                  <a-button size="small" danger>
                    <template #icon><DeleteOutlined /></template>
                    删除
                  </a-button>
                </a-popconfirm>
              </a-space>
            </template>
          </template>
        </a-table>
      </a-spin>
    </a-layout-content>
  </a-layout>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { PlusOutlined, DownloadOutlined, DeleteOutlined } from '@ant-design/icons-vue'
import { useTextsStore } from '../stores/texts'
import FolderTree from '../components/FolderTree.vue'

const textsStore = useTextsStore()
const selectedFolderId = ref(null)
const searchQuery = ref('')
const sortBy = ref('created_at')
const sortOrder = ref('desc')

const loading = computed(() => textsStore.loading)

const columns = [
  { title: '标题', key: 'title', dataIndex: 'title' },
  { title: '标签', key: 'tags' },
  { title: '创建时间', key: 'created_at' },
  { title: '更新时间', key: 'updated_at' },
  { title: '操作', key: 'action', width: 200 },
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
  return new Date(dateStr).toLocaleString('zh-CN')
}

const handleExport = async (id) => {
  await textsStore.exportSrt(id, { speed: 5, max_chars: 20 })
}

const handleDelete = async (id) => {
  await textsStore.deleteText(id)
}
</script>
