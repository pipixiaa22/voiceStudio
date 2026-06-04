<template>
  <div class="graph-inspector" v-if="node || edge">
    <!-- Node detail -->
    <template v-if="node">
      <div class="inspector-header">
        <span class="inspector-type" :style="{ color: typeColor }">{{ typeLabel }}</span>
        <span class="inspector-name">{{ node.name || node.title }}</span>
      </div>

      <div class="inspector-body">
        <div v-if="node.aliases && node.aliases.length" class="inspector-field">
          <span class="field-label">别名</span>
          <span class="field-value">{{ node.aliases.join(', ') }}</span>
        </div>

        <div v-if="node.summary" class="inspector-field">
          <span class="field-label">简介</span>
          <span class="field-value">{{ node.summary }}</span>
        </div>

        <div v-if="node.importance != null" class="inspector-field">
          <span class="field-label">重要度</span>
          <a-rate :value="node.importance" :count="10" disabled style="font-size: 12px;" />
        </div>

        <div v-if="node.event_type" class="inspector-field">
          <span class="field-label">事件类型</span>
          <span class="field-value">{{ node.event_type }}</span>
        </div>

        <div v-if="node.timeline_order != null" class="inspector-field">
          <span class="field-label">时间线序号</span>
          <span class="field-value">{{ node.timeline_order }}</span>
        </div>

        <div v-if="node.attributes && Object.keys(node.attributes).length" class="inspector-field">
          <span class="field-label">属性</span>
          <div class="attrs-grid">
            <div v-for="(v, k) in node.attributes" :key="k" class="attr-item">
              <span class="attr-key">{{ k }}:</span>
              <span class="attr-val">{{ typeof v === 'object' ? JSON.stringify(v) : v }}</span>
            </div>
          </div>
        </div>

        <div v-if="node.effects && node.effects.length" class="inspector-field">
          <span class="field-label">效果</span>
          <div v-for="(eff, i) in node.effects" :key="i" class="effect-item">
            <span v-if="eff.target">{{ eff.target }}:</span>
            <span>{{ eff.description || eff.type || JSON.stringify(eff) }}</span>
          </div>
        </div>
      </div>

      <div class="inspector-actions">
        <a-button size="small" @click="$emit('focus', node.id)">聚焦</a-button>
        <a-button size="small" @click="$emit('edit', node)">编辑</a-button>
      </div>
    </template>

    <!-- Edge detail -->
    <template v-else-if="edge">
      <div class="inspector-header">
        <span class="inspector-type" :style="{ color: edgeColor }">关系</span>
        <span class="inspector-name">{{ edge.label || edge.type || edge.relation_type }}</span>
      </div>

      <div class="inspector-body">
        <div class="inspector-field">
          <span class="field-label">类型</span>
          <span class="field-value">{{ edge.type || edge.relation_type }}</span>
        </div>

        <div v-if="edge.description" class="inspector-field">
          <span class="field-label">描述</span>
          <span class="field-value">{{ edge.description }}</span>
        </div>

        <div v-if="edge.strength != null" class="inspector-field">
          <span class="field-label">强度</span>
          <a-progress :percent="Math.round(edge.strength * 100)" size="small" :stroke-color="'#58a6ff'" />
        </div>

        <div v-if="edge.confidence != null" class="inspector-field">
          <span class="field-label">置信度</span>
          <a-progress :percent="Math.round(edge.confidence * 100)" size="small" :stroke-color="'#7ee787'" />
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { getNodeColor, getEdgeColor } from './useForceGraph'

const props = defineProps({
  node: { type: Object, default: null },
  edge: { type: Object, default: null },
  graphType: { type: String, default: 'characters' },
})

defineEmits(['focus', 'edit'])

const NODE_TYPE_LABELS = {
  character: '人物',
  location: '地点',
  item: '物品',
  faction: '势力',
}

const typeLabel = computed(() => {
  if (!props.node) return ''
  return NODE_TYPE_LABELS[props.node.type] || props.node.type || '节点'
})

const typeColor = computed(() => getNodeColor(props.node?.type))
const edgeColor = computed(() => getEdgeColor(props.edge?.type || props.edge?.relation_type))
</script>

<style scoped>
.graph-inspector {
  position: absolute;
  top: 48px;
  right: 8px;
  width: 260px;
  max-height: calc(100% - 56px);
  background: #161b22;
  border: 1px solid #21262d;
  border-radius: 6px;
  padding: 12px;
  z-index: 10;
  overflow-y: auto;
}

.inspector-header {
  margin-bottom: 12px;
}

.inspector-type {
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.inspector-name {
  display: block;
  font-size: 16px;
  font-weight: 600;
  color: #c9d1d9;
  margin-top: 2px;
}

.inspector-body {
  margin-bottom: 12px;
}

.inspector-field {
  margin-bottom: 8px;
}

.field-label {
  display: block;
  font-size: 10px;
  color: #8b949e;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 2px;
}

.field-value {
  display: block;
  font-size: 12px;
  color: #c9d1d9;
  line-height: 1.5;
}

.attrs-grid {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.attr-item {
  font-size: 12px;
  color: #c9d1d9;
}

.attr-key {
  color: #8b949e;
  margin-right: 4px;
}

.effect-item {
  font-size: 12px;
  color: #c9d1d9;
  margin-bottom: 2px;
}

.inspector-actions {
  display: flex;
  gap: 8px;
}
</style>
