<template>
  <div class="voice-flow-canvas">
    <VueFlow
      :nodes="flowNodes"
      :edges="flowEdges"
      :default-edge-options="{ type: 'smoothstep', animated: false }"
      fit-view-on-init
      @node-click="handleNodeClick"
      @nodes-change="handleNodesChange"
      @connect="handleConnect"
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
})
const emit = defineEmits(['select', 'move', 'add-edge', 'remove-edge'])
const { onNodesChange, setNodes, fitView } = useVueFlow()

const flowNodes = computed(() => props.segments.map(segment => ({
  id: String(segment.id),
  type: 'segment',
  position: { x: segment.node_x || 0, y: segment.node_y || 0 },
  data: segment,
})))

const flowEdges = computed(() => props.edges.map(edge => ({
  id: String(edge.id || `e-${edge.source_segment_id}-${edge.target_segment_id}`),
  source: String(edge.source_segment_id),
  target: String(edge.target_segment_id),
  type: 'smoothstep',
  animated: false,
  markerEnd: { type: 'arrowclosed', color: '#8e7f67' },
})))

const handleNodeClick = ({ node }) => emit('select', node.id)

const handleNodesChange = changes => {
  changes.forEach(change => {
    if (change.type === 'position' && change.position) {
      emit('move', change.id, { node_x: change.position.x, node_y: change.position.y })
    }
  })
}

const handleConnect = params => {
  emit('add-edge', {
    source_segment_id: params.source,
    target_segment_id: params.target,
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
.voice-flow-canvas { height: 100%; background: var(--paper-soft); border-radius: var(--radius-md); overflow: hidden; }
</style>
