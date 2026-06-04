<template>
  <div class="obsidian-graph" ref="containerRef">
    <svg ref="svgRef" class="obsidian-graph-svg" @click="handleCanvasClick"></svg>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useForceGraph } from './useForceGraph'

const props = defineProps({
  nodes: { type: Array, default: () => [] },
  edges: { type: Array, default: () => [] },
  graphType: { type: String, default: 'characters' },
  selectedId: { type: String, default: null },
  hoveredId: { type: String, default: null },
  query: { type: String, default: '' },
  mode: { type: String, default: 'explore' },
})

const emit = defineEmits(['select', 'hover', 'unhover', 'dblclick', 'drag-end', 'canvas-click', 'create-edge'])

const containerRef = ref(null)
const svgRef = ref(null)

const {
  init,
  highlightNode,
  clearHighlight,
  selectNode,
  highlightQuery,
  focusNode,
  fitAll,
  updateData,
  getPositions,
  destroy,
  getNodeColor,
  getEdgeColor,
  NODE_TYPE_COLORS,
  EDGE_TYPE_COLORS,
} = useForceGraph({
  graphType: props.graphType,
  onHover: (d) => emit('hover', d),
  onUnhover: (d) => emit('unhover', d),
  onSelect: (d) => emit('select', d),
  onDblClick: (d) => emit('dblclick', d),
  onDragEnd: (d) => emit('drag-end', d),
})

function handleCanvasClick(event) {
  // Only if clicking the SVG background (not a node)
  if (event.target === svgRef.value) {
    emit('canvas-click')
  }
}

// Initialize when mounted and data is ready
onMounted(() => {
  if (svgRef.value && props.nodes.length) {
    init(svgRef.value, props.nodes, props.edges)
  }
})

// Watch for data changes
watch(() => [props.nodes, props.edges], ([newNodes, newEdges]) => {
  if (svgRef.value && newNodes.length) {
    nextTick(() => {
      if (!svgRef.value) return
      // If already initialized, update data; otherwise init
      try {
        updateData(newNodes, newEdges)
      } catch {
        init(svgRef.value, newNodes, newEdges)
      }
    })
  }
}, { deep: true })

// Watch for selection changes
watch(() => props.selectedId, (newId) => {
  if (newId) {
    const neighbors = selectNode(newId)
    emit('select', props.nodes.find(n => n.id === newId))
  } else {
    clearHighlight()
  }
})

// Watch for hover changes
watch(() => props.hoveredId, (newId) => {
  if (newId) {
    highlightNode(newId)
  } else if (!props.selectedId) {
    clearHighlight()
  }
})

// Watch for query changes
watch(() => props.query, (q) => {
  highlightQuery(q)
})

onBeforeUnmount(() => {
  destroy()
})

// Expose methods for parent components
defineExpose({
  fitAll,
  focusNode,
  getPositions,
  highlightNode,
  clearHighlight,
})
</script>

<style scoped>
.obsidian-graph {
  width: 100%;
  height: 100%;
  background: #0d1117;
  border-radius: 6px;
  overflow: hidden;
  position: relative;
}

.obsidian-graph-svg {
  width: 100%;
  height: 100%;
  display: block;
}
</style>
