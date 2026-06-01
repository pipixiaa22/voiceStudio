<template>
  <div class="workflow-toolbar">
    <div class="project-switcher">
      <span class="project-switcher-label">工程</span>
      <a-select
        :value="currentWorkflowId"
        :loading="switching"
        show-search
        :filter-option="filterWorkflowOption"
        placeholder="切换配音工程"
        class="project-select"
        @change="$emit('switch-workflow', $event)"
      >
        <a-select-option
          v-for="workflow in workflows"
          :key="workflow.id"
          :value="workflow.id"
          :label="workflow.title"
        >
          <div class="project-option">
            <span>{{ workflow.title || '未命名配音工程' }}</span>
            <small>#{{ workflow.id }}</small>
          </div>
        </a-select-option>
      </a-select>
    </div>
    <div class="title-block">
      <a-input v-model:value="localTitle" class="title-input" @blur="emitTitle" />
      <span class="save-state" :class="{ dirty, error: !!saveError }">
        {{ saveLabel }}
      </span>
    </div>
    <div class="default-voice">
      <span class="default-voice-label">默认音色</span>
      <VoiceProfileIdField
        :model-value="defaultVoiceProfileId"
        :profiles="voiceProfiles"
        placeholder="选择默认音色"
        can-create
        :create-initial-values="{ scene: 'short_video' }"
        @update:model-value="$emit('update:defaultVoiceProfileId', $event)"
        @created="$emit('voice-profile-created', $event)"
      />
    </div>
    <a-space>
      <a-button @click="$emit('import-text')">导入文本</a-button>
      <a-button @click="$emit('auto-layout')">自动重排</a-button>
      <a-button :loading="saving" @click="$emit('save')">保存</a-button>
      <a-button type="primary" :loading="exporting" @click="$emit('export')">导出</a-button>
      <a-button :loading="exportingJianying" @click="$emit('export-jianying')">写入剪映</a-button>
      <a-tooltip title="清除所有缓存音频，下次导出重新合成">
        <a-button @click="$emit('clear-cache')">清除缓存</a-button>
      </a-tooltip>
    </a-space>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import VoiceProfileIdField from './VoiceProfileIdField.vue'

const props = defineProps({
  title: { type: String, required: true },
  saving: Boolean,
  dirty: Boolean,
  saveError: { type: String, default: '' },
  lastSavedAt: { type: String, default: null },
  exporting: Boolean,
  exportingJianying: Boolean,
  switching: Boolean,
  currentWorkflowId: { type: [Number, String, null], default: null },
  workflows: { type: Array, default: () => [] },
  defaultVoiceProfileId: { type: [Number, String, null], default: null },
  voiceProfiles: { type: Array, default: () => [] },
})
const emit = defineEmits(['update:title', 'update:defaultVoiceProfileId', 'save', 'export', 'export-jianying', 'import-text', 'auto-layout', 'voice-profile-created', 'clear-cache', 'switch-workflow'])
const localTitle = ref(props.title)

const saveLabel = computed(() => {
  if (props.saving) return '保存中'
  if (props.saveError) return '保存失败'
  if (props.dirty) return '未保存'
  if (!props.lastSavedAt) return '已保存'
  return `已保存 ${new Date(props.lastSavedAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`
})

watch(() => props.title, value => {
  localTitle.value = value
})

const emitTitle = () => emit('update:title', localTitle.value || '未命名配音工程')

const filterWorkflowOption = (input, option) => {
  const text = String(option?.label || '').toLowerCase()
  return text.includes(input.toLowerCase())
}
</script>

<style scoped>
.workflow-toolbar { display: flex; align-items: center; justify-content: space-between; gap: 14px; min-height: 100%; flex-wrap: wrap; }
.project-switcher { display: flex; align-items: center; gap: 8px; min-width: 260px; }
.project-switcher-label { color: var(--text-muted); font-size: 12px; white-space: nowrap; }
.project-select { width: 220px; }
.project-option { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.project-option small { color: var(--text-muted); font-size: 11px; }
.title-block { display: flex; align-items: center; gap: 10px; }
.title-input { width: 220px; font-weight: 650; }
.save-state { color: var(--text-muted); font-size: 12px; white-space: nowrap; }
.save-state.dirty { color: #ad6800; }
.save-state.error { color: #cf1322; }
.default-voice { display: flex; align-items: center; gap: 8px; min-width: 260px; }
.default-voice-label { color: var(--text-muted); font-size: 12px; white-space: nowrap; }
.default-voice :deep(.voice-profile-id-field) { flex: 1; }

@media (max-width: 1180px) {
  .workflow-toolbar { align-items: flex-start; }
  .project-switcher,
  .title-block,
  .default-voice {
    min-width: min(100%, 320px);
  }
  .project-select,
  .title-input {
    width: min(100%, 240px);
  }
}
</style>
