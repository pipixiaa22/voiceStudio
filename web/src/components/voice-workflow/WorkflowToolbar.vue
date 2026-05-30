<template>
  <div class="workflow-toolbar">
    <div class="title-block">
      <a-input v-model:value="localTitle" class="title-input" @blur="emitTitle" />
      <span class="save-state">{{ saving ? '保存中' : '已保存' }}</span>
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
      <a-tooltip title="清除所有缓存音频，下次导出重新合成">
        <a-button @click="$emit('clear-cache')">清除缓存</a-button>
      </a-tooltip>
    </a-space>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import VoiceProfileIdField from './VoiceProfileIdField.vue'

const props = defineProps({
  title: { type: String, required: true },
  saving: Boolean,
  exporting: Boolean,
  defaultVoiceProfileId: { type: [Number, String, null], default: null },
  voiceProfiles: { type: Array, default: () => [] },
})
const emit = defineEmits(['update:title', 'update:defaultVoiceProfileId', 'save', 'export', 'import-text', 'auto-layout', 'voice-profile-created', 'clear-cache'])
const localTitle = ref(props.title)

watch(() => props.title, value => {
  localTitle.value = value
})

const emitTitle = () => emit('update:title', localTitle.value || '未命名配音工程')
</script>

<style scoped>
.workflow-toolbar { display: flex; align-items: center; justify-content: space-between; gap: 14px; height: 100%; }
.title-block { display: flex; align-items: center; gap: 10px; }
.title-input { width: 260px; font-weight: 650; }
.save-state { color: var(--text-muted); font-size: 12px; }
.default-voice { display: flex; align-items: center; gap: 8px; min-width: 260px; }
.default-voice-label { color: var(--text-muted); font-size: 12px; white-space: nowrap; }
.default-voice :deep(.voice-profile-id-field) { flex: 1; }
</style>
