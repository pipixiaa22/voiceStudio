<template>
  <div class="novel-relation-inspector" v-if="relation">
    <h4>关系属性</h4>
    <a-form layout="vertical" size="small">
      <a-form-item label="关系类型">
        <a-select v-model:value="relation.relation_type" @change="handleUpdate">
          <a-select-option value="师徒">师徒</a-select-option>
          <a-select-option value="同盟">同盟</a-select-option>
          <a-select-option value="敌对">敌对</a-select-option>
          <a-select-option value="亲属">亲属</a-select-option>
          <a-select-option value="恋人">恋人</a-select-option>
          <a-select-option value="背叛">背叛</a-select-option>
          <a-select-option value="其他">其他</a-select-option>
        </a-select>
      </a-form-item>
      <a-form-item label="标签">
        <a-input v-model:value="relation.label" @change="handleUpdate" />
      </a-form-item>
      <a-form-item label="描述">
        <a-textarea v-model:value="relation.description" :autoSize="{ minRows: 2, maxRows: 4 }" @change="handleUpdate" />
      </a-form-item>
      <a-form-item label="强度">
        <a-slider v-model:value="relation.strength" :min="1" :max="10" @change="handleUpdate" />
      </a-form-item>
      <a-form-item label="状态">
        <a-select v-model:value="relation.status" @change="handleUpdate">
          <a-select-option value="active">活跃</a-select-option>
          <a-select-option value="hidden">隐藏</a-select-option>
          <a-select-option value="ended">结束</a-select-option>
        </a-select>
      </a-form-item>
    </a-form>
    <a-button danger size="small" @click="handleDelete">删除</a-button>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useNovelsStore } from '../../stores/novels'
const store = useNovelsStore()
const relation = computed(() => store.selectedRelation)

let updateTimer = null
const handleUpdate = () => {
  clearTimeout(updateTimer)
  updateTimer = setTimeout(() => {
    if (relation.value) {
      store.updateRelation(store.currentProject.id, relation.value.id, relation.value)
    }
  }, 500)
}

const handleDelete = async () => {
  if (relation.value) {
    await store.deleteRelation(store.currentProject.id, relation.value.id)
    store.selectedRelationId = null
  }
}
</script>

<style scoped>
.novel-relation-inspector { padding: 12px; }
h4 { margin: 0 0 12px; }
</style>
