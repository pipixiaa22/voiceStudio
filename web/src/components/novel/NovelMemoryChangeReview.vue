<template>
  <div class="novel-memory-change-review">
    <a-spin :spinning="loading">
      <a-empty v-if="!loading && !store.memoryChanges.length" description="暂无待确认的记忆变更" />
      <div v-else>
        <div v-for="change in store.memoryChanges" :key="change.id" class="change-card">
          <div class="change-header">
            <a-tag :color="change.change_type === 'add' ? 'green' : 'blue'" size="small">
              {{ change.change_type === 'add' ? '新增' : '修改' }}
            </a-tag>
            <span class="change-type">{{ change.after?.memory_type || '未知' }}</span>
          </div>

          <!-- Add: show content directly -->
          <div v-if="change.change_type === 'add'" class="change-body">
            <strong>{{ change.after?.title || '无标题' }}</strong>
            <p>{{ change.after?.content?.slice(0, 200) || '无内容' }}...</p>
          </div>

          <!-- Modify: show before/after diff -->
          <div v-else-if="change.change_type === 'modify'" class="change-diff">
            <div class="diff-before" v-if="change.before">
              <strong>修改前:</strong>
              <p>{{ change.before.content?.slice(0, 200) || '无内容' }}...</p>
            </div>
            <div class="diff-after">
              <strong>修改后:</strong>
              <p>{{ change.after?.content?.slice(0, 200) || '无内容' }}...</p>
            </div>
          </div>

          <div class="change-actions">
            <a-button size="small" type="primary" @click="handleConfirm(change.id)">确认</a-button>
            <a-button size="small" danger @click="handleReject(change.id)">拒绝</a-button>
          </div>
        </div>
      </div>
    </a-spin>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { useNovelsStore } from '../../stores/novels'

const store = useNovelsStore()
const loading = ref(false)

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

onMounted(async () => {
  if (store.currentProject) {
    loading.value = true
    try {
      await store.fetchMemoryChanges(store.currentProject.id)
    } finally {
      loading.value = false
    }
  }
})
</script>

<style scoped>
.change-card { padding: 12px; border: 1px solid var(--surface-border); border-radius: 6px; margin-bottom: 8px; }
.change-header { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.change-type { font-size: 12px; color: var(--text-muted); }
.change-body p { font-size: 12px; color: var(--text-secondary); margin-top: 4px; }
.change-actions { display: flex; gap: 8px; margin-top: 8px; }
.change-diff { display: flex; flex-direction: column; gap: 8px; }
.diff-before { background: #fff2f0; padding: 8px; border-radius: 4px; border-left: 3px solid #ff4d4f; }
.diff-after { background: #f6ffed; padding: 8px; border-radius: 4px; border-left: 3px solid #52c41a; }
.diff-before strong, .diff-after strong { font-size: 12px; display: block; margin-bottom: 4px; }
.diff-before p, .diff-after p { font-size: 12px; color: var(--text-secondary); margin: 0; }
</style>
