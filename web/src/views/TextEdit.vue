<template>
  <div style="max-width: 1200px; margin: 0 auto">
    <a-card>
      <template #title>
        <a-input
          v-model:value="title"
          placeholder="输入标题..."
          size="large"
          style="font-size: 18px"
        />
      </template>
      <template #extra>
        <a-space>
          <a-button type="primary" :loading="saving" @click="handleSave">
            <template #icon><SaveOutlined /></template>
            保存
          </a-button>
          <a-button v-if="textId" @click="handleExport">
            <template #icon><DownloadOutlined /></template>
            导出 SRT
          </a-button>
          <a-button @click="router.push('/')">
            返回列表
          </a-button>
        </a-space>
      </template>

      <a-form layout="vertical">
        <a-row :gutter="24">
          <a-col :span="8">
            <a-form-item label="文件夹">
              <a-select v-model:value="folderId" placeholder="选择文件夹" allowClear>
                <a-select-option v-for="folder in folders" :key="folder.id" :value="folder.id">
                  {{ folder.name }}
                </a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
          <a-col :span="16">
            <a-form-item label="标签">
              <TagSelector v-model="selectedTags" />
            </a-form-item>
          </a-col>
        </a-row>

        <a-form-item label="文本内容">
          <a-textarea
            v-model:value="content"
            placeholder="输入文本内容..."
            :autoSize="{ minRows: 15, maxRows: 30 }"
          />
        </a-form-item>
      </a-form>
    </a-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { SaveOutlined, DownloadOutlined } from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
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

const folders = computed(() => foldersStore.folders)

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
      message.success('保存成功')
    } else {
      const newText = await textsStore.createText(data)
      message.success('创建成功')
      router.replace(`/edit/${newText.id}`)
    }
  } catch (e) {
    message.error('保存失败')
  } finally {
    saving.value = false
  }
}

const handleExport = async () => {
  await textsStore.exportSrt(textId, { speed: 5, max_chars: 20 })
  message.success('导出成功')
}
</script>
