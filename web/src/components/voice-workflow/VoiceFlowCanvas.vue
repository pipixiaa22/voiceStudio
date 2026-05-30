<template>
  <div class="voice-flow-canvas">
    <div class="canvas-toolbar">
      <button
        class="mode-btn"
        :class="{ active: localArrowMode }"
        @click="toggleArrowMode"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
          <line x1="5" y1="12" x2="19" y2="12"/>
          <polyline points="12 5 19 12 12 19"/>
        </svg>
        {{ localArrowMode ? '退出箭头模式' : '箭头模式' }}
      </button>
      <span v-if="localArrowMode" class="mode-hint">
        {{ arrowSourceId ? '② 点击目标卡片（已有连线则删除）' : '① 点击起始卡片' }}
      </span>
      <span v-if="localArrowMode && arrowSourceId" class="mode-source">
        起点: #{{ sourceOrderIndex }}
      </span>
    </div>
    <VueFlow
      :nodes="flowNodes"
      :edges="flowEdges"
      fit-view-on-init
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
import { ref, computed } from 'vue'
import { VueFlow, useVueFlow } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import '@vue-flow/controls/dist/style.css'
import VoiceSegmentNode from './VoiceSegmentNode.vue'
import { formatSegmentVoiceLabel } from '../../utils/voiceWorkflowProfiles'

const props = defineProps({
  segments: { type: Array, default: () => [] },
  edges: { type: Array, default: () => [] },
  voiceProfiles: { type: Array, default: () => [] },
  defaultVoiceProfileId: { type: [Number, String, null], default: null },
})
const emit = defineEmits(['select', 'move', 'add-edge', 'remove-edge'])

const { onNodeClick, setNodes, fitView } = useVueFlow()

// Arrow mode state
const localArrowMode = ref(false)
const arrowSourceId = ref(null)

const sourceOrderIndex = computed(() => {
  if (!arrowSourceId.value) return null
  const seg = props.segments.find(s => String(s.id) === String(arrowSourceId.value))
  return seg?.order_index ?? '?'
})

const toggleArrowMode = () => {
  localArrowMode.value = !localArrowMode.value
  arrowSourceId.value = null
}

const flowNodes = computed(() => props.segments.map(segment => {
  const segId = String(segment.id)
  return {
    id: segId,
    type: 'segment',
    position: { x: segment.node_x || 0, y: segment.node_y || 0 },
    data: {
      ...segment,
      voice_label: formatSegmentVoiceLabel(segment, props.defaultVoiceProfileId, props.voiceProfiles),
      isArrowSource: localArrowMode.value && arrowSourceId.value === segId,
      arrowMode: localArrowMode.value,
    },
    selected: false,
  }
}))

// Build a position lookup for smart routing
const nodePositionMap = computed(() => {
  const map = new Map()
  // Node dimensions (must match VoiceSegmentNode CSS)
  const W = 190
  const H = 100
  for (const seg of props.segments) {
    const x = seg.node_x || 0
    const y = seg.node_y || 0
    map.set(String(seg.id), { cx: x + W / 2, cy: y + H / 2 })
  }
  return map
})

// Smart routing: pick the shortest-path handle pair based on relative position
const pickHandles = (sourceId, targetId) => {
  const s = nodePositionMap.value.get(String(sourceId))
  const t = nodePositionMap.value.get(String(targetId))
  if (!s || !t) return { sourceHandle: 'right', targetHandle: 'left' }

  const dx = t.cx - s.cx
  const dy = t.cy - s.cy
  const adx = Math.abs(dx)
  const ady = Math.abs(dy)

  if (adx >= ady) {
    // Horizontal dominant: left-right connection
    return dx >= 0
      ? { sourceHandle: 'right', targetHandle: 'left' }
      : { sourceHandle: 'left', targetHandle: 'right' }
  } else {
    // Vertical dominant: top-bottom connection
    return dy >= 0
      ? { sourceHandle: 'bottom', targetHandle: 'top' }
      : { sourceHandle: 'top', targetHandle: 'bottom' }
  }
}

const flowEdges = computed(() => props.edges.map(edge => {
  const { sourceHandle, targetHandle } = pickHandles(edge.source_segment_id, edge.target_segment_id)
  return {
    id: String(edge.id || `e-${edge.source_segment_id}-${edge.target_segment_id}`),
    source: String(edge.source_segment_id),
    target: String(edge.target_segment_id),
    sourceHandle,
    targetHandle,
    type: 'smoothstep',
    animated: false,
    markerEnd: { type: 'arrowclosed', color: '#8e7f67' },
  }
}))

// Check if an edge exists between two nodes
const findEdgeBetween = (idA, idB) => {
  return props.edges.find(e =>
    (String(e.source_segment_id) === String(idA) && String(e.target_segment_id) === String(idB)) ||
    (String(e.source_segment_id) === String(idB) && String(e.target_segment_id) === String(idA))
  )
}

// Use Vue Flow's composable callback - this fires reliably for all node clicks
onNodeClick(({ node }) => {
  const clickedId = node.id

  if (!localArrowMode.value) {
    emit('select', clickedId)
    return
  }

  // Arrow mode
  if (!arrowSourceId.value) {
    // Step 1: select source
    arrowSourceId.value = clickedId
  } else if (arrowSourceId.value === clickedId) {
    // Clicked same node: cancel
    arrowSourceId.value = null
  } else {
    // Step 2: toggle edge between source and target
    const existing = findEdgeBetween(arrowSourceId.value, clickedId)
    if (existing) {
      // Edge exists: remove it
      emit('remove-edge', existing.id)
    } else {
      // No edge: create one
      emit('add-edge', {
        source_segment_id: arrowSourceId.value,
        target_segment_id: clickedId,
      })
    }
    arrowSourceId.value = null
  }
})

const handleNodesChange = changes => {
  changes.forEach(change => {
    if (change.type === 'position' && change.position) {
      // Keep ID as string - don't Number() convert, it breaks tmp-* IDs
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
.mode-source {
  font-size: 11px;
  color: var(--text-muted);
  background: rgba(250, 140, 22, 0.08);
  padding: 1px 6px;
  border-radius: 4px;
}
</style>
