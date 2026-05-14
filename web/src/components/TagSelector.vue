<template>
  <div class="tag-selector">
    <div class="selected-tags">
      <span v-for="tag in selectedTags" :key="tag.id" class="tag">
        {{ tag.name }}
        <button @click="removeTag(tag.id)" class="tag-remove">×</button>
      </span>
    </div>
    <div class="tag-input">
      <input
        v-model="newTagName"
        placeholder="输入标签名称"
        @keyup.enter="handleAddTag"
      />
      <button @click="handleAddTag">添加</button>
    </div>
    <div class="available-tags">
      <span
        v-for="tag in availableTags"
        :key="tag.id"
        class="tag tag-available"
        @click="addTag(tag)"
      >
        {{ tag.name }}
      </span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
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
  const tag = await tagsStore.createTag({ name: newTagName.value })
  addTag(tag)
  newTagName.value = ''
}
</script>

<style scoped>
.tag-selector {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.selected-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}
.tag {
  display: inline-flex;
  align-items: center;
  background: #e8f5e9;
  color: #2e7d32;
  padding: 0.25rem 0.5rem;
  border-radius: 12px;
  font-size: 0.875rem;
}
.tag-remove {
  background: none;
  border: none;
  margin-left: 0.25rem;
  cursor: pointer;
  color: #2e7d32;
}
.tag-input {
  display: flex;
  gap: 0.5rem;
}
.tag-input input {
  flex: 1;
  padding: 0.25rem;
  border: 1px solid #ddd;
  border-radius: 4px;
}
.available-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}
.tag-available {
  background: #f5f5f5;
  color: #666;
  cursor: pointer;
}
.tag-available:hover {
  background: #e0e0e0;
}
</style>
