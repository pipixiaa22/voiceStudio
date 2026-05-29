<template>
  <div class="workflow-toolbar">
    <div class="title-block">
      <a-input v-model:value="localTitle" class="title-input" @blur="emitTitle" />
      <span class="save-state">{{ saving ? '保存中' : '已保存' }}</span>
    </div>
    <a-space>
      <a-button @click="$emit('import-text')">导入文本</a-button>
      <a-button @click="$emit('auto-layout')">自动重排</a-button>
      <a-button :loading="saving" @click="$emit('save')">保存</a-button>
      <a-button type="primary" :loading="exporting" @click="$emit('export')">导出</a-button>
    </a-space>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  title: { type: String, required: true },
  saving: Boolean,
  exporting: Boolean,
})
const emit = defineEmits(['update:title', 'save', 'export', 'import-text', 'auto-layout'])
const localTitle = ref(props.title)

watch(() => props.title, value => {
  localTitle.value = value
})

const emitTitle = () => emit('update:title', localTitle.value || '未命名配音工程')
</script>

<style scoped>
.workflow-toolbar { display: flex; align-items: center; justify-content: space-between; height: 100%; }
.title-block { display: flex; align-items: center; gap: 10px; }
.title-input { width: 260px; font-weight: 650; }
.save-state { color: var(--text-muted); font-size: 12px; }
</style>
