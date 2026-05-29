<template>
  <div class="voice-flow-canvas">
    <div class="canvas-toolbar">
      <button
        class="mode-btn"
        :class="{ active: arrowMode }"
        @click="$emit('toggle-arrow-mode')"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
          <line x1="5" y1="12" x2="19" y2="12"/>
          <polyline points="12 5 19 12 12 19"/>
        </svg>
        {{ arrowMode ? '退出箭头模式' : '箭头模式' }}
      </button>
      <span v-if="arrowMode" class="mode-hint">
        {{ arrowSource ? '点击目标卡片完成连线' : '点击起始卡片' }}
      </span>
    </div>
    <VueFlow
      :nodes="flowNodes"
      :edges="flowEdges"
      :default-edge-options="{ type: 'smoothstep', animated: false }"
      fit-view-on-init
      @node-click="handleNodeClick"
      @nodes-change="handleNodesChange"
      @edges-change="handleEdgesChange"
    >
      <template #node-segment="nodeProps">
        <VoiceSegmentNode v-bind="nodeProps" />
      </template>
      <Background />
      <Controls />
    </VueFlow>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { VueFlow, useVueFlow } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import '@vue-flow/controls/dist/style.css'
import VoiceSegmentNode from './VoiceSegmentNode.vue'

const props = defineProps({
  segments: { type: Array, default: () => [] },
  edges: { type: Array, default: () => [] },
  arrowMode: { type: Boolean, default: false },
  arrowSource: { type: [String, Number], default: null },
})
const emit = defineEmits(['select', 'move', 'add-edge', 'remove-edge', 'toggle-arrow-mode', 'arrow-source'])
const { onNodesChange, setNodes, fitView } = useVueFlow()

const flowNodes = computed(() => props.segments.map(segment => ({
  id: String(segment.id),
  type: 'segment',
  position: { x: segment.node_x || 0, y: segment.node_y || 0 },
  data: segment,
  selected: false,
  isArrowSource: props.arrowMode && String(props.arrowSource) === String(segment.id),
})))

const flowEdges = computed(() => props.edges.map(edge => ({
  id: String(edge.id || `e-${edge.source_segment_id}-${edge.target_segment_id}`),
  source: String(edge.source_segment_id),
  target: String(edge.target_segment_id),
  type: 'smoothstep',
  animated: false,
  markerEnd: { type: 'arrowclosed', color: '#8e7f67' },
})))

const handleNodeClick = ({ node }) => {
  if (props.arrowMode) {
    if (!props.arrowSource) {
      // First click: set source
      emit('arrow-source', node.id)
    } else if (String(props.arrowSource) !== String(node.id)) {
      // Second click on different node: create edge
      emit('add-edge', {
        source_segment_id: props.arrowSource,
        target_segment_id: node.id,
      })
      emit('arrow-source', null)
    } else {
      // Click on same node: cancel
      emit('arrow-source', null)
    }
  } else {
    emit('select', node.id)
  }
}

const handleNodesChange = changes => {
  changes.forEach(change => {
    if (change.type === 'position' && change.position) {
      emit('move', change.id, { node_x: change.position.x, node_y: change.position.y })
    }
  })
}

const handleEdgesChange = changes => {
  changes.forEach(change => {
    if (change.type === 'remove' && change.id) {
      emit('remove-edge', change.id)
    }
  })
}

onNodesChange(handleNodesChange)

const setNodePositions = positionMap => {
  setNodes(nodes => nodes.map(node => {
    const pos = positionMap.get(node.id)
    return pos ? { ...node, position: pos } : node
  }))
  setTimeout(() => fitView({ padding: 0.2 }), 50)
}

defineExpose({ setNodePositions, fitView })
</script>

<style scoped>
.voice-flow-canvas { height: 100%; background: var(--paper-soft); border-radius: var(--radius-md); overflow: hidden; position: relative; }
.canvas-toolbar {
  position: absolute;
  top: 8px;
  left: 8px;
  z-index: 10;
  display: flex;
  align-items: center;
  gap: 8px;
}
.mode-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border: 1px solid var(--surface-border);
  border-radius: 6px;
  background: var(--surface);
  color: var(--text-secondary);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s ease;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
}
.mode-btn:hover {
  background: var(--surface-hover, #f0f0f0);
}
.mode-btn.active {
  background: #fa8c16;
  border-color: #fa8c16;
  color: #fff;
}
.mode-hint {
  font-size: 11px;
  color: #fa8c16;
  font-weight: 500;
}
</style>
