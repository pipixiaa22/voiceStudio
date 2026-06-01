<template>
  <a-modal
    :open="open"
    title="生成视频"
    @update:open="$emit('update:open', $event)"
    :footer="null"
    width="680px"
    :destroy-on-close="true"
  >
    <a-steps :current="currentStep" size="small" style="margin-bottom: 24px">
      <a-step title="模板" />
      <a-step title="画面" />
      <a-step title="音色" />
      <a-step title="音频" />
      <a-step title="预览" />
      <a-step title="生成" />
    </a-steps>

    <a-alert
      v-if="!hasTtsKey"
      type="warning"
      show-icon
      style="margin-bottom: 16px"
    >
      <template #message>
        <span>视频旁白生成需要 MiMo TTS API Key。</span>
        <a-button type="link" size="small" @click="handleOpenSettings">去设置</a-button>
      </template>
    </a-alert>

    <div class="step-content">
      <VideoTemplateStep
        v-if="currentStep === 0"
        v-model:selected-template="selectedTemplate"
        :preferred-template-key="prefill?.template_key"
        @next="currentStep = 1"
      />
      <ScenePlannerStep
        v-if="currentStep === 1"
        v-model:scenes="scenes"
        :subtitle-count="subtitleCount"
        @prev="currentStep = 0"
        @next="currentStep = 2"
      />
      <SpeakerVoiceStep
        v-if="currentStep === 2"
        v-model:speaker-profiles="speakerProfiles"
        :content="textContent"
        @prev="currentStep = 1"
        @next="currentStep = 3"
      />
      <AudioMixStep
        v-if="currentStep === 3"
        v-model:audio-options="audioOptions"
        @prev="currentStep = 2"
        @next="currentStep = 4"
      />
      <VideoPreviewStep
        v-if="currentStep === 4"
        :selected-template="selectedTemplate"
        :scenes="scenes"
        :speaker-profiles="speakerProfiles"
        :audio-options="audioOptions"
        @prev="currentStep = 3"
        @generate="handleGenerate"
      />
      <VideoJobProgress
        v-if="currentStep === 5"
        :job-id="currentJobId"
        @done="handleDone"
        @retry="currentStep = 4"
      />
    </div>
  </a-modal>
</template>

<script setup>
import { ref, watch } from 'vue'
import { message } from 'ant-design-vue'
import { videoApi } from '../../api'
import { useSettings } from '../../stores/settings'
import VideoTemplateStep from './VideoTemplateStep.vue'
import ScenePlannerStep from './ScenePlannerStep.vue'
import SpeakerVoiceStep from './SpeakerVoiceStep.vue'
import AudioMixStep from './AudioMixStep.vue'
import VideoPreviewStep from './VideoPreviewStep.vue'
import VideoJobProgress from './VideoJobProgress.vue'

const props = defineProps({
  open: Boolean,
  textId: { type: Number, required: true },
  textTitle: { type: String, default: '视频' },
  textContent: { type: String, default: '' },
  subtitleCount: { type: Number, default: 0 },
  prefill: { type: Object, default: null },
})

const emit = defineEmits(['update:open'])

const { llmKey, ttsKey, hasTtsKey } = useSettings()

const handleOpenSettings = () => {
  window.dispatchEvent(new CustomEvent('open-settings'))
}

const currentStep = ref(0)
const selectedTemplate = ref(null)
const scenes = ref([])
const speakerProfiles = ref({})
const audioOptions = ref({
  voice_source: props.prefill?.audio_options?.voice_source || 'generate',
  voice_workflow_id: props.prefill?.audio_options?.voice_workflow_id || null,
  bgm_path: props.prefill?.audio_options?.bgm_path || null,
  bgm_enabled: false,
  bgm_volume: 0.18,
  bgm_fade_in: 1.0,
  bgm_fade_out: 1.5,
  ambient_enabled: false,
  ambient_key: 'wind',
  ambient_volume: 0.12,
})
const currentJobId = ref(null)

watch(() => props.open, (val) => {
  if (val) {
    currentStep.value = 0
    currentJobId.value = null
    selectedTemplate.value = null
    audioOptions.value = {
      voice_source: props.prefill?.audio_options?.voice_source || 'generate',
      voice_workflow_id: props.prefill?.audio_options?.voice_workflow_id || null,
      bgm_path: props.prefill?.audio_options?.bgm_path || null,
      bgm_enabled: props.prefill?.audio_options?.bgm_enabled ?? false,
      bgm_volume: props.prefill?.audio_options?.bgm_volume ?? 0.18,
      bgm_fade_in: props.prefill?.audio_options?.bgm_fade_in ?? 1.0,
      bgm_fade_out: props.prefill?.audio_options?.bgm_fade_out ?? 1.5,
      ambient_enabled: props.prefill?.audio_options?.ambient_enabled ?? false,
      ambient_key: props.prefill?.audio_options?.ambient_key ?? 'wind',
      ambient_volume: props.prefill?.audio_options?.ambient_volume ?? 0.12,
    }
  }
})

const handleGenerate = async () => {
  if (!ttsKey.value) {
    message.error('请先配置 TTS API Key')
    return
  }

  try {
    // Upload images first
    const uploadedScenes = []
    for (const scene of scenes.value) {
      if (scene.imageFile) {
        const formData = new FormData()
        formData.append('image', scene.imageFile)
        const uploadRes = await videoApi.uploadImage(formData)
        uploadedScenes.push({
          ...scene,
          imagePath: uploadRes.data.path,
          imageFile: undefined,
        })
      } else {
        uploadedScenes.push(scene)
      }
    }

    const response = await videoApi.createJob({
      text_id: props.textId,
      title: props.textTitle,
      template_key: selectedTemplate.value?.template_key || 'xianxia_narration',
      scenes: uploadedScenes,
      speaker_profiles: speakerProfiles.value,
      audio_options: audioOptions.value,
      voice_source: audioOptions.value.voice_source || 'generate',
      voice_workflow_id: audioOptions.value.voice_workflow_id || null,
      subtitle_options: props.prefill?.subtitle_options || undefined,
      voice_description: props.prefill?.voice_description,
      source_context: props.prefill?.source_context,
      api_key: ttsKey.value,
    })

    currentJobId.value = response.data.job_id
    currentStep.value = 5
  } catch (error) {
    message.error(error.response?.data?.error || '创建任务失败')
  }
}

const handleDone = () => {
  message.success('视频生成完成')
  emit('update:open', false)
}
</script>

<style scoped>
.step-content {
  min-height: 300px;
}
</style>
