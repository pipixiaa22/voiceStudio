<template>
  <div class="folder-tree">
    <div class="tree-header">
      <h3 class="tree-title">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="tree-icon">
          <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
        </svg>
        <span>文件夹</span>
      </h3>
      <a-dropdown :trigger="['click']">
        <a-button type="text" size="small" class="add-btn">
          <template #icon>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="12" y1="5" x2="12" y2="19"/>
              <line x1="5" y1="12" x2="19" y2="12"/>
            </svg>
          </template>
        </a-button>
        <template #overlay>
          <a-menu @click="handleRootMenuClick">
            <a-menu-item key="add-root">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width: 14px; height: 14px; margin-right: 8px; vertical-align: -2px">
                <line x1="12" y1="5" x2="12" y2="19"/>
                <line x1="5" y1="12" x2="19" y2="12"/>
              </svg>
              创建文件夹
            </a-menu-item>
          </a-menu>
        </template>
      </a-dropdown>
    </div>

    <!-- Add Folder Input -->
    <div v-if="showAddFolder" class="add-folder-form">
      <a-input-group compact>
        <a-input
          v-model:value="newFolderName"
          placeholder="文件夹名称"
          @keyup.enter="handleAdd"
          class="folder-input"
          autofocus
        />
        <a-button type="primary" @click="handleAdd" class="submit-btn">确定</a-button>
        <a-button @click="cancelAdd" class="cancel-btn">取消</a-button>
      </a-input-group>
    </div>

    <!-- Folder List -->
    <div class="folder-list">
      <!-- All Texts -->
      <div
        class="folder-item"
        :class="{ active: selectedFolderId === null, 'drag-over': dragOverFolderId === 'all' }"
        @click="$emit('select', null)"
        @dragover.prevent="handleDragOver('all')"
        @dragleave="handleDragLeave"
        @drop.prevent="handleDrop(null, $event)"
      >
        <div class="folder-item-content">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="folder-icon">
            <rect x="3" y="3" width="7" height="7"/>
            <rect x="14" y="3" width="7" height="7"/>
            <rect x="14" y="14" width="7" height="7"/>
            <rect x="3" y="14" width="7" height="7"/>
          </svg>
          <span class="folder-name">全部文本</span>
        </div>
        <span class="folder-count">{{ totalCount }}</span>
      </div>

      <!-- Folder Items -->
      <div
        v-for="folder in folders"
        :key="folder.id"
        class="folder-item"
        :class="{
          active: selectedFolderId === folder.id,
          'drag-over': dragOverFolderId === folder.id,
          'dragging': draggingFolderId === folder.id
        }"
        @click="$emit('select', folder.id)"
        @dragover.prevent="handleDragOver(folder.id)"
        @dragleave="handleDragLeave"
        @drop.prevent="handleDrop(folder.id, $event)"
        draggable="true"
        @dragstart="handleDragStart(folder.id, $event)"
        @dragend="handleDragEnd"
      >
        <div class="folder-item-content">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="folder-icon">
            <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
          </svg>
          <span class="folder-name">{{ folder.name }}</span>
        </div>
        <FolderActions @action="(key) => handleFolderAction(key, folder)" />
      </div>
    </div>

    <!-- Rename Modal -->
    <a-modal
      v-model:open="showRenameModal"
      title="重命名文件夹"
      @ok="handleRename"
      @cancel="showRenameModal = false"
      okText="确定"
      cancelText="取消"
    >
      <a-input
        v-model:value="renameFolderName"
        placeholder="输入新名称"
        @keyup.enter="handleRename"
        autofocus
      />
    </a-modal>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { Modal, message } from 'ant-design-vue'
import { useFoldersStore } from '../stores/folders'
import { useTextsStore } from '../stores/texts'
import FolderActions from './FolderActions.vue'

const props = defineProps({
  selectedFolderId: { type: Number, default: null }
})

const emit = defineEmits(['select', 'moveText'])
const foldersStore = useFoldersStore()
const textsStore = useTextsStore()

const showAddFolder = ref(false)
const newFolderName = ref('')
const addingParentId = ref(null)

// Drag and drop state
const dragOverFolderId = ref(null)
const draggingFolderId = ref(null)
const dragCounter = ref(0)

// Rename state
const showRenameModal = ref(false)
const renameFolderId = ref(null)
const renameFolderName = ref('')

onMounted(() => foldersStore.fetchFolders())

const folders = computed(() => foldersStore.folders)
const totalCount = computed(() => textsStore.texts.length)

// Menu handlers
const handleRootMenuClick = ({ key }) => {
  if (key === 'add-root') {
    addingParentId.value = null
    showAddFolder.value = true
  }
}

const handleFolderAction = (key, folder) => {
  switch (key) {
    case 'add-child':
      addingParentId.value = folder.id
      showAddFolder.value = true
      break
    case 'rename':
      renameFolderId.value = folder.id
      renameFolderName.value = folder.name
      showRenameModal.value = true
      break
    case 'delete':
      Modal.confirm({
        title: '确定删除此文件夹？',
        content: '文件夹内的文本不会被删除，但会移到"全部文本"。',
        okText: '删除',
        cancelText: '取消',
        okButtonProps: { danger: true },
        onOk: () => handleDelete(folder.id)
      })
      break
  }
}

// Add folder
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
  message.success('文件夹已创建')
}

// Delete folder
const handleDelete = async (id) => {
  await foldersStore.deleteFolder(id)
  if (props.selectedFolderId === id) {
    emit('select', null)
  }
  message.success('文件夹已删除')
}

// Rename folder
const handleRename = async () => {
  if (!renameFolderName.value.trim()) return
  // Note: You'll need to add this API endpoint
  try {
    await foldersStore.updateFolder(renameFolderId.value, { name: renameFolderName.value })
    showRenameModal.value = false
    message.success('文件夹已重命名')
  } catch (e) {
    message.error('重命名失败')
  }
}

// Drag and drop handlers
const handleDragStart = (folderId, event) => {
  draggingFolderId.value = folderId
  event.dataTransfer.setData('folderId', folderId)
  event.dataTransfer.effectAllowed = 'move'
}

const handleDragEnd = () => {
  draggingFolderId.value = null
  dragOverFolderId.value = null
  dragCounter.value = 0
}

const handleDragOver = (folderId) => {
  dragOverFolderId.value = folderId
  dragCounter.value++
}

const handleDragLeave = () => {
  dragCounter.value--
  if (dragCounter.value === 0) {
    dragOverFolderId.value = null
  }
}

const handleDrop = async (folderId, event) => {
  dragOverFolderId.value = null
  dragCounter.value = 0

  const textId = event.dataTransfer.getData('textId')
  if (textId) {
    // Move text to folder
    await textsStore.updateText(parseInt(textId), { folder_id: folderId })
    message.success(folderId ? '已移入文件夹' : '已移出文件夹')
    emit('moveText')
  }
}
</script>

<style scoped>
.folder-tree {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.tree-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-md);
  padding-bottom: var(--space-md);
  border-bottom: 1px solid var(--surface-border);
}

.tree-title {
  font-size: 14px;
  font-weight: 560;
  color: var(--text-secondary);
  margin: 0;
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  text-transform: none;
  letter-spacing: 0;
}

.tree-icon {
  width: 18px;
  height: 18px;
  color: var(--text-secondary);
}

.add-btn {
  color: var(--text-muted) !important;
  width: 28px;
  height: 28px;
  padding: 0 !important;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-sm) !important;
  transition: all var(--transition-fast) !important;
}

.add-btn:hover {
  color: var(--text-primary) !important;
  background: var(--surface-hover) !important;
}

.add-btn svg {
  width: 16px;
  height: 16px;
}

/* Add Folder Form */
.add-folder-form {
  margin-bottom: var(--space-md);
  animation: slideDown 0.2s ease;
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.folder-input {
  width: calc(100% - 120px) !important;
}

.submit-btn {
  width: 60px !important;
}

.cancel-btn {
  width: 60px !important;
}

/* Folder List */
.folder-list {
  flex: 1;
  overflow-y: auto;
}

.folder-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  margin-bottom: 4px;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--transition-fast);
  position: relative;
  border: 1px solid transparent;
}

.folder-item:hover {
  background: var(--surface-hover);
}

.folder-item.active {
  background: var(--surface-active);
  border-left: 3px solid var(--text-primary);
  padding-left: 9px;
}

.folder-item.active .folder-name {
  color: var(--text-primary);
  font-weight: 560;
}

/* Drag and Drop States */
.folder-item.drag-over {
  background: var(--surface-active) !important;
  border-color: var(--text-primary) !important;
  box-shadow: var(--shadow-focus);
}

.folder-item.dragging {
  opacity: 0.5;
}

.folder-item-content {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  min-width: 0;
}

.folder-icon {
  width: 16px;
  height: 16px;
  color: var(--text-muted);
  flex-shrink: 0;
}

.folder-item.active .folder-icon {
  color: var(--text-primary);
}

.folder-name {
  font-size: 13px;
  color: var(--text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  transition: color var(--transition-fast);
}

.folder-count {
  font-size: 11px;
  color: var(--text-muted);
  background: var(--surface-muted);
  padding: 2px 6px;
  border-radius: 10px;
  min-width: 20px;
  text-align: center;
}

.folder-item :deep(.more-btn) {
  opacity: 0;
  transition: all var(--transition-fast);
}

.folder-item:hover :deep(.more-btn) {
  opacity: 1;
}
</style>
