<template>
  <div class="novel-character-graph">
    <div class="graph-toolbar">
      <a-button size="small" @click="handleAddCharacter">新增人物</a-button>
      <a-button size="small" @click="handleAddRelation">新增关系</a-button>
      <a-button size="small" @click="handleSaveLayout">保存布局</a-button>
      <a-button size="small" @click="handleAutoLayout">自动布局</a-button>
    </div>
    <VueFlow
      :nodes="flowNodes"
      :edges="flowEdges"
      fit-view-on-init
      @nodes-change="handleNodesChange"
      @node-click="handleNodeClick"
      @edge-click="handleEdgeClick"
    >
      <template #node-character="nodeProps">
        <div class="char-node" :class="{ selected: nodeProps.id == store.selectedEntityId }">
          <strong>{{ nodeProps.data.name }}</strong>
          <span>{{ nodeProps.data.summary?.slice(0, 20) }}</span>
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
    store.loadCharacterGraph(store.currentProject.id)
  }
})

const flowNodes = computed(() =>
  store.entities.map(e => ({
    id: String(e.id),
    type: 'character',
    position: { x: e.x ?? e.node_x ?? 0, y: e.y ?? e.node_y ?? 0 },
    data: { name: e.name, summary: e.summary, importance: e.importance },
  }))
)

const edgeColors = {
  师徒: '#1890ff', 同盟: '#52c41a', 敌对: '#ff4d4f',
  亲属: '#722ed1', 恋人: '#eb2f96', 背叛: '#fa8c16',
}
const flowEdges = computed(() =>
  store.relations.map(r => ({
    id: String(r.id),
    source: String(r.source_entity_id),
    target: String(r.target_entity_id),
    label: r.label || r.relation_type,
    style: { stroke: edgeColors[r.relation_type] || '#999' },
    animated: r.status === 'hidden',
  }))
)

const handleNodesChange = (changes) => {
  for (const c of changes) {
    if (c.type === 'position' && c.position) {
      const entity = store.entities.find(e => String(e.id) === c.id)
      if (entity) {
        entity.node_x = c.position.x
        entity.node_y = c.position.y
      }
    }
  }
}

const handleNodeClick = ({ node }) => {
  store.selectedEntityId = Number(node.id)
  store.selectedRelationId = null
  store.selectedEventId = null
}

const handleEdgeClick = ({ edge }) => {
  store.selectedRelationId = Number(edge.id)
  store.selectedEntityId = null
}

const handleAddCharacter = async () => {
  await store.createEntity(store.currentProject.id, { name: '新角色', entity_type: 'character' })
}

const handleAddRelation = async () => {
  // Simple: prompt for source/target
  if (store.entities.length < 2) return
  await store.createRelation(store.currentProject.id, {
    source_entity_id: store.entities[0].id,
    target_entity_id: store.entities[1].id,
    relation_type: '其他',
  })
}

const handleSaveLayout = async () => {
  const positions = store.entities.map(e => ({ id: e.id, x: e.node_x || 0, y: e.node_y || 0 }))
  await store.saveGraphLayout(store.currentProject.id, positions, [])
}

const handleAutoLayout = () => {
  // Simple grid layout
  const cols = Math.ceil(Math.sqrt(store.entities.length))
  store.entities.forEach((e, i) => {
    e.node_x = (i % cols) * 250
    e.node_y = Math.floor(i / cols) * 150
  })
}
</script>

<style scoped>
.novel-character-graph { height: 100%; display: flex; flex-direction: column; }
.graph-toolbar {
  display: flex; gap: 4px; padding: 8px;
  border-bottom: 1px solid var(--surface-border);
}
.char-node {
  background: white; border: 2px solid #1890ff; border-radius: 8px;
  padding: 8px 12px; min-width: 120px; text-align: center;
}
.char-node.selected { border-color: #ff4d4f; box-shadow: 0 0 0 2px rgba(255,77,79,0.2); }
.char-node strong { display: block; font-size: 13px; }
.char-node span { font-size: 11px; color: #999; }
</style>
