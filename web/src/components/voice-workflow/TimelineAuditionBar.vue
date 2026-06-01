<template>
  <div class="timeline-bar">
    <div class="timeline-actions">
      <span>{{ segments.length }} 句旁白</span>
      <a-space>
        <a-button :loading="preflightLoading" @click="$emit('preflight')">导出前检查</a-button>
        <a-button :loading="regenerateLoading" @click="$emit('regenerate-missing')">生成缺失音频</a-button>
        <a-button :loading="auditionSelectedLoading" @click="$emit('audition-selected')">试听选中</a-button>
        <a-button :loading="auditionPathLoading" @click="$emit('audition-path')">
          {{ pathAudioUrl ? '重新生成整条试听' : '生成整条试听' }}
        </a-button>
        <a-button @click="$emit('export')">导出同步包</a-button>
      </a-space>
    </div>
    <div v-if="preflight" class="preflight-panel" :class="{ ok: preflight.ok }">
      <div class="preflight-summary">
        <strong>{{ preflight.ok ? '可导出' : '需要处理' }}</strong>
        <span>{{ preflight.ready_count }}/{{ preflight.segment_count }} 段已缓存</span>
        <span v-if="preflight.missing_count">{{ preflight.missing_count }} 段待生成</span>
      </div>
      <div v-if="preflight.issues?.length" class="preflight-lines">
        <span v-for="issue in preflight.issues.slice(0, 3)" :key="`${issue.code}-${issue.segment_id || issue.message}`">
          {{ issue.message }}
        </span>
      </div>
      <div v-else-if="preflight.warnings?.length" class="preflight-lines">
        <span v-for="warning in preflight.warnings.slice(0, 2)" :key="warning.code">
          {{ warning.message }}
        </span>
      </div>
    </div>
    <div v-if="pathAudioUrl" class="path-player">
      <div class="path-player-meta">
        <span>整条路径试听</span>
        <span v-if="pathDuration">{{ pathDuration }}s</span>
      </div>
      <audio :src="pathAudioUrl" controls preload="metadata" class="path-audio" />
    </div>
    <div class="timeline-track">
      <button
        v-for="segment in segments"
        :key="segment.id"
        class="timeline-segment"
        :class="{ active: String(segment.id) === String(selectedSegmentId), ready: segment.audio_status === 'ready', failed: segment.audio_status === 'failed' }"
        @click="$emit('select', segment.id)"
      >
        <span class="timeline-main">{{ segment.order_index }} · {{ segment.emotion }}</span>
        <span class="timeline-meta">
          {{ statusLabel(segment.audio_status) }}
          <template v-if="timelineMeta(segment.id)"> · {{ timelineMeta(segment.id) }}</template>
        </span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  segments: { type: Array, default: () => [] },
  selectedSegmentId: { type: [Number, String], default: null },
  auditionSelectedLoading: { type: Boolean, default: false },
  auditionPathLoading: { type: Boolean, default: false },
  preflightLoading: { type: Boolean, default: false },
  regenerateLoading: { type: Boolean, default: false },
  pathAudioUrl: { type: String, default: '' },
  pathDuration: { type: [Number, String], default: null },
  pathTimeline: { type: Array, default: () => [] },
  preflight: { type: Object, default: null },
})
defineEmits(['select', 'audition-selected', 'audition-path', 'export', 'preflight', 'regenerate-missing'])

const timelineBySegment = computed(() => {
  const map = new Map()
  for (const item of props.pathTimeline) {
    const key = String(item.segment_id)
    const existing = map.get(key)
    if (!existing) {
      map.set(key, { start: item.start, end: item.end })
    } else {
      existing.end = item.end
    }
  }
  return map
})

const statusLabel = status => {
  if (status === 'ready') return '已缓存'
  if (status === 'failed') return '失败'
  if (status === 'generating') return '生成中'
  return '未生成'
}

const timelineMeta = segmentId => {
  const item = timelineBySegment.value.get(String(segmentId))
  if (!item) return ''
  return `${item.start.toFixed(1)}-${item.end.toFixed(1)}s`
}
</script>

<style scoped>
.timeline-bar { height: 100%; display: flex; flex-direction: column; gap: var(--space-sm); }
.timeline-actions { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.preflight-panel { border: 1px solid rgba(250, 140, 22, 0.35); background: rgba(250, 140, 22, 0.08); border-radius: var(--radius-sm); padding: 8px 10px; display: flex; flex-direction: column; gap: 4px; }
.preflight-panel.ok { border-color: rgba(82, 196, 26, 0.35); background: rgba(82, 196, 26, 0.08); }
.preflight-summary { display: flex; align-items: center; gap: 10px; font-size: 12px; }
.preflight-lines { display: flex; flex-wrap: wrap; gap: 8px; color: var(--text-muted); font-size: 11px; }
.path-player { display: grid; grid-template-columns: 120px minmax(180px, 1fr); align-items: center; gap: 10px; }
.path-player-meta { display: flex; flex-direction: column; gap: 2px; color: var(--text-muted); font-size: 12px; }
.path-audio { width: 100%; height: 32px; }
.timeline-track { display: grid; grid-auto-flow: column; grid-auto-columns: minmax(140px, 1fr); gap: 6px; overflow-x: auto; }
.timeline-segment { border: 1px solid var(--surface-border); background: var(--surface-muted); border-radius: var(--radius-sm); padding: 8px 9px; cursor: pointer; display: flex; flex-direction: column; align-items: flex-start; gap: 3px; min-height: 50px; }
.timeline-segment.active { border-color: var(--text-primary); background: var(--surface-active); }
.timeline-segment.ready { border-color: rgba(82, 196, 26, 0.5); }
.timeline-segment.failed { border-color: rgba(207, 19, 34, 0.6); }
.timeline-main { font-weight: 600; }
.timeline-meta { color: var(--text-muted); font-size: 11px; }

@media (max-width: 860px) {
  .timeline-actions { align-items: flex-start; flex-direction: column; }
}
</style>
