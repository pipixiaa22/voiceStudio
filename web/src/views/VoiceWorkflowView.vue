<template>
  <div class="voice-workflow-view">
    <div class="workflow-loading" v-if="store.loading">加载中</div>
    <div v-else class="workflow-shell">
      <div class="workflow-top">
        <WorkflowToolbar
          :title="store.workflow.title"
          :saving="store.saving"
          :exporting="store.exporting"
          @update:title="store.workflow.title = $event"
          @save="store.save()"
          @export="handleExport"
          @import-text="handleImportText"
          @auto-layout="handleAutoLayout"
        />
      </div>
      <div class="workflow-left">
        <SourcePanel
          :source-content="store.workflow.source_content"
          @update:source-content="store.workflow.source_content = $event"
          @plan="handlePlanSegments"
          @add-segment="handleAddSegment"
          @add-pause="handleAddPause"
          @apply-emotion="handleApplyEmotion"
        />
      </div>
      <div class="workflow-canvas">
        <VoiceFlowCanvas
          :segments="store.segments"
          :edges="store.edges"
          @select="store.selectSegment($event)"
          @move="(id, pos) => store.updateSegment(id, pos)"
        />
      </div>
      <div class="workflow-right">
        <SegmentInspector
          :segment="store.selectedSegment"
          @update="(id, patch) => store.updateSegment(id, patch)"
          @audition="handleAudition"
        />
      </div>
      <div class="workflow-bottom">
        <TimelineAuditionBar
          :segments="store.orderedSegments"
          :selected-segment-id="store.selectedSegmentId"
          @select="store.selectSegment($event)"
          @audition-selected="handleAuditionSelected"
          @export="handleExport"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useVoiceWorkflowsStore } from '../stores/voiceWorkflows'
import WorkflowToolbar from '../components/voice-workflow/WorkflowToolbar.vue'
import SourcePanel from '../components/voice-workflow/SourcePanel.vue'
import VoiceFlowCanvas from '../components/voice-workflow/VoiceFlowCanvas.vue'
import SegmentInspector from '../components/voice-workflow/SegmentInspector.vue'
import TimelineAuditionBar from '../components/voice-workflow/TimelineAuditionBar.vue'

const route = useRoute()
const router = useRouter()
const store = useVoiceWorkflowsStore()

onMounted(async () => {
  if (route.params.id && route.params.id !== 'new') {
    await store.fetch(route.params.id)
    return
  }
  const data = await store.create({ title: '未命名配音工程', source_content: '' })
  router.replace(`/voice-workflows/${data.id}`)
})

const handleAutoLayout = () => {
  store.segments.forEach((segment, index) => {
    store.updateSegment(segment.id, {
      node_x: 80 + index * 240,
      node_y: 120 + (index % 2) * 80,
      audio_status: segment.audio_status,
    })
  })
}

const handleImportText = () => { /* TODO: Task 7 */ }
const handlePlanSegments = () => { /* TODO: Task 7 */ }
const handleAddSegment = () => { /* TODO: Task 7 */ }
const handleAddPause = () => { /* TODO: Task 7 */ }
const handleApplyEmotion = () => { /* TODO: Task 7 */ }
const handleAudition = () => { /* TODO: Task 7 */ }
const handleAuditionSelected = () => { /* TODO: Task 7 */ }
const handleExport = () => { /* TODO: Task 7 */ }
</script>

<style scoped>
.voice-workflow-view { height: calc(100vh - 64px); padding: var(--space-md); }
.workflow-shell { display: grid; grid-template-columns: 260px 1fr 340px; grid-template-rows: 56px 1fr 126px; gap: 12px; height: 100%; }
.workflow-top, .workflow-left, .workflow-canvas, .workflow-right, .workflow-bottom { border: 1px solid var(--surface-border); border-radius: var(--radius-md); background: var(--surface); padding: var(--space-md); }
.workflow-top, .workflow-bottom { grid-column: 1 / 4; }
.workflow-loading { padding: var(--space-xl); }
</style>
