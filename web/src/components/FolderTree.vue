<template>
  <div class="folder-tree">
    <div class="tree-header">
      <h3 class="tree-title">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="tree-icon">
          <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
        </svg>
        <span>文件夹</span>
      </h3>
      <a-button type="text" size="small" @click="handleAddRoot" class="add-btn">
        <template #icon>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="12" y1="5" x2="12" y2="19"/>
            <line x1="5" y1="12" x2="19" y2="12"/>
          </svg>
        </template>
      </a-button>
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
      <div
        class="folder-item"
        :class="{ active: selectedFolderId === null }"
        @click="$emit('select', null)"
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

      <div
        v-for="folder in folders"
        :key="folder.id"
        class="folder-item"
        :class="{ active: selectedFolderId === folder.id }"
        @click="$emit('select', folder.id)"
      >
        <div class="folder-item-content">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="folder-icon">
            <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
          </svg>
          <span class="folder-name">{{ folder.name }}</span>
        </div>
        <a-dropdown :trigger="['click']" placement="bottomRight">
          <a-button type="text" size="small" class="more-btn" @click.stop>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="1"/>
              <circle cx="19" cy="12" r="1"/>
              <circle cx="5" cy="12" r="1"/>
            </svg>
          </a-button>
          <template #overlay>
            <a-menu @click="({ key }) => handleFolderAction(key, folder)">
              <a-menu-item key="add-child">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right: 8px">
                  <line x1="12" y1="5" x2="12" y2="19"/>
                  <line x1="5" y1="12" x2="19" y2="12"/>
                </svg>
                新增子文件夹
              </a-menu-item>
              <a-menu-item key="delete" danger>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right: 8px">
                  <polyline points="3 6 5 6 21 6"/>
                  <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                </svg>
                删除文件夹
              </a-menu-item>
            </a-menu>
          </template>
        </a-dropdown>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { Modal, message } from 'ant-design-vue'
import { useFoldersStore } from '../stores/folders'
import { useTextsStore } from '../stores/texts'

const props = defineProps({
  selectedFolderId: { type: Number, default: null }
})

const emit = defineEmits(['select'])
const foldersStore = useFoldersStore()
const textsStore = useTextsStore()
const showAddFolder = ref(false)
const newFolderName = ref('')
const addingParentId = ref(null)

onMounted(() => foldersStore.fetchFolders())

const folders = computed(() => foldersStore.folders)

const totalCount = computed(() => textsStore.texts.length)

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
  message.success('文件夹已创建')
}

const handleDelete = async (id) => {
  await foldersStore.deleteFolder(id)
  if (props.selectedFolderId === id) {
    emit('select', null)
  }
  message.success('文件夹已删除')
}

const handleFolderAction = (key, folder) => {
  if (key === 'add-child') {
    handleAddChild(folder)
  } else if (key === 'delete') {
    Modal.confirm({
      title: '确定删除此文件夹？',
      content: '文件夹内的文本不会被删除，但删除后不可恢复。',
      okText: '删除',
      cancelText: '取消',
      okButtonProps: { danger: true },
      onOk: () => handleDelete(folder.id)
    })
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
  font-weight: 600;
  color: var(--text-secondary);
  margin: 0;
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  text-transform: uppercase;
  letter-spacing: 2px;
}

.tree-icon {
  width: 18px;
  height: 18px;
  color: var(--gold);
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
  color: var(--gold) !important;
  background: var(--gold-glow) !important;
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
}

.folder-item:hover {
  background: var(--surface-hover);
}

.folder-item.active {
  background: var(--gold-glow);
  border-left: 3px solid var(--gold);
  padding-left: 9px;
}

.folder-item.active .folder-name {
  color: var(--gold);
  font-weight: 500;
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
  color: var(--gold);
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
  background: var(--ink-subtle);
  padding: 2px 6px;
  border-radius: 10px;
  min-width: 20px;
  text-align: center;
}

.more-btn {
  color: var(--text-muted) !important;
  width: 24px;
  height: 24px;
  padding: 0 !important;
  opacity: 0;
  transition: all var(--transition-fast) !important;
}

.folder-item:hover .more-btn {
  opacity: 1;
}

.more-btn:hover {
  color: var(--gold) !important;
}

.more-btn svg {
  width: 14px;
  height: 14px;
}
</style>
