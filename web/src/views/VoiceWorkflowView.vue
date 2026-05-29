<template>
  <div class="voice-workflow-view">
    <div class="workflow-loading" v-if="store.loading">加载中</div>
    <div v-else class="workflow-shell">
      <div class="workflow-top">配音工作台</div>
      <div class="workflow-left">素材区</div>
      <div class="workflow-canvas">画布区</div>
      <div class="workflow-right">参数区</div>
      <div class="workflow-bottom">时间线</div>
    </div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useVoiceWorkflowsStore } from '../stores/voiceWorkflows'

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
</script>

<style scoped>
.voice-workflow-view { height: calc(100vh - 64px); padding: var(--space-md); }
.workflow-shell { display: grid; grid-template-columns: 260px 1fr 340px; grid-template-rows: 56px 1fr 126px; gap: 12px; height: 100%; }
.workflow-top, .workflow-left, .workflow-canvas, .workflow-right, .workflow-bottom { border: 1px solid var(--surface-border); border-radius: var(--radius-md); background: var(--surface); padding: var(--space-md); }
.workflow-top, .workflow-bottom { grid-column: 1 / 4; }
.workflow-loading { padding: var(--space-xl); }
</style>
