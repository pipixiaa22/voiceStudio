<template>
  <div class="novel-event-graph">
    <ObsidianGraphCanvas
      ref="canvasRef"
      :nodes="graphNodes"
      :edges="graphEdges"
      graphType="events"
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
    store.loadEventGraph(store.currentProject.id)
  }
})

// Map events to graph nodes with namespaced IDs, applying filters
const graphNodes = computed(() => {
  const f = store.graphView.filters
  return store.events
    .filter(e => {
      // Node type filter
      if (f.nodeTypes && f.nodeTypes.length > 0 && !f.nodeTypes.includes(e.event_type || 'event')) return false
      return true
    })
    .map(e => ({
      id: `event:${e.id}`,
      _rawId: e.id,
      name: e.title,
      title: e.title,
      type: e.event_type || 'event',
      importance: 5,
      summary: e.summary,
      event_type: e.event_type,
      timeline_order: e.timeline_order || 0,
      chapter_id: e.chapter_id,
      x: e.x ?? e.node_x ?? 0,
      y: e.y ?? e.node_y ?? 0,
    }))
})

// Map event-relations to graph edges with namespaced IDs, applying filters
const graphEdges = computed(() => {
  const f = store.graphView.filters
  const nodeIds = new Set(graphNodes.value.map(n => n.id))
  return store.eventRelations
    .filter(r => {
      const sid = `event:${r.source || r.source_event_id}`
      const tid = `event:${r.target || r.target_event_id}`
      if (!nodeIds.has(sid) || !nodeIds.has(tid)) return false
      // Edge type filter
      if (f.edgeTypes && f.edgeTypes.length > 0 && !f.edgeTypes.includes(r.type || r.relation_type)) return false
      return true
    })
    .map(r => ({
      id: `erel:${r.id}`,
      _rawId: r.id,
      source: `event:${r.source || r.source_event_id}`,
      target: `event:${r.target || r.target_event_id}`,
      type: r.type || r.relation_type,
      label: r.label || r.type || r.relation_type,
      description: r.description,
      confidence: r.confidence || 1.0,
    }))
})

function handleSelect(d) {
  if (d) {
    store.graphView.selectedId = d.id
    store.selectedEventId = d._rawId
    store.selectedEntityId = null
    store.selectedRelationId = null
    const neighbors = canvasRef.value?.highlightNode(d.id)
    store.graphView.neighborIds = neighbors || []
  }
}

function handleEdgeSelect(d) {
  if (d) {
    store.graphView.selectedId = d.id
    store.selectedEventId = null
    store.selectedEntityId = null
    store.selectedRelationId = null
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
  const event = store.events.find(e => `event:${e.id}` === d.id)
  if (event) {
    event.node_x = d.x
    event.node_y = d.y
    store.setGraphViewPinned(d.id, { x: d.x, y: d.y })
  }
}

function handleCanvasClick() {
  store.graphView.selectedId = null
  store.graphView.neighborIds = []
  store.selectedEventId = null
  canvasRef.value?.clearHighlight()
}

defineExpose({
  fitAll: () => canvasRef.value?.fitAll(),
  getPositions: () => canvasRef.value?.getPositions() || [],
})
</script>

<style scoped>
.novel-event-graph {
  width: 100%;
  height: 100%;
}
</style>
