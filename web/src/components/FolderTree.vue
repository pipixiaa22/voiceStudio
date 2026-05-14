<template>
  <div>
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px">
      <h3 style="margin: 0">文件夹</h3>
      <a-button type="primary" size="small" @click="showAddFolder = true">
        <template #icon><PlusOutlined /></template>
      </a-button>
    </div>

    <a-input-group v-if="showAddFolder" compact style="margin-bottom: 16px">
      <a-input
        v-model:value="newFolderName"
        placeholder="文件夹名称"
        @keyup.enter="handleAdd"
        style="width: calc(100% - 64px)"
      />
      <a-button type="primary" @click="handleAdd">添加</a-button>
      <a-button @click="showAddFolder = false">取消</a-button>
    </a-input-group>

    <a-menu
      mode="inline"
      :selectedKeys="selectedKeys"
      @click="handleMenuClick"
    >
      <a-menu-item key="all">
        <FolderOutlined />
        <span>全部文本</span>
      </a-menu-item>
      <a-menu-item v-for="folder in folders" :key="folder.id">
        <FolderOutlined />
        <span>{{ folder.name }}</span>
        <a-popconfirm
          title="确定删除此文件夹？"
          @confirm="handleDelete(folder.id)"
          @click.stop
        >
          <DeleteOutlined style="float: right; margin-top: 4px; color: #999" @click.stop />
        </a-popconfirm>
      </a-menu-item>
    </a-menu>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { PlusOutlined, FolderOutlined, DeleteOutlined } from '@ant-design/icons-vue'
import { useFoldersStore } from '../stores/folders'

const props = defineProps({
  selectedFolderId: { type: Number, default: null }
})

const emit = defineEmits(['select'])
const foldersStore = useFoldersStore()
const showAddFolder = ref(false)
const newFolderName = ref('')

onMounted(() => foldersStore.fetchFolders())

const folders = computed(() => foldersStore.folders)

const selectedKeys = computed(() => {
  return props.selectedFolderId ? [String(props.selectedFolderId)] : ['all']
})

const handleMenuClick = ({ key }) => {
  emit('select', key === 'all' ? null : parseInt(key))
}

const handleAdd = async () => {
  if (!newFolderName.value.trim()) return
  await foldersStore.createFolder({ name: newFolderName.value })
  newFolderName.value = ''
  showAddFolder.value = false
}

const handleDelete = async (id) => {
  await foldersStore.deleteFolder(id)
  if (props.selectedFolderId === id) {
    emit('select', null)
  }
}
</script>
