<template>
  <div class="text-list-page">
    <FolderTree
      :selectedFolderId="selectedFolderId"
      @select="selectedFolderId = $event"
    />

    <div class="text-list-content">
      <div class="toolbar">
        <input v-model="searchQuery" placeholder="搜索文本..." class="search-input" />
        <select v-model="sortBy" class="sort-select">
          <option value="created_at">创建时间</option>
          <option value="updated_at">更新时间</option>
        </select>
        <select v-model="sortOrder" class="sort-select">
          <option value="desc">降序</option>
          <option value="asc">升序</option>
        </select>
        <router-link to="/edit" class="btn btn-primary">新建文本</router-link>
      </div>

      <div v-if="loading" class="loading">加载中...</div>

      <table v-else class="text-table">
        <thead>
          <tr>
            <th>标题</th>
            <th>标签</th>
            <th>创建时间</th>
            <th>更新时间</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="text in filteredTexts" :key="text.id">
            <td>
              <router-link :to="`/edit/${text.id}`">{{ text.title }}</router-link>
            </td>
            <td>
              <span v-for="tag in text.tags" :key="tag.id" class="tag">{{ tag.name }}</span>
            </td>
            <td>{{ formatDate(text.created_at) }}</td>
            <td>{{ formatDate(text.updated_at) }}</td>
            <td>
              <button @click="handleExport(text.id)" class="btn btn-sm">导出SRT</button>
              <button @click="handleDelete(text.id)" class="btn btn-sm btn-danger">删除</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useTextsStore } from '../stores/texts'
import FolderTree from '../components/FolderTree.vue'

const textsStore = useTextsStore()
const selectedFolderId = ref(null)
const searchQuery = ref('')
const sortBy = ref('created_at')
const sortOrder = ref('desc')

const loading = computed(() => textsStore.loading)

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
  if (confirm('确定删除此文本？')) {
    await textsStore.deleteText(id)
  }
}
</script>

<style scoped>
.text-list-page {
  display: flex;
  min-height: calc(100vh - 60px);
}
.text-list-content {
  flex: 1;
  padding: 1rem;
}
.toolbar {
  display: flex;
  gap: 1rem;
  margin-bottom: 1rem;
  align-items: center;
}
.search-input {
  flex: 1;
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
}
.sort-select {
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
}
.btn {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  text-decoration: none;
}
.btn-primary {
  background: #42b883;
  color: white;
}
.btn-sm {
  padding: 0.25rem 0.5rem;
  font-size: 0.875rem;
}
.btn-danger {
  background: #e74c3c;
  color: white;
}
.text-table {
  width: 100%;
  border-collapse: collapse;
}
.text-table th,
.text-table td {
  padding: 0.75rem;
  border-bottom: 1px solid #eee;
  text-align: left;
}
.text-table th {
  background: #f5f5f5;
}
.tag {
  display: inline-block;
  background: #e8f5e9;
  color: #2e7d32;
  padding: 0.125rem 0.5rem;
  border-radius: 12px;
  font-size: 0.75rem;
  margin-right: 0.25rem;
}
.loading {
  text-align: center;
  padding: 2rem;
  color: #999;
}
</style>
