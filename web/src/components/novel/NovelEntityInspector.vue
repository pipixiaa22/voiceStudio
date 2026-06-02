<template>
  <div class="novel-entity-inspector" v-if="entity">
    <h4>人物属性</h4>
    <a-form layout="vertical" size="small">
      <a-form-item label="名称">
        <a-input v-model:value="entity.name" @change="handleUpdate" />
      </a-form-item>
      <a-form-item label="类型">
        <a-select v-model:value="entity.entity_type" @change="handleUpdate">
          <a-select-option value="character">人物</a-select-option>
          <a-select-option value="faction">势力</a-select-option>
          <a-select-option value="location">地点</a-select-option>
          <a-select-option value="item">物品</a-select-option>
        </a-select>
      </a-form-item>
      <a-form-item label="简介">
        <a-textarea v-model:value="entity.summary" :autoSize="{ minRows: 2, maxRows: 4 }" @change="handleUpdate" />
      </a-form-item>
      <a-form-item label="重要度">
        <a-slider v-model:value="entity.importance" :min="1" :max="10" @change="handleUpdate" />
      </a-form-item>
    </a-form>
    <a-button danger size="small" @click="handleDelete">删除</a-button>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useNovelsStore } from '../../stores/novels'
const store = useNovelsStore()
const entity = computed(() => store.selectedEntity)

let updateTimer = null
const handleUpdate = () => {
  clearTimeout(updateTimer)
  updateTimer = setTimeout(() => {
    if (entity.value) {
      store.updateEntity(store.currentProject.id, entity.value.id, entity.value)
    }
  }, 500)
}

const handleDelete = async () => {
  if (entity.value) {
    await store.deleteEntity(store.currentProject.id, entity.value.id)
    store.selectedEntityId = null
  }
}
</script>

<style scoped>
.novel-entity-inspector { padding: 12px; }
h4 { margin: 0 0 12px; }
</style>
