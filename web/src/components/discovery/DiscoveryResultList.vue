<template>
  <section class="result-panel">
    <div class="result-toolbar">
      <div>
        <strong>{{ loading ? '正在采集' : `${items.length} 条候选` }}</strong>
        <span>综合分接近时优先显示热度更高的样本</span>
      </div>
      <a-select :value="sortBy" size="small" class="sort-select" @change="$emit('sort', $event)">
        <a-select-option value="recommended">综合推荐</a-select-option>
        <a-select-option value="latest">最新</a-select-option>
        <a-select-option value="hot">热度</a-select-option>
        <a-select-option value="relevance">相关性</a-select-option>
      </a-select>
    </div>

    <div v-if="loading" class="skeleton-list">
      <a-skeleton v-for="index in 6" :key="index" active :paragraph="{ rows: 3 }" />
    </div>

    <div v-else-if="items.length" class="result-list">
      <DiscoveryResultItem
        v-for="item in items"
        :key="item.id"
        :item="item"
        :active="item.id === selectedId"
        @select="$emit('select', $event)"
        @favorite="$emit('favorite', $event)"
        @analyze="$emit('analyze', $event)"
      />
    </div>

    <div v-else class="empty-state">
      <h2>没有找到匹配样本</h2>
      <p>可以放宽时间范围、减少关键词，或使用手动链接导入。</p>
      <div class="empty-actions">
        <a-button @click="$emit('clear-filters')">清空筛选</a-button>
        <a-button type="primary" @click="$emit('try-keyword', '修仙小说 一张图')">试试：修仙小说 一张图</a-button>
      </div>
    </div>
  </section>
</template>

<script setup>
import DiscoveryResultItem from './DiscoveryResultItem.vue'

defineProps({
  items: { type: Array, default: () => [] },
  selectedId: { type: [String, Number], default: null },
  loading: Boolean,
  sortBy: { type: String, default: 'recommended' },
})

defineEmits(['select', 'favorite', 'analyze', 'sort', 'clear-filters', 'try-keyword'])
</script>

<style scoped>
.result-panel {
  min-width: 0;
  background: var(--paper-soft);
  border-right: 1px solid var(--surface-border);
  display: flex;
  flex-direction: column;
}

.result-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-md);
  min-height: 52px;
  padding: 0 var(--space-md);
  border-bottom: 1px solid var(--surface-border);
}

.result-toolbar strong {
  display: block;
  color: var(--text-primary);
  font-size: 13px;
  font-weight: 650;
}

.result-toolbar span {
  color: var(--text-subtle);
  font-size: 11px;
}

.sort-select {
  width: 112px;
}

.result-list,
.skeleton-list {
  display: grid;
  gap: var(--space-sm);
  padding: var(--space-sm);
  overflow-y: auto;
}

.empty-state {
  margin: auto;
  max-width: 360px;
  padding: var(--space-xl);
  text-align: center;
}

.empty-state h2 {
  margin: 0 0 8px;
  color: var(--text-primary);
  font-size: 18px;
}

.empty-state p {
  margin: 0;
  color: var(--text-muted);
  font-size: 13px;
  line-height: 1.7;
}

.empty-actions {
  display: flex;
  justify-content: center;
  gap: var(--space-sm);
  margin-top: var(--space-md);
  flex-wrap: wrap;
}
</style>
