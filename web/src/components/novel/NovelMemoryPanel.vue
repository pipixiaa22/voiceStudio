<template>
  <div class="novel-memory-panel">
    <div class="memory-header">
      <a-input-search
        v-model:value="searchKeyword"
        placeholder="搜索记忆..."
        size="small"
        @search="handleSearch"
      />
      <div class="memory-filters">
        <a-select v-model:value="filterType" placeholder="类型" size="small" allow-clear style="width: 100px">
          <a-select-option value="character">人物</a-select-option>
          <a-select-option value="world_rule">世界观</a-select-option>
          <a-select-option value="event">事件</a-select-option>
          <a-select-option value="foreshadowing">伏笔</a-select-option>
          <a-select-option value="relationship">关系</a-select-option>
          <a-select-option value="style">文风</a-select-option>
          <a-select-option value="summary">摘要</a-select-option>
        </a-select>
        <a-button size="small" @click="showCreateModal = true">新增</a-button>
        <a-button size="small" :loading="reindexing" @click="handleReindex">重建索引</a-button>
      </div>
    </div>

    <a-spin :spinning="store.memoryLoading">
      <a-list :data-source="store.memories" size="small">
        <template #renderItem="{ item }">
          <a-list-item>
            <a-list-item-meta>
              <template #title>
                <span>{{ item.title || item.memory_type }}</span>
                <a-tag :color="typeColor(item.memory_type)" size="small" style="margin-left: 8px">
                  {{ typeLabel(item.memory_type) }}
                </a-tag>
                <a-tag :color="item.vector_status === 'indexed' ? 'green' : 'orange'" size="small">
                  {{ item.vector_status }}
                </a-tag>
              </template>
              <template #description>
                <div class="memory-content">{{ item.content?.slice(0, 100) }}...</div>
              </template>
            </a-list-item-meta>
            <template #actions>
              <a-button size="small" type="link" @click="handleEdit(item)">编辑</a-button>
              <a-popconfirm title="确认删除？" @confirm="handleDelete(item.id)">
                <a-button size="small" type="link" danger>删除</a-button>
              </a-popconfirm>
            </template>
          </a-list-item>
        </template>
      </a-list>
    </a-spin>

    <!-- Create/Edit Modal -->
    <a-modal
      v-model:open="showCreateModal"
      :title="editingMemory ? '编辑记忆' : '新增记忆'"
      @ok="handleSave"
      @cancel="resetForm"
      width="600px"
    >
      <a-form layout="vertical">
        <a-form-item label="标题">
          <a-input v-model:value="form.title" />
        </a-form-item>
        <a-form-item label="类型">
          <a-select v-model:value="form.memory_type">
            <a-select-option value="character">人物</a-select-option>
            <a-select-option value="world_rule">世界观</a-select-option>
            <a-select-option value="event">事件</a-select-option>
            <a-select-option value="foreshadowing">伏笔</a-select-option>
            <a-select-option value="relationship">关系</a-select-option>
            <a-select-option value="style">文风</a-select-option>
            <a-select-option value="summary">摘要</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="内容">
          <a-textarea v-model:value="form.content" :rows="6" />
        </a-form-item>
        <a-form-item label="重要性">
          <a-rate v-model:value="form.importance" :count="5" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { message } from 'ant-design-vue'
import { useNovelsStore } from '../../stores/novels'
import { typeColor, typeLabel } from '../../utils/memoryTypes'

const store = useNovelsStore()
const searchKeyword = ref('')
const filterType = ref(undefined)
const showCreateModal = ref(false)
const editingMemory = ref(null)
const reindexing = ref(false)
const form = ref({ title: '', content: '', memory_type: 'character', importance: 3 })

const resetForm = () => {
  editingMemory.value = null
  form.value = { title: '', content: '', memory_type: 'character', importance: 3 }
}

const handleSearch = () => {
  const params = {}
  if (searchKeyword.value) params.keyword = searchKeyword.value
  if (filterType.value) params.memory_type = filterType.value
  store.fetchMemories(store.currentProject.id, params)
}

const handleEdit = (item) => {
  editingMemory.value = item
  form.value = { title: item.title, content: item.content, memory_type: item.memory_type, importance: item.importance }
  showCreateModal.value = true
}

const handleSave = async () => {
  try {
    if (editingMemory.value) {
      await store.updateMemory(store.currentProject.id, editingMemory.value.id, form.value)
      message.success('已更新')
    } else {
      await store.createMemory(store.currentProject.id, { ...form.value, source_type: 'manual_note' })
      message.success('已创建')
    }
    showCreateModal.value = false
    resetForm()
  } catch {
    message.error('操作失败')
  }
}

const handleDelete = async (id) => {
  try {
    await store.deleteMemory(store.currentProject.id, id)
    message.success('已删除')
  } catch {
    message.error('删除失败')
  }
}

const handleReindex = async () => {
  reindexing.value = true
  try {
    await store.reindexMemories(store.currentProject.id)
    await store.fetchMemories(store.currentProject.id)
    message.success('索引已重建')
  } catch {
    message.error('重建失败')
  } finally {
    reindexing.value = false
  }
}

watch(filterType, () => handleSearch())

onMounted(() => {
  if (store.currentProject) {
    store.fetchMemories(store.currentProject.id)
  }
})
</script>

<style scoped>
.novel-memory-panel { padding: 8px; }
.memory-header { margin-bottom: 12px; }
.memory-filters { display: flex; gap: 4px; margin-top: 8px; }
.memory-content { font-size: 12px; color: var(--text-muted); }
</style>
