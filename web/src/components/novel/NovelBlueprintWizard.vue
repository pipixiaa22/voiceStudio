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
      <a-form-item label="生成深度">
        <a-radio-group v-model:value="depth" button-style="solid">
          <a-radio-button value="quick">快速蓝图</a-radio-button>
          <a-radio-button value="standard">标准蓝图</a-radio-button>
          <a-radio-button value="deep">深度蓝图</a-radio-button>
        </a-radio-group>
        <div class="depth-hint">{{ depthHint }}</div>
      </a-form-item>
      <a-form-item label="章节节点数">
        <a-input-number v-model:value="outlineChapters" :min="3" :max="20" :step="1" style="width: 100%" />
      </a-form-item>
    </a-form>
    <div v-if="generating" class="gen-status">
      <a-progress :percent="store.generation?.progress || 0" status="active" />
      <p>正在生成蓝图，请稍候...</p>
    </div>
  </a-modal>
</template>

<script setup>
import { ref, computed } from 'vue'
import { message } from 'ant-design-vue'
import { useNovelsStore } from '../../stores/novels'

const props = defineProps({ open: Boolean })
const emit = defineEmits(['update:open'])
const store = useNovelsStore()
const premise = ref('')
const outlineChapters = ref(12)
const depth = ref('standard')
const depthHint = computed(() => {
  if (depth.value === 'quick') return '快速探索创意：少量角色和事件，1卷骨架'
  if (depth.value === 'deep') return '完整世界构建：详细角色、事件、伏笔、道具和记忆种子'
  return '平衡模式：多卷骨架 + 当前卷详细章纲'
})
const generating = ref(false)

const handleGenerate = async () => {
  if (!premise.value.trim()) {
    message.warning('请填写创意')
    return
  }
  generating.value = true
  try {
    await store.startGeneration('blueprint', {
      premise: premise.value,
      outline_chapters: outlineChapters.value,
      depth: depth.value,
    })
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
.depth-hint { margin-top: 4px; font-size: 12px; color: var(--text-muted); }
</style>
