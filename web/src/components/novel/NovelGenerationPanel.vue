<template>
  <div class="novel-generation-panel">
    <div v-if="store.generation?.status === 'running' || store.generation?.status === 'pending'" class="gen-progress">
      <a-progress :percent="store.generation.progress" status="active" />
      <p>{{ store.generation.status === 'pending' ? '等待中...' : '生成中...' }}</p>
    </div>
    <template v-else>
      <a-form layout="vertical" size="small">
        <a-form-item label="版本方向">
          <a-select v-model:value="versionType" style="width: 100%">
            <a-select-option value="steady">稳健推进</a-select-option>
            <a-select-option value="conflict">强冲突</a-select-option>
            <a-select-option value="climax">爽点爆发</a-select-option>
            <a-select-option value="suspense">悬疑反转</a-select-option>
            <a-select-option value="romance">感情拉扯</a-select-option>
            <a-select-option value="polish">文风精修</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="用户指令">
          <a-textarea v-model:value="userInstruction" placeholder="可选：对本次生成的特殊要求..." :auto-size="{ minRows: 3, maxRows: 6 }" />
        </a-form-item>
        <a-button type="primary" block @click="handleGenerate">生成 3 个版本</a-button>
      </a-form>
    </template>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { message } from 'ant-design-vue'
import { useNovelsStore } from '../../stores/novels'

const store = useNovelsStore()
const versionType = ref('steady')
const userInstruction = ref('')

const handleGenerate = async () => {
  if (!store.currentChapter) {
    message.warning('请先选择章节')
    return
  }
  await store.startGeneration('chapter_version', {
    version_types: [versionType.value],
    user_instruction: userInstruction.value,
  })
}
</script>

<style scoped>
.novel-generation-panel {
  padding: 8px;
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
</style>
