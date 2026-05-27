<template>
  <div class="progress-step">
    <h4>{{ job?.status === 'completed' ? '视频生成完成' : '视频生成中' }}</h4>

    <div v-if="job" class="progress-content">
      <!-- Progress bar (hidden when completed) -->
      <template v-if="job.status !== 'completed'">
        <a-progress :percent="Math.round(job.progress * 100)" :status="progressStatus" />
        <div class="progress-info">
          <a-tag :color="statusColor">{{ statusLabel }}</a-tag>
          <span v-if="job.message" class="progress-message">{{ job.message }}</span>
        </div>
      </template>

      <!-- Video preview when completed -->
      <div v-if="job.status === 'completed' && job.has_video" class="video-preview">
        <video
          ref="videoPlayer"
          :src="`/api/video/jobs/${jobId}/preview`"
          controls
          preload="metadata"
          class="video-player"
        />
      </div>

      <!-- Action buttons when completed -->
      <div v-if="job.status === 'completed'" class="completed-actions">
        <a-space direction="vertical" :size="12" style="width: 100%">
          <a-space>
            <a-button type="primary" @click="handleDownloadVideo">
              下载视频
            </a-button>
            <a-button @click="handleDownloadPackage">
              下载素材包
            </a-button>
          </a-space>
          <a-space>
            <a-button @click="$emit('done')">完成</a-button>
            <a-button @click="$emit('retry')">重新生成</a-button>
          </a-space>
        </a-space>
      </div>

      <!-- Failed state -->
      <div v-if="job.status === 'failed'" class="failed-actions">
        <a-alert type="error" :message="job.error_message || '生成失败'" style="margin-bottom: 16px" />
        <a-button @click="$emit('retry')">重试</a-button>
      </div>
    </div>

    <div v-else class="loading">
      <a-spin tip="正在创建任务..." />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { videoApi } from '../../api'

const props = defineProps({
  jobId: String,
})

const emit = defineEmits(['done', 'retry'])

const job = ref(null)
const videoPlayer = ref(null)
let pollTimer = null

const handleDownloadVideo = () => {
  if (!props.jobId) return
  const url = `/api/video/jobs/${props.jobId}/download-video`
  const link = document.createElement('a')
  link.href = url
  link.download = `${job.value?.title || '视频'}.mp4`
  link.click()
}

const handleDownloadPackage = () => {
  if (!props.jobId) return
  const url = `/api/video/jobs/${props.jobId}/download`
  const link = document.createElement('a')
  link.href = url
  link.download = `${job.value?.title || '视频'}_素材包.zip`
  link.click()
}

const STATUS_LABELS = {
  queued: '排队中',
  planning: '规划中',
  synthesizing_voice: '合成语音',
  mixing_audio: '混合音频',
  rendering_video: '渲染视频',
  packaging: '打包中',
  completed: '已完成',
  failed: '失败',
}

const STATUS_COLORS = {
  queued: 'default',
  planning: 'processing',
  synthesizing_voice: 'processing',
  mixing_audio: 'processing',
  rendering_video: 'processing',
  packaging: 'processing',
  completed: 'success',
  failed: 'error',
}

const statusLabel = computed(() => STATUS_LABELS[job.value?.status] || job.value?.status)
const statusColor = computed(() => STATUS_COLORS[job.value?.status] || 'default')

const progressStatus = computed(() => {
  if (job.value?.status === 'completed') return 'success'
  if (job.value?.status === 'failed') return 'exception'
  return 'active'
})

const pollJob = async () => {
  if (!props.jobId) return

  try {
    const response = await videoApi.getJob(props.jobId)
    job.value = response.data

    if (job.value.status === 'completed' || job.value.status === 'failed') {
      clearInterval(pollTimer)
    }
  } catch (error) {
    console.error('查询任务状态失败:', error)
  }
}

onMounted(() => {
  pollJob()
  pollTimer = setInterval(pollJob, 2000)
})

onUnmounted(() => {
  if (pollTimer) {
    clearInterval(pollTimer)
  }
})

watch(() => props.jobId, () => {
  if (pollTimer) clearInterval(pollTimer)
  pollJob()
  pollTimer = setInterval(pollJob, 2000)
})
</script>

<style scoped>
.progress-step h4 {
  margin-bottom: 16px;
}

.progress-content {
  padding: 16px 0;
}

.progress-info {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
}

.progress-message {
  color: var(--text-secondary, #999);
  font-size: 13px;
}

.video-preview {
  margin: 16px 0;
  border-radius: 8px;
  overflow: hidden;
  background: #000;
}

.video-player {
  width: 100%;
  max-height: 400px;
  display: block;
}

.completed-actions {
  margin-top: 16px;
  text-align: center;
}

.failed-actions {
  margin-top: 16px;
  text-align: center;
}

.loading {
  display: flex;
  justify-content: center;
  padding: 48px 0;
}
</style>
