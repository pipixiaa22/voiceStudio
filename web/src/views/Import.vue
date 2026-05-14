<template>
  <div class="import-page">
    <h1>导入文本</h1>

    <div
      class="drop-zone"
      @dragover.prevent
      @drop.prevent="handleDrop"
      @click="triggerFileInput"
    >
      <input
        ref="fileInput"
        type="file"
        accept=".txt"
        @change="handleFileSelect"
        style="display: none"
      />
      <p v-if="!file">拖拽 .txt 文件到此处，或点击选择文件</p>
      <p v-else>已选择：{{ file.name }}</p>
    </div>

    <div v-if="previewContent" class="preview">
      <h3>预览内容</h3>
      <textarea v-model="previewContent" class="preview-content"></textarea>
    </div>

    <div v-if="previewContent" class="import-options">
      <div class="option">
        <label>标题：</label>
        <input v-model="title" />
      </div>
      <div class="option">
        <label>文件夹：</label>
        <select v-model="folderId">
          <option :value="null">无</option>
          <option v-for="folder in folders" :key="folder.id" :value="folder.id">
            {{ folder.name }}
          </option>
        </select>
      </div>
      <button @click="handleImport" class="btn btn-primary" :disabled="importing">
        {{ importing ? '导入中...' : '确认导入' }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useTextsStore } from '../stores/texts'
import { useFoldersStore } from '../stores/folders'

const router = useRouter()
const textsStore = useTextsStore()
const foldersStore = useFoldersStore()

const fileInput = ref(null)
const file = ref(null)
const previewContent = ref('')
const title = ref('')
const folderId = ref(null)
const importing = ref(false)

const folders = foldersStore.folders

onMounted(() => foldersStore.fetchFolders())

const triggerFileInput = () => {
  fileInput.value.click()
}

const handleFileSelect = (e) => {
  const selected = e.target.files[0]
  if (selected) readFile(selected)
}

const handleDrop = (e) => {
  const dropped = e.dataTransfer.files[0]
  if (dropped && dropped.name.endsWith('.txt')) {
    readFile(dropped)
  }
}

const readFile = (f) => {
  file.value = f
  title.value = f.name.replace('.txt', '')
  const reader = new FileReader()
  reader.onload = (e) => {
    previewContent.value = e.target.result
  }
  reader.readAsText(f)
}

const handleImport = async () => {
  importing.value = true
  try {
    const formData = new FormData()
    formData.append('file', file.value)
    const text = await textsStore.importText(formData)
    if (folderId.value) {
      await textsStore.updateText(text.id, { folder_id: folderId.value })
    }
    router.push('/')
  } finally {
    importing.value = false
  }
}
</script>

<style scoped>
.import-page {
  max-width: 800px;
  margin: 0 auto;
}
.drop-zone {
  border: 2px dashed #ddd;
  border-radius: 8px;
  padding: 3rem;
  text-align: center;
  cursor: pointer;
  margin: 1rem 0;
}
.drop-zone:hover {
  border-color: #42b883;
}
.preview {
  margin: 1rem 0;
}
.preview-content {
  width: 100%;
  min-height: 200px;
  padding: 1rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-family: inherit;
  resize: vertical;
}
.import-options {
  display: flex;
  gap: 1rem;
  align-items: center;
  margin-top: 1rem;
}
.option {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.option input,
.option select {
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
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
</style>
