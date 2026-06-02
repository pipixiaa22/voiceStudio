<template>
  <a-modal
    v-model:open="visible"
    title="AI 图谱提取结果"
    :footer="null"
    width="700px"
  >
    <div v-if="!changes.length" class="empty">
      <a-empty description="未发现新的图谱变更" />
    </div>
    <template v-else>
      <a-tabs size="small">
        <a-tab-pane v-for="cat in categories" :key="cat.key" :tab="cat.label">
          <a-list :data-source="changesByCategory(cat.key)" size="small">
            <template #renderItem="{ item }">
              <a-list-item>
                <a-list-item-meta :title="changeTitle(item)" :description="changeDescription(item)" />
                <template #actions>
                  <a-button size="small" type="primary" @click="handleAccept(item)">接受</a-button>
                  <a-button size="small" danger @click="handleReject(item)">拒绝</a-button>
                </template>
              </a-list-item>
            </template>
          </a-list>
        </a-tab-pane>
      </a-tabs>
      <div class="modal-footer">
        <a-button @click="handleAcceptAll">全部接受</a-button>
        <a-button danger @click="handleRejectAll">全部拒绝</a-button>
      </div>
    </template>
  </a-modal>
</template>

<script setup>
import { computed } from 'vue'
import { message } from 'ant-design-vue'
import { useNovelsStore } from '../../stores/novels'
const store = useNovelsStore()

const visible = computed({
  get: () => store.graphChanges.length > 0,
  set: () => {},
})

const changes = computed(() => store.graphChanges)

const categories = [
  { key: 'entity', label: '人物' },
  { key: 'relation', label: '关系' },
  { key: 'event', label: '事件' },
  { key: 'event_relation', label: '因果' },
]

const changesByCategory = (cat) => changes.value.filter(c => c.target_type === cat)

const changeTitle = (c) => {
  if (c.after?.name) return c.after.name
  if (c.after?.title) return c.after.title
  if (c.after?.relation_type) return c.after.relation_type
  return '变更'
}

const changeDescription = (c) => {
  if (c.after?.summary) return c.after.summary
  if (c.after?.description) return c.after.description
  return JSON.stringify(c.after || {}).slice(0, 100)
}

const handleAccept = async (c) => {
  try {
    await store.acceptGraphChange(store.currentProject.id, c.id)
    message.success('已接受')
  } catch (e) {
    message.error('接受失败: ' + (e.response?.data?.error || e.message))
  }
}

const handleReject = async (c) => {
  await store.rejectGraphChange(store.currentProject.id, c.id)
}

const handleAcceptAll = async () => {
  for (const c of [...store.graphChanges]) {
    try { await store.acceptGraphChange(store.currentProject.id, c.id) } catch {}
  }
  message.success('全部处理完成')
}

const handleRejectAll = async () => {
  for (const c of [...store.graphChanges]) {
    await store.rejectGraphChange(store.currentProject.id, c.id)
  }
}
</script>

<style scoped>
.empty { padding: 24px; }
.modal-footer { display: flex; gap: 8px; margin-top: 16px; justify-content: flex-end; }
</style>
