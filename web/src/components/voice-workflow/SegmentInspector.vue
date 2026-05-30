<template>
  <div class="segment-inspector" v-if="segment">
    <div class="panel-title">语句参数</div>
    <a-form layout="vertical">
      <a-form-item label="文本">
        <a-textarea :value="segment.text" @update:value="patch({ text: $event })" :autoSize="{ minRows: 3, maxRows: 6 }" />
      </a-form-item>
      <a-form-item label="本句音色">
        <VoiceProfileIdField
          :model-value="segment.voice_profile_id"
          :profiles="voiceProfiles"
          :default-voice-profile-id="defaultVoiceProfileId"
          allow-follow-default
          can-create
          :create-initial-values="{ audition_text: segment.text, scene: 'short_video' }"
          @update:model-value="value => patch({ voice_profile_id: value })"
          @created="$emit('profile-created', $event)"
        />
      </a-form-item>
      <a-form-item label="情绪">
        <a-select :value="segment.emotion" @change="value => patch({ emotion: value })">
          <a-select-option value="neutral">中性</a-select-option>
          <a-select-option value="calm">平静</a-select-option>
          <a-select-option value="suppressed">压抑</a-select-option>
          <a-select-option value="angry_burst">爆发愤怒</a-select-option>
          <a-select-option value="sad">悲伤</a-select-option>
          <a-select-option value="cold">冷漠</a-select-option>
          <a-select-option value="excited">兴奋</a-select-option>
          <a-select-option value="whisper">耳语</a-select-option>
        </a-select>
      </a-form-item>
      <a-form-item label="强度">
        <a-slider :value="segment.intensity" :min="0" :max="2" :step="0.05" @change="value => patch({ intensity: value })" />
      </a-form-item>
      <a-form-item label="语速">
        <a-slider :value="segment.rate" :min="0.5" :max="2" :step="0.05" @change="value => patch({ rate: value })" />
      </a-form-item>
      <a-form-item label="音高">
        <a-slider :value="segment.pitch" :min="-12" :max="12" :step="1" @change="value => patch({ pitch: value })" />
      </a-form-item>
      <a-form-item label="音量 dB">
        <a-slider :value="segment.volume_db" :min="-12" :max="12" :step="1" @change="value => patch({ volume_db: value })" />
      </a-form-item>
      <div class="pause-grid">
        <a-form-item label="段前 ms">
          <a-input-number :value="segment.pause_before_ms" :min="0" :max="10000" @change="value => patch({ pause_before_ms: value })" />
        </a-form-item>
        <a-form-item label="段后 ms">
          <a-input-number :value="segment.pause_after_ms" :min="0" :max="10000" @change="value => patch({ pause_after_ms: value })" />
        </a-form-item>
      </div>
      <a-form-item label="转场">
        <a-select :value="segment.transition" @change="value => patch({ transition: value })">
          <a-select-option value="normal">正常</a-select-option>
          <a-select-option value="burst">爆发</a-select-option>
        </a-select>
      </a-form-item>
      <a-form-item label="表演指令">
        <a-textarea
          :value="segment.delivery_instruction"
          @update:value="patch({ delivery_instruction: $event })"
          placeholder="补充表演要求，例如：语气温柔但坚定"
          :autoSize="{ minRows: 2, maxRows: 4 }"
        />
      </a-form-item>
      <a-button block :loading="auditionLoading" @click="$emit('audition', segment)">试听这一句</a-button>
    </a-form>
  </div>
  <div v-else class="empty-inspector">选择一个语句节点</div>
</template>

<script setup>
import VoiceProfileIdField from './VoiceProfileIdField.vue'

const props = defineProps({
  segment: { type: Object, default: null },
  voiceProfiles: { type: Array, default: () => [] },
  defaultVoiceProfileId: { type: [Number, String, null], default: null },
  auditionLoading: { type: Boolean, default: false },
})
const emit = defineEmits(['update', 'audition', 'profile-created'])
const patch = patch => emit('update', props.segment.id, patch)
</script>

<style scoped>
.panel-title { font-weight: 650; margin-bottom: var(--space-sm); }
.pause-grid { display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-sm); }
.empty-inspector { color: var(--text-muted); }
</style>
