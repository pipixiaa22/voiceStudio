<template>
  <div class="novel-generation-panel">
    <div v-if="store.generation?.status === 'running' || store.generation?.status === 'pending'" class="gen-progress">
      <a-progress :percent="store.generation.progress" status="active" />
      <p>{{ store.generation.status === 'pending' ? '等待中...' : '生成中...' }}</p>
    </div>
    <a-alert
      v-else-if="store.generation?.status === 'failed'"
      type="error"
      show-icon
      message="生成失败"
      :description="store.generation.error || '请重新发起生成。'"
      class="gen-alert"
    />
    <template v-else>
      <div v-if="knowledgeIncrement" class="knowledge-increment">
        <a-alert type="info" show-icon>
          <template #message>
            本次生成引入
            <a-tag v-if="knowledgeIncrement.graphChanges > 0" color="blue" size="small">{{ knowledgeIncrement.graphChanges }} 条图谱变更</a-tag>
            <a-tag v-if="knowledgeIncrement.memoryChanges > 0" color="purple" size="small">{{ knowledgeIncrement.memoryChanges }} 条记忆变更</a-tag>
            <span v-if="!knowledgeIncrement.graphChanges && !knowledgeIncrement.memoryChanges">无知识变更</span>
          </template>
        </a-alert>
      </div>
      <div class="gen-summary">
        <span class="panel-kicker">AI 续写</span>
        <strong>{{ store.currentChapter?.title || '未选择章节' }}</strong>
        <p>{{ generationHint }}</p>
      </div>
      <a-form layout="vertical" size="small">
        <a-form-item label="版本方向">
          <div class="direction-grid">
            <button
              v-for="option in directionOptions"
              :key="option.value"
              type="button"
              class="direction-card"
              :class="{ active: versionType === option.value }"
              @click="versionType = option.value"
            >
              <strong>{{ option.label }}</strong>
              <span>{{ option.desc }}</span>
            </button>
          </div>
        </a-form-item>
        <a-form-item label="用户指令">
          <a-textarea v-model:value="userInstruction" placeholder="可选：对本次生成的特殊要求..." :auto-size="{ minRows: 3, maxRows: 6 }" />
        </a-form-item>
        <a-button type="primary" block :disabled="!canGenerate" @click="handleGenerate">
          {{ canGenerate ? '生成续写版本' : '请先选择章节' }}
        </a-button>
      </a-form>
    </template>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { message } from 'ant-design-vue'
import { useNovelsStore } from '../../stores/novels'

const store = useNovelsStore()
const versionType = ref('steady')
const userInstruction = ref('')
const knowledgeIncrement = computed(() => {
  const gen = store.generation
  if (!gen || gen.status !== 'completed' || gen.generation_type !== 'chapter_version') return null
  const result = gen.result
  if (!result?.versions) return null
  const graphChanges = result.versions.reduce((sum, v) => sum + (v.generated_graph_changes?.length || 0), 0)
  const memoryChanges = result.versions.reduce((sum, v) => sum + (v.generated_memory_changes?.length || 0), 0)
  return { graphChanges, memoryChanges }
})
const directionOptions = [
  { value: 'steady', label: '稳健推进', desc: '承接大纲，平滑续写' },
  { value: 'conflict', label: '强冲突', desc: '放大矛盾和阻力' },
  { value: 'climax', label: '爽点爆发', desc: '强化情绪和反击' },
  { value: 'suspense', label: '悬疑反转', desc: '制造钩子和误导' },
  { value: 'romance', label: '感情拉扯', desc: '突出关系张力' },
  { value: 'polish', label: '文风精修', desc: '保留剧情，优化表达' },
]
const canGenerate = computed(() => !!store.currentChapter)
const generationHint = computed(() => {
  if (!store.currentChapter) return '从左侧选择章节，或先创建第一章。'
  if (store.dirty) return '生成前会自动保存当前未保存内容。'
  return '选择方向后生成候选版本，可在“版本”页对比并采纳。'
})

const handleGenerate = async () => {
  if (!store.currentChapter) {
    message.warning('请先选择章节')
    return
  }
  try {
    await store.startGeneration('chapter_version', {
      version_types: [versionType.value],
      user_instruction: userInstruction.value,
    })
  } catch (e) {
    message.error('生成失败: ' + (e.response?.data?.error || e.message))
  }
}
</script>

<style scoped>
.novel-generation-panel {
  padding: 8px;
}
.gen-summary {
  margin-bottom: 12px;
  padding: 12px;
  border: 1px solid var(--surface-border);
  border-radius: var(--radius-md);
  background: #fff;
}
.panel-kicker {
  display: block;
  margin-bottom: 4px;
  color: var(--text-muted);
  font-size: 11px;
}
.gen-summary strong {
  display: block;
  color: var(--text-primary);
  font-size: 14px;
}
.gen-summary p {
  margin: 6px 0 0;
  color: var(--text-muted);
  font-size: 12px;
  line-height: 1.6;
}
.direction-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}
.direction-card {
  min-height: 68px;
  padding: 10px;
  border: 1px solid var(--surface-border);
  border-radius: var(--radius-md);
  background: #fff;
  cursor: pointer;
  text-align: left;
  transition: border-color var(--transition-fast), box-shadow var(--transition-fast), transform var(--transition-fast);
}
.direction-card:hover {
  border-color: var(--surface-border-strong);
  transform: translateY(-1px);
}
.direction-card.active {
  border-color: var(--text-primary);
  box-shadow: var(--shadow-focus);
}
.direction-card strong,
.direction-card span {
  display: block;
}
.direction-card strong {
  color: var(--text-primary);
  font-size: 13px;
}
.direction-card span {
  margin-top: 4px;
  color: var(--text-muted);
  font-size: 11px;
  line-height: 1.4;
}
.gen-progress {
  text-align: center;
  padding: 16px;
}
.gen-progress p {
  margin-top: 8px;
  font-size: 13px;
  color: var(--text-muted);
}
.gen-alert {
  margin-bottom: 12px;
}
.knowledge-increment { margin-bottom: 12px; }
</style>
