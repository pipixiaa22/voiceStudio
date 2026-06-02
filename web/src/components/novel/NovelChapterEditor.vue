<template>
  <div class="novel-chapter-editor">
    <div v-if="!store.currentChapter" class="editor-empty">
      <p>请从左侧选择一个章节</p>
    </div>
    <template v-else>
      <div class="editor-title">
        <a-input
          v-model:value="store.currentChapter.title"
          placeholder="章节标题"
          size="large"
          @change="scheduleAutoSave()"
        />
      </div>
      <div class="editor-toolbar">
        <a-button size="small" @click="insertMarkdown('## ')">H2</a-button>
        <a-button size="small" @click="insertMarkdown('### ')">H3</a-button>
        <a-button size="small" @click="wrapMarkdown('**')">B</a-button>
        <a-button size="small" @click="insertMarkdown('> ')">引用</a-button>
        <a-button size="small" @click="insertMarkdown('---\n')">分割线</a-button>
      </div>
      <div class="editor-body">
        <a-textarea
          ref="textareaRef"
          v-model:value="store.currentChapter.content_markdown"
          :auto-size="{ minRows: 20 }"
          placeholder="开始写作..."
          @change="handleContentChange"
        />
      </div>
      <div class="editor-footer">
        <a-progress
          :percent="wordCountPercent"
          :show-info="false"
          size="small"
          style="width: 120px"
        />
        <span>{{ store.chapterWordCount }} / {{ store.currentChapter.target_words || '—' }} 字</span>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useNovelsStore } from '../../stores/novels'

const store = useNovelsStore()
const textareaRef = ref(null)
let saveTimer = null

const wordCountPercent = computed(() => {
  const target = store.currentChapter?.target_words
  if (!target) return 0
  return Math.min(100, Math.round((store.chapterWordCount / target) * 100))
})

const scheduleAutoSave = () => {
  store.dirty = true
  clearTimeout(saveTimer)
  saveTimer = setTimeout(() => {
    if (store.dirty && store.currentChapter) {
      store.saveChapter(store.currentProject.id, store.currentChapter.id, store.currentChapter.content_markdown, store.currentChapter.title)
    }
  }, 2000)
}

const handleContentChange = () => {
  scheduleAutoSave()
}

const insertMarkdown = (prefix) => {
  const ta = textareaRef.value?.$el?.querySelector('textarea')
  if (!ta) return
  const start = ta.selectionStart
  const end = ta.selectionEnd
  const text = store.currentChapter.content_markdown
  store.currentChapter.content_markdown = text.slice(0, start) + prefix + text.slice(end)
  scheduleAutoSave()
}

const wrapMarkdown = (wrapper) => {
  const ta = textareaRef.value?.$el?.querySelector('textarea')
  if (!ta) return
  const start = ta.selectionStart
  const end = ta.selectionEnd
  const text = store.currentChapter.content_markdown
  const selected = text.slice(start, end)
  store.currentChapter.content_markdown = text.slice(0, start) + wrapper + selected + wrapper + text.slice(end)
  scheduleAutoSave()
}
</script>

<style scoped>
.novel-chapter-editor {
  padding: 16px 24px;
  max-width: 800px;
  margin: 0 auto;
}
.editor-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 300px;
  color: var(--text-muted);
}
.editor-title { margin-bottom: 12px; }
.editor-toolbar {
  display: flex;
  gap: 4px;
  margin-bottom: 8px;
}
.editor-body :deep(.ant-input) {
  font-family: var(--font-mono);
  font-size: 14px;
  line-height: 1.8;
}
.editor-footer {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
  font-size: 12px;
  color: var(--text-muted);
}
</style>
