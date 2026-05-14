<template>
  <div class="text-edit-page">
    <div class="edit-header">
      <input v-model="title" placeholder="输入标题..." class="title-input" />
      <div class="edit-actions">
        <button @click="handleSave" class="btn btn-primary" :disabled="saving">
          {{ saving ? '保存中...' : '保存' }}
        </button>
        <button v-if="textId" @click="handleExport" class="btn">导出 SRT</button>
      </div>
    </div>

    <div class="edit-meta">
      <div class="meta-item">
        <label>文件夹：</label>
        <select v-model="folderId">
          <option :value="null">无</option>
          <option v-for="folder in folders" :key="folder.id" :value="folder.id">
            {{ folder.name }}
          </option>
        </select>
      </div>
      <div class="meta-item">
        <label>标签：</label>
        <TagSelector v-model="selectedTags" />
      </div>
    </div>

    <textarea
      v-model="content"
      placeholder="输入文本内容..."
      class="content-input"
    ></textarea>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useTextsStore } from '../stores/texts'
import { useFoldersStore } from '../stores/folders'
import TagSelector from '../components/TagSelector.vue'

const router = useRouter()
const route = useRoute()
const textsStore = useTextsStore()
const foldersStore = useFoldersStore()

const textId = route.params.id ? parseInt(route.params.id) : null
const title = ref('未命名')
const content = ref('')
const folderId = ref(null)
const selectedTags = ref([])
const saving = ref(false)

const folders = foldersStore.folders

onMounted(async () => {
  foldersStore.fetchFolders()
  if (textId) {
    const text = await textsStore.fetchText(textId)
    title.value = text.title
    content.value = text.content
    folderId.value = text.folder_id
    selectedTags.value = text.tags || []
  }
})

const handleSave = async () => {
  saving.value = true
  try {
    const data = {
      title: title.value,
      content: content.value,
      folder_id: folderId.value,
      tag_ids: selectedTags.value.map(t => t.id),
    }
    if (textId) {
      await textsStore.updateText(textId, data)
    } else {
      const newText = await textsStore.createText(data)
      router.replace(`/edit/${newText.id}`)
    }
  } finally {
    saving.value = false
  }
}

const handleExport = async () => {
  await textsStore.exportSrt(textId, { speed: 5, max_chars: 20 })
}
</script>

<style scoped>
.text-edit-page {
  max-width: 1200px;
  margin: 0 auto;
}
.edit-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}
.title-input {
  font-size: 1.5rem;
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  flex: 1;
  margin-right: 1rem;
}
.edit-actions {
  display: flex;
  gap: 0.5rem;
}
.btn {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}
.btn-primary {
  background: #42b883;
  color: white;
}
.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.edit-meta {
  margin-bottom: 1rem;
  display: flex;
  gap: 2rem;
}
.meta-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.meta-item label {
  font-weight: bold;
  white-space: nowrap;
}
.meta-item select {
  padding: 0.25rem;
  border: 1px solid #ddd;
  border-radius: 4px;
}
.content-input {
  width: 100%;
  min-height: 400px;
  padding: 1rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-family: inherit;
  font-size: 1rem;
  line-height: 1.6;
  resize: vertical;
}
</style>
