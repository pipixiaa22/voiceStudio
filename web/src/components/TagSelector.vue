<template>
  <div class="tag-selector">
    <!-- Selected Tags -->
    <div class="selected-tags" v-if="selectedTags.length > 0">
      <a-tag
        v-for="tag in selectedTags"
        :key="tag.id"
        closable
        class="selected-tag"
        @close="removeTag(tag.id)"
      >
        {{ tag.name }}
      </a-tag>
    </div>

    <!-- Add Tag Input -->
    <div class="add-tag-row">
      <a-input-group compact class="tag-input-group">
        <a-input
          v-model:value="newTagName"
          placeholder="输入标签名称"
          @keyup.enter="handleAddTag"
          class="tag-input"
          size="small"
        />
        <a-button type="primary" size="small" @click="handleAddTag" :disabled="!newTagName.trim()" class="add-btn">
          添加
        </a-button>
      </a-input-group>
    </div>

    <!-- Available Tags -->
    <div v-if="availableTags.length > 0" class="available-tags">
      <span class="available-label">可用标签</span>
      <div class="tag-list">
        <a-tag
          v-for="tag in availableTags"
          :key="tag.id"
          class="available-tag"
          @click="addTag(tag)"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="add-icon">
            <line x1="12" y1="5" x2="12" y2="19"/>
            <line x1="5" y1="12" x2="19" y2="12"/>
          </svg>
          {{ tag.name }}
        </a-tag>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { useTagsStore } from '../stores/tags'

const props = defineProps({
  modelValue: { type: Array, default: () => [] }
})

const emit = defineEmits(['update:modelValue'])
const tagsStore = useTagsStore()
const newTagName = ref('')

onMounted(() => tagsStore.fetchTags())

const selectedTags = computed(() => props.modelValue)

const availableTags = computed(() =>
  tagsStore.tags.filter(t => !props.modelValue.some(s => s.id === t.id))
)

const addTag = (tag) => {
  emit('update:modelValue', [...props.modelValue, tag])
}

const removeTag = (id) => {
  emit('update:modelValue', props.modelValue.filter(t => t.id !== id))
}

const handleAddTag = async () => {
  if (!newTagName.value.trim()) return
  try {
    const tag = await tagsStore.createTag({ name: newTagName.value })
    addTag(tag)
    newTagName.value = ''
    message.success('标签已创建')
  } catch (e) {
    message.error('创建标签失败')
  }
}
</script>

<style scoped>
.tag-selector {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}

/* Selected Tags */
.selected-tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-xs);
  margin-bottom: var(--space-xs);
}

.selected-tag {
  background: var(--gold-glow) !important;
  border: 1px solid rgba(212, 168, 83, 0.3) !important;
  color: var(--gold) !important;
  border-radius: var(--radius-sm) !important;
  padding: 4px 12px !important;
  font-size: 13px !important;
  display: inline-flex !important;
  align-items: center;
  gap: 6px;
  transition: all var(--transition-fast);
}

.selected-tag:hover {
  background: rgba(212, 168, 83, 0.2) !important;
}

/* Add Tag Row */
.add-tag-row {
  margin-top: var(--space-xs);
}

.tag-input-group {
  display: flex;
  width: 100%;
}

.tag-input {
  flex: 1;
  border-top-right-radius: 0 !important;
  border-bottom-right-radius: 0 !important;
}

.add-btn {
  border-top-left-radius: 0 !important;
  border-bottom-left-radius: 0 !important;
  min-width: 60px;
}

/* Available Tags */
.available-tags {
  margin-top: var(--space-sm);
  padding-top: var(--space-sm);
  border-top: 1px solid var(--surface-border);
}

.available-label {
  font-size: 11px;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 1px;
  margin-bottom: var(--space-xs);
  display: block;
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-xs);
}

.available-tag {
  background: var(--ink-medium) !important;
  border: 1px solid var(--ink-subtle) !important;
  color: var(--text-muted) !important;
  border-radius: var(--radius-sm) !important;
  padding: 4px 10px !important;
  font-size: 12px !important;
  cursor: pointer !important;
  transition: all var(--transition-fast);
  display: inline-flex !important;
  align-items: center;
  gap: 4px;
}

.available-tag:hover {
  background: var(--gold-glow) !important;
  border-color: rgba(212, 168, 83, 0.3) !important;
  color: var(--gold) !important;
}

.add-icon {
  width: 12px;
  height: 12px;
  opacity: 0;
  transition: opacity var(--transition-fast);
}

.available-tag:hover .add-icon {
  opacity: 1;
}
</style>
