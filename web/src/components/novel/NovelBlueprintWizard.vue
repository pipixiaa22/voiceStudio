<template>
  <a-modal
    :open="props.open"
    @update:open="emit('update:open', $event)"
    title="AI 生成创作蓝图"
    ok-text="生成"
    cancel-text="取消"
    :confirm-loading="generating"
    @ok="handleGenerate"
    width="560px"
  >
    <a-form layout="vertical">
      <a-form-item label="一句话创意" required>
        <a-textarea v-model:value="premise" placeholder="描述你的小说核心创意..." :autoSize="{ minRows: 2, maxRows: 4 }" />
      </a-form-item>
    </a-form>
    <div v-if="generating" class="gen-status">
      <a-progress :percent="store.generation?.progress || 0" status="active" />
      <p>正在生成蓝图，请稍候...</p>
    </div>
  </a-modal>
</template>

<script setup>
import { ref } from 'vue'
import { message } from 'ant-design-vue'
import { useNovelsStore } from '../../stores/novels'

const props = defineProps({ open: Boolean })
const emit = defineEmits(['update:open'])
const store = useNovelsStore()
const premise = ref('')
const generating = ref(false)

const handleGenerate = async () => {
  if (!premise.value.trim()) {
    message.warning('请填写创意')
    return
  }
  generating.value = true
  try {
    await store.startGeneration('blueprint', { premise: premise.value })
    emit('update:open', false)
  } catch (e) {
    message.error('生成失败')
  } finally {
    generating.value = false
  }
}
</script>

<style scoped>
.gen-status { margin-top: 16px; text-align: center; }
</style>
