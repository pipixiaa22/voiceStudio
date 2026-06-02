<!-- web/src/views/NovelWorkspace.vue -->
<template>
  <div class="novel-workspace">
    <div v-if="loading" class="workspace-loading">加载中...</div>
    <div v-else class="workspace-shell">
      <!-- Top bar -->
      <div class="workspace-top">
        <div class="top-left">
          <a-button type="text" size="small" @click="$router.push('/novels')">
            ← 返回
          </a-button>
          <span class="project-title">{{ store.currentProject?.title }}</span>
          <span v-if="store.currentChapter" class="chapter-title">
            · {{ store.currentChapter.title }}
          </span>
        </div>
        <div class="top-center">
          <a-segmented v-model:value="store.activeMode" :options="[
            { label: '写作', value: 'write' },
            { label: '图谱', value: 'graph' },
            { label: '审稿', value: 'review' },
          ]" size="small" />
        </div>
        <div class="top-right">
          <span class="save-status" :class="saveStatusClass">{{ saveStatusText }}</span>
          <a-button size="small" @click="handleSave" :loading="store.saving">保存</a-button>
          <a-button size="small" @click="showBlueprintWizard = true">生成蓝图</a-button>
          <a-button size="small" type="primary" @click="handleGenerate">生成</a-button>
          <a-button size="small" @click="handleReview">审稿</a-button>
          <a-button size="small" @click="handleExtract">提取图谱</a-button>
        </div>
      </div>

      <!-- Write mode -->
      <div v-if="store.activeMode === 'write'" class="workspace-main">
        <div class="workspace-left">
          <NovelOutlinePanel />
        </div>
        <div class="workspace-center">
          <NovelChapterEditor />
        </div>
        <div class="workspace-right">
          <a-tabs v-model:activeKey="store.rightTab" size="small">
            <a-tab-pane key="generation" tab="生成">
              <NovelGenerationPanel />
            </a-tab-pane>
            <a-tab-pane key="versions" tab="版本">
              <NovelVersionList />
            </a-tab-pane>
            <a-tab-pane key="context" tab="上下文">
              <NovelContextPanel />
            </a-tab-pane>
            <a-tab-pane key="review" tab="审稿">
              <NovelReviewPanel />
            </a-tab-pane>
          </a-tabs>
        </div>
      </div>

      <!-- Graph mode -->
      <div v-else-if="store.activeMode === 'graph'" class="workspace-main">
        <div class="workspace-graph">
          <NovelCharacterGraph v-if="store.graphType === 'characters'" />
          <NovelEventGraph v-else />
        </div>
        <div class="workspace-right">
          <NovelEntityInspector v-if="store.selectedEntityId && store.graphType === 'characters'" />
          <NovelRelationInspector v-else-if="store.selectedRelationId && store.graphType === 'characters'" />
          <NovelEventInspector v-else-if="store.selectedEventId && store.graphType === 'events'" />
          <div v-else class="inspector-empty">
            <p>点击图谱节点查看属性</p>
          </div>
        </div>
      </div>

      <!-- Review mode -->
      <div v-else class="workspace-main">
        <div class="workspace-left">
          <NovelOutlinePanel />
        </div>
        <div class="workspace-center">
          <NovelChapterEditor />
        </div>
        <div class="workspace-right">
          <NovelReviewPanel />
        </div>
      </div>

      <!-- Bottom status bar -->
      <div class="workspace-bottom">
        <span>{{ store.chapterWordCount }} 字</span>
        <span v-if="store.currentChapter?.target_words">
          / 目标 {{ store.currentChapter.target_words }} 字
        </span>
        <span class="status-sep">|</span>
        <span>{{ store.currentProject?.knowledge_update_mode }}</span>
      </div>
    </div>

    <!-- Modals -->
    <NovelExtractionReviewModal />
    <NovelBlueprintWizard v-model:open="showBlueprintWizard" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { message } from 'ant-design-vue'
import { useNovelsStore } from '../stores/novels'
import NovelOutlinePanel from '../components/novel/NovelOutlinePanel.vue'
import NovelChapterEditor from '../components/novel/NovelChapterEditor.vue'
import NovelGenerationPanel from '../components/novel/NovelGenerationPanel.vue'
import NovelVersionList from '../components/novel/NovelVersionList.vue'
import NovelContextPanel from '../components/novel/NovelContextPanel.vue'
import NovelReviewPanel from '../components/novel/NovelReviewPanel.vue'
import NovelCharacterGraph from '../components/novel/NovelCharacterGraph.vue'
import NovelEventGraph from '../components/novel/NovelEventGraph.vue'
import NovelEntityInspector from '../components/novel/NovelEntityInspector.vue'
import NovelRelationInspector from '../components/novel/NovelRelationInspector.vue'
import NovelEventInspector from '../components/novel/NovelEventInspector.vue'
import NovelExtractionReviewModal from '../components/novel/NovelExtractionReviewModal.vue'
import NovelBlueprintWizard from '../components/novel/NovelBlueprintWizard.vue'

const route = useRoute()
const store = useNovelsStore()
const loading = ref(true)
const showBlueprintWizard = ref(false)

onMounted(async () => {
  try {
    await store.loadWorkspace(route.params.id)
  } catch (e) {
    message.error('加载失败')
  } finally {
    loading.value = false
  }
})

onUnmounted(() => {
  store.cleanup()
})

const saveStatusClass = computed(() => {
  if (store.saveError) return 'status-error'
  if (store.saving) return 'status-saving'
  if (store.dirty) return 'status-dirty'
  return 'status-saved'
})

const saveStatusText = computed(() => {
  if (store.saveError) return '保存失败'
  if (store.saving) return '保存中...'
  if (store.dirty) return '未保存'
  return '已保存'
})

const handleSave = async () => {
  if (!store.currentChapter) return
  try {
    await store.saveChapter(store.currentProject.id, store.currentChapter.id, store.currentChapter.content_markdown, store.currentChapter.title)
    message.success('已保存')
  } catch {
    message.error('保存失败')
  }
}

const handleGenerate = () => {
  if (!store.currentChapter) {
    message.warning('请先选择一个章节')
    return
  }
  store.rightTab = 'generation'
}

const handleReview = async () => {
  if (!store.currentChapter) {
    message.warning('请先选择一个章节')
    return
  }
  await store.startGeneration('review', {})
}

const handleExtract = async () => {
  if (!store.currentChapter) {
    message.warning('请先选择一个章节')
    return
  }
  await store.startGeneration('extract', {})
}

// Watch for chapter content changes to mark dirty (compare against last saved snapshot)
watch(
  () => [store.currentChapter?.title, store.currentChapter?.content_markdown],
  ([title, content]) => {
    const snapshot = `${title}||${content}`
    if (snapshot !== store._lastSavedSnapshot) {
      store.dirty = true
    }
  },
)
</script>

<style scoped>
.novel-workspace {
  height: calc(100vh - 64px);
  display: flex;
  flex-direction: column;
}
.workspace-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
}
.workspace-shell {
  display: flex;
  flex-direction: column;
  height: 100%;
}
.workspace-main {
  display: flex;
  flex: 1;
  min-height: 0;
}
.workspace-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 16px;
  border-bottom: 1px solid var(--surface-border);
  background: var(--surface-card);
  gap: 16px;
  flex-shrink: 0;
}
.top-left {
  display: flex;
  align-items: center;
  gap: 8px;
}
.project-title {
  font-weight: 600;
  font-size: 14px;
}
.chapter-title {
  color: var(--text-muted);
  font-size: 13px;
}
.top-right {
  display: flex;
  align-items: center;
  gap: 8px;
}
.save-status {
  font-size: 12px;
}
.status-saved { color: var(--success); }
.status-dirty { color: var(--warning); }
.status-saving { color: var(--text-muted); }
.status-error { color: var(--error); }

.workspace-left {
  width: 300px;
  border-right: 1px solid var(--surface-border);
  overflow-y: auto;
  flex-shrink: 0;
}
.workspace-center {
  flex: 1;
  overflow-y: auto;
}
.workspace-right {
  width: 380px;
  border-left: 1px solid var(--surface-border);
  overflow-y: auto;
  flex-shrink: 0;
}
.workspace-graph {
  flex: 1;
}
.workspace-bottom {
  display: flex;
  align-items: center;
  padding: 4px 16px;
  border-top: 1px solid var(--surface-border);
  font-size: 12px;
  color: var(--text-muted);
  background: var(--surface-card);
  flex-shrink: 0;
  gap: 4px;
}
.status-sep { margin: 0 8px; }
.inspector-empty {
  padding: 24px;
  text-align: center;
  color: var(--text-muted);
}
</style>
