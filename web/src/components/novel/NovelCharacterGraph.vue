<template>
  <div class="novel-character-graph">
    <ObsidianGraphCanvas
      ref="canvasRef"
      :nodes="graphNodes"
      :edges="graphEdges"
      graphType="characters"
      :selectedId="store.graphView.selectedId"
      :hoveredId="store.graphView.hoveredId"
      :query="store.graphView.query"
      :mode="store.graphView.mode"
      @select="handleSelect"
      @edge-select="handleEdgeSelect"
      @hover="handleHover"
      @unhover="handleUnhover"
      @dblclick="handleDblClick"
      @drag-end="handleDragEnd"
      @canvas-click="handleCanvasClick"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useNovelsStore } from '../../stores/novels'
import ObsidianGraphCanvas from './ObsidianGraphCanvas.vue'

const store = useNovelsStore()
const canvasRef = ref(null)

onMounted(() => {
  if (store.currentProject) {
    store.loadCharacterGraph(store.currentProject.id)
  }
})

// Map entities to graph nodes with namespaced IDs, applying filters
const graphNodes = computed(() => {
  const f = store.graphView.filters
  return store.entities
    .filter(e => {
      // Node type filter
      if (f.nodeTypes && f.nodeTypes.length > 0 && !f.nodeTypes.includes(e.entity_type || 'character')) return false
      // Importance range filter
      if (f.importanceRange) {
        const imp = e.importance || 5
        if (imp < f.importanceRange[0] || imp > f.importanceRange[1]) return false
      }
      return true
    })
    .map(e => ({
      id: `entity:${e.id}`,
      _rawId: e.id,
      name: e.name,
      type: e.entity_type || 'character',
      importance: e.importance || 5,
      aliases: e.aliases || [],
      summary: e.summary,
      attributes: e.attributes || {},
      x: e.x ?? e.node_x ?? 0,
      y: e.y ?? e.node_y ?? 0,
    }))
})

// Map relations to graph edges with namespaced IDs, applying filters
const graphEdges = computed(() => {
  const f = store.graphView.filters
  const nodeIds = new Set(graphNodes.value.map(n => n.id))
  return store.relations
    .filter(r => {
      // Only include edges whose both endpoints are visible
      if (!nodeIds.has(`entity:${r.source_entity_id}`) || !nodeIds.has(`entity:${r.target_entity_id}`)) return false
      // Edge type filter
      if (f.edgeTypes && f.edgeTypes.length > 0 && !f.edgeTypes.includes(r.relation_type)) return false
      return true
    })
    .map(r => ({
      id: `rel:${r.id}`,
      _rawId: r.id,
      source: `entity:${r.source_entity_id}`,
      target: `entity:${r.target_entity_id}`,
      type: r.relation_type,
      label: r.label || r.relation_type,
      description: r.description,
      strength: r.strength || 0.5,
      status: r.status,
    }))
})

function handleSelect(d) {
  if (d) {
    store.graphView.selectedId = d.id
    store.selectedEntityId = d._rawId
    store.selectedRelationId = null
    store.selectedEventId = null
    // Update neighborIds
    const neighbors = canvasRef.value?.highlightNode(d.id)
    store.graphView.neighborIds = neighbors || []
  }
}

function handleEdgeSelect(d) {
  if (d) {
    store.graphView.selectedId = d.id
    store.selectedRelationId = d._rawId
    store.selectedEntityId = null
    store.selectedEventId = null
    store.graphView.neighborIds = []
    canvasRef.value?.clearHighlight()
  }
}

function handleHover(d) {
  store.graphView.hoveredId = d.id
}

function handleUnhover() {
  store.graphView.hoveredId = null
}

function handleDblClick(d) {
  canvasRef.value?.focusNode(d.id)
}

function handleDragEnd(d) {
  // Save position to store
  const entity = store.entities.find(e => `entity:${e.id}` === d.id)
  if (entity) {
    entity.node_x = d.x
    entity.node_y = d.y
    store.setGraphViewPinned(d.id, { x: d.x, y: d.y })
  }
}

function handleCanvasClick() {
  store.graphView.selectedId = null
  store.graphView.neighborIds = []
  store.selectedEntityId = null
  store.selectedRelationId = null
  canvasRef.value?.clearHighlight()
}

// Expose for parent
defineExpose({
  fitAll: () => canvasRef.value?.fitAll(),
  getPositions: () => canvasRef.value?.getPositions() || [],
})
</script>

<style scoped>
.novel-character-graph {
  width: 100%;
  height: 100%;
}
</style>
