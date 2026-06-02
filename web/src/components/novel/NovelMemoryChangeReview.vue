<template>
  <div class="novel-memory-change-review">
    <a-empty v-if="!store.memoryChanges.length" description="暂无待确认的记忆变更" />
    <div v-else>
      <div v-for="change in store.memoryChanges" :key="change.id" class="change-card">
        <div class="change-header">
          <a-tag :color="change.change_type === 'add' ? 'green' : 'blue'" size="small">
            {{ change.change_type === 'add' ? '新增' : '修改' }}
          </a-tag>
          <span class="change-type">{{ change.after?.memory_type || '未知' }}</span>
        </div>
        <div class="change-body">
          <strong>{{ change.after?.title || '无标题' }}</strong>
          <p>{{ change.after?.content?.slice(0, 200) || '无内容' }}...</p>
        </div>
        <div class="change-actions">
          <a-button size="small" type="primary" @click="handleConfirm(change.id)">确认</a-button>
          <a-button size="small" danger @click="handleReject(change.id)">拒绝</a-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { useNovelsStore } from '../../stores/novels'

const store = useNovelsStore()

const handleConfirm = async (cid) => {
  try {
    await store.confirmMemoryChange(store.currentProject.id, cid)
    message.success('已确认')
  } catch {
    message.error('确认失败')
  }
}

const handleReject = async (cid) => {
  try {
    await store.rejectMemoryChange(store.currentProject.id, cid)
    message.success('已拒绝')
  } catch {
    message.error('拒绝失败')
  }
}

onMounted(() => {
  if (store.currentProject) {
    store.fetchMemoryChanges(store.currentProject.id)
  }
})
</script>

<style scoped>
.change-card { padding: 12px; border: 1px solid var(--surface-border); border-radius: 6px; margin-bottom: 8px; }
.change-header { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.change-type { font-size: 12px; color: var(--text-muted); }
.change-body p { font-size: 12px; color: var(--text-secondary); margin-top: 4px; }
.change-actions { display: flex; gap: 8px; margin-top: 8px; }
</style>
