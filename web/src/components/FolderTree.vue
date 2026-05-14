<template>
  <div>
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px">
      <h3 style="margin: 0">文件夹</h3>
      <a-button type="primary" size="small" @click="handleAddRoot">
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
      <a-button @click="cancelAdd">取消</a-button>
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
        <div style="display: flex; justify-content: space-between; align-items: center; width: 100%">
          <span>
            <FolderOutlined />
            <span style="margin-left: 8px">{{ folder.name }}</span>
          </span>
          <a-dropdown :trigger="['click']" @click.stop>
            <EllipsisOutlined style="font-size: 16px; padding: 4px" @click.stop />
            <template #overlay>
              <a-menu @click="({ key }) => handleFolderAction(key, folder)">
                <a-menu-item key="add-child">
                  <PlusOutlined />
                  <span>新增子文件夹</span>
                </a-menu-item>
                <a-menu-item key="delete" danger>
                  <DeleteOutlined />
                  <span>删除</span>
                </a-menu-item>
              </a-menu>
            </template>
          </a-dropdown>
        </div>
      </a-menu-item>
    </a-menu>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { PlusOutlined, FolderOutlined, DeleteOutlined, EllipsisOutlined } from '@ant-design/icons-vue'
import { Modal } from 'ant-design-vue'
import { useFoldersStore } from '../stores/folders'

const props = defineProps({
  selectedFolderId: { type: Number, default: null }
})

const emit = defineEmits(['select'])
const foldersStore = useFoldersStore()
const showAddFolder = ref(false)
const newFolderName = ref('')
const addingParentId = ref(null)

onMounted(() => foldersStore.fetchFolders())

const folders = computed(() => foldersStore.folders)

const selectedKeys = computed(() => {
  return props.selectedFolderId ? [String(props.selectedFolderId)] : ['all']
})

const handleMenuClick = ({ key }) => {
  emit('select', key === 'all' ? null : parseInt(key))
}

const handleAddRoot = () => {
  addingParentId.value = null
  showAddFolder.value = true
}

const handleAddChild = (folder) => {
  addingParentId.value = folder.id
  showAddFolder.value = true
}

const cancelAdd = () => {
  showAddFolder.value = false
  newFolderName.value = ''
  addingParentId.value = null
}

const handleAdd = async () => {
  if (!newFolderName.value.trim()) return
  await foldersStore.createFolder({
    name: newFolderName.value,
    parent_id: addingParentId.value
  })
  newFolderName.value = ''
  showAddFolder.value = false
  addingParentId.value = null
}

const handleDelete = async (id) => {
  await foldersStore.deleteFolder(id)
  if (props.selectedFolderId === id) {
    emit('select', null)
  }
}

const handleFolderAction = (key, folder) => {
  if (key === 'add-child') {
    handleAddChild(folder)
  } else if (key === 'delete') {
    Modal.confirm({
      title: '确定删除此文件夹？',
      content: '删除后不可恢复',
      okText: '确定',
      cancelText: '取消',
      onOk: () => handleDelete(folder.id)
    })
  }
}
</script>
