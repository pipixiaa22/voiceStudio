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
    </div>

    <div v-else class="speaker-list">
      <div v-for="speaker in speakers" :key="speaker" class="speaker-item">
        <div class="speaker-name">
          <span class="speaker-tag">{{ speaker }}</span>
        </div>
        <div class="speaker-voice">
          <a-select
            :value="localProfiles[speaker]"
            @change="(val) => updateProfile(speaker, val)"
            placeholder="选择音色档案"
            style="width: 100%"
            allow-clear
          >
            <a-select-option v-for="profile in voiceProfiles" :key="profile.id" :value="profile.id">
              {{ profile.name }}
            </a-select-option>
          </a-select>
        </div>
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

const props = defineProps({
  speakerProfiles: { type: Object, default: () => ({}) },
  content: { type: String, default: '' },
})

const emit = defineEmits(['update:speakerProfiles', 'prev', 'next'])

const localProfiles = ref({ ...props.speakerProfiles })
const voiceProfiles = ref([])

const speakers = computed(() => {
  const regex = /【([^】]+)】/g
  const found = new Set()
  let match
  while ((match = regex.exec(props.content)) !== null) {
    found.add(match[1])
  }
  return Array.from(found)
})

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

const updateProfile = (speaker, profileId) => {
  if (profileId) {
    localProfiles.value[speaker] = profileId
  } else {
    delete localProfiles.value[speaker]
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
}

.speaker-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.speaker-item {
  display: flex;
  align-items: center;
  gap: 16px;
}

.speaker-name {
  min-width: 80px;
}

.speaker-tag {
  background: var(--primary-bg, #e6f7ff);
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 13px;
}

.speaker-voice {
  flex: 1;
}

.step-actions {
  display: flex;
  justify-content: space-between;
  margin-top: 16px;
}
</style>
