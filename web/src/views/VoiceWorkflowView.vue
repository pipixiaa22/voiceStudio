<template>
  <div class="voice-workflow-view">
    <div class="workflow-loading" v-if="store.loading">加载中</div>
    <div v-else class="workflow-shell">
      <div class="workflow-top">
        <WorkflowToolbar
          :title="store.workflow.title"
          :saving="store.saving"
          :exporting="store.exporting"
          :exporting-jianying="store.exportingJianying"
          :switching="store.loading"
          :current-workflow-id="store.workflow.id"
          :workflows="store.workflows"
          :default-voice-profile-id="store.workflow.default_voice_profile_id"
          :voice-profiles="voiceProfiles"
          @update:title="store.workflow.title = $event"
          @update:default-voice-profile-id="store.updateDefaultVoiceProfile($event)"
          @switch-workflow="handleSwitchWorkflow"
          @save="store.save()"
          @export="handleExport"
          @export-jianying="showJianyingExportModal = true"
          @import-text="showImportModal = true"
          @auto-layout="handleAutoLayout"
          @voice-profile-created="handleDefaultProfileCreated"
          @clear-cache="handleClearCache"
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
          ref="canvasRef"
          :segments="store.segments"
          :edges="store.edges"
          :voice-profiles="voiceProfiles"
          :default-voice-profile-id="store.workflow.default_voice_profile_id"
          @select="store.selectSegment($event)"
          @move="(id, pos) => store.updateSegment(id, pos)"
          @add-edge="handleAddEdge"
          @remove-edge="handleRemoveEdge"
        />
      </div>
      <div class="workflow-right">
        <SegmentInspector
          :segment="store.selectedSegment"
          :voice-profiles="voiceProfiles"
          :default-voice-profile-id="store.workflow.default_voice_profile_id"
          :audition-loading="auditioningSegment"
          @update="(id, patch) => store.updateSegment(id, patch)"
          @audition="handleAudition"
          @profile-created="handleSegmentProfileCreated"
        />
      </div>
      <div class="workflow-bottom">
        <TimelineAuditionBar
          :segments="store.orderedSegments"
          :selected-segment-id="store.selectedSegmentId"
          :audition-selected-loading="auditioningSegment"
          :audition-path-loading="auditioningPath"
          :path-audio-url="pathAudition.audioUrl"
          :path-duration="pathAudition.duration"
          @select="store.selectSegment($event)"
          @audition-selected="handleAuditionSelected"
          @audition-path="handleAuditionPath"
          @export="handleExport"
        />
      </div>
    </div>

    <!-- Import Text Modal -->
    <a-modal
      v-model:open="showImportModal"
      title="导入文本"
      @ok="handleImportConfirm"
      ok-text="导入"
      cancel-text="取消"
      width="560px"
    >
      <a-tabs v-model:activeKey="importTab" size="small">
        <a-tab-pane key="paste" tab="粘贴文本">
          <a-textarea
            v-model:value="importText"
            placeholder="粘贴中文旁白文本..."
            :autoSize="{ minRows: 6, maxRows: 12 }"
          />
        </a-tab-pane>
        <a-tab-pane key="select" tab="选择已有文本">
          <a-select
            v-model:value="importTextId"
            placeholder="选择一篇文本"
            show-search
            :filter-option="filterTextOption"
            style="width: 100%"
            @change="handleTextSelect"
          >
            <a-select-option v-for="t in allTexts" :key="t.id" :value="t.id">
              {{ t.title }}
            </a-select-option>
          </a-select>
        </a-tab-pane>
      </a-tabs>
    </a-modal>

    <a-modal
      v-model:open="showJianyingExportModal"
      title="写入剪映工程"
      ok-text="写入"
      cancel-text="取消"
      :confirm-loading="store.exportingJianying"
      @ok="handleExportToJianying"
    >
      <a-alert
        type="warning"
        show-icon
        message="写入前请关闭剪映中的目标工程"
        description="系统会先备份草稿 JSON，再写入一条新的“墨影字幕”文本轨。当前仅支持未加密的 Mac 本地剪映草稿。"
        class="jianying-alert"
      />
      <a-form layout="vertical">
        <a-form-item label="剪映工程目录">
          <div style="display: flex; gap: 8px;">
            <a-input
              v-model:value="jianyingDraftDir"
              placeholder="/Users/你的用户名/Movies/JianyingPro/User Data/Projects/com.lveditor.draft/工程ID"
              style="flex: 1"
            />
            <a-button @click="showFolderBrowser = true">浏览</a-button>
          </div>
        </a-form-item>
      </a-form>
      <FolderBrowser
        v-model:open="showFolderBrowser"
        @select="jianyingDraftDir = $event"
      />
    </a-modal>
  </div>
</template>

<script setup>
import { ref, computed, onBeforeUnmount, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { voiceProfilesApi } from '../api'
import { useVoiceWorkflowsStore } from '../stores/voiceWorkflows'
import { useSettings } from '../stores/settings'
import { useTextsStore } from '../stores/texts'
import WorkflowToolbar from '../components/voice-workflow/WorkflowToolbar.vue'
import SourcePanel from '../components/voice-workflow/SourcePanel.vue'
import VoiceFlowCanvas from '../components/voice-workflow/VoiceFlowCanvas.vue'
import SegmentInspector from '../components/voice-workflow/SegmentInspector.vue'
import TimelineAuditionBar from '../components/voice-workflow/TimelineAuditionBar.vue'
import FolderBrowser from '../components/FolderBrowser.vue'

const route = useRoute()
const router = useRouter()
const store = useVoiceWorkflowsStore()
const textsStore = useTextsStore()
const { ttsKey } = useSettings()
const fallbackVoiceDescription = '稳定自然的中文旁白声线，吐字清晰，情绪服从每句设置。'
const auditioningPath = ref(false)
const auditioningSegment = ref(false)
const pathAudition = ref({
  audioUrl: '',
  duration: null,
})

const canvasRef = ref(null)

const handleAddEdge = ({ source_segment_id, target_segment_id }) => {
  store.addEdge({ source_segment_id, target_segment_id })
  const src = store.segments.find(s => String(s.id) === String(source_segment_id))
  const tgt = store.segments.find(s => String(s.id) === String(target_segment_id))
  message.success(`已连接: #${src?.order_index || '?'} → #${tgt?.order_index || '?'}`)
}

const handleRemoveEdge = (edgeId) => {
  store.removeEdge(edgeId)
  message.success('已删除连线')
}

// Import modal state
const showImportModal = ref(false)
const showJianyingExportModal = ref(false)
const importTab = ref('paste')
const importText = ref('')
const importTextId = ref(null)
const jianyingDraftDir = ref(localStorage.getItem('jianying_draft_dir') || '')
const showFolderBrowser = ref(false)
const voiceProfiles = ref([])
const allTexts = computed(() => textsStore.texts)

const fetchVoiceProfiles = async () => {
  try {
    const { data } = await voiceProfilesApi.list({ active: 1 })
    voiceProfiles.value = data
  } catch {
    voiceProfiles.value = []
  }
}

const handleDefaultProfileCreated = async profile => {
  await fetchVoiceProfiles()
  store.updateDefaultVoiceProfile(profile.id)
  message.success(`已创建并应用默认音色: ${profile.name}`)
}

const handleSegmentProfileCreated = async profile => {
  await fetchVoiceProfiles()
  if (store.selectedSegmentId) {
    store.updateSegment(store.selectedSegmentId, { voice_profile_id: profile.id })
  }
  message.success(`已创建并应用音色: ${profile.name}`)
}

const loadWorkflowForRoute = async id => {
  if (id && id !== 'new') {
    await store.fetch(id)
    return
  }

  const data = await store.create({ title: '未命名配音工程', source_content: '' })
  await store.fetchList()
  router.replace(`/voice-workflows/${data.id}`)
}

onMounted(async () => {
  if (!textsStore.texts.length) {
    textsStore.fetchTexts()
  }
  fetchVoiceProfiles()
  await store.fetchList()
  await loadWorkflowForRoute(route.params.id)
})

watch(() => route.params.id, async (id, oldId) => {
  if (!oldId || String(id) === String(oldId)) return
  await loadWorkflowForRoute(id)
})

onBeforeUnmount(() => {
  revokePathAuditionUrl()
  if (currentAudio) {
    currentAudio.pause()
    currentAudio = null
  }
})

const filterTextOption = (input, option) => {
  return option.children[0].children.toLowerCase().includes(input.toLowerCase())
}

const handleTextSelect = async (id) => {
  const text = await textsStore.fetchText(id)
  if (text) {
    importText.value = text.content
    importTextId.value = id
  }
}

const handleImportConfirm = () => {
  const content = importText.value.trim()
  if (!content) {
    message.warning('请输入或选择文本')
    return
  }
  store.workflow.source_content = content
  store.workflow.source_text_id = importTab.value === 'select' ? importTextId.value : null
  showImportModal.value = false
  importText.value = ''
  importTextId.value = null
  message.success('文本已导入，点击"自动切句"生成节点')
}

const handleSwitchWorkflow = workflowId => {
  if (!workflowId || String(workflowId) === String(store.workflow.id)) return
  router.push(`/voice-workflows/${workflowId}`)
}

const handleAutoLayout = () => {
  const positionMap = new Map()
  store.segments.forEach((segment, index) => {
    const x = 80 + index * 240
    const y = 120 + (index % 2) * 80
    store.updateSegment(segment.id, {
      node_x: x,
      node_y: y,
      audio_status: segment.audio_status,
    })
    positionMap.set(String(segment.id), { x, y })
  })
  // Rebuild edges to match new layout order
  store.rebuildEdges()
  if (canvasRef.value?.setNodePositions) {
    canvasRef.value.setNodePositions(positionMap)
  }
}

const handleAddSegment = () => {
  const seg = store.addSegment('新语句。', { emotion: 'calm' })
  message.success(`已添加语句节点 #${seg.order_index}`)
}

const handleAddPause = () => {
  const seg = store.addSegment('……', {
    emotion: 'suppressed',
    pause_before_ms: 500,
    pause_after_ms: 500,
    transition: 'normal',
  })
  message.success(`已添加停顿节点 #${seg.order_index}`)
}

const handleApplyEmotion = (emotion) => {
  if (!store.selectedSegment) {
    message.warning('请先选择一个语句节点')
    return
  }
  const presets = {
    calm: { emotion: 'calm', intensity: 0.25, rate: 0.95, pitch: -1, volume_db: -1 },
    suppressed: { emotion: 'suppressed', intensity: 0.55, rate: 0.9, pitch: -1, volume_db: -2 },
    angry_burst: { emotion: 'angry_burst', intensity: 1.6, rate: 1.15, pitch: 2, volume_db: 3 },
    cold: { emotion: 'cold', intensity: 0.7, rate: 0.8, pitch: -2, volume_db: -2 },
  }
  const preset = presets[emotion]
  if (preset) {
    store.updateSegment(store.selectedSegmentId, preset)
    const labels = { calm: '平静', suppressed: '压抑', angry_burst: '爆发愤怒', cold: '冷漠' }
    message.success(`已应用情绪: ${labels[emotion] || emotion}`)
  }
}

const handlePlanSegments = async () => {
  if (!store.workflow.source_content.trim()) {
    message.warning('请先输入源文本')
    return
  }
  await store.planSegments()
  message.success('已生成语句节点')
}

let currentAudio = null
const base64ToAudioUrl = audioBase64 => {
  const binary = atob(audioBase64)
  const bytes = new Uint8Array(binary.length)
  for (let index = 0; index < binary.length; index += 1) bytes[index] = binary.charCodeAt(index)
  return URL.createObjectURL(new Blob([bytes], { type: 'audio/wav' }))
}

const revokePathAuditionUrl = () => {
  if (pathAudition.value.audioUrl) {
    URL.revokeObjectURL(pathAudition.value.audioUrl)
  }
  pathAudition.value = { audioUrl: '', duration: null }
}

const playBase64Audio = audioBase64 => {
  if (currentAudio) {
    currentAudio.pause()
    currentAudio.currentTime = 0
    currentAudio = null
  }
  const url = base64ToAudioUrl(audioBase64)
  const audio = new Audio(url)
  currentAudio = audio
  audio.onended = () => {
    URL.revokeObjectURL(url)
    if (currentAudio === audio) currentAudio = null
  }
  audio.play()
}

const handleAudition = async segment => {
  if (!ttsKey.value) {
    message.warning('请先配置 TTS API Key')
    return
  }
  auditioningSegment.value = true
  try {
    const data = await store.auditionSegment(segment, ttsKey.value, fallbackVoiceDescription)
    if (data) playBase64Audio(data.audio_base64)
  } finally {
    auditioningSegment.value = false
  }
}

const handleAuditionSelected = async () => {
  if (store.selectedSegment) await handleAudition(store.selectedSegment)
}

const handleAuditionPath = async () => {
  if (!ttsKey.value) {
    message.warning('请先配置 TTS API Key')
    return
  }
  if (auditioningPath.value) return
  auditioningPath.value = true
  try {
    const data = await store.auditionPath(ttsKey.value, fallbackVoiceDescription)
    if (data) {
      revokePathAuditionUrl()
      pathAudition.value = {
        audioUrl: base64ToAudioUrl(data.audio_base64),
        duration: data.total_duration,
      }
      message.success('整条试听已生成，可在底部播放器控制播放')
    }
  } finally {
    auditioningPath.value = false
  }
}

const handleExport = async () => {
  if (!ttsKey.value) {
    message.warning('请先配置 TTS API Key')
    return
  }
  const response = await store.exportPackage(ttsKey.value, fallbackVoiceDescription)
  const url = URL.createObjectURL(new Blob([response.data], { type: 'application/zip' }))
  const link = document.createElement('a')
  link.href = url
  link.download = `${store.workflow.title || '配音工作流'}_配音工作流.zip`
  link.click()
  URL.revokeObjectURL(url)
  message.success('导出完成')
}

const handleExportToJianying = async () => {
  if (!ttsKey.value) {
    message.warning('请先配置 TTS API Key')
    return
  }
  const draftDir = jianyingDraftDir.value.trim()
  if (!draftDir) {
    message.warning('请填写剪映工程目录')
    return
  }
  const result = await store.exportToJianying(ttsKey.value, fallbackVoiceDescription, draftDir)
  localStorage.setItem('jianying_draft_dir', draftDir)
  showJianyingExportModal.value = false
  message.success(`已写入 ${result.subtitle_count} 条字幕，备份已保存`)
}

const handleClearCache = async () => {
  await store.clearCache()
  message.success('已清除所有缓存音频')
}
</script>

<style scoped>
.voice-workflow-view { height: calc(100vh - 64px); padding: var(--space-md); }
.workflow-shell { display: grid; grid-template-columns: 260px 1fr 340px; grid-template-rows: 56px 1fr 126px; gap: 12px; height: 100%; }
.workflow-top, .workflow-left, .workflow-canvas, .workflow-right, .workflow-bottom { border: 1px solid var(--surface-border); border-radius: var(--radius-md); background: var(--surface); padding: var(--space-md); }
.workflow-top, .workflow-bottom { grid-column: 1 / 4; }
.workflow-loading { padding: var(--space-xl); }
.jianying-alert { margin-bottom: var(--space-md); }
</style>
