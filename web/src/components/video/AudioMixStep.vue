<template>
  <div class="audio-step">
    <h4>音频设置</h4>

    <a-form layout="vertical">
      <a-divider orientation="left">旁白来源</a-divider>

      <a-form-item>
        <a-radio-group v-model:value="localOptions.voice_source" button-style="solid">
          <a-radio-button value="generate">实时生成</a-radio-button>
          <a-radio-button value="workflow">配音工程</a-radio-button>
        </a-radio-group>
      </a-form-item>

      <template v-if="localOptions.voice_source === 'workflow'">
        <a-form-item label="选择配音工程">
          <a-select
            v-model:value="localOptions.voice_workflow_id"
            placeholder="选择一个配音工程"
            show-search
            :filter-option="filterWorkflowOption"
            style="width: 100%"
          >
            <a-select-option v-for="wf in workflows" :key="wf.id" :value="wf.id">
              {{ wf.title }} ({{ wf.updated_at?.slice(0, 10) }})
            </a-select-option>
          </a-select>
        </a-form-item>
      </template>

      <a-divider orientation="left">背景音乐 (BGM)</a-divider>

      <a-form-item>
        <a-switch v-model:checked="localOptions.bgm_enabled" checked-children="开启" un-checked-children="关闭" />
      </a-form-item>

      <template v-if="localOptions.bgm_enabled">
        <a-form-item label="BGM 文件">
          <a-upload
            :before-upload="handleBgmUpload"
            :show-upload-list="false"
            accept=".wav"
          >
            <a-button>
              {{ bgmFile ? '更换 BGM' : '上传 BGM' }}
            </a-button>
          </a-upload>
          <span v-if="bgmFile" class="file-name">{{ bgmFile.name }}</span>
        </a-form-item>

        <a-form-item label="BGM 音量">
          <a-slider
            v-model:value="localOptions.bgm_volume"
            :min="0"
            :max="1"
            :step="0.01"
            :tip-formatter="(v) => `${Math.round(v * 100)}%`"
          />
        </a-form-item>

        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="淡入">
              <a-input-number v-model:value="localOptions.bgm_fade_in" :min="0" :max="5" :step="0.1" style="width: 100%" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="淡出">
              <a-input-number v-model:value="localOptions.bgm_fade_out" :min="0" :max="5" :step="0.1" style="width: 100%" />
            </a-form-item>
          </a-col>
        </a-row>
      </template>

      <a-divider orientation="left">环境音</a-divider>

      <a-form-item>
        <a-switch v-model:checked="localOptions.ambient_enabled" checked-children="开启" un-checked-children="关闭" />
      </a-form-item>

      <template v-if="localOptions.ambient_enabled">
        <a-form-item label="环境音类型">
          <a-select v-model:value="localOptions.ambient_key" style="width: 100%">
            <a-select-option value="wind">风声</a-select-option>
            <a-select-option value="rain">雨声</a-select-option>
            <a-select-option value="thunder">雷声</a-select-option>
            <a-select-option value="sword">剑鸣</a-select-option>
            <a-select-option value="bell">钟声</a-select-option>
            <a-select-option value="fire">火焰声</a-select-option>
          </a-select>
        </a-form-item>

        <a-form-item label="环境音音量">
          <a-slider
            v-model:value="localOptions.ambient_volume"
            :min="0"
            :max="1"
            :step="0.01"
            :tip-formatter="(v) => `${Math.round(v * 100)}%`"
          />
        </a-form-item>
      </template>
    </a-form>

    <div class="step-actions">
      <a-button @click="$emit('prev')">上一步</a-button>
      <a-button type="primary" @click="handleNext">下一步</a-button>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { videoApi, voiceWorkflowsApi } from '../../api'

const props = defineProps({
  audioOptions: { type: Object, default: () => ({}) },
})

const emit = defineEmits(['update:audioOptions', 'prev', 'next'])

const localOptions = ref({
  voice_source: 'generate',
  voice_workflow_id: null,
  bgm_path: null,
  ...props.audioOptions,
})
const bgmFile = ref(null)
const workflows = ref([])

watch(() => props.audioOptions, (val) => {
  localOptions.value = { voice_source: 'generate', voice_workflow_id: null, bgm_path: null, ...val }
})

onMounted(async () => {
  try {
    const { data } = await voiceWorkflowsApi.list()
    workflows.value = data
  } catch {
    workflows.value = []
  }
})

const filterWorkflowOption = (input, option) => {
  return option.children[0].children.toLowerCase().includes(input.toLowerCase())
}

const handleBgmUpload = async (file) => {
  if (!file.name?.toLowerCase().endsWith('.wav')) {
    message.error('第一阶段只支持 WAV 格式 BGM')
    return false
  }

  try {
    const formData = new FormData()
    formData.append('audio', file)
    const { data } = await videoApi.uploadAudio(formData)
    bgmFile.value = file
    localOptions.value.bgm_path = data.path
    emit('update:audioOptions', { ...localOptions.value })
    message.success('BGM 上传成功')
  } catch (error) {
    message.error(error.response?.data?.error || 'BGM 上传失败')
  }

  return false
}

const handleNext = () => {
  if (localOptions.value.voice_source === 'workflow' && !localOptions.value.voice_workflow_id) {
    message.error('请选择配音工程')
    return
  }
  if (localOptions.value.bgm_enabled && !localOptions.value.bgm_path) {
    message.error('请先上传 BGM 文件')
    return
  }
  emit('update:audioOptions', { ...localOptions.value })
  emit('next')
}
</script>

<style scoped>
.audio-step h4 {
  margin-bottom: 16px;
}

.file-name {
  margin-left: 8px;
  font-size: 13px;
  color: var(--text-secondary, #999);
}

.step-actions {
  display: flex;
  justify-content: space-between;
  margin-top: 16px;
}
</style>
