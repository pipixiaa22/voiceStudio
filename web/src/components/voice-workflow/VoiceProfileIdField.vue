<template>
  <div class="voice-profile-id-field">
    <a-select
      :value="selectValue"
      :placeholder="placeholder"
      show-search
      allow-clear
      :filter-option="filterProfileOption"
      style="flex: 1"
      @change="handleChange"
    >
      <a-select-option v-if="allowFollowDefault" value="__default__">
        {{ defaultProfile ? `跟随默认：${defaultProfile.name}` : '跟随工程默认音色' }}
      </a-select-option>
      <a-select-option
        v-for="profile in profiles"
        :key="profile.id"
        :value="profile.id"
      >
        {{ profile.name }}
      </a-select-option>
    </a-select>
    <a-tooltip v-if="canCreate" title="新建音色档案">
      <a-button size="small" class="create-btn" @click="showDrawer = true">+</a-button>
    </a-tooltip>
    <a-button
      v-if="allowFollowDefault && modelValue != null"
      size="small"
      type="link"
      class="reset-btn"
      @click="handleChange('__default__')"
    >
      恢复默认
    </a-button>
    <VoiceProfileDrawer
      v-if="canCreate"
      :open="showDrawer"
      :initial-values="createInitialValues"
      @update:open="showDrawer = $event"
      @created="handleCreated"
    />
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { findVoiceProfile, normalizeVoiceProfileId } from '../../utils/voiceWorkflowProfiles'
import VoiceProfileDrawer from '../VoiceProfileDrawer.vue'

const props = defineProps({
  modelValue: { type: [Number, String, null], default: null },
  profiles: { type: Array, default: () => [] },
  defaultVoiceProfileId: { type: [Number, String, null], default: null },
  allowFollowDefault: { type: Boolean, default: false },
  placeholder: { type: String, default: '选择音色档案' },
  canCreate: { type: Boolean, default: false },
  createInitialValues: { type: Object, default: () => ({}) },
})

const emit = defineEmits(['update:modelValue', 'change', 'created'])

const showDrawer = ref(false)

const defaultProfile = computed(() => findVoiceProfile(props.profiles, props.defaultVoiceProfileId))
const selectValue = computed(() => {
  if (props.allowFollowDefault && props.modelValue == null) return '__default__'
  return props.modelValue ?? undefined
})

const filterProfileOption = (input, option) => {
  const text = String(option?.children?.[0]?.children || option?.label || '').toLowerCase()
  return text.includes(input.toLowerCase())
}

const handleChange = value => {
  const nextValue = value === '__default__' ? null : normalizeVoiceProfileId(value)
  emit('update:modelValue', nextValue)
  emit('change', nextValue)
}

const handleCreated = profile => {
  showDrawer.value = false
  emit('created', profile)
  emit('update:modelValue', profile.id)
  emit('change', profile.id)
}
</script>

<style scoped>
.voice-profile-id-field {
  display: flex;
  align-items: center;
  gap: 6px;
}
.create-btn {
  flex-shrink: 0;
  font-weight: 700;
  line-height: 1;
}
.reset-btn {
  flex-shrink: 0;
  padding: 0;
}
</style>
