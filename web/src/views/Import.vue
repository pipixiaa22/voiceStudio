<template>
  <div style="max-width: 800px; margin: 0 auto">
    <a-card title="导入文本">
      <a-upload-dragger
        name="file"
        :beforeUpload="handleBeforeUpload"
        :showUploadList="false"
        accept=".txt"
      >
        <p class="ant-upload-drag-icon">
          <InboxOutlined />
        </p>
        <p class="ant-upload-text">拖拽 .txt 文件到此处，或点击选择文件</p>
      </a-upload-dragger>

      <div v-if="file" style="margin-top: 16px">
        <a-alert :message="`已选择：${file.name}`" type="info" showIcon />
      </div>

      <div v-if="previewContent" style="margin-top: 24px">
        <a-form layout="vertical">
          <a-form-item label="标题">
            <a-input v-model:value="title" />
          </a-form-item>

          <a-form-item label="文件夹">
            <a-select v-model:value="folderId" placeholder="选择文件夹" allowClear>
              <a-select-option v-for="folder in folders" :key="folder.id" :value="folder.id">
                {{ folder.name }}
              </a-select-option>
            </a-select>
          </a-form-item>

          <a-form-item label="预览内容">
            <a-textarea
              v-model:value="previewContent"
              :autoSize="{ minRows: 10, maxRows: 20 }"
            />
          </a-form-item>

          <a-form-item>
            <a-button
              type="primary"
              :loading="importing"
              @click="handleImport"
              size="large"
            >
              <template #icon><ImportOutlined /></template>
              确认导入
            </a-button>
          </a-form-item>
        </a-form>
      </div>
    </a-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { InboxOutlined, ImportOutlined } from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
import { useTextsStore } from '../stores/texts'
import { useFoldersStore } from '../stores/folders'

const router = useRouter()
const textsStore = useTextsStore()
const foldersStore = useFoldersStore()

const file = ref(null)
const previewContent = ref('')
const title = ref('')
const folderId = ref(null)
const importing = ref(false)

const folders = computed(() => foldersStore.folders)

onMounted(() => foldersStore.fetchFolders())

const handleBeforeUpload = (f) => {
  if (!f.name.endsWith('.txt')) {
    message.error('只支持 .txt 文件')
    return false
  }
  readFile(f)
  return false
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
    message.success('导入成功')
    router.push('/')
  } catch (e) {
    message.error('导入失败')
  } finally {
    importing.value = false
  }
}
</script>
