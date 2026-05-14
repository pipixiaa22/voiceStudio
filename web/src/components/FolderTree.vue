<template>
  <div class="folder-tree">
    <div class="folder-header">
      <h3>文件夹</h3>
      <button @click="showAddFolder = true" class="btn-add">+</button>
    </div>

    <div v-if="showAddFolder" class="add-folder">
      <input v-model="newFolderName" placeholder="文件夹名称" @keyup.enter="handleAdd" />
      <button @click="handleAdd">添加</button>
      <button @click="showAddFolder = false">取消</button>
    </div>

    <div class="folder-list">
      <div
        v-for="folder in folders"
        :key="folder.id"
        class="folder-item"
        :class="{ active: selectedFolderId === folder.id }"
        @click="$emit('select', folder.id)"
      >
        <span>{{ folder.name }}</span>
        <button @click.stop="handleDelete(folder.id)" class="btn-delete">×</button>
      </div>
      <div
        class="folder-item"
        :class="{ active: selectedFolderId === null }"
        @click="$emit('select', null)"
      >
        <span>全部文本</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useFoldersStore } from '../stores/folders'

const props = defineProps({
  selectedFolderId: { type: Number, default: null }
})

const emit = defineEmits(['select'])
const foldersStore = useFoldersStore()
const showAddFolder = ref(false)
const newFolderName = ref('')

onMounted(() => foldersStore.fetchFolders())

const folders = foldersStore.folders

const handleAdd = async () => {
  if (!newFolderName.value.trim()) return
  await foldersStore.createFolder({ name: newFolderName.value })
  newFolderName.value = ''
  showAddFolder.value = false
}

const handleDelete = async (id) => {
  if (confirm('确定删除此文件夹？')) {
    await foldersStore.deleteFolder(id)
    if (props.selectedFolderId === id) {
      emit('select', null)
    }
  }
}
</script>

<style scoped>
.folder-tree {
  width: 200px;
  border-right: 1px solid #eee;
  padding: 1rem;
}
.folder-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.btn-add {
  background: #42b883;
  color: white;
  border: none;
  width: 24px;
  height: 24px;
  border-radius: 4px;
  cursor: pointer;
}
.folder-item {
  padding: 0.5rem;
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.folder-item:hover {
  background: #f5f5f5;
}
.folder-item.active {
  background: #e8f5e9;
}
.btn-delete {
  background: none;
  border: none;
  color: #999;
  cursor: pointer;
  font-size: 1.2rem;
}
.add-folder {
  margin: 0.5rem 0;
  display: flex;
  gap: 0.5rem;
}
.add-folder input {
  flex: 1;
  padding: 0.25rem;
}
</style>
