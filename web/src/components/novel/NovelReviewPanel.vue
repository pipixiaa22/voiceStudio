<template>
  <div class="novel-review-panel">
    <div v-if="!reviewResult" class="review-empty">
      <p>点击顶部"审稿"按钮开始一致性检查</p>
    </div>
    <template v-else>
      <div class="review-score">
        <a-progress type="circle" :percent="reviewResult.overall_score" :width="80" />
        <p>一致性评分</p>
      </div>
      <p class="review-summary">{{ reviewResult.summary }}</p>
      <a-list :data-source="reviewResult.issues" size="small">
        <template #renderItem="{ item }">
          <a-list-item>
            <a-list-item-meta>
              <template #title>
                <a-tag :color="severityColor(item.severity)">{{ item.severity }}</a-tag>
                <a-tag>{{ item.category }}</a-tag>
              </template>
              <template #description>
                <p>{{ item.description }}</p>
                <p class="suggestion">建议：{{ item.suggestion }}</p>
              </template>
            </a-list-item-meta>
          </a-list-item>
        </template>
      </a-list>
    </template>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useNovelsStore } from '../../stores/novels'
const store = useNovelsStore()

const reviewResult = computed(() => {
  if (store.generation?.generation_type === 'review' && store.generation?.result) {
    return store.generation.result
  }
  return null
})

const severityColor = (s) => ({ high: 'red', medium: 'orange', low: 'blue' }[s] || 'default')
</script>

<style scoped>
.novel-review-panel { padding: 8px; }
.review-empty { text-align: center; padding: 24px; color: var(--text-muted); }
.review-score { text-align: center; margin-bottom: 12px; }
.review-summary { font-size: 13px; margin-bottom: 12px; }
.suggestion { font-size: 12px; color: var(--text-muted); }
</style>
