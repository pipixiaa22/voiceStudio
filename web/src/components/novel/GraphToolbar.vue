<template>
  <div class="graph-toolbar">
    <div class="toolbar-left">
      <a-input-search
        v-model:value="localQuery"
        placeholder="搜索节点..."
        size="small"
        allow-clear
        class="toolbar-search"
        @search="onSearch"
        @change="onSearchChange"
      />
      <a-button size="small" @click="$emit('toggle-filters')" :type="filtersVisible ? 'primary' : 'default'">
        <template #icon><FilterOutlined /></template>
      </a-button>
    </div>

    <div class="toolbar-center">
      <a-radio-group v-model:value="graphType" size="small" button-style="solid" class="type-toggle">
        <a-radio-button value="characters">人物</a-radio-button>
        <a-radio-button value="events">事件</a-radio-button>
      </a-radio-group>

      <a-radio-group v-model:value="mode" size="small" button-style="solid" class="mode-toggle">
        <a-radio-button value="explore">浏览</a-radio-button>
        <a-radio-button value="edit">编辑</a-radio-button>
      </a-radio-group>
    </div>

    <div class="toolbar-right">
      <template v-if="mode === 'edit'">
        <a-button size="small" @click="$emit('add-node')">
          {{ graphType === 'characters' ? '新增人物' : '新增事件' }}
        </a-button>
        <a-button size="small" @click="$emit('add-relation')">新增关系</a-button>
        <a-button
          type="primary"
          size="small"
          @click="$emit('save-layout')"
        >
          保存布局
        </a-button>
      </template>
      <a-button size="small" @click="$emit('fit')">
        <template #icon><ExpandOutlined /></template>
      </a-button>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { ExpandOutlined, FilterOutlined } from '@ant-design/icons-vue'

const props = defineProps({
  modelValue: { type: String, default: '' },
  graphType: { type: String, default: 'characters' },
  mode: { type: String, default: 'explore' },
  filtersVisible: { type: Boolean, default: false },
})

const emit = defineEmits([
  'update:modelValue', 'update:graphType', 'update:mode',
  'search', 'fit', 'zoom-in', 'zoom-out',
  'save-layout', 'add-node', 'add-relation', 'toggle-filters',
])

const localQuery = ref(props.modelValue)

watch(() => props.modelValue, (v) => { localQuery.value = v })

const graphType = ref(props.graphType)
watch(() => props.graphType, (v) => { graphType.value = v })
watch(graphType, (v) => emit('update:graphType', v))

const mode = ref(props.mode)
watch(() => props.mode, (v) => { mode.value = v })
watch(mode, (v) => emit('update:mode', v))

function onSearch(value) {
  emit('update:modelValue', value)
  emit('search', value)
}

function onSearchChange(e) {
  const value = e.target.value
  emit('update:modelValue', value)
  emit('search', value)
}
</script>

<style scoped>
.graph-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
  background: #161b22;
  border-bottom: 1px solid #21262d;
}

.toolbar-left {
  flex: 0 0 240px;
  display: flex;
  gap: 6px;
}

.toolbar-search {
  background: #0d1117;
  border-color: #30363d;
}

.toolbar-center {
  flex: 1;
  display: flex;
  justify-content: center;
  gap: 12px;
}

.toolbar-right {
  display: flex;
  gap: 6px;
}

.type-toggle :deep(.ant-radio-button-wrapper),
.mode-toggle :deep(.ant-radio-button-wrapper) {
  background: #0d1117;
  border-color: #30363d;
  color: #8b949e;
}

.type-toggle :deep(.ant-radio-button-wrapper-checked),
.mode-toggle :deep(.ant-radio-button-wrapper-checked) {
  background: #21262d;
  border-color: #58a6ff;
  color: #c9d1d9;
}
</style>
