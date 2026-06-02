<template>
  <div class="novel-event-graph">
    <div class="graph-toolbar">
      <a-button size="small" @click="handleAddEvent">新增事件</a-button>
      <a-button size="small" @click="handleSaveLayout">保存布局</a-button>
    </div>
    <VueFlow
      :nodes="flowNodes"
      :edges="flowEdges"
      fit-view-on-init
      @nodes-change="handleNodesChange"
      @node-click="handleNodeClick"
      @edge-click="handleEdgeClick"
    >
      <template #node-event="nodeProps">
        <div class="event-node" :class="[nodeProps.data.event_type, { selected: nodeProps.id == store.selectedEventId }]">
          <strong>{{ nodeProps.data.title }}</strong>
          <span>{{ nodeProps.data.event_type }}</span>
        </div>
      </template>
      <Background />
      <Controls />
    </VueFlow>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { VueFlow } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import '@vue-flow/controls/dist/style.css'
import { useNovelsStore } from '../../stores/novels'

const store = useNovelsStore()

onMounted(() => {
  if (store.currentProject) {
    store.loadEventGraph(store.currentProject.id)
  }
})

const flowNodes = computed(() =>
  store.events.map(e => ({
    id: String(e.id),
    type: 'event',
    position: { x: e.node_x || 0, y: e.node_y || 0 },
    data: { title: e.title, event_type: e.event_type, summary: e.summary },
  }))
)

const edgeColors = {
  causes: '#52c41a', drives: '#1890ff', blocks: '#ff4d4f',
  reverses: '#fa8c16', reveals: '#722ed1', escalates: '#eb2f96',
}
const flowEdges = computed(() =>
  store.eventRelations.map(r => ({
    id: String(r.id),
    source: String(r.source_event_id),
    target: String(r.target_event_id),
    label: r.label || r.relation_type,
    style: { stroke: edgeColors[r.relation_type] || '#999' },
  }))
)

const handleNodesChange = (changes) => {
  for (const c of changes) {
    if (c.type === 'position' && c.position) {
      const ev = store.events.find(e => String(e.id) === c.id)
      if (ev) { ev.node_x = c.position.x; ev.node_y = c.position.y }
    }
  }
}

const handleNodeClick = ({ node }) => {
  store.selectedEventId = Number(node.id)
  store.selectedEntityId = null
  store.selectedRelationId = null
}

const handleEdgeClick = ({ edge }) => {
  // Could show edge inspector
}

const handleAddEvent = async () => {
  await store.createEvent(store.currentProject.id, { title: '新事件', event_type: 'event' })
}

const handleSaveLayout = async () => {
  const positions = store.events.map(e => ({ id: e.id, x: e.node_x || 0, y: e.node_y || 0 }))
  await store.saveGraphLayout(store.currentProject.id, [], positions)
}
</script>

<style scoped>
.novel-event-graph { height: 100%; display: flex; flex-direction: column; }
.graph-toolbar { display: flex; gap: 4px; padding: 8px; border-bottom: 1px solid var(--surface-border); }
.event-node {
  background: white; border: 2px solid #1890ff; border-radius: 8px;
  padding: 8px 12px; min-width: 140px; text-align: center;
}
.event-node.selected { border-color: #ff4d4f; }
.event-node strong { display: block; font-size: 13px; }
.event-node span { font-size: 11px; color: #999; }
</style>
