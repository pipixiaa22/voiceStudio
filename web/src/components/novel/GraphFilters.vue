<template>
  <div class="graph-filters" v-if="visible">
    <div class="filter-section">
      <div class="filter-title">节点类型</div>
      <a-checkbox-group v-model:value="localFilters.nodeTypes" :options="nodeTypeOptions" @change="emitChange" />
    </div>

    <div class="filter-section">
      <div class="filter-title">关系类型</div>
      <a-checkbox-group v-model:value="localFilters.edgeTypes" :options="edgeTypeOptions" @change="emitChange" />
    </div>

    <div class="filter-section">
      <div class="filter-title">重要度</div>
      <a-slider
        v-model:value="localFilters.importanceRange"
        range
        :min="0"
        :max="10"
        @change="emitChange"
      />
    </div>

    <div class="filter-section">
      <a-button size="small" @click="resetFilters">重置筛选</a-button>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, reactive } from 'vue'

const props = defineProps({
  visible: { type: Boolean, default: true },
  filters: { type: Object, default: () => ({}) },
  graphType: { type: String, default: 'characters' },
})

const emit = defineEmits(['update:filters'])

const nodeTypeOptions = [
  { label: '人物', value: 'character' },
  { label: '地点', value: 'location' },
  { label: '物品', value: 'item' },
  { label: '势力', value: 'faction' },
]

const characterEdgeOptions = [
  { label: '师徒', value: 'mentor' },
  { label: '同盟', value: 'ally' },
  { label: '敌对', value: 'enemy' },
  { label: '亲属', value: 'family' },
  { label: '恋人', value: 'lover' },
  { label: '背叛', value: 'betrayal' },
]

const eventEdgeOptions = [
  { label: '引发', value: 'causes' },
  { label: '推动', value: 'drives' },
  { label: '阻碍', value: 'blocks' },
  { label: '逆转', value: 'reverses' },
  { label: '揭示', value: 'reveals' },
  { label: '升级', value: 'escalates' },
]

const edgeTypeOptions = ref(props.graphType === 'events' ? eventEdgeOptions : characterEdgeOptions)

watch(() => props.graphType, (type) => {
  edgeTypeOptions.value = type === 'events' ? eventEdgeOptions : characterEdgeOptions
})

const localFilters = reactive({
  nodeTypes: props.filters.nodeTypes || [],
  edgeTypes: props.filters.edgeTypes || [],
  importanceRange: props.filters.importanceRange || [0, 10],
})

watch(() => props.filters, (f) => {
  localFilters.nodeTypes = f.nodeTypes || []
  localFilters.edgeTypes = f.edgeTypes || []
  localFilters.importanceRange = f.importanceRange || [0, 10]
}, { deep: true })

function emitChange() {
  emit('update:filters', { ...localFilters })
}

function resetFilters() {
  localFilters.nodeTypes = []
  localFilters.edgeTypes = []
  localFilters.importanceRange = [0, 10]
  emitChange()
}
</script>

<style scoped>
.graph-filters {
  position: absolute;
  top: 48px;
  left: 8px;
  width: 200px;
  background: #161b22;
  border: 1px solid #21262d;
  border-radius: 6px;
  padding: 12px;
  z-index: 10;
}

.filter-section {
  margin-bottom: 12px;
}

.filter-section:last-child {
  margin-bottom: 0;
}

.filter-title {
  font-size: 11px;
  color: #8b949e;
  margin-bottom: 6px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.graph-filters :deep(.ant-checkbox-wrapper) {
  color: #c9d1d9;
  font-size: 12px;
}

.graph-filters :deep(.ant-slider-rail) {
  background: #21262d;
}

.graph-filters :deep(.ant-slider-track) {
  background: #58a6ff;
}
</style>
