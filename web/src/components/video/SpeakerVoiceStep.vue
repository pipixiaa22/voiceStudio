<template>
  <div class="speaker-step">
    <h4>角色声线绑定</h4>
    <p class="hint">系统已从文本中识别出以下角色，请为每个角色选择音色档案。</p>

    <div v-if="speakers.length === 0" class="no-speakers">
      <a-empty description="未检测到角色标注">
        <template #description>
          <span>文本中未发现【角色】格式的标注，将使用默认音色。</span>
        </template>
      </a-empty>
      <div class="default-voice">
        <span class="default-label">默认音色</span>
        <VoiceProfileSelector
          :model-value="defaultProfile"
          @update:model-value="handleDefaultProfileChange"
        />
      </div>
    </div>

    <div v-else class="speaker-list">
      <div v-for="speaker in speakers" :key="speaker" class="speaker-item">
        <div class="speaker-header">
          <span class="speaker-tag">{{ speaker }}</span>
          <a-tag v-if="speaker === '旁白'" color="orange">默认</a-tag>
        </div>
        <VoiceProfileSelector
          :model-value="localProfiles[speaker] ? findProfileById(localProfiles[speaker]) : null"
          @update:model-value="(profile) => updateProfile(speaker, profile)"
        />
      </div>
    </div>

    <div class="step-actions">
      <a-button @click="$emit('prev')">上一步</a-button>
      <a-button type="primary" @click="handleNext">下一步</a-button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { voiceProfilesApi } from '../../api'
import VoiceProfileSelector from '../VoiceProfileSelector.vue'

const props = defineProps({
  speakerProfiles: { type: Object, default: () => ({}) },
  content: { type: String, default: '' },
})

const emit = defineEmits(['update:speakerProfiles', 'prev', 'next'])

const localProfiles = ref({ ...props.speakerProfiles })
const voiceProfiles = ref([])
const defaultProfile = ref(null)

const speakers = computed(() => {
  const regex = /【([^】]+)】/g
  const found = new Set()
  let match
  while ((match = regex.exec(props.content)) !== null) {
    found.add(match[1])
  }
  return Array.from(found)
})

const findProfileById = (id) => {
  return voiceProfiles.value.find(p => p.id === id) || null
}

watch(() => props.speakerProfiles, (val) => {
  localProfiles.value = { ...val }
})

onMounted(async () => {
  try {
    const response = await voiceProfilesApi.list()
    voiceProfiles.value = response.data
  } catch (error) {
    console.error('加载音色档案失败:', error)
  }
})

const updateProfile = (speaker, profile) => {
  if (profile) {
    localProfiles.value[speaker] = profile.id
  } else {
    delete localProfiles.value[speaker]
  }
}

const handleDefaultProfileChange = (profile) => {
  defaultProfile.value = profile
  if (profile) {
    localProfiles.value['旁白'] = profile.id
  }
}

const handleNext = () => {
  emit('update:speakerProfiles', localProfiles.value)
  emit('next')
}
</script>

<style scoped>
.speaker-step h4 {
  margin-bottom: 8px;
}

.hint {
  color: var(--text-secondary, #999);
  font-size: 13px;
  margin-bottom: 16px;
}

.no-speakers {
  padding: 24px 0;
  text-align: center;
}

.default-voice {
  margin-top: 24px;
  text-align: left;
}

.default-label {
  display: block;
  font-size: 13px;
  color: var(--text-secondary, #999);
  margin-bottom: 8px;
}

.speaker-list {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.speaker-item {
  padding: 16px;
  background: var(--paper-soft, #fafafa);
  border: 1px solid var(--surface-border, #e8e8e8);
  border-radius: 8px;
}

.speaker-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.speaker-tag {
  background: var(--primary-bg, #e6f7ff);
  padding: 2px 10px;
  border-radius: 4px;
  font-size: 14px;
  font-weight: 500;
}

.step-actions {
  display: flex;
  justify-content: space-between;
  margin-top: 24px;
}
</style>
