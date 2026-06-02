<template>
  <div class="novel-memory-search">
    <a-input-search
      v-model:value="query"
      placeholder="输入章节目标或关键词，预览 RAG 召回结果"
      size="small"
      @search="handleSearch"
      :loading="searching"
    />
    <div v-if="store.memorySearchResults.length" class="search-results">
      <div v-for="(r, i) in store.memorySearchResults" :key="i" class="search-item">
        <div class="search-item-header">
          <a-tag :color="typeColor(r.memory_type)" size="small">{{ r.memory_type }}</a-tag>
          <span class="search-score">相关度: {{ Math.min(100, (r.score * 100)).toFixed(0) }}%</span>
        </div>
        <p class="search-item-content">{{ r.content }}</p>
      </div>
    </div>
    <a-empty v-else-if="searched" description="未找到相关记忆" />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { message } from 'ant-design-vue'
import { useNovelsStore } from '../../stores/novels'
import { typeColor } from '../../utils/memoryTypes'

const store = useNovelsStore()
const query = ref('')
const searching = ref(false)
const searched = ref(false)

const handleSearch = async () => {
  if (!query.value.trim() || !store.currentProject) return
  searching.value = true
  searched.value = true
  try {
    await store.searchMemories(store.currentProject.id, query.value)
  } catch {
    message.error('搜索失败')
  } finally {
    searching.value = false
  }
}
</script>

<style scoped>
.novel-memory-search { padding: 8px; }
.search-results { margin-top: 12px; }
.search-item { padding: 8px; border-bottom: 1px solid var(--surface-border); }
.search-item-header { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.search-score { font-size: 11px; color: var(--text-muted); }
.search-item-content { font-size: 12px; color: var(--text-secondary); margin: 0; }
</style>
