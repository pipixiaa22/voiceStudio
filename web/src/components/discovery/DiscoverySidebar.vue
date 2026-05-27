<template>
  <aside class="discovery-sidebar">
    <section class="side-section">
      <div class="section-head">
        <span>关键词包</span>
      </div>
      <button
        v-for="keyword in keywords"
        :key="keyword"
        class="keyword-chip"
        type="button"
        @click="$emit('use-keyword', keyword)"
      >
        {{ keyword }}
      </button>
    </section>

    <section class="side-section">
      <div class="section-head">
        <span>历史查询</span>
        <small>{{ history.length }}</small>
      </div>
      <div v-if="history.length" class="history-list">
        <button
          v-for="entry in history"
          :key="entry.id"
          class="history-item"
          type="button"
          @click="$emit('restore-query', entry)"
        >
          <span>{{ entry.query }}</span>
          <small>{{ platformLabel(entry.platform) }} · {{ entry.resultCount }} 条</small>
        </button>
      </div>
      <div v-else class="empty-note">搜索一次后会出现在这里</div>
    </section>

    <section class="side-section">
      <div class="section-head">
        <span>收藏夹</span>
        <small>{{ favoriteCount }}</small>
      </div>
      <button
        class="filter-row"
        :class="{ active: favoriteOnly }"
        type="button"
        @click="$emit('toggle-favorite-filter', !favoriteOnly)"
      >
        <span>全部收藏</span>
        <small>{{ favoriteCount }}</small>
      </button>
      <button
        v-for="option in statusOptions"
        :key="option.value"
        class="filter-row"
        :class="{ active: statusFilter === option.value }"
        type="button"
        @click="$emit('set-status-filter', option.value)"
      >
        <span>{{ option.label }}</span>
        <small>{{ option.count }}</small>
      </button>
    </section>
  </aside>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  history: { type: Array, default: () => [] },
  favoriteCount: { type: Number, default: 0 },
  analyzedCount: { type: Number, default: 0 },
  scriptedCount: { type: Number, default: 0 },
  favoriteOnly: Boolean,
  statusFilter: { type: String, default: 'all' },
})

defineEmits(['use-keyword', 'restore-query', 'toggle-favorite-filter', 'set-status-filter'])

const keywords = ['修仙小说 一张图', '仙帝重生', '废柴逆袭', '宗门 天劫', '女帝 师尊', '系统流 小师妹']

const platformLabel = (platform) => {
  const labels = {
    all: '全部',
    youtube: 'YouTube',
    douyin: '抖音',
    kuaishou: '快手',
    bilibili: 'B 站',
  }
  return labels[platform] || platform
}

const statusOptions = computed(() => [
  { value: 'all', label: '全部样本', count: '' },
  { value: 'analyzed', label: '已分析', count: props.analyzedCount },
  { value: 'scripted', label: '已生成脚本', count: props.scriptedCount },
  { value: 'imported', label: '已导入文本', count: '' },
])
</script>

<style scoped>
.discovery-sidebar {
  background: var(--paper-soft);
  border-right: 1px solid var(--surface-border);
  padding: var(--space-md);
  overflow-y: auto;
}

.side-section + .side-section {
  margin-top: var(--space-lg);
}

.section-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-sm);
  color: var(--text-primary);
  font-size: 13px;
  font-weight: 650;
}

.section-head small {
  color: var(--text-subtle);
  font-weight: 500;
}

.keyword-chip,
.history-item,
.filter-row {
  width: 100%;
  border: 1px solid transparent;
  border-radius: var(--radius-md);
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  font-family: inherit;
  text-align: left;
  transition: background var(--transition-fast), border-color var(--transition-fast), color var(--transition-fast);
}

.keyword-chip {
  display: block;
  padding: 8px 10px;
  font-size: 13px;
}

.keyword-chip:hover,
.history-item:hover,
.filter-row:hover,
.filter-row.active {
  background: var(--surface);
  border-color: var(--surface-border);
  color: var(--text-primary);
}

.history-list {
  display: grid;
  gap: 4px;
}

.history-item {
  display: grid;
  gap: 3px;
  padding: 9px 10px;
}

.history-item span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
}

.history-item small,
.filter-row small,
.empty-note {
  color: var(--text-subtle);
  font-size: 11px;
}

.filter-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 9px 10px;
  font-size: 13px;
}

.empty-note {
  padding: 10px;
}
</style>
