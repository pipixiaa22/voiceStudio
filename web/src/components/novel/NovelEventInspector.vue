<template>
  <div class="novel-event-inspector" v-if="event">
    <h4>事件属性</h4>
    <a-form layout="vertical" size="small">
      <a-form-item label="标题">
        <a-input v-model:value="event.title" @change="handleUpdate" />
      </a-form-item>
      <a-form-item label="事件类型">
        <a-select v-model:value="event.event_type" @change="handleUpdate">
          <a-select-option value="event">事件</a-select-option>
          <a-select-option value="turning_point">转折点</a-select-option>
          <a-select-option value="climax">高潮</a-select-option>
          <a-select-option value="foreshadowing">伏笔</a-select-option>
          <a-select-option value="reveal">揭示</a-select-option>
        </a-select>
      </a-form-item>
      <a-form-item label="摘要">
        <a-textarea v-model:value="event.summary" :autoSize="{ minRows: 2, maxRows: 4 }" @change="handleUpdate" />
      </a-form-item>
      <a-form-item label="时间线顺序">
        <a-input-number v-model:value="event.timeline_order" :min="0" style="width: 100%" @change="handleUpdate" />
      </a-form-item>
    </a-form>
    <a-button danger size="small" @click="handleDelete">删除</a-button>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useNovelsStore } from '../../stores/novels'
const store = useNovelsStore()
const event = computed(() => store.selectedEvent)

let updateTimer = null
const handleUpdate = () => {
  clearTimeout(updateTimer)
  updateTimer = setTimeout(() => {
    if (event.value) {
      store.updateEvent(store.currentProject.id, event.value.id, event.value)
    }
  }, 500)
}

const handleDelete = async () => {
  if (event.value) {
    await store.deleteEvent(store.currentProject.id, event.value.id)
    store.selectedEventId = null
  }
}
</script>

<style scoped>
.novel-event-inspector { padding: 12px; }
h4 { margin: 0 0 12px; }
</style>
