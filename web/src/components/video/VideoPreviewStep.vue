<template>
  <div class="preview-step">
    <h4>生成预览</h4>

    <a-descriptions :column="1" bordered size="small">
      <a-descriptions-item label="模板">
        {{ selectedTemplate?.name || '未选择' }}
      </a-descriptions-item>
      <a-descriptions-item label="画面比例">
        {{ aspectRatioLabel }}
      </a-descriptions-item>
      <a-descriptions-item label="分镜数量">
        {{ scenes.length }} 个
      </a-descriptions-item>
      <a-descriptions-item label="角色绑定">
        <span v-if="Object.keys(speakerProfiles).length === 0">无（使用默认音色）</span>
        <span v-else>
          <a-tag v-for="(profileId, speaker) in speakerProfiles" :key="speaker">
            {{ speaker }}
          </a-tag>
        </span>
      </a-descriptions-item>
      <a-descriptions-item label="音频来源">
        {{ audioOptions.voice_source === 'workflow' ? (audioOptions.voice_workflow_id ? `配音工程 #${audioOptions.voice_workflow_id}` : '配音工程未选择') : '实时生成' }}
      </a-descriptions-item>
      <a-descriptions-item label="BGM">
        {{ audioOptions.bgm_enabled ? '开启' : '关闭' }}
        <span v-if="audioOptions.bgm_enabled"> ({{ Math.round(audioOptions.bgm_volume * 100) }}%)</span>
      </a-descriptions-item>
      <a-descriptions-item label="环境音">
        {{ audioOptions.ambient_enabled ? AMBIENT_NAMES[audioOptions.ambient_key] || '开启' : '关闭' }}
        <span v-if="audioOptions.ambient_enabled"> ({{ Math.round(audioOptions.ambient_volume * 100) }}%)</span>
      </a-descriptions-item>
    </a-descriptions>

    <a-alert
      v-if="scenes.some(s => !s.imageFile)"
      type="warning"
      message="部分分镜未上传图片，将使用默认背景"
      style="margin-top: 16px"
      show-icon
    />

    <div class="step-actions">
      <a-button @click="$emit('prev')">上一步</a-button>
      <a-button type="primary" @click="$emit('generate')">开始生成</a-button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  selectedTemplate: Object,
  aspectRatio: { type: String, default: '9:16' },
  scenes: { type: Array, default: () => [] },
  speakerProfiles: { type: Object, default: () => ({}) },
  audioOptions: { type: Object, default: () => ({}) },
})

defineEmits(['prev', 'generate'])

const AMBIENT_NAMES = {
  wind: '风声',
  rain: '雨声',
  thunder: '雷声',
  sword: '剑鸣',
  bell: '钟声',
  fire: '火焰声',
}

const ASPECT_RATIO_LABELS = {
  '9:16': '抖音短视频 9:16（1080x1920）',
  '16:9': 'B站横屏 16:9（1920x1080）',
  '1:1': '方形通用 1:1（1080x1080）',
}

const aspectRatioLabel = computed(() => ASPECT_RATIO_LABELS[props.aspectRatio] || props.aspectRatio)
</script>

<style scoped>
.preview-step h4 {
  margin-bottom: 16px;
}

.step-actions {
  display: flex;
  justify-content: space-between;
  margin-top: 16px;
}
</style>
