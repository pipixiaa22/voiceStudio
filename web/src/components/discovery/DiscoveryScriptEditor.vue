<template>
  <div class="script-editor">
    <div class="script-controls">
      <a-select v-model:value="localLength" size="small">
        <a-select-option value="short">短 30-60 秒</a-select-option>
        <a-select-option value="medium">中 1-2 分钟</a-select-option>
        <a-select-option value="long">长 3-5 分钟</a-select-option>
      </a-select>
      <a-select v-model:value="localStyle" size="small">
        <a-select-option value="热血">热血</a-select-option>
        <a-select-option value="冷峻">冷峻</a-select-option>
        <a-select-option value="爽文">爽文</a-select-option>
        <a-select-option value="悬疑">悬疑</a-select-option>
        <a-select-option value="女频">女频</a-select-option>
      </a-select>
      <a-button size="small" type="primary" :loading="generating" @click="$emit('generate', { length: localLength, style: localStyle })">
        生成原创脚本
      </a-button>
    </div>

    <template v-if="draft">
      <a-form layout="vertical" class="script-form">
        <a-form-item label="标题">
          <a-input v-model:value="editable.title" @change="emitDraft" />
        </a-form-item>
        <a-form-item label="正文">
          <a-textarea v-model:value="editable.content" :rows="12" @change="emitDraft" />
        </a-form-item>
      </a-form>

      <div class="script-footer">
        <span>{{ editable.content.length }} 字</span>
        <div class="footer-actions">
          <a-button v-if="importedText" @click="$emit('edit-text', importedText)">去编辑</a-button>
          <a-button v-if="importedText" type="primary" @click="$emit('open-video', importedText)">生成视频</a-button>
          <a-button v-else type="primary" :loading="importing" @click="$emit('import-text', editable)">导入文本库</a-button>
        </div>
      </div>

      <a-alert
        v-if="importedText"
        class="import-success"
        type="success"
        :message="`已导入文本库：${importedText.title}`"
        show-icon
      />
    </template>

    <div v-else class="empty-script">
      <p>先生成一版原创脚本，再决定是否导入文本库。</p>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref, watch } from 'vue'

const props = defineProps({
  draft: Object,
  importedText: Object,
  generating: Boolean,
  importing: Boolean,
})

const emit = defineEmits(['generate', 'update-draft', 'import-text', 'edit-text', 'open-video'])

const localLength = ref('short')
const localStyle = ref('热血')
const editable = reactive({
  title: '',
  content: '',
})

watch(() => props.draft, (draft) => {
  editable.title = draft?.title || ''
  editable.content = draft?.content || ''
}, { immediate: true })

const emitDraft = () => {
  emit('update-draft', { title: editable.title, content: editable.content })
}
</script>

<style scoped>
.script-editor {
  display: grid;
  gap: var(--space-md);
}

.script-controls {
  display: grid;
  grid-template-columns: 1fr 1fr auto;
  gap: var(--space-sm);
}

.script-form :deep(.ant-form-item) {
  margin-bottom: 12px;
}

.script-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-md);
  color: var(--text-muted);
  font-size: 12px;
}

.footer-actions {
  display: flex;
  gap: var(--space-sm);
}

.import-success {
  margin-top: var(--space-sm);
}

.empty-script {
  padding: var(--space-lg);
  border: 1px dashed var(--surface-border);
  border-radius: var(--radius-md);
  color: var(--text-muted);
  font-size: 13px;
  line-height: 1.7;
}

.empty-script p {
  margin: 0;
}

@media (max-width: 760px) {
  .script-controls {
    grid-template-columns: 1fr;
  }

  .script-footer {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
