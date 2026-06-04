<template>
  <div class="graph-legend">
    <div class="legend-section">
      <div class="legend-title">节点</div>
      <div v-for="item in nodeItems" :key="item.type" class="legend-item">
        <span class="legend-dot" :style="{ background: item.color }"></span>
        <span class="legend-label">{{ item.label }}</span>
      </div>
    </div>
    <div class="legend-section">
      <div class="legend-title">关系</div>
      <div v-for="item in edgeItems" :key="item.type" class="legend-item">
        <span class="legend-line" :style="{ background: item.color }"></span>
        <span class="legend-label">{{ item.label }}</span>
      </div>
    </div>
    <div class="legend-section">
      <div class="legend-title">大小</div>
      <div class="legend-size">
        <span class="size-dot small"></span>
        <span class="size-label">低重要度</span>
        <span class="size-dot large"></span>
        <span class="size-label">高重要度</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { NODE_TYPE_COLORS, EDGE_TYPE_COLORS } from './useForceGraph'

const props = defineProps({
  graphType: { type: String, default: 'characters' },
})

const NODE_LABELS = {
  character: '人物',
  location: '地点',
  item: '物品',
  faction: '势力',
}

const CHARACTER_EDGE_LABELS = {
  mentor: '师徒',
  ally: '同盟',
  enemy: '敌对',
  family: '亲属',
  lover: '恋人',
  betrayal: '背叛',
}

const EVENT_EDGE_LABELS = {
  causes: '引发',
  drives: '推动',
  blocks: '阻碍',
  reverses: '逆转',
  reveals: '揭示',
  escalates: '升级',
}

const nodeItems = computed(() => {
  return Object.entries(NODE_TYPE_COLORS)
    .filter(([type]) => type !== 'default')
    .map(([type, color]) => ({ type, color, label: NODE_LABELS[type] || type }))
})

const edgeItems = computed(() => {
  const labels = props.graphType === 'events' ? EVENT_EDGE_LABELS : CHARACTER_EDGE_LABELS
  const types = Object.keys(labels)
  return types.map(type => ({
    type,
    color: EDGE_TYPE_COLORS[type] || EDGE_TYPE_COLORS.default,
    label: labels[type] || type,
  }))
})
</script>

<style scoped>
.graph-legend {
  position: absolute;
  bottom: 12px;
  left: 12px;
  background: rgba(22, 27, 34, 0.9);
  border: 1px solid #21262d;
  border-radius: 6px;
  padding: 10px 14px;
  z-index: 10;
  font-size: 11px;
}

.legend-section {
  margin-bottom: 8px;
}

.legend-section:last-child {
  margin-bottom: 0;
}

.legend-title {
  color: #8b949e;
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 4px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 2px;
}

.legend-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.legend-line {
  width: 16px;
  height: 2px;
  border-radius: 1px;
  flex-shrink: 0;
}

.legend-label {
  color: #c9d1d9;
}

.legend-size {
  display: flex;
  align-items: center;
  gap: 6px;
}

.size-dot {
  border-radius: 50%;
  background: #8b949e;
}

.size-dot.small {
  width: 5px;
  height: 5px;
}

.size-dot.large {
  width: 11px;
  height: 11px;
}

.size-label {
  color: #8b949e;
  margin-right: 8px;
}
</style>
