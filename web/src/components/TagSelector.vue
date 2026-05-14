<template>
  <div>
    <div style="margin-bottom: 8px">
      <a-tag
        v-for="tag in selectedTags"
        :key="tag.id"
        closable
        color="success"
        @close="removeTag(tag.id)"
      >
        {{ tag.name }}
      </a-tag>
    </div>

    <a-input-group compact style="margin-bottom: 8px">
      <a-input
        v-model:value="newTagName"
        placeholder="输入标签名称"
        @keyup.enter="handleAddTag"
        style="width: calc(100% - 64px)"
      />
      <a-button type="primary" @click="handleAddTag">添加</a-button>
    </a-input-group>

    <div v-if="availableTags.length > 0">
      <span style="color: #999; font-size: 12px; margin-right: 8px">可用标签：</span>
      <a-tag
        v-for="tag in availableTags"
        :key="tag.id"
        style="cursor: pointer"
        @click="addTag(tag)"
      >
        {{ tag.name }}
      </a-tag>
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
