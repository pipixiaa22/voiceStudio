<template>
  <div class="voice-workflow-list">
    <div class="page-header">
      <h1 class="page-title">配音工作台</h1>
      <a-button type="primary" @click="$router.push('/voice-workflows/new')">新建配音工程</a-button>
    </div>
    <div class="workflow-grid">
      <button
        v-for="workflow in store.workflows"
        :key="workflow.id"
        class="workflow-item"
        @click="$router.push(`/voice-workflows/${workflow.id}`)"
      >
        <strong>{{ workflow.title }}</strong>
        <span>{{ workflow.updated_at }}</span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useVoiceWorkflowsStore } from '../stores/voiceWorkflows'

const store = useVoiceWorkflowsStore()
onMounted(() => store.fetchList())
</script>

<style scoped>
.voice-workflow-list { max-width: 1180px; margin: 0 auto; padding: var(--space-xl); }
.page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: var(--space-lg); }
.page-title { margin: 0; font-size: 28px; font-weight: 650; }
.workflow-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: var(--space-md); }
.workflow-item { text-align: left; border: 1px solid var(--surface-border); background: var(--surface); border-radius: var(--radius-md); padding: var(--space-md); cursor: pointer; }
.workflow-item span { display: block; margin-top: 8px; color: var(--text-muted); font-size: 12px; }
</style>
