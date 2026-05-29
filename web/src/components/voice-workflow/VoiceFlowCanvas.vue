<template>
  <div class="voice-flow-canvas">
    <VueFlow
      :nodes="flowNodes"
      :edges="flowEdges"
      fit-view-on-init
      @node-click="handleNodeClick"
      @nodes-change="handleNodesChange"
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
const emit = defineEmits(['select', 'move'])
const { onNodesChange } = useVueFlow()

const flowNodes = computed(() => props.segments.map(segment => ({
  id: String(segment.id),
  type: 'segment',
  position: { x: segment.node_x || 0, y: segment.node_y || 0 },
  data: segment,
})))

const flowEdges = computed(() => props.edges.map(edge => ({
  id: String(edge.id || `${edge.source_segment_id}-${edge.target_segment_id}`),
  source: String(edge.source_segment_id),
  target: String(edge.target_segment_id),
  animated: false,
})))

const handleNodeClick = ({ node }) => emit('select', Number(node.id))

const handleNodesChange = changes => {
  changes.forEach(change => {
    if (change.type === 'position' && change.position) {
      emit('move', Number(change.id), { node_x: change.position.x, node_y: change.position.y })
    }
  })
}

onNodesChange(handleNodesChange)
</script>

<style scoped>
.voice-flow-canvas { height: 100%; background: var(--paper-soft); border-radius: var(--radius-md); overflow: hidden; }
</style>
