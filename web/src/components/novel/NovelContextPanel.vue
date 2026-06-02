<template>
  <div class="novel-context-panel">
    <a-collapse size="small">
      <a-collapse-panel key="outline" header="本章大纲">
        <p>{{ outlineText }}</p>
      </a-collapse-panel>
      <a-collapse-panel key="characters" header="相关人物">
        <div v-for="e in store.entities.slice(0, 5)" :key="e.id">
          <strong>{{ e.name }}</strong>
          <p class="ctx-text">{{ e.summary }}</p>
        </div>
      </a-collapse-panel>
      <a-collapse-panel key="events" header="相关事件">
        <div v-for="e in store.events.slice(0, 5)" :key="e.id">
          <strong>{{ e.title }}</strong>
          <p class="ctx-text">{{ e.summary }}</p>
        </div>
      </a-collapse-panel>
    </a-collapse>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useNovelsStore } from '../../stores/novels'
const store = useNovelsStore()

const findOutlineNode = (nodes, id) => {
  for (const n of nodes) {
    if (n.id === id) return n
    if (n.children) {
      const found = findOutlineNode(n.children, id)
      if (found) return found
    }
  }
  return null
}

const outlineText = computed(() => {
  const nodeId = store.currentChapter?.outline_node_id
  if (!nodeId) return '暂无大纲信息'
  const node = findOutlineNode(store.outlineTree, nodeId)
  return node?.summary || '暂无大纲信息'
})
</script>

<style scoped>
.novel-context-panel { padding: 8px; }
.ctx-text { font-size: 12px; color: var(--text-muted); margin: 2px 0 8px; }
</style>
